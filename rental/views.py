import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from .models import Vehicle
from .models import Booking
from decimal import Decimal

from django import forms
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from reportlab.pdfgen import canvas
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404
from .models import MaintenanceBlock

logger = logging.getLogger(__name__)


def rental_profile(user):
    profile, _ = CustomUser.objects.get_or_create(
        account=user,
        defaults={
            "email": user.email or f"account-{user.pk}@invalid.invalid",
            "name": (user.get_full_name() or user.email or user.username)[:100],
        },
    )
    return profile


def search_vehicles(params):
    vehicles = Vehicle.objects.filter(is_available=True, archived_at__isnull=True)
    filters = {key: params.get(key, "").strip() for key in
               ("q", "type", "fuel", "location", "start_date", "end_date")}
    for key, lookup in (("q", "name__icontains"), ("type", "vehicle_type"),
                        ("fuel", "fuel_type__icontains"), ("location", "location__icontains")):
        if filters[key]:
            vehicles = vehicles.filter(**{lookup: filters[key]})
    dates = BookingDatesForm(params if filters["start_date"] or filters["end_date"] else None)
    if dates.is_bound and dates.is_valid():
        conflicting = active_bookings().filter(
            start_date__lte=dates.cleaned_data["end_date"],
            end_date__gte=dates.cleaned_data["start_date"],
        )
        blocked = MaintenanceBlock.objects.filter(
            start_date__lte=dates.cleaned_data["end_date"], end_date__gte=dates.cleaned_data["start_date"],
        )
        vehicles = vehicles.exclude(pk__in=conflicting.values("vehicle_id")).exclude(
            pk__in=blocked.values("vehicle_id")
        )
    return vehicles, filters, dates


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


def active_bookings():
    today = timezone.localdate()
    return Booking.objects.filter(
        models.Q(status=Booking.Status.IN_PROGRESS)
        | models.Q(status=Booking.Status.CONFIRMED, end_date__gte=today)
        | (
            models.Q(status=Booking.Status.PENDING, start_date__gte=today)
            & (models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now()))
        )
    )


def rental_quote(vehicle, start_date, end_date):
    days = (end_date - start_date).days + 1
    total_price = days * vehicle.price_per_day
    if not 0 < total_price <= Decimal("99999999.99"):
        raise forms.ValidationError("This rental cannot be priced for the selected dates.")
    return days, total_price


@transaction.atomic
def reserve_vehicle(user_id, vehicle_id, start_date, end_date):
    # Lock in a consistent order so requests serialize per renter and vehicle.
    CustomUser.objects.select_for_update().get(pk=user_id)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=vehicle_id)
    active = active_bookings()
    if end_date < start_date or start_date < timezone.localdate():
        raise forms.ValidationError("Choose a valid pickup and return date.")
    if not vehicle.is_available or vehicle.archived_at:
        raise forms.ValidationError("This vehicle is no longer available.")
    if active.filter(user_id=user_id).count() >= 3:
        raise forms.ValidationError("You can only have 3 active bookings at a time.")
    if active.filter(
        vehicle=vehicle, start_date__lte=end_date, end_date__gte=start_date
    ).exists():
        raise forms.ValidationError("Vehicle already booked for these dates.")
    if MaintenanceBlock.objects.filter(
        vehicle=vehicle, start_date__lte=end_date, end_date__gte=start_date,
    ).exists():
        raise forms.ValidationError("This vehicle has scheduled maintenance for those dates.")
    _, total_price = rental_quote(vehicle, start_date, end_date)
    return Booking.objects.create(
        user_id=user_id, vehicle=vehicle, start_date=start_date, end_date=end_date,
        total_price=total_price, quoted_daily_rate=vehicle.price_per_day,
        expires_at=timezone.now() + timedelta(hours=24),
    )


@transaction.atomic
def transition_booking(actor, booking_id, destination, allowed, *, owner=False):
    profile = rental_profile(actor)
    scope = {"vehicle__owner": profile} if owner else {"user": profile}
    reference = get_object_or_404(Booking, pk=booking_id, **scope)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=reference.vehicle_id)
    booking = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id)
    if booking.display_status not in allowed:
        raise forms.ValidationError("This booking has changed. Check its current status.")

    today = timezone.localdate()
    if destination == Booking.Status.CANCELLED and booking.status == Booking.Status.CONFIRMED and today >= booking.start_date:
        raise forms.ValidationError("Confirmed bookings can be cancelled before the pickup date.")
    if destination == Booking.Status.CONFIRMED and booking.start_date < today:
        raise forms.ValidationError("The pickup date has passed.")
    if destination == Booking.Status.IN_PROGRESS:
        if not booking.start_date <= today <= booking.end_date:
            raise forms.ValidationError("Pickup must be within the booked dates.")
        if Booking.objects.filter(vehicle=vehicle, status=Booking.Status.IN_PROGRESS).exists():
            raise forms.ValidationError("Record the previous rental's return before pickup.")
        booking.picked_up_at = timezone.now()
    if destination == Booking.Status.RETURNED:
        booking.returned_at = timezone.now()
    booking.status = destination
    booking.status_changed_at = timezone.now()
    booking.status_changed_by = actor
    booking.save(update_fields=[
        "status", "picked_up_at", "returned_at", "status_changed_at", "status_changed_by",
    ])
    logger.info("booking_status_changed booking_id=%s actor_id=%s status=%s", booking.pk, actor.pk, destination)
    return booking


