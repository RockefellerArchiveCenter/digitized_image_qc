import logging
from os import getenv

from django.conf import settings
from django.core.management.base import BaseCommand

from package_review.models import Package

logging.basicConfig(
    level=int(getenv('LOGGING_LEVEL', logging.INFO)),
    format='%(filename)s::%(funcName)s::%(lineno)s %(message)s')


class Command(BaseCommand):
    """
    This command is designed to clean up erroneously created packages,
    and should not need to be run regularly. It should only be run
    once when the service is first started.
    """

    help = "Removes packages which have already been approved."

    def handle(self, *args, **options):
        if not settings.BASE_STORAGE_DIR.is_dir():
            self.stdout.write(self.style.ERROR(f'Root directory {str(settings.BASE_STORAGE_DIR)} for files waiting to be QCed does not exist.'))
            exit()
        deleted_list = []
        for package in Package.objects.filter(process_status=Package.PENDING):
            if not (settings.BASE_STORAGE_DIR / package.refid).exists():
                package.delete()
                deleted_list.append(package.refid)

        message = f'Packages deleted: {", ".join(deleted_list)}' if len(deleted_list) else 'No approved packages to delete.'
        self.stdout.write(self.style.SUCCESS(message))
