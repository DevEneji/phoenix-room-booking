from django.urls import path
from .views import (
    # Authentication
    PublicRegisterView,
    StaffRegisterView,
    AdminRegisterView,
    UserManagementAPIView,
    LoginView,
    VerifyEmailView,
    ResendOTPView,
    
    # Hotel & Rooms
    HotelListAPIView,
    HotelDetailAPIView,
    RoomTypeListAPIView,
    RoomListAPIView,
    RoomDetailAPIView,
    AvailabilityAPIView,
    
    # Bookings
    BookingListCreateAPIView,
    BookingDetailAPIView,
    BookingConfirmAPIView,
    MyBookingsAPIView,
    
    # Payments
    PaymentListCreateAPIView,
    
    # Reviews
    ReviewListCreateAPIView,
    
    # User Profiles
    UserProfileAPIView,
)

urlpatterns = [
    # Authentication
    # Registration endpoints
    path('auth/register/', PublicRegisterView.as_view(), name='register-public'),  # Customers only
    path('auth/register/staff/', StaffRegisterView.as_view(), name='register-staff'),
    path('auth/register/admin/', AdminRegisterView.as_view(), name='register-admin'),

    # Email Verification
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    
    # User management
    path('admin/users/', UserManagementAPIView.as_view(), name='user-management'),
    path('admin/users/<int:pk>/', UserManagementAPIView.as_view(), name='user-detail'),

    # Login endpoint
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # Hotels
    path('hotels/', HotelListAPIView.as_view(), name='hotel-list'),
    path('hotels/<int:pk>/', HotelDetailAPIView.as_view(), name='hotel-detail'),
    
    # Room Types
    path('room-types/', RoomTypeListAPIView.as_view(), name='room-type-list'),
    
    # Rooms
    path('rooms/', RoomListAPIView.as_view(), name='room-list'),
    path('rooms/<int:pk>/', RoomDetailAPIView.as_view(), name='room-detail'),
    
    # Availability & Search
    path('availability/', AvailabilityAPIView.as_view(), name='availability'),
    
    # Bookings
    path('bookings/', BookingListCreateAPIView.as_view(), name='booking-list'),
    path('bookings/my/', MyBookingsAPIView.as_view(), name='my-bookings'),
    path('bookings/<uuid:pk>/', BookingDetailAPIView.as_view(), name='booking-detail'),
    path('bookings/<uuid:pk>/confirm/', BookingConfirmAPIView.as_view(), name='booking-confirm'),
    
    # Payments
    path('payments/', PaymentListCreateAPIView.as_view(), name='payment-list'),
    
    # Reviews
    path('reviews/', ReviewListCreateAPIView.as_view(), name='review-list'),
    
    # User Profile
    path('profile/', UserProfileAPIView.as_view(), name='user-profile'),
]