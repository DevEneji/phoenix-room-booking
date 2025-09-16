# hotel/api_urls.py
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, BookingViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'rooms', RoomViewSet)
router.register(r'bookings', BookingViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = router.urls
