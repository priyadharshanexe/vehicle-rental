from django.shortcuts import render, redirect
from .models import CustomUser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Vehicle
from .models import Booking
from decimal import Decimal

from django import forms
from django.db import models, transaction
from django.utils import timezone
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Feedback

def rental_profile(user):
    profile, _ = CustomUser.objects.get_or_create(
        account=user,
        defaults={
            "email": user.email or f"account-{user.pk}@invalid.invalid",
            "name": (user.get_full_name() or user.email or user.username)[:100],
        },
    )
    return profile


@login_required
def dashboard(request):
    user = rental_profile(request.user)

    # get user's bookings
    bookings = Booking.objects.filter(user=user)

    recommended = []

    if bookings.exists():

        # most booked vehicle type
        vehicle_type = bookings.values_list(
            'vehicle__vehicle_type', flat=True
        )[0]

        recommended = Vehicle.objects.filter(vehicle_type=vehicle_type)[:3]

    context = {
        "recommended": recommended
    }

    return render(request, 'rental/dashboard.html', context)

@login_required
def vehicle_list(request):
    query = request.GET.get('q')
    vehicle_type = request.GET.get('type')
    fuel_type = request.GET.get('fuel')
    location = request.GET.get('location')

    vehicles = Vehicle.objects.filter(is_available=True)

    if query:
        vehicles = vehicles.filter(name__icontains=query)

    if vehicle_type:
        vehicles = vehicles.filter(vehicle_type=vehicle_type)

    if fuel_type:
        vehicles = vehicles.filter(fuel_type__icontains=fuel_type)

    if location:
        vehicles = vehicles.filter(location__icontains=location)

    context = {
        "vehicles": vehicles
    }

    return render(request, 'rental/vehicle_list.html', context)

class BookingDatesForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        start = data.get("start_date")
        end = data.get("end_date")
        if start and start < timezone.localdate():
            self.add_error("start_date", "Choose today or a later date.")
        if start and end and end < start:
            self.add_error("end_date", "End date cannot be before start date.")
        return data


ACTIVE_BOOKING_STATUSES = (
    Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.IN_PROGRESS,
)


@transaction.atomic
def reserve_vehicle(user_id, vehicle_id, start_date, end_date):
    # Lock in a consistent order so requests serialize per renter and vehicle.
    CustomUser.objects.select_for_update().get(pk=user_id)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=vehicle_id)
    active = Booking.objects.filter(status__in=ACTIVE_BOOKING_STATUSES)
    if not vehicle.is_available:
        raise forms.ValidationError("This vehicle is no longer available.")
    if active.filter(user_id=user_id).count() >= 3:
        raise forms.ValidationError("You can only have 3 active bookings at a time.")
    if active.filter(
        vehicle=vehicle, start_date__lte=end_date, end_date__gte=start_date
    ).exists():
        raise forms.ValidationError("Vehicle already booked for these dates.")
    days = (end_date - start_date).days + 1
    total_price = days * vehicle.price_per_day
    if not 0 < total_price <= Decimal("99999999.99"):
        raise forms.ValidationError("This rental cannot be priced for the selected dates.")
    return Booking.objects.create(
        user_id=user_id, vehicle=vehicle, start_date=start_date, end_date=end_date,
        total_price=total_price,
    )


@login_required
def book_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    user = rental_profile(request.user)
    form = BookingDatesForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            reserve_vehicle(user.pk, vehicle.pk, **form.cleaned_data)
        except forms.ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("my_bookings")

    booked_dates = Booking.objects.filter(
        vehicle=vehicle, status__in=ACTIVE_BOOKING_STATUSES,
        end_date__gte=timezone.localdate(),
    ).order_by("start_date")
    return render(request, "rental/book_vehicle.html", {
        "vehicle": vehicle, "booked_dates": booked_dates, "form": form,
    })


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user_id=rental_profile(request.user).pk)

    for booking in bookings:
        booking.days = (booking.end_date - booking.start_date).days + 1

    return render(request, 'rental/my_bookings.html', {'bookings': bookings})

