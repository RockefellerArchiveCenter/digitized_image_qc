import logging
import traceback
from os import getenv

from django.conf import settings
from django.core.management.base import BaseCommand

from package_review.clients import ArchivesSpaceClient, AWSClient
from package_review.helpers import get_config
from package_review.models import Package

logging.basicConfig(
    level=int(getenv('LOGGING_LEVEL', logging.INFO)),
    format='%(filename)s::%(funcName)s::%(lineno)s %(message)s')


class Command(BaseCommand):
    help = "Discovers new packages to be QCed."

    def add_arguments(self, parser):
        parser.add_argument("refid")

    def handle(self, *args, **options):
        configuration = get_config(f"/{getenv('ENV')}/{getenv('APP_CONFIG_PATH')}")

        client = ArchivesSpaceClient(
            baseurl=configuration.get('AS_BASEURL'),
            username=configuration.get('AS_USERNAME'),
            password=configuration.get('AS_PASSWORD'),
            repository=configuration.get('AS_REPO'))

        refid = options['refid']
        try:
            title, uri, resource_title, resource_uri, undated_object, already_digitized = client.get_package_data(refid)
            Package.objects.create(
                title=title,
                uri=uri,
                resource_title=resource_title,
                resource_uri=resource_uri,
                undated_object=undated_object,
                already_digitized=already_digitized,
                refid=refid,
                process_status=Package.PENDING)
            message = f'Package created: {refid}'
            self.stdout.write(self.style.SUCCESS(message))
        except Exception as e:
            logging.exception(e)
            exception = "\n".join(traceback.format_exception(e))
            sns_client = AWSClient('sns', settings.AWS['role_arn'])
            sns_client.deliver_message(
                settings.AWS['sns_topic'],
                None,
                f'Error discovering refid {refid}',
                'FAILURE',
                traceback=exception)
            message = f'Error creating packages: {e}'
            self.stdout.write(self.style.ERROR(message))
