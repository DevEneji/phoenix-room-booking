# hotel/management/commands/seed_rooms.py
# ---------------------------------------
# Custom management command to pre-populate demo rooms.

from django.core.management.base import BaseCommand
from hotel.models import Room

class Command(BaseCommand):
    help = 'Seed the database with demo rooms'

    def handle(self, *args, **kwargs):
        rooms = [
            {"number": "101", "room_type": "Single", "capacity": 1, "price_per_night": 100},
            {"number": "102", "room_type": "Double", "capacity": 2, "price_per_night": 150},
            {"number": "201", "room_type": "Suite", "capacity": 4, "price_per_night": 300},
        ]
        for room_data in rooms:
            Room.objects.get_or_create(**room_data)
            self.stdout.write(self.style.SUCCESS('Successfully added room %s' % room_data["number"]))