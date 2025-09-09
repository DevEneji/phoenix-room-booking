# -------------
# Routes for frontend (basic pages) and backend (API endpoints).
# -------------

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import landing_page, room_list, book_room, payment_success_view, payment_view, RoomViewSet, BookingViewSet, PaymentViewSet

# DRF router for API endpoints
router = DefaultRouter()
router.register(r'rooms', RoomViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    # Frontend pages
    path('', landing_page, name = 'landing_page'),
    path('rooms/', room_list, name = 'room_list'),
    path('book/', book_room, name = 'book_room'),
    path('payment/<int:booking_id>/', payment_view, name='payment'),
    path('payment_success/<int:booking_id>/', payment_success_view, name='payment_success'),
    # API endpoints
    path('api/', include(router.urls)),
]