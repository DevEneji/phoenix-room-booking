# hotel/urls.py
from django.http import JsonResponse
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hotel.views import RoomViewSet, BookingViewSet, PaymentViewSet


router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'payments', PaymentViewSet, basename='payment')


def root_view(request):
    return JsonResponse({"message": "Welcome to the Phoenix Hotel API. Visit /api/ for endpoints."})

urlpatterns = [
    path('', root_view),
    
    # All API routes live under /api/
    path('api/', include(router.urls)),
]
