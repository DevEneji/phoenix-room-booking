# hotel/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hotel.views import BookingViewSet, PaymentViewSet, RegisterView, LoginView, RoomListAPIView, RoomDetailAPIView, AvailableRoomsAPIView, UpdateRoomStatusAPIView


router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')


urlpatterns = [
    # Room endpoints
    path('rooms/', RoomListAPIView.as_view(), name='room-list'),
    path('rooms/<int:pk>/', RoomDetailAPIView.as_view(), name='room-detail'),
    path('rooms/available/', AvailableRoomsAPIView.as_view(), name='available-rooms'),
    path('rooms/<int:pk>/status/', UpdateRoomStatusAPIView.as_view(), name='update-room-status'),
    
    path('', include(router.urls)),  # all API routes
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
]
