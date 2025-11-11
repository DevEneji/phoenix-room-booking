# Serializers convert model data into JSON and validate API input.

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.utils.translation import gettext as _
from django.utils import timezone

from .models import (
    CustomUser, Hotel, RoomType, Room, CustomerProfile, 
    StaffProfile, Booking, Payment, Review
)


# --------------------
# USER & AUTHENTICATION SERIALIZERS
# --------------------

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number']
        read_only_fields = ['id', 'role']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(
        choices = CustomUser.ROLE_CHOICES,
        required = False,
        default = 'customer'
    )
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone_number', 'role']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Role permission validation
        request = self.context.get('request')
        requested_role = data.get('role', 'customer')

        # Staff can create customers and other staff
        if requested_role in ['staff', 'admin']:
            if not request or not request.user.is_authenticated:
                raise serializers.ValidationError(
                    "Authentication required to create staff/admin accounts."
                )
            if request.user.role not in ['staff', 'admin']:
                raise serializers.ValidationError(
                    "Only staff or admin can create staff/admin accounts"
                )
            if requested_role == 'admin' and request.user.role != 'admin':
                raise serializers.ValidationError(
                    "Only admin users can create admin accounts."
                )
            
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        role = validated_data.pop('role', 'customer')

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role = role
        )

        # Send OTP for email verification
        user.send_verification_email()

        Token.objects.create(user=user)
        return user
    
class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length = 6)

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        help_text="The username of the user.",
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        help_text="The user's password.",
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError(_("Invalid username or password"))
        
        attrs["user"] = user
        return attrs


# --------------------
# PROFILE SERIALIZERS
# --------------------

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = ['id', 'user', 'gender', 'nationality', 'identification_number', 'preferences']

class StaffProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role__in=['staff', 'admin']),
        source='user',
        write_only=True,
        required=False
    )

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'user_id', 'gender', 'date_of_birth', 'contact_phone',
            'emergency_contact', 'address', 'staff_role', 'date_of_employment',
            'employment_status', 'department', 'salary'
        ]


# --------------------
# HOTEL & ROOM SERIALIZERS
# --------------------

class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = [
            'id', 'name', 'description', 'address', 'city', 'state', 'country',
            'postal_code', 'phone_number', 'email', 'check_in_time', 'check_out_time',
            'amenities', 'images'
        ]

class RoomTypeSerializer(serializers.ModelSerializer):
    hotel = HotelSerializer(read_only=True)
    hotel_id = serializers.PrimaryKeyRelatedField(
        queryset=Hotel.objects.all(),
        source='hotel',
        write_only=True
    )
    
    class Meta:
        model = RoomType
        fields = [
            'id', 'hotel', 'hotel_id', 'name', 'description', 'base_price',
            'capacity', 'amenities', 'size_sqft', 'images'
        ]

class RoomSerializer(serializers.ModelSerializer):
    room_type = RoomTypeSerializer(read_only=True)
    room_type_id = serializers.PrimaryKeyRelatedField(
        queryset=RoomType.objects.all(),
        source='room_type',
        write_only=True
    )
    price_per_night = serializers.DecimalField(
        source='room_type.base_price', 
        read_only=True, 
        max_digits=8, 
        decimal_places=2
    )
    
    class Meta:
        model = Room
        fields = [
            'id', 'room_type', 'room_type_id', 'room_number', 'floor',
            'status', 'is_active', 'price_per_night'
        ]
        read_only_fields = ['price_per_night']


