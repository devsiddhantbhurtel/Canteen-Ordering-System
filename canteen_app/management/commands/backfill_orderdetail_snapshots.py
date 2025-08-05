from django.core.management.base import BaseCommand
from canteen_app.models import OrderDetail

class Command(BaseCommand):
    help = 'Backfill food_item_name and food_item_price for existing OrderDetail records.'

    def handle(self, *args, **options):
        updated = 0
        for od in OrderDetail.objects.all():
            if od.food_item and (not od.food_item_name or not od.food_item_price):
                od.food_item_name = od.food_item.name
                od.food_item_price = od.food_item.price
                od.save()
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} OrderDetail records.'))
