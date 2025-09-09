# API views and frontend views (landing page, room listings, booking forms).

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
import os
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from .forms import BookingForm
from .models import Room, Booking, Payment
from .serializers import RoomSerializer, BookingSerializer, PaymentSerializer

# --------------------
# FRONTEND VIEWS (basic HTML templates)
# --------------------

def landing_page(request):
    # A simple landing page
    return render(request, 'hotel/landing.html')

def room_list(request):
    # Display all rooms (basic HTML rendering)
    rooms = Room.objects.all()
    return render(request, 'hotel/rooms.html', {'rooms': rooms})

def book_room(request):
    rooms = Room.objects.filter(is_available=True)  # only show available rooms
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save()

            # Optional: mark the room unavailable after booking
            booking.room.is_available = False
            booking.room.save()

            return redirect('payment', booking_id=booking.id)
    else:
        form = BookingForm()
    return render(request, 'hotel/book.html', {'form': form, 'rooms': rooms})

def payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == "POST":
        bank_name = request.POST.get("bank_name")
        card_type = request.POST.get("card_type")
        currency = request.POST.get("currency")
        card_number = request.POST.get("card_number")
        expiry_date = request.POST.get("expiry_date")

        # Simulate saving payment details into a text file
        payments_dir = os.path.join(settings.BASE_DIR, "payments")
        os.makedirs(payments_dir, exist_ok=True)  # Ensure directory exists

        file_path = os.path.join(payments_dir, f"payment_booking_{booking.id}.txt")
        with open(file_path, "w") as f:
            f.write(f"Booking ID: {booking.id}\n")
            f.write(f"Room: {booking.room}\n")
            f.write(f"Check-in: {booking.check_in}\n")
            f.write(f"Check-out: {booking.check_out}\n")
            f.write(f"Total: {booking.total_price}\n\n")
            f.write("---- Payment Details ----\n")
            f.write(f"Bank Name: {bank_name}\n")
            f.write(f"Card Type: {card_type}\n")
            f.write(f"Currency: {currency}\n")
            f.write(f"Card Number: {card_number}\n")
            f.write(f"Expiry Date: {expiry_date}\n")

        # Redirect to payment success page
        return redirect("payment_success", booking_id=booking.id)

    return render(request, "hotel/payment.html", {"booking": booking})


def payment_success_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, "payment_success.html", {"booking": booking})

def payment_success_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, 'hotel/payment_success.html', {'booking': booking})

# --------------------
# API VIEWS (Django REST Framework)
# --------------------

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['room_type'] # Allow searching by room type

    @action(detail = False, methods = ['get'])
    def available(self, request):
        # Custom endpoint: /api/rooms/available/?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')

        # Return rooms marked as available
        rooms = Room.objects.filter(is_available = True)
        serializer = self.get_serializer(rooms, many = True)
        return Response(serializer.data)
    

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    @action(detail = True, methods = ['post'])
    def confirm(self, request, pk = None):
        # confirm booking manually via API
        booking = self.get_object()
        booking.is_confirmed = True
        booking.save()
        return Response({'status': 'Booking confirmed'})
    
    @action(detail = True, methods = ['post'])
    def cancel(self, request, pk = None):
        # Cancel booking manually via API
        booking = self.get_object()
        booking.delete()
        return Response({'status': 'Booking canceled'})
        

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    @action(detail = True, methods = ['post'])
    def succeed(self, request, pk = None):
        # Mark payment as successful
        payment = self.get_object()
        payment.is_paid = True
        payment.save()
        return Response({'status': 'Payment successful'})
    