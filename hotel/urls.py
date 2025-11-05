# hotel/urls.py
from django.urls import path
from hotel.views import (
    RegisterView,
    LoginView,
    RoomListAPIView,
    RoomDetailAPIView,
    AvailableRoomsAPIView,
    UpdateRoomStatusAPIView,
    BookingListCreateAPIView,
    BookingDetailAPIView,
    BookingConfirmAPIView,
    BookingCancelAPIView,
    PaymentListCreateAPIView,
    PaymentDetailAPIView,
    StaffAPIView,
)


urlpatterns = [
    # Room endpoints
    path('rooms/', RoomListAPIView.as_view(), name='room-list'),
    path('rooms/<int:pk>/', RoomDetailAPIView.as_view(), name='room-detail'),
    path('rooms/available/', AvailableRoomsAPIView.as_view(), name='available-rooms'),
    path('rooms/<int:pk>/status/', UpdateRoomStatusAPIView.as_view(), name='update-room-status'),

    # Booking endpoints
    path('bookings/', BookingListCreateAPIView.as_view(), name='booking-list'),
    path('bookings/<int:pk>/', BookingDetailAPIView.as_view(), name='booking-detail'),
    path('bookings/<int:pk>/confirm/', BookingConfirmAPIView.as_view(), name='booking-confirm'),
    path('bookings/<int:pk>/cancel/', BookingCancelAPIView.as_view(), name='booking-cancel'),

    # Payment endpoints
    path('payments/', PaymentListCreateAPIView.as_view(), name='payment-list-create'),
    path('payments/<int:pk>/', PaymentDetailAPIView.as_view(), name='payment-detail'),

    # Staff Management endpoints
    path('staff/', StaffAPIView.as_view(), name = 'staff_list_create'),
    path('staff/<int:pk>/', StaffAPIView.as_view(), name = 'staff-detail'),
    
    # All API routes
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
]
