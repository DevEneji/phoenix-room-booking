# Serializers convert model data into JSON and validat API input.

from rest_framework import serializers
from .models import Room, Booking, Payment

class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'

class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id','booking','amount','is_paid','payment_date']
        read_only_fields = ['paid_at','created_at']

    def validate(self, data):
        booking = data.get('booking')
        if booking and booking.status == booking.BookingStatus.CANCELLED:
            raise serializers.ValidationError("Cannot pay for a cancelled booking.")
        return data
