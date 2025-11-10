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

class PublicRegisterView(APIView):
    """Public registration - customers only"""
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        # Force role to 'customer' for public registration
        data = request.data.copy()
        data['role'] = 'customer'

        serializer = RegisterSerializer(data = data, context = {'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "user": UserSerializer(user).data,
                "token": Token.objects.get(user = user).key
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
class StaffRegisterView(APIView):
    """Staff registration - requires staff/admin permissions"""
    permission_classes = [IsAuthenticated] # Staff or admin can access
    serializer_class = RegisterSerializer

    def post(self, request):
        if request.user.role not in ['staff', 'admin']:
            return Response(
                {"error": "Only staff or admin can register staff accounts."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Force role to 'staff'
        data = request.data.copy()
        data['role'] = 'staff'

        serializer = RegisterSerializer(data = data, context = {'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "user": UserSerializer(user).data,
                "message": "Staff account created successfully"
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
class AdminRegisterView(APIView):
    """Admin registration - requires admin permissions only"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = RegisterSerializer

    def post(self, request):
        # Force role to 'admin'
        data = request.data.copy()
        data['role'] = 'admin'

        serializer = RegisterSerializer(data = data, context = {'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "user": UserSerializer(user).data,
                "message": "Admin account created successfully"
            }, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

class UserManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def check_permissions(self, request):
        """Override to check for admin/staff permissions based on action"""
        super().check_permissions(request)

        # For listing and creating users, require staff / admin
        if request.method in ['GET', 'POST'] and request.user.role not in ['staff', 'admin']:
            self.permission_denied(
                request,
                message = 'Only staff or admin can access user management.'
            )

        # For updating/deleting, require admin only for role changes
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if 'role' in request.data and request.user.role != 'admin':
                self.permission_denied(
                    request,
                    message = "Only admin can change user roles"
                )

    def get(self, request):
        """List all users (staff/admin only)"""
        users = CustomUser.objects.all()

        # Filter by role if provided
        role_filter = request.GET.get('role')
        if role_filter:
            users = users.filter(role = role_filter)

        serializer = UserSerializer(users, many = True)
        return Response(serializer.data)
    
    def post(self, request):
        """Create new user with any role (staff/admin only)"""
        serializer = RegisterSerializer(data = request.data, context = {'request': request})

        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def get_object(self, pk):
        user = get_object_or_404(CustomUser, pk = pk)

        # User can view their own profile, but need permissions for others
        if self.request.user.pk != user.pk and self.request.user.role not in ['staff', 'admin']:
            raise PermissionDenied("You can only view your own profile.")

        return user
    
    def get(self, request, pk = None):
        """Get specific user profile"""
        if pk:
            user = self.get_object(pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        else:
            # List all users (handled by the get method without pk)
            return self.get(request)
        
    def patch(self, request, pk = None):
        """Update user profile or role"""
        if not pk:
            return Response({"error": "User ID required"}, status = status.HTTP_400_BAD_REQUEST)
        user = self.get_object(pk)

        # Users can only update their own profile unless they're staff/adminn
        if request.user.pk != user.pk and request.user.role not in ['staff', 'admin']:
            return Response(
                {"error": "You can only update your own profile."},
                status = status.HTTP_403_FORBIDDEN
            )
        
        serializer = UserSerializer(user, data = request.data, partial = True)
        if serializer.is_valid():
            # Check if trying to change role
            if 'role' in request.data and request.user.role != 'admin':
                return Response(
                    {"error": "Only admin can change user roles"},
                    status = status.HTTP_403_FORBIDDEN
                )
            
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk = None):
        """Delete user (admin only)"""
        if not pk:
            return Response({"error": "User ID required"}, status = status.HTTP_400_BAD_REQUEST)
        
        if request.user.role != 'admin':
            return Response(
                {"error": "Only admin can delete users."},
                status = status.HTTP_403_FORBIDDEN
            )
        
        user = get_object_or_404(CustomUser, pk = pk)

        # Prevent self-deletion
        if user.pk == request.user.pk:
            return Response(
                {"error": "You cannot delete your own account."},
                status = status.HTTP_400_BAD_REQUEST
            )
        user.delete()
        return Response(
            {"message": "User deleted successfully."},
            status = status.HTTP_204_NO_CONTENT
        )

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