@staff_member_required
def admin_dashboard(request):

    return render(request, "rental/admin_dashboard.html", {
        "pending_count": active_bookings().filter(status=Booking.Status.PENDING).count(),
        "overdue_count": Booking.objects.filter(
            status=Booking.Status.IN_PROGRESS, end_date__lt=timezone.localdate(),
        ).count(),
        "recent_bookings": Booking.objects.select_related("user", "vehicle").order_by("-pk")[:15],
    })


@login_required
def download_receipt(request, booking_id):
    user_id = rental_profile(request.user).pk
    booking = get_object_or_404(Booking, id=booking_id, user_id=user_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="booking-summary.pdf"'

    p = canvas.Canvas(response)

    p.drawString(100, 800, "Vehicle Rental Booking Summary")
    p.drawString(100, 760, f"User: {booking.user.name}")
    p.drawString(100, 740, f"Vehicle: {booking.vehicle.name}")
    p.drawString(100, 720, f"Start Date: {booking.start_date}")
    p.drawString(100, 700, f"End Date: {booking.end_date}")
    p.drawString(100, 680, f"Total Price: INR {booking.total_price}")
    p.drawString(100, 660, f"Status: {booking.display_status}")

    p.showPage()
    p.save()

    return response

class VehicleForm(forms.ModelForm):
    price_per_day = forms.DecimalField(max_digits=8, decimal_places=2,
                                      validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        model = Vehicle
        fields = ("name", "vehicle_type", "fuel_type", "location", "price_per_day", "vehicle_image")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["vehicle_image"].required = False

    def clean_vehicle_image(self):
        image = self.cleaned_data.get("vehicle_image")
        if getattr(image, "image", None):
            if image.size > 5 * 1024 * 1024 or max(image.image.size) > 4096:
                raise forms.ValidationError("Use an image up to 5 MB and 4096 pixels per side.")
            if image.image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("Choose a JPEG, PNG, or WebP image.")
        return image


@transaction.atomic
def create_listing(owner, form):
    CustomUser.objects.select_for_update().get(pk=owner.pk)
    if Vehicle.objects.filter(owner=owner, archived_at__isnull=True).count() >= 3:
        raise forms.ValidationError("You can list up to three vehicles at a time.")
    vehicle = form.save(commit=False)
    vehicle.owner = owner
    vehicle.save()
    return vehicle


def archive_listing(vehicle):
    if active_bookings().filter(vehicle=vehicle).exists():
        raise forms.ValidationError("Resolve open bookings before archiving this vehicle.")
    if vehicle.archived_at is None:
        vehicle.archived_at = timezone.now()
        vehicle.is_available = False
        vehicle.save(update_fields=["archived_at", "is_available"])


class ReportDatesForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
            self.add_error("end_date", "Return date must be on or after the start date.")
        return data


def completed_booking_values(owner, form):
    completed = Booking.objects.filter(vehicle__owner=owner, status=Booking.Status.RETURNED)
    if form.is_valid():
        for field, lookup in (("start_date", "gte"), ("end_date", "lte")):
            if value := form.cleaned_data[field]:
                completed = completed.filter(
                    models.Q(**{f"returned_at__date__{lookup}": value})
                    | models.Q(returned_at__isnull=True, **{f"end_date__{lookup}": value})
                )
    rows = list(completed.values("vehicle_id", "vehicle__name").annotate(
        bookings=models.Count("pk"), value=models.Sum("total_price"),
    ).order_by("vehicle__name", "vehicle_id"))
    return rows


def home(request):
    return redirect("/app/")


class FeedbackForm(forms.Form):
    rating = forms.TypedChoiceField(choices=[(i, i) for i in range(1, 6)], coerce=int)
    comment = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 4}))


class MaintenanceForm(BookingDatesForm):
    reason = forms.CharField(max_length=120)


def schedule_maintenance(vehicle, start_date, end_date, reason):
    overlap = {"start_date__lte": end_date, "end_date__gte": start_date}
    blocks = vehicle.maintenance_blocks
    if active_bookings().filter(vehicle=vehicle, **overlap).exists() or blocks.filter(**overlap).exists():
        raise forms.ValidationError("Those dates overlap an existing rental or maintenance block.")
    return blocks.create(start_date=start_date, end_date=end_date, reason=reason)


def react_app(request):
    index = settings.FRONTEND_BUILD / "index.html"
    if not index.is_file():
        raise Http404("Build the frontend before opening the marketplace.")
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response