# --------------------
# BOOKING & PAYMENT SERIALIZERS
# --------------------

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    room = RoomSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='user',
        write_only=True,
        required=False
    )
    room_id = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.filter(is_active=True, status='AVAILABLE'),
        source='room',
        write_only=True
    )
    total_nights = serializers.IntegerField(read_only=True)
    total_guests = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'user_id', 'room', 'room_id', 'check_in_date', 'check_out_date',
            'adults', 'children', 'total_guests', 'special_requests', 'status',
            'total_amount', 'total_nights', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'total_amount', 'total_nights', 'total_guests', 'created_at', 'updated_at']
    
    def validate(self, data):
        check_in = data.get('check_in_date')
        check_out = data.get('check_out_date')
        room = data.get('room')
        adults = data.get('adults', 1)
        children = data.get('children', 0)
        
        if check_in and check_out:
            if check_in >= check_out:
                raise serializers.ValidationError("Check-out date must be after check-in date.")
            
            if (check_out - check_in).days < 1:
                raise serializers.ValidationError("Stay must be at least one night.")
        
        if room:
            # Check room capacity
            total_guests = adults + children
            if total_guests > room.room_type.capacity:
                raise serializers.ValidationError(
                    f"Room capacity exceeded. Maximum {room.room_type.capacity} guests allowed."
                )
            
            # Check room availability for dates
            if check_in and check_out:
                conflicting_bookings = Booking.objects.filter(
                    room=room,
                    check_in_date__lt=check_out,
                    check_out_date__gt=check_in,
                    status__in=['CONFIRMED', 'CHECKED_IN', 'PENDING']
                ).exclude(id=self.instance.id if self.instance else None)
                
                if conflicting_bookings.exists():
                    raise serializers.ValidationError("Room is not available for the selected dates.")
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            if 'user' not in validated_data:
                validated_data['user'] = request.user
        
        return super().create(validated_data)

class PaymentSerializer(serializers.ModelSerializer):
    booking = BookingSerializer(read_only=True)
    booking_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.all(),
        source='booking',
        write_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'booking_id', 'amount', 'payment_method', 'status',
            'transaction_id', 'reference', 'paid_at', 'created_at'
        ]
        read_only_fields = ['paid_at', 'created_at']
    
    def validate(self, data):
        booking = data.get('booking')
        amount = data.get('amount')
        
        if booking and amount:
            if amount != booking.total_amount:
                raise serializers.ValidationError(
                    f"Payment amount must match booking total: {booking.total_amount}"
                )
        
        return data


# --------------------
# REVIEW SERIALIZER
# --------------------

class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    booking = BookingSerializer(read_only=True)
    booking_id = serializers.PrimaryKeyRelatedField(
        queryset=Booking.objects.filter(status='CHECKED_OUT'),
        source='booking',
        write_only=True
    )
    
    class Meta:
        model = Review
        fields = [
            'id', 'user', 'booking', 'booking_id', 'rating', 'comment',
            'created_at', 'is_approved'
        ]
        read_only_fields = ['user', 'created_at', 'is_approved']
    
    def validate(self, data):
        request = self.context.get('request')
        booking = data.get('booking')
        
        if request and booking:
            # Ensure user can only review their own bookings
            if booking.user != request.user:
                raise serializers.ValidationError("You can only review your own bookings.")
            
            # Check if review already exists for this booking
            if Review.objects.filter(booking=booking, user=request.user).exists():
                raise serializers.ValidationError("You have already reviewed this booking.")
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return super().create(validated_data)


# --------------------
# AVAILABILITY SERIALIZER
# --------------------

class AvailabilitySerializer(serializers.Serializer):
    check_in = serializers.DateField(required=True)
    check_out = serializers.DateField(required=True)
    adults = serializers.IntegerField(min_value=1, max_value=10, default=1)
    children = serializers.IntegerField(min_value=0, max_value=10, default=0)
    hotel_id = serializers.IntegerField(required=False)
    
    def validate(self, data):
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        
        if check_in and check_out:
            if check_in >= check_out:
                raise serializers.ValidationError("Check-out date must be after check-in date.")
            
            if check_in < timezone.now().date():
                raise serializers.ValidationError("Check-in date cannot be in the past.")
        
        total_guests = data.get('adults', 1) + data.get('children', 0)
        if total_guests > 10:
            raise serializers.ValidationError("Maximum 10 guests allowed per booking.")
        
        return data


# --------------------
# LEGACY SERIALIZERS (for backward compatibility during migration)
# --------------------

class LegacyRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class LegacyBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

class LegacyPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'booking', 'amount', 'is_paid', 'payment_date', 'method', 'reference']
        read_only_fields = ['payment_date']

    def validate(self, data):
        booking = data.get('booking')
        if booking and booking.is_confirmed and data.get('is_paid'):
            raise serializers.ValidationError("This booking is already confirmed and paid.")
        return data

class LegacyStaffSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='user',
        write_only=True,
        required=False
    )

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'user_id', 'gender', 'date_of_birth', 'contact_phone',
            'emergency_contact', 'address', 'staff_role', 'date_of_employment',
            'employment_status', 'is_active'
        ]