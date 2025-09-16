# Core database models for Rooms, Bookings, and Payments.

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Room(models.Model):
    # Hotel room with capacity and price
    number = models.CharField(max_length = 10, unique = True)
    room_type = models.CharField(max_length = 50) # e.g., Single, Double, Suite
    capacity = models.IntegerField()
    price_per_night = models.DecimalField(max_digits = 10, decimal_places = 2)
    is_available = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.room_type} - ${self.price_per_night}"

class Booking(models.Model):
    # Represents a reservation for a room by a user
    full_name = models.CharField(max_length=200, default="Unkown Guest")
    email = models.EmailField(default="johndoe@email.com")
    phone = models.CharField(max_length=20, blank=True, null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    check_in = models.DateField()
    check_out = models.DateField()
    created_at = models.DateTimeField(auto_now_add = True)
    guests = models.PositiveIntegerField(default=1)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Booking by {self.full_name} for Room {self.room.number}"
    
    @property
    def total_price(self):
        """Calculate price based on number of nights × room price."""
        nights = (self.check_out - self.check_in).days
        return nights * self.room.price_per_night if nights > 0 else self.room.price_per_night
    
class Payment(models.Model):
    # Tracks payment for a booking
    booking = models.OneToOneField(Booking, on_delete = models.CASCADE)
    amount = models.DecimalField(max_digits = 10, decimal_places= 2)
    is_paid = models.BooleanField(default = False)
    payment_date = models.DateTimeField(auto_now_add = True)
    method = models.CharField(max_length=20, blank=True, null=True)
    reference = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"payment for {self.booking} - {'Paid' if self.is_paid else 'Pending'}"