import logging
from datetime import timedelta
from django.shortcuts import render, redirect
from .models import CustomUser
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Vehicle
from .models import Booking
from decimal import Decimal

from django import forms
from django.core.paginator import Paginator
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Feedback, MaintenanceBlock

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


@login_required
def dashboard(request):
    profile = rental_profile(request.user)
    upcoming = active_bookings().filter(user=profile).select_related("vehicle").order_by("start_date").first()
    return render(request, "rental/dashboard.html", {"upcoming": upcoming})


def vehicle_list(request):
    vehicles = Vehicle.objects.filter(is_available=True, archived_at__isnull=True)
    filters = {key: request.GET.get(key, "").strip() for key in
               ("q", "type", "fuel", "location", "start_date", "end_date")}
    for key, lookup in (("q", "name__icontains"), ("type", "vehicle_type"),
                        ("fuel", "fuel_type__icontains"), ("location", "location__icontains")):
        if filters[key]:
            vehicles = vehicles.filter(**{lookup: filters[key]})
    dates = BookingDatesForm(request.GET if filters["start_date"] or filters["end_date"] else None)
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
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "rental/vehicle_list.html", {
        "page": Paginator(vehicles.order_by("name", "pk"), 12).get_page(request.GET.get("page")),
        "filters": filters, "dates": dates, "querystring": params.urlencode(),
    })


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
    days = (end_date - start_date).days + 1
    total_price = days * vehicle.price_per_day
    if not 0 < total_price <= Decimal("99999999.99"):
        raise forms.ValidationError("This rental cannot be priced for the selected dates.")
    return Booking.objects.create(
        user_id=user_id, vehicle=vehicle, start_date=start_date, end_date=end_date,
        total_price=total_price, quoted_daily_rate=vehicle.price_per_day,
        expires_at=timezone.now() + timedelta(hours=24),
    )


@login_required
def book_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    user = rental_profile(request.user)
    form = BookingDatesForm(request.POST if request.method == "POST" else None, initial=request.GET)
    if request.method == "POST" and form.is_valid():
        try:
            reserve_vehicle(user.pk, vehicle.pk, **form.cleaned_data)
        except forms.ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("my_bookings")

    booked_dates = active_bookings().filter(
        vehicle=vehicle,
        end_date__gte=timezone.localdate(),
    ).order_by("start_date")
    return render(request, "rental/book_vehicle.html", {
        "vehicle": vehicle, "booked_dates": booked_dates, "form": form,
        "maintenance": vehicle.maintenance_blocks.filter(end_date__gte=timezone.localdate()),
        "reviews": Feedback.objects.filter(vehicle=vehicle, booking__isnull=False).order_by("-created_at")[:5],
    })


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user_id=rental_profile(request.user).pk).select_related("vehicle", "review")
    return render(request, "rental/my_bookings.html", {
        "page": Paginator(bookings.order_by("-start_date", "-pk"), 15).get_page(request.GET.get("page")),
    })


@transaction.atomic
def change_booking_status(request, booking_id, destination, allowed, *, owner=False):
    profile = rental_profile(request.user)
    scope = {"vehicle__owner": profile} if owner else {"user": profile}
    reference = get_object_or_404(Booking, pk=booking_id, **scope)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=reference.vehicle_id)
    booking = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id)
    target = "owner_bookings" if owner else "my_bookings"
    if booking.display_status not in allowed:
        messages.error(request, "This booking has changed. Check its current status.")
        return redirect(target)

    today = timezone.localdate()
    if destination == Booking.Status.CANCELLED and booking.status == Booking.Status.CONFIRMED and today >= booking.start_date:
        messages.error(request, "Confirmed bookings can be cancelled before the pickup date.")
        return redirect(target)
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
    booking.status_changed_at = timezone.now()
    booking.status_changed_by = request.user
    booking.save(update_fields=[
        "status", "picked_up_at", "returned_at", "status_changed_at", "status_changed_by",
    ])
    logger.info("booking_status_changed booking_id=%s actor_id=%s status=%s", booking.pk, request.user.pk, destination)
    messages.success(request, f"Booking updated to {destination.lower()}.")
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

    def clean_vehicle_image(self):
        image = self.cleaned_data.get("vehicle_image")
        if getattr(image, "image", None):
            if image.size > 5 * 1024 * 1024 or max(image.image.size) > 4096:
                raise forms.ValidationError("Use an image up to 5 MB and 4096 pixels per side.")
            if image.image.format not in {"JPEG", "PNG", "WEBP"}:
                raise forms.ValidationError("Choose a JPEG, PNG, or WebP image.")
        return image


@login_required
def add_vehicle(request):
    owner = rental_profile(request.user)
    form = VehicleForm(request.POST if request.method == "POST" else None, request.FILES)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            CustomUser.objects.select_for_update().get(pk=owner.pk)
            if Vehicle.objects.filter(owner=owner, archived_at__isnull=True).count() < 3:
                vehicle = form.save(commit=False)
                vehicle.owner = owner
                vehicle.save()
                return redirect("my_vehicles")
        form.add_error(None, "You can list up to three vehicles at a time.")
    return render(request, "rental/vehicle_form.html", {"form": form, "heading": "List a vehicle"})


@login_required
def my_vehicles(request):

    owner = rental_profile(request.user)

    vehicles = Vehicle.objects.filter(owner=owner)

    return render(request, "rental/my_vehicles.html", {"vehicles": vehicles})

