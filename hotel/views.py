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
    AvailabilitySerializer,
    ResendOTPSerializer,
    OTPVerificationSerializer,
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

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    serializer_class = OTPVerificationSerializer

    def post(self, request):
        serializer = OTPVerificationSerializer(data = request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                user = CustomUser.objects.get(email = email)
                if user.verify_otp(otp):
                    return Response({
                        "message": "Email verified successfully!",
                        "user": UserSerializer(user).data
                    }, status = status.HTTP_200_OK)
                else:
                    return Response({
                        "error": "Invalid or expired OTP"
                    }, status = status.HTTP_400_BAD_REQUEST)
            except CustomUser.DoesNotExist:
                return Response({
                    "error": "User with this email does not exist"
                }, status = status.HTTP_404_NOT_FOUND)
            
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    serializer_class = ResendOTPSerializer

    def post(self, request):
        serializer = ResendOTPSerializer(data = request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = CustomUser.objects.get(email = email)
                if user.is_email_verified:
                    return Response({
                        "error": "Email is already verified"
                    }, status = status.HTTP_400_BAD_REQUEST)
                
                user.send_verification_email()
                return Response({
                    "message": "OTP sent successfully!"
                }, status = status.HTTP_200_OK)
            except CustomUser.DoesNotExist:
                return Response({
                    "error": "User with this email does not exist"
                }, status = status.HTTP_404_NOT_FOUND)
            
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)

# Enhanced User Management with Staff Permissions
class UserManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def check_permissions(self, request):
        """Enhanced permission checking based on user roles"""
        super().check_permissions(request)

        # Define role-based permissions
        user_role = request.user.role

        # Staff can: list users, create customers/staff, update customers/staff
        # Admin can: do everything including role changes and deletions

        if request.method == 'GET':
            # Staff and admin can list users
            if user_role not in ['staff', 'admin']:
                self.permission_denied(request, message = "Insufficient permissions to view users.")

        elif request.method == 'POST':
            # Staff can create customers and staff, admin can create anyone
            requested_role = request.data.get('role', 'customer')
            if user_role == 'staff' and requested_role == 'admin':
                self.permission_denied(request, message = "Staff cannot create admin accounts")

        elif request.method in ['PUT', 'PATCH']:
            # Check if trying to modify sensitive fields
            if 'role' in request.data and user_role != 'admin':
                self.permission_denied(request, message = "Only admin can change user roles.")

            # Staff can only modify customers and other staffs, not admins
            if 'pk' in self.kwargs:
                target_user = get_object_or_404(CustomUser, pk = self.kwargs['pk'])
                if user_role == 'staff' and target_user.role == 'admin':
                    self.permission_denied(request, message = "Staff cannot modify admin accounts.")

        elif request.method == 'DELETE':
            # Only admin can delete users
            if user_role != 'admin':
                self.permission_denied(request, message = "Only admin can delete users.")

    def get_query(self):
        """Filter queryset based on user role"""
        user = self.request.user

        if user.role == 'admin':
            return CustomUser.objects.all()
        elif user.role == 'staff':
            # Staff can see customers and other staff (but not admins)
            return CustomUser.objects.filter(role__in = ['customer', 'staff'])
        else:
            # Customers can only see themselves
            return CustomUser.objects.filter(pk = user.pk)

    def get(self, request, pk = None):
        """List users or get specific user"""
        if pk:
            user = get_object_or_404(self.get_queryset(), pk = pk)
            serializer = UserSerializer(user)
            return Response (serializer.data)
        else:
            # Filter by role if provided
            role_filter = request.GET.get('role')
            users = self.get_queryset()

            if role_filter:
                users = users.filter(role = role_filter)

            serializer = UserSerializer(users, many = True)
            return Response(serializer.data)
            
    def post(self, request):
        """Create new user with role-based permissions"""
        serializer = RegisterSerializer(data = request.data, context = {'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status = status.HTTP_201_CREATED)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request, pk = None):
        """Update user with role-based permissions"""
        if not pk:
            return Response({"error": "User ID required"}, status = status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(self.get_queryset(), pk = pk)

        serializer = UserSerializer(user, data = request.data, partial = True)
        if serializer.is_valid():
            # Additional permission checks for role changes
            if 'role' in request.data and request.user.role != 'admin':
                return Response(
                    {"error": "Only admin can change user roles."},
                    status = status.HTTP_403_FORBIDDEN
                )
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status = status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk=None):
        """Delete user (admin only)"""
        if not pk:
            return Response({"error": "User ID required"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = get_object_or_404(CustomUser, pk=pk)
        
        # Prevent self-deletion
        if user.pk == request.user.pk:
            return Response(
                {"error": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.delete()
        return Response(
            {"message": "User deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
        

# Enhanced Staff Registration View
class StaffRegisterView(APIView):
    """Staff registration - staff can register staff, admin can register anyone"""
    permission_classes = [IsAuthenticated]
    serializer_class = RegisterSerializer

    def post(self, request):
        user_role = request.user.role
        requested_role = request.data.get('role', 'staff')
        
        # Permission checks
        if user_role == 'customer':
            return Response(
                {"error": "Customers cannot register staff accounts."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if requested_role == 'admin' and user_role != 'admin':
            return Response(
                {"error": "Only admin can register admin accounts."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Staff can only register staff, not admins
        if user_role == 'staff' and requested_role not in ['customer', 'staff']:
            return Response(
                {"error": "Staff can only register customer and staff accounts."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "user": UserSerializer(user).data,
                "message": f"{requested_role.title()} account created successfully"
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