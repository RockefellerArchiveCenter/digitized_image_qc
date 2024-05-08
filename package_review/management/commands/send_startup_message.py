from django.conf import settings
from django.core.management.base import BaseCommand

from package_review.clients import AWSClient


class Command(BaseCommand):
    help = "Sends a messaage when app starts"

    def handle(self, *args, **options):
        sns_client = AWSClient('sns', settings.AWS['role_arn'])

        sns_client.deliver_message(
            settings.AWS['sns_topic'],
            None,
            'Packages are waiting to be QCed',
            'STARTED')