@require_POST
@login_required
@transaction.atomic
def toggle_vehicle(request, vehicle_id):

    user_id = rental_profile(request.user).pk
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(), id=vehicle_id, owner_id=user_id, archived_at__isnull=True,
    )

    if vehicle.is_available:
        vehicle.is_available = False
    else:
        vehicle.is_available = True

    vehicle.save(update_fields=["is_available"])

    return redirect('my_vehicles')

@require_POST
@login_required
@transaction.atomic
def archive_vehicle(request, vehicle_id):
    owner = rental_profile(request.user)
    vehicle = get_object_or_404(Vehicle.objects.select_for_update(), pk=vehicle_id, owner=owner)
    open_bookings = active_bookings().filter(vehicle=vehicle)
    if open_bookings.exists():
        messages.error(request, "Resolve open bookings before archiving this vehicle.")
    elif vehicle.archived_at is None:
        vehicle.archived_at = timezone.now()
        vehicle.is_available = False
        vehicle.save(update_fields=["archived_at", "is_available"])
        messages.success(request, "Vehicle archived. Its booking history is preserved.")
    return redirect("my_vehicles")


@login_required
@transaction.atomic
def edit_vehicle(request, vehicle_id):
    vehicles = Vehicle.objects.select_for_update() if request.method == "POST" else Vehicle.objects
    vehicle = get_object_or_404(vehicles, pk=vehicle_id, owner=rental_profile(request.user),
                               archived_at__isnull=True)
    form = VehicleForm(request.POST if request.method == "POST" else None, request.FILES, instance=vehicle)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("my_vehicles")
    return render(request, "rental/vehicle_form.html", {"form": form, "heading": "Edit vehicle"})


class ReportDatesForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def clean(self):
        data = super().clean()
        if data.get("start_date") and data.get("end_date") and data["end_date"] < data["start_date"]:
            self.add_error("end_date", "Return date must be on or after the start date.")
        return data


@login_required
def owner_earnings(request):
    owner = rental_profile(request.user)
    form = ReportDatesForm(request.GET)
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
    return render(request, "rental/owner_earnings.html", {
        "rows": rows, "total": sum(row["value"] for row in rows), "form": form,
    })


@login_required
def owner_bookings(request):

    owner = rental_profile(request.user)

    bookings = Booking.objects.filter(vehicle__owner=owner).select_related("vehicle", "user")
    queue = request.GET.get("queue", "requests")
    status = {"requests": Booking.Status.PENDING, "pickups": Booking.Status.CONFIRMED,
              "returns": Booking.Status.IN_PROGRESS}.get(queue)
    if status:
        bookings = bookings.filter(pk__in=active_bookings().filter(status=status).values("pk"))
    return render(request, "rental/owner_bookings.html", {
        "page": Paginator(bookings.order_by("start_date", "pk"), 15).get_page(request.GET.get("page")),
        "queue": queue, "today": timezone.localdate(),
        "querystring": f"queue={queue}" if queue in {"requests", "pickups", "returns", "all"} else "",
    })

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

class FeedbackForm(forms.Form):
    rating = forms.TypedChoiceField(choices=[(i, i) for i in range(1, 6)], coerce=int)
    comment = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 4}))


@login_required
@transaction.atomic
def add_feedback(request, booking_id):
    profile = rental_profile(request.user)
    bookings = Booking.objects.select_for_update() if request.method == "POST" else Booking.objects
    booking = get_object_or_404(bookings, pk=booking_id, user=profile, status=Booking.Status.RETURNED)
    if Feedback.objects.filter(booking=booking).exists():
        return redirect("my_bookings")
    form = FeedbackForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        Feedback.objects.create(booking=booking, vehicle=booking.vehicle, user=profile, **form.cleaned_data)
        messages.success(request, "Review published.")
        return redirect("my_bookings")
    return render(request, "rental/add_feedback.html", {"booking": booking, "form": form})


class MaintenanceForm(BookingDatesForm):
    reason = forms.CharField(max_length=120)


@login_required
@transaction.atomic
def vehicle_maintenance(request, vehicle_id):
    owner = rental_profile(request.user)
    vehicles = Vehicle.objects.select_for_update() if request.method == "POST" else Vehicle.objects
    vehicle = get_object_or_404(vehicles, pk=vehicle_id, owner=owner, archived_at__isnull=True)
    blocks = vehicle.maintenance_blocks.order_by("start_date", "pk")
    form = MaintenanceForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and "remove_block" in request.POST:
        block = get_object_or_404(blocks, pk=request.POST["remove_block"])
        block.delete()
        return redirect("vehicle_maintenance", vehicle.pk)
    if request.method == "POST" and form.is_valid():
        overlap = {"start_date__lte": form.cleaned_data["end_date"],
                   "end_date__gte": form.cleaned_data["start_date"]}
        if active_bookings().filter(vehicle=vehicle, **overlap).exists() or blocks.filter(**overlap).exists():
            form.add_error(None, "Those dates overlap an existing rental or maintenance block.")
        else:
            blocks.create(vehicle=vehicle, **form.cleaned_data)
            return redirect("vehicle_maintenance", vehicle.pk)
    return render(request, "rental/maintenance.html", {"vehicle": vehicle, "form": form, "blocks": blocks})
