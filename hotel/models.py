from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


# --------------------
# CUSTOM USER MODEL
# --------------------

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"


# --------------------
# HOTEL MODEL
# --------------------

class Hotel(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Kenya")
    postal_code = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    check_in_time = models.TimeField(default='14:00')
    check_out_time = models.TimeField(default='12:00')
    amenities = models.JSONField(default=list, blank=True)  # e.g., ["pool", "wifi", "gym"]
    images = models.JSONField(default=list, blank=True)  # URLs to hotel images
    
    def __str__(self):
        return self.name


# --------------------
# ROOM TYPE MODEL
# --------------------

class RoomType(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="room_types")
    name = models.CharField(max_length=100)  # e.g., "Deluxe King Suite"
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    amenities = models.JSONField(default=list, blank=True)
    size_sqft = models.IntegerField(blank=True, null=True)
    images = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.hotel.name} - {self.name}"


# --------------------
# ROOM MODEL
# --------------------

class Room(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('MAINTENANCE', 'Under Maintenance'),
        ('CLEANING', 'Cleaning'),
    ]

    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name="rooms")
    room_number = models.CharField(max_length=10)
    floor = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['room_type', 'room_number']

    def __str__(self):
        return f"{self.room_number} - {self.room_type.name}"

    @property
    def price_per_night(self):
        return self.room_type.base_price


# --------------------
# CUSTOMER PROFILE MODEL
# --------------------

class CustomerProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="customer_profile")
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female')
    ]
    
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    identification_number = models.CharField(max_length=50, blank=True)
    preferences = models.JSONField(default=dict, blank=True)  # e.g., {"smoking": False, "accessible": True}

    def __str__(self):
        return f"Customer: {self.user.get_full_name()}"


# --------------------
# STAFF PROFILE MODEL
# --------------------

class StaffProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="staff_profile")
    
    ROLE_CHOICES = [
        ('Manager', 'Manager'),
        ('Receptionist', 'Receptionist'),
        ('Housekeeping', 'Housekeeping'),
        ('Chef', 'Chef'),
        ('Maintenance', 'Maintenance'),
        ('Other', 'Other'),
    ]
    
    EMPLOYMENT_STATUS = [
        ('Active', 'Active'),
        ('On Leave', 'On leave'),
        ('Terminated', 'Terminated'),
    ]

    gender = models.CharField(max_length=10, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ])
    date_of_birth = models.DateField()
    contact_phone = models.CharField(max_length=20)
    emergency_contact = models.CharField(max_length=100)
    address = models.TextField()
    
    staff_role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    date_of_employment = models.DateField()
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default='Active')
    department = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.staff_role})"


# --------------------
# BOOKING MODEL
# --------------------

class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CHECKED_IN', 'Checked In'),
        ('CHECKED_OUT', 'Checked Out'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # Public facing ID
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="bookings", null = True, blank = True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)
    special_requests = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track who created the booking (staff or customer)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="created_bookings")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.id} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Calculate total amount before saving
        if not self.total_amount and self.room and self.check_in_date and self.check_out_date:
            nights = (self.check_out_date - self.check_in_date).days
            if nights > 0:
                self.total_amount = nights * self.room.price_per_night
        super().save(*args, **kwargs)

    @property
    def total_guests(self):
        return self.adults + self.children

    @property
    def total_nights(self):
        if self.check_in_date and self.check_out_date:
            return (self.check_out_date - self.check_in_date).days
        return 0


# --------------------
# PAYMENT MODEL
# --------------------

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('MPESA', 'M-Pesa'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
        ('CANCELLED', 'Cancelled'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null = True, blank = True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True)  # From payment gateway
    reference = models.CharField(max_length=100, blank=True, null = True)  # Internal reference
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id or self.id} - {self.amount}"

    def save(self, *args, **kwargs):
        # Auto-set paid_at when status changes to COMPLETED
        if self.status == 'COMPLETED' and not self.paid_at:
            from django.utils import timezone
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)


# --------------------
# REVIEW MODEL
# --------------------

class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reviews")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'booking']

    def __str__(self):
        return f"Review by {self.user.get_full_name()} - {self.rating} stars"