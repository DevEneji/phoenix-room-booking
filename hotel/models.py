# Core database models for Rooms, Bookings, and Payments.

from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Room(models.Model):
    # Hotel room with type and price
    ROOM_TYPES = [
        ('SINGLE', 'Single Room'),
        ('DOUBLE', 'Double Room'),
        ('SUITE', 'Suite'),
        ('DELUXE', 'Deluxe Room'),
    ]
    
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('MAINTENANCE', 'Under Maintenance'),
    ]

    room_number = models.CharField(max_length=10, unique = True)
    room_type = models.CharField(max_length = 20, choices = ROOM_TYPES)
    status = models.CharField(max_length=20, choices = STATUS_CHOICES, default = 'AVAILABLE')
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.IntegerField()
    description = models.TextField(blank = True)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.room_number} - ${self.room_type} - ${self.price_per_night}"

class Staff(models.Model):
    # Link to django's built-in User model for login/authentication
    user = models.OneToOneField(User, on_delete = models.CASCADE)

     # Staff-specific information
    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=10, choices = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    date_of_birth = models.DateField()
    contact_details = models.CharField(max_length=100)# Could be phone or email
    address = models.TextField()
    emergency_contact = models.CharField(max_length = 100)

    # Job details
    role = models.CharField(max_length=50, choices = [
        ('Manager', 'Manager'),
        ('Receptionist', 'Receptionist'),
        ('Cleaner', 'Cleaner'),
        ('Chef', 'Chef'),
        ('Other', 'Other'),
    ])
    date_of_employment = models.DateField()
    employment_status = models.CharField(max_length=20, choices = [
        ('Active', 'Active'),
        ('On leave', 'On leave'),
        ('Retired', 'Retired'),
        ('Terminated', 'Terminated'),
    ])

    # Active status (instead of deleting staff)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"
    
class Customer(models.Model):
    # Basic information
    full_name = models.CharField(max_length = 150)
    gender = models.CharField(max_length = 10, choices = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ])
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length = 100)

    # Contact details
    phone_number = models.CharField(max_length = 20, unique = True)
    email = models.EmailField(unique = True)
    home_address = models.TextField()

    # Record management
    is_active = models.BooleanField(default = True) # mark inactive instead of del

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

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

    # Link booking to receptionist (staff member who created it)
    created_by = models.ForeignKey(
        Staff,
        on_delete=models.SET_NULL,
        null = True,
        blank = True,
        related_name = "bookings"
    )
    # Link customer to bookings
    customer = models.ForeignKey(
        Customer,
        on_delete = models.CASCADE,
        related_name = "bookings"
    )

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


