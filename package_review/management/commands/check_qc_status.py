from django.conf import settings
from django.core.management.base import BaseCommand

from package_review.clients import AWSClient


class Command(BaseCommand):
    help = "Sends a messaage if QC is complete"

    def handle(self, *args, **options):
        s3_client = AWSClient('s3', settings.AWS['role_arn'])
        sns_client = AWSClient('sns', settings.AWS['role_arn'])

        response = s3_client.client.list_objects_v2(
            Bucket=settings.AWS['bucket'],
            MaxKeys=1)

        if 'Contents' not in response:
            sns_client.deliver_message(
                settings.AWS['sns_topic'],
                None,
                'No packages left to QC',
                'COMPLETE')

        self.stdout.write(self.style.SUCCESS("Status check complete"))
