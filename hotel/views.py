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
from .models import Room, Booking, Payment
from .serializers import (
    RoomSerializer,
    BookingSerializer,
    PaymentSerializer,
    RegisterSerializer,
    UserSerializer,
    LoginSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiTypes


# --------------------
# ROOM VIEWS
# --------------------

class RoomListAPIView(APIView):
    """List all active rooms or create a new room."""
    def get(self, request):
        rooms = Room.objects.filter(is_active=True)
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = RoomSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoomDetailAPIView(APIView):
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
# BOOKING & PAYMENT VIEWS
# --------------------

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        booking = serializer.save()
        booking.room.is_available = False
        booking.room.save()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        booking = self.get_object()
        booking.is_confirmed = True
        booking.save()
        return Response({'status': 'Booking confirmed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        booking.delete()
        return Response({'status': 'Booking canceled'})


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        self._save_payment_record(payment)

        if payment.is_paid:
            booking = payment.booking
            booking.is_confirmed = True
            booking.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def _save_payment_record(self, payment):
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


# --------------------
# AUTHENTICATION VIEWS
# --------------------

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: OpenApiExample("User created", value={"message": "User created successfully"}),
            400: OpenApiExample("Error", value={"error": "Validation error"})
        },
        description="Register a new user with username, email, and password."
    )
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
