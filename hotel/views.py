# Clean API Views for Phoenix Hotel

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import os
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import Room, Booking, Payment, Staff
from .serializers import (
    RoomSerializer,
    BookingSerializer,
    PaymentSerializer,
    RegisterSerializer,
    UserSerializer,
    LoginSerializer,
    StaffSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiTypes


# --------------------
# ROOM VIEWS
# --------------------

class RoomListAPIView(APIView):
    serializer_class = RoomSerializer
    """List all active rooms or create a new room."""
    def get(self, request):
        rooms = Room.objects.all()
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoomDetailAPIView(APIView):
    serializer_class = RoomSerializer
    """Retrieve, update, or soft-delete a room."""
    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk, is_active=True)
        serializer = RoomSerializer(room)
        return Response(serializer.data)
    
    def put(self, request, pk):
        room = get_object_or_404(Room, pk=pk, is_active=True)
        serializer = RoomSerializer(room, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        room = get_object_or_404(Room, pk=pk, is_active=True)
        room.is_active = False
        room.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AvailableRoomsAPIView(APIView):
    serializer_class = RoomSerializer
    """Filter available rooms by type or price."""
    def get(self, request):
        room_type = request.GET.get('room_type')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')

        rooms = Room.objects.filter(status='Available', is_active=True)

        if room_type:
            rooms = rooms.filter(room_type=room_type)
        if min_price:
            rooms = rooms.filter(price_per_night__gte=min_price)
        if max_price:
            rooms = rooms.filter(price_per_night__lte=max_price)

        serializer = RoomSerializer(rooms, many=True)
        return Response({'count': rooms.count(), 'rooms': serializer.data})


class UpdateRoomStatusAPIView(APIView):
    serializer_class = RoomSerializer
    """Patch endpoint to update room availability status."""
    def patch(self, request, pk):
        room = get_object_or_404(Room, pk=pk, is_active=True)
        new_status = request.data.get('status')

        valid_statuses = [choice[0] for choice in Room.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Status must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        room.status = new_status
        room.save()
        return Response(RoomSerializer(room).data)


# --------------------
# BOOKING VIEWS
# --------------------

class BookingListCreateAPIView(APIView):
    serializer_class = BookingSerializer
    """
    Handles:
    - Get /bookings/ → list all bookings
    - POST /bookings/ → create a new booking
    """

    def get(self, request):
        # get booking objects
        bookings = Booking.objects.all()
        # pass them through the serializer
        serializer = BookingSerializer(bookings, many = True)
        # return the serialized data
        return Response(serializer.data)
    
    def post(self, request):
        # pass data through serializer
        serializer = BookingSerializer(data = request.data)
        # check if data is valid, if valid return serializer data and status 201
        if serializer.is_valid():
            booking = serializer.save()             # save serializer
            booking.room.is_available = False       # mark room as unavailable
            booking.room.save()
            return Response(serializer.data, status = status.HTTP_201_CREATED)
        # return serializer.errors and 400 status
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

class BookingDetailAPIView(APIView):
    serializer_class = BookingSerializer
    """
    Handles:
    - GET /bookings/<id>/ → retrieve booking
    - PUT /bookings/<id>/ → update booking
    - DELETE /bookings/<id>/ → delete booking
    """

    def get_object(self, pk):
        return get_object_or_404(Booking, pk = pk)
    
    def get(self, request, pk):
        booking = self.get_object(pk)       # get booking object
        serializer = BookingSerializer(booking, data = request.data)        # pass it through a serializer
        # return the serialized data
        return Response(serializer.data)
    
    def put(self, request, pk):
        booking = self.get_object(pk)       # get booking object
        serializer = BookingSerializer(booking, data = request.data)        # pass it through a serializer
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    
    def delete (self, request, pk):
        booking = self.get_object(pk)
        booking.delete()
        return Response(status = status.HTTP_204_NO_CONTENT)

class BookingConfirmAPIView(APIView):
    serializer_class = BookingSerializer
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.is_confirmed = True
        booking.save()
        return Response({'status': 'Booking confirmed'})
    
class BookingCancelAPIView(APIView):
    serializer_class = BookingSerializer
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.delete()
        return Response({'status': 'Booking canceled'})


class StaffAPIView(APIView):
    """
    API endpoint for listing, creating, and managing staff records.
    """

    permission_classes = [AllowAny]
    """Retrieve all staff or a single staff member by ID."""
    def get(self, request, pk = None):
        if pk:
            staff = get_object_or_404(Staff, pk = pk, is_active = True)
            serializer = StaffSerializer(staff)
            return Response(serializer.data, status = status.HTTP_200_OK)
        else:
            staff = Staff.objects.filter(is_active = True)
            serializer = StaffSerializer(staff, many = True)
            return Response(serializer.data, status = status.HTTP_200_OK)
        
    def post(self, request):
        """Create a new staff record."""
        serializer = StaffSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        """Update an existing staff record."""
        staff = get_object_or_404(Staff, pk = pk, is_active = True)
        serializer = StaffSerializer(staff, data = request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status = status.HTTP_200_OK)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        """Soft-delete a staff member by marking them inactive"""
        staff = get_object_or_404(Staff, pk = pk)
        staff.is_active = False
        staff.save()
        return Response({"message": "Staff member deactivated successfully."}, status=status.HTTP_204_NO_CONTENT)
    

# --------------------
# PAYMENT VIEWS
# --------------------

class PaymentListCreateAPIView(APIView):
    serializer_class = PaymentSerializer
    """
    Handles:
    - GET /payments/ → list all payments
    - POST /payments/ → create a payment and save a record
    """

    def get(self, request):
        payments = Payment.objects.all()                            # get all payment objects
        serializer = PaymentSerializer(payments, many = True)       # pass them through a serializer
        return Response(serializer.data)                            # return serialized data
    
    def post(self, request):
        serializer = PaymentSerializer(data = request.data)     # pass the written data through a serializer for proper ordering 
        if serializer.is_valid():                   # check for validity of serialized data
            payment = serializer.save()             # save serialized data
            self._save_payment_record(payment)      # create text file or record of payment

            # If payment is successful, confirm its related booking
            if payment.is_paid:
                booking = payment.booking
                booking.is_confirmed = True
                booking.save()

            return Response(serializer.data, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def _save_payment_record(self,payment):
        """Save a text record of the payment to a local file."""
        payments_dir = os.path.join(settings.BASE_DIR, "payments")
        os.makedirs(payments_dir, exist_ok=True)

        file_path = os.path.join(payments_dir, f"payment_booking_{payment.booking.id}.txt")
        total_price = getattr(payment.booking, "total_price", "N/A")

        with open(file_path, "w") as f:
            f.write(f"Booking ID: {payment.booking.id}\n")
            f.write(f"Total: {total_price}\n")
            f.write(f"Method: {payment.method}\n")
            f.write(f"Reference: {payment.reference}\n")
            f.write(f"Paid: {payment.is_paid}\n")

class PaymentDetailAPIView(APIView):
    serializer_class = PaymentSerializer
    """
    Handles:
    - GET /payments/<id>/ → retrieve a payment
    - PUT /payments/<id>/ → update a payment
    - DELETE /payments/<id>/ → delete a payment
    """

    def get_object(self, pk):
        return get_object_or_404(Payment, pk=pk)
    
    def get(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)
    
    def put(self, request, pk):
        payment = self.get_object(pk)
        serializer = PaymentSerializer(payment, data = request.data)
        if serializer.is_valid():
            payment = serializer.save()
            return Response(PaymentSerializer(payment).data)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        payment = self.get_object(pk)
        payment.delet()
        return Response(status = status.HTTP_204_NO_CONTENT)


# --------------------
# AUTHENTICATION VIEWS
# --------------------

class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiExample("User created", value={"message": "User created successfully"}),
            400: OpenApiExample("Error", value={"error": "Validation error"})
        },
        description="Register a new user with username, email, and password."
    )

    def get(self, request):
        registered_user = User.objects.all()
        serializer = UserSerializer(registered_user, many = True)
        return Response(serializer.data)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="user_login",
        summary="Login and retrieve authentication token",
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(description="Success"),
            401: OpenApiResponse(description="Invalid credentials")
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"]
        )
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)
