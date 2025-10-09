# hotel/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hotel.views import RoomViewSet, BookingViewSet, PaymentViewSet, RegisterView, LoginView, RoomTypeViewSet


router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'room-types', RoomTypeViewSet, basename = 'roo')


urlpatterns = [
    path('', include(router.urls)),  # all API routes
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
]
