from django.core.management.base import BaseCommand
from canteen_app.models import UserProfile

class Command(BaseCommand):
    help = 'List all RFID cards registered in the database'

    def handle(self, *args, **options):
        profiles = UserProfile.objects.filter(rfid_id__isnull=False).exclude(rfid_id='')
        
        if not profiles:
            self.stdout.write(self.style.WARNING('No RFID cards found in the database.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Found {profiles.count()} RFID cards:'))
        
        for profile in profiles:
            self.stdout.write(f'User: {profile.user.username}, RFID ID: {profile.rfid_id}, Role: {profile.role}') 