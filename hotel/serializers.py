# Serializers convert model data into JSON and validat API input.

from rest_framework import serializers
from .models import Room, Booking, Payment, RoomType
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.utils.translation import gettext as _


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["room_number", "is_available"]

class RoomTypeSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = ["id", "name", "description", "price_per_night", "capacity", "beds", "rooms"]

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id','booking','amount','is_paid','payment_date', 'method','reference']
        read_only_fields = ['payment_date']

    def validate(self, data):
        booking = data.get('booking')
        if booking and booking.is_confirmed and data.get('is_paid'):
            raise serializers.ValidationError("This booking is already confirmed and paid.")
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username = validated_data['username'],
            email = validated_data.get('email'),
            password = validated_data['password']
        )
        Token.objects.create(user = user)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        help_text = "The username of the user.",
    )
    password = serializers.CharField(
        required = True,
        write_only = True,
        help_text = "The user's password.",
        style = {'input_type': 'password'}
    )

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(username = username, password = password)
        if not user:
            raise serializers.ValidationError(_("Invalid username or password"))
        
        attrs["user"] = user
        return attrs