@transaction.atomic
def change_booking_status(request, booking_id, destination, allowed, *, owner=False):
    profile = rental_profile(request.user)
    scope = {"vehicle__owner": profile} if owner else {"user": profile}
    reference = get_object_or_404(Booking, pk=booking_id, **scope)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=reference.vehicle_id)
    booking = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id)
    target = "owner_bookings" if owner else "my_bookings"
    if booking.status not in allowed:
        messages.error(request, "This booking has changed. Check its current status.")
        return redirect(target)

    today = timezone.localdate()
    if destination == Booking.Status.CONFIRMED and booking.start_date < today:
        messages.error(request, "The pickup date has passed.")
        return redirect(target)
    if destination == Booking.Status.IN_PROGRESS:
        if not booking.start_date <= today <= booking.end_date:
            messages.error(request, "Pickup must be within the booked dates.")
            return redirect(target)
        if Booking.objects.filter(vehicle=vehicle, status=Booking.Status.IN_PROGRESS).exists():
            messages.error(request, "Record the previous rental's return before pickup.")
            return redirect(target)
        booking.picked_up_at = timezone.now()
    if destination == Booking.Status.RETURNED:
        booking.returned_at = timezone.now()
    booking.status = destination
    booking.save(update_fields=["status", "picked_up_at", "returned_at"])
    return redirect(target)


@require_POST
@login_required
def cancel_booking(request, booking_id):
    return change_booking_status(
        request, booking_id, Booking.Status.CANCELLED,
        (Booking.Status.PENDING, Booking.Status.CONFIRMED),
    )


@require_POST
@login_required
def pickup_vehicle(request, booking_id):
    return change_booking_status(
        request, booking_id, Booking.Status.IN_PROGRESS, (Booking.Status.CONFIRMED,), owner=True,
    )


@require_POST
@login_required
def return_vehicle(request, booking_id):
    return change_booking_status(
        request, booking_id, Booking.Status.RETURNED, (Booking.Status.IN_PROGRESS,), owner=True,
    )


@staff_member_required
def admin_dashboard(request):

    # basic statistics
    total_users = CustomUser.objects.count()
    total_vehicles = Vehicle.objects.count()
    total_bookings = Booking.objects.count()

    total_revenue = Booking.objects.filter(status="Returned").aggregate(
    total=models.Sum("total_price")
    )["total"] or 0

    # bookings by vehicle (for chart)
    vehicle_names = []
    booking_counts = []

    vehicles = Vehicle.objects.all()

    for v in vehicles:
        count = Booking.objects.filter(vehicle=v).count()
        vehicle_names.append(v.name)
        booking_counts.append(count)

    # vehicle popularity ranking
    popular_vehicles = []

    for v in vehicles:
        count = Booking.objects.filter(vehicle=v).count()
        popular_vehicles.append({
            "name": v.name,
            "count": count
        })

    popular_vehicles = sorted(popular_vehicles, key=lambda x: x["count"], reverse=True)

    # recent booking activity
    recent_bookings = Booking.objects.select_related(
        'user', 'vehicle'
    ).order_by('-id')[:5]

    context = {
        "total_users": total_users,
        "total_vehicles": total_vehicles,
        "total_bookings": total_bookings,
        "total_revenue": total_revenue,
        "vehicle_names": vehicle_names,
        "booking_counts": booking_counts,
        "popular_vehicles": popular_vehicles,
        "recent_bookings": recent_bookings
    }

    return render(request, "rental/admin_dashboard.html", context)

