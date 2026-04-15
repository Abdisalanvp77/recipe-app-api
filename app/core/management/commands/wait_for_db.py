"""_summary_ Django command to wait for database
to be available before connecting to prevent race condition
and errors in developmnet and production
"""
import time
from psycopg2 import OperationalError as Psycopg2Error
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """_summary_ Test commands
    Args:
        BaseCommand (_type_): _description_
        Base class for management commands
    """
    help = "Wait for database to be available"

    def handle(self, *args, **options):
        """Entry point for the command"""
        self.stdout.write("Waiting for database...")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except (Psycopg2Error, OperationalError):
                self.stdout.write("Database unavailable, waiting 1 second...")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("Database available!"))
