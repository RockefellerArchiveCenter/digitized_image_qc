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
        parser.add_argument("package_id")
        parser.add_argument("source_filename")

    def handle(self, *args, **options):
        configuration = get_config(f"/{getenv('ENV')}/{getenv('APP_CONFIG_PATH')}")

        client = ArchivesSpaceClient(
            baseurl=configuration.get('AS_BASEURL'),
            username=configuration.get('AS_USERNAME'),
            password=configuration.get('AS_PASSWORD'),
            repository=configuration.get('AS_REPO'))

        s3_client = AWSClient('s3', settings.AWS['role_arn'])

        refid = options['refid']
        package_id = options['package_id']
        source_filename = options['source_filename']
        try:
            title, uri, resource_title, resource_uri, undated_object, already_digitized, reel_box = client.get_package_data(refid)
            size = s3_client.calculate_package_size(package_id)
            Package.objects.create(
                title=title,
                uri=uri,
                resource_title=resource_title,
                resource_uri=resource_uri,
                undated_object=undated_object,
                already_digitized=already_digitized,
                package_id=package_id,
                reel_box=reel_box,
                refid=refid,
                size_bytes=size,
                source_filename=source_filename,
                process_status=Package.PENDING)
            message = f'Package created: {package_id}'
            self.stdout.write(self.style.SUCCESS(message))
        except Exception as e:
            logging.exception(e)
            exception = "\n".join(traceback.format_exception(e))
            sns_client = AWSClient('sns', settings.AWS['role_arn'])
            sns_client.deliver_message(
                settings.AWS['sns_topic'],
                None,
                f'Error discovering package with {refid} and package_id {package_id}',
                'FAILURE',
                traceback=exception)
            message = f'Error creating packages: {e}'
            self.stdout.write(self.style.ERROR(message))
