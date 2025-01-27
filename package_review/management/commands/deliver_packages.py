import logging
from os import getenv
from pathlib import Path
from shutil import copytree, rmtree

from django.conf import settings
from django.core.management.base import BaseCommand

from package_review.models import Package

logging.basicConfig(
    level=int(getenv('LOGGING_LEVEL', logging.INFO)),
    format='%(filename)s::%(funcName)s::%(lineno)s %(message)s')


class Command(BaseCommand):
    help = "Delivers approved packages."

    PID_FILE_PATH = Path("pid_file.txt")

    def _is_running(self):
        """Checks to see if this process is already running."""
        return self.PID_FILE_PATH.is_file()

    def _set_is_running(self, is_running):
        """Handles change in process status"""
        if is_running:
            self.PID_FILE_PATH.touch()
        else:
            self.PID_FILE_PATH.unlink()

    def move_files(self, package):
        """Moves files to packaging directory."""
        bag_dir = Path(settings.BASE_STORAGE_DIR, package.refid)
        new_path = Path(settings.BASE_DESTINATION_DIR, package.refid)
        copytree(bag_dir, new_path)
        rmtree(bag_dir)

    def handle(self, *args, **options):
        if not settings.BASE_STORAGE_DIR.is_dir():
            self.stdout.write(self.style.ERROR(f'Root directory {str(settings.BASE_DESTINATION_DIR)} for to be delivered to does not exist.'))
            exit()
        if not self._is_running():
            self._set_is_running(True)

            for package in Package.objects.filter(process_status=Package.APPROVED):
                try:
                    self.move_files(package)
                    message = f'Package {package.refid} delivered.'
                    self.stdout.write(self.style.SUCCESS(message))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(str(e)))

            self._set_is_running(False)