@login_required
def download_receipt(request, booking_id):
    user_id = rental_profile(request.user).pk
    booking = get_object_or_404(Booking, id=booking_id, user_id=user_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="receipt.pdf"'

    p = canvas.Canvas(response)

    p.drawString(100, 800, "Vehicle Rental Receipt")
    p.drawString(100, 760, f"User: {booking.user.name}")
    p.drawString(100, 740, f"Vehicle: {booking.vehicle.name}")
    p.drawString(100, 720, f"Start Date: {booking.start_date}")
    p.drawString(100, 700, f"End Date: {booking.end_date}")
    p.drawString(100, 680, f"Total Price: ₹{booking.total_price}")
    p.drawString(100, 660, f"Status: {booking.status}")

    p.showPage()
    p.save()

    return response

@login_required
def add_vehicle(request):

    if request.method == "POST":

        name = request.POST['name']
        vehicle_type = request.POST['vehicle_type']
        fuel_type = request.POST['fuel_type']
        location = request.POST['location'].strip()
        price = request.POST['price']
        image = request.FILES.get('image')

        owner = rental_profile(request.user)

        vehicle_count = Vehicle.objects.filter(owner=owner).count()

        if vehicle_count >= 3:
            messages.error(request, "You can only add up to 3 vehicles.")
            return redirect('my_vehicles')

        Vehicle.objects.create(
            owner=owner,
            name=name,
            vehicle_type=vehicle_type,
            fuel_type=fuel_type,
            location=location,
            price_per_day=price,
            vehicle_image=image
        )

        return redirect('vehicle_list')

    return render(request, "rental/add_vehicle.html")

@login_required
def my_vehicles(request):

    owner = rental_profile(request.user)

    vehicles = Vehicle.objects.filter(owner=owner)

    return render(request, "rental/my_vehicles.html", {"vehicles": vehicles})

@require_POST
@login_required
def toggle_vehicle(request, vehicle_id):

    user_id = rental_profile(request.user).pk
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner_id=user_id)

    if vehicle.is_available:
        vehicle.is_available = False
    else:
        vehicle.is_available = True

    vehicle.save()

    return redirect('my_vehicles')

@require_POST
@login_required
def delete_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(
    Vehicle,
    id=vehicle_id,
    owner_id=rental_profile(request.user).pk
    )
    vehicle.delete()

    return redirect('my_vehicles')

@login_required
def edit_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(
    Vehicle,
    id=vehicle_id,
    owner_id=rental_profile(request.user).pk
    )

    if request.method == "POST":

        vehicle.name = request.POST['name']
        vehicle.vehicle_type = request.POST['vehicle_type']
        vehicle.fuel_type = request.POST['fuel_type']
        vehicle.price_per_day = request.POST['price']

        vehicle.save()

        return redirect('my_vehicles')

    return render(request, "rental/edit_vehicle.html", {"vehicle": vehicle})

@login_required
def owner_earnings(request):

    owner = rental_profile(request.user)

    vehicles = Vehicle.objects.filter(owner=owner)

    earnings_data = []
    total_earnings = 0

    for vehicle in vehicles:

        bookings = Booking.objects.filter(vehicle=vehicle, status="Returned")

        booking_count = bookings.count()

        revenue = bookings.aggregate(
            total=models.Sum("total_price")
        )["total"] or 0

        total_earnings += revenue

        earnings_data.append({
            "vehicle": vehicle.name,
            "bookings": booking_count,
            "revenue": revenue
        })

    context = {
        "earnings_data": earnings_data,
        "total_earnings": total_earnings
    }

    return render(request, "rental/owner_earnings.html", context)

@login_required
def owner_bookings(request):

    owner = rental_profile(request.user)

    bookings = Booking.objects.filter(vehicle__owner=owner)

    return render(request, "rental/owner_bookings.html", {"bookings": bookings})

@require_POST
@login_required
def approve_booking(request, booking_id):
    return change_booking_status(
        request, booking_id, Booking.Status.CONFIRMED, (Booking.Status.PENDING,), owner=True,
    )


@require_POST
@login_required
def reject_booking(request, booking_id):
    return change_booking_status(
        request, booking_id, Booking.Status.REJECTED, (Booking.Status.PENDING,), owner=True,
    )


def home(request):
    return render(request, "rental/home.html")

@login_required
def add_feedback(request, vehicle_id):

    user = rental_profile(request.user)
    vehicle = Vehicle.objects.get(id=vehicle_id)

    if request.method == "POST":
        rating = request.POST['rating']
        comment = request.POST['comment']

        Feedback.objects.create(
            user=user,
            vehicle=vehicle,
            rating=rating,
            comment=comment
        )

        return redirect('vehicle_list')

    return render(request, "rental/add_feedback.html", {"vehicle": vehicle})