# API views and frontend views (landing page, room listings, booking forms).

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
import os
from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .forms import BookingForm
from .models import Room, Booking, Payment
from .serializers import RoomSerializer, BookingSerializer, PaymentSerializer, RegisterSerializer, UserSerializer, LoginSerializer

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiRequest, OpenApiResponse, OpenApiTypes


# --------------------
# API VIEWS (Django REST Framework)
# --------------------

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['room_type'] # Allow searching by room type

    @action(detail = False, methods = ['get'])
    def available(self, request):
        # Custom endpoint: /api/rooms/available/?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')

        # Return rooms marked as available
        rooms = Room.objects.filter(is_available = True)
        serializer = self.get_serializer(rooms, many = True)
        return Response(serializer.data)
    

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def perform_create(self, serializer):
        """
        Called by `.create()`. Save booking and mark room unavailable.
        Validation (no-overlap) should already be enforced in serializer.validate().
        """
        booking = serializer.save()
        # Mark the room unavailable
        booking.room.is_available = False
        booking.room.save()

    @action(detail = True, methods = ['post'])
    def confirm(self, request, pk = None):
        # confirm booking manually via API
        booking = self.get_object()
        booking.is_confirmed = True
        booking.save()
        return Response({'status': 'Booking confirmed'})
    
    @action(detail = True, methods = ['post'])
    def cancel(self, request, pk = None):
        # Cancel booking manually via API
        booking = self.get_object()
        booking.delete()
        return Response({'status': 'Booking canceled'})
        

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        """
        Expected output example:
        {
          "booking": <id>,
          "amount": 50000,
          "method": "card",
          "is_paid": true,
          "reference": "REF12345"
        }
        The serializer should validate the bookmount correctness.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        self._save_payment_record(payment)

        # If payment is paid, mark booking confirmed
        if payment.is_paid:
            bk = payment.booking
            bk.is_confirmed = True
            bk.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def _save_payment_record(self, payment):
        payments_dir = os.path.join(settings.BASE_DIR, "payments")
        os.makedirs(payments_dir, exist_ok=True)
        file_path = os.path.join(payments_dir, f"payment_booking_{payment.booking.id}.txt")
        with open(file_path, "w") as f:
            f.write(f"Booking ID: {payment.booking.id}\n")
            f.write(f"Total: {payment.booking.total_price}\n")
            f.write(f"Method: {payment.method}\n")
            f.write(f"Reference: {payment.reference}\n")
            f.write(f"Paid: {payment.is_paid}\n")

class RegisterView(APIView):
    permission_classes =  [AllowAny]
    serializer_class = RegisterSerializer
    queryset = User.objects.all()

    @extend_schema(
        request = RegisterSerializer,
        responses = {
            201: OpenApiExample(
                'Successful Registration',
                summary="Success Example",
                value = {"message": "User created successfully"}
            ),
            400: OpenApiExample(
                'Invalid Request',
                summary="Error Example",
                value = {"error": "Username already exists"}
            )
        },
        description="Register a new user by providing username, email, and password."
    )
    
    def post(self, request):
        serializer = RegisterSerializer(data = request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user = user)
            return Response({
                "user": UserSerializer(user).data,
                "token": token.key
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes =  [AllowAny]

    @extend_schema(
        operation_id="user_login",
        summary = "Login user and obtain authentication token",
        description = (
            "Authenticate a user using their **username** and **password**.\n\n"
            "If credentials are valid, the system returns the user's details and a token.\n"
            "Otherwise, it returns a 401 error."
        ),
        request = LoginSerializer, # the serializer describing the input fields
        responses={
            200: OpenApiResponse(
                response = OpenApiTypes.OBJECT,
                description="Login success with token",
                examples=[
                    OpenApiExample(
                        "Success Example",
                        summary="Successful login response",
                        value = {
                            "user": {
                                "id": 1,
                                "username": "john_doe",
                                "email": "john@example.com"
                            },
                            "token": "0a1b2c3d4e5f6g7h8i9j"
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description = "Invalid credentials",
                examples = [
                    OpenApiExample(
                        "Error Example",
                        summary = "Failed login attempt",
                        value = {"error": "Invalid credentials"}
                    )
                ]
            )
        },
        tags = ["Authentication"]
    )
    
    def post(self, request):
        serializer = LoginSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(username = username, password = password)
        if not user:
            return Response({"error": "Invalid credentials"}, status = status.HTTP_401_UNAUTHORIZED)
        token, _ = Token.objects.get_or_create(user = user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status = status.HTTP_200_OK)
        