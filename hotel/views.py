from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import authenticate
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError

from .models import (
    CustomUser, Hotel, RoomType, Room, CustomerProfile, StaffProfile, 
    Booking, Payment, Review
)
from .serializers import (
    UserSerializer,
    HotelSerializer,
    RoomTypeSerializer,
    RoomSerializer,
    BookingSerializer,
    PaymentSerializer,
    ReviewSerializer,
    RegisterSerializer,
    LoginSerializer,
    StaffProfileSerializer,
    CustomerProfileSerializer,
    AvailabilitySerializer
)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample


# --------------------
# AUTHENTICATION VIEWS
# --------------------

class RegisterView(APIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

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


# --------------------
# HOTEL VIEWS
# --------------------

class HotelListAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = HotelSerializer

    def get(self, request):
        hotels = Hotel.objects.all()
        serializer = HotelSerializer(hotels, many=True)
        return Response(serializer.data)


class HotelDetailAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = HotelSerializer

    def get(self, request, pk):
        hotel = get_object_or_404(Hotel, pk=pk)
        serializer = HotelSerializer(hotel)
        return Response(serializer.data)


# --------------------
# ROOM TYPE VIEWS
# --------------------

class RoomTypeListAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RoomTypeSerializer

    def get(self, request):
        hotel_id = request.GET.get('hotel_id')
        room_types = RoomType.objects.all()
        
        if hotel_id:
            room_types = room_types.filter(hotel_id=hotel_id)
        
        serializer = RoomTypeSerializer(room_types, many=True)
        return Response(serializer.data)


# --------------------
# ROOM VIEWS
# --------------------

class RoomListAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RoomSerializer

    def get(self, request):
        rooms = Room.objects.filter(is_active=True)
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)


class RoomDetailAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RoomSerializer

    def get(self, request, pk):
        room = get_object_or_404(Room, pk=pk, is_active=True)
        serializer = RoomSerializer(room)
        return Response(serializer.data)


# --------------------
# AVAILABILITY VIEW (New)
# --------------------

class AvailabilityAPIView(APIView):
    permission_classes = [AllowAny]
    serializer_class = AvailabilitySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='check_in', description='Check-in date (YYYY-MM-DD)', required=True, type=str),
            OpenApiParameter(name='check_out', description='Check-out date (YYYY-MM-DD)', required=True, type=str),
            OpenApiParameter(name='adults', description='Number of adults', required=False, type=int),
            OpenApiParameter(name='children', description='Number of children', required=False, type=int),
            OpenApiParameter(name='hotel_id', description='Filter by hotel', required=False, type=int),
        ]
    )
    def get(self, request):
        serializer = AvailabilitySerializer(data=request.GET)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        check_in = data['check_in']
        check_out = data['check_out']
        adults = data.get('adults', 1)
        children = data.get('children', 0)
        hotel_id = data.get('hotel_id')
        
        total_guests = adults + children
        
        # Find conflicting bookings
        conflicting_bookings = Booking.objects.filter(
            Q(check_in_date__lt=check_out, check_out_date__gt=check_in),
            status__in=['CONFIRMED', 'CHECKED_IN', 'PENDING']
        ).values_list('room_id', flat=True)
        
        # Get available rooms
        available_rooms = Room.objects.filter(
            is_active=True,
            status='AVAILABLE',
            room_type__capacity__gte=total_guests
        ).exclude(id__in=conflicting_bookings)
        
        if hotel_id:
            available_rooms = available_rooms.filter(room_type__hotel_id=hotel_id)
        
        room_data = []
        for room in available_rooms:
            nights = (check_out - check_in).days
            total_price = nights * room.price_per_night if nights > 0 else room.price_per_night
            
            room_data.append({
                'room': RoomSerializer(room).data,
                'room_type': RoomTypeSerializer(room.room_type).data,
                'total_nights': nights,
                'total_price': total_price
            })
        
        return Response({
            'check_in': check_in,
            'check_out': check_out,
            'total_guests': total_guests,
            'available_rooms': room_data
        })


# --------------------
# BOOKING VIEWS
# --------------------

class BookingListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get(self, request):
        if request.user.role in ['staff', 'admin']:
            bookings = Booking.objects.all()
        else:
            bookings = Booking.objects.filter(user=request.user)
        
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            booking = serializer.save()
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookingDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get_object(self, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if self.request.user.role not in ['staff', 'admin'] and booking.user != self.request.user:
            raise PermissionDenied("You don't have permission to access this booking.")
        return booking

    def get(self, request, pk):
        booking = self.get_object(pk)
        serializer = BookingSerializer(booking)
        return Response(serializer.data)

    def put(self, request, pk):
        booking = self.get_object(pk)
        serializer = BookingSerializer(booking, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        booking = self.get_object(pk)
        booking.status = 'CANCELLED'
        booking.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookingConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        if request.user.role not in ['staff', 'admin']:
            return Response({"error": "Only staff can confirm bookings"}, status=status.HTTP_403_FORBIDDEN)
        
        booking.status = 'CONFIRMED'
        booking.save()
        return Response({'status': 'Booking confirmed'})


# --------------------
# PAYMENT VIEWS
# --------------------

class PaymentListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get(self, request):
        if request.user.role in ['staff', 'admin']:
            payments = Payment.objects.all()
        else:
            payments = Payment.objects.filter(booking__user=request.user)
        
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            payment = serializer.save()
            
            # If payment is completed, update booking status
            if payment.status == 'COMPLETED':
                payment.booking.status = 'CONFIRMED'
                payment.booking.save()
            
            return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------------------
# REVIEW VIEWS
# --------------------

class ReviewListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReviewSerializer

    def get(self, request):
        hotel_id = request.GET.get('hotel_id')
        reviews = Review.objects.filter(is_approved=True)
        
        if hotel_id:
            reviews = reviews.filter(booking__room__room_type__hotel_id=hotel_id)
        
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ReviewSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            review = serializer.save()
            return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --------------------
# PROFILE VIEWS
# --------------------

class UserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyBookingsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get(self, request):
        bookings = Booking.objects.filter(user=request.user)
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)