from collections.abc import Mapping

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.http import Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from rest_framework import generics, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Feedback, Vehicle, Favorite
from .views import (
    BookingDatesForm, FeedbackForm, MaintenanceForm, ReportDatesForm, VehicleForm,
    active_bookings, archive_listing, completed_booking_values, create_listing,
    rental_profile, rental_quote, reserve_vehicle, schedule_maintenance, search_vehicles, transition_booking,
)


class VehicleSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    def get_rating(self, vehicle):
        return self._reviews(vehicle)["average"]

    def get_review_count(self, vehicle):
        return self._reviews(vehicle)["count"]

    def _reviews(self, vehicle):
        if hasattr(vehicle, "review_average"):
            return {"average": vehicle.review_average, "count": vehicle.review_total}
        if not hasattr(vehicle, "_review_summary"):
            vehicle._review_summary = Feedback.objects.filter(vehicle=vehicle, booking__isnull=False).aggregate(average=Avg("rating"), count=Count("id"))
        return vehicle._review_summary

    class Meta:
        model = Vehicle
        fields = ("id", "name", "vehicle_type", "fuel_type", "location", "price_per_day", "vehicle_image", "description", "transmission", "seats", "model_year", "pickup_instructions", "rating", "review_count")


class CheckoutContactSerializer(serializers.Serializer):
    contact_name = serializers.CharField(max_length=100)
    contact_phone = serializers.RegexField(r"^\+?[0-9 ()-]{7,30}$")
    pickup_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    accepted_conditions = serializers.BooleanField()

    def validate_accepted_conditions(self, value):
        if not value:
            raise serializers.ValidationError("Review and accept the rental conditions before requesting.")
        return value


class BookingSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    status = serializers.CharField(source="display_status")
    renter_name = serializers.CharField(source="user.name")
    reviewed = serializers.SerializerMethodField()
    overdue = serializers.SerializerMethodField()

    def get_overdue(self, booking):
        return booking.status == Booking.Status.IN_PROGRESS and booking.end_date < timezone.localdate()

    def get_reviewed(self, booking):
        return hasattr(booking, "review")

    class Meta:
        model = Booking
        fields = ("id", "vehicle", "start_date", "end_date", "status", "total_price", "quoted_daily_rate",
                  "renter_name", "contact_name", "contact_phone", "pickup_notes", "picked_up_at", "returned_at", "reviewed", "overdue", "status_changed_at")


@never_cache
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def session(request):
    user = request.user
    return Response({
        "csrf_token": get_token(request),
        "google_enabled": settings.GOOGLE_SIGN_IN_ENABLED,
        "user": {"id": user.pk, "name": user.get_full_name() or user.username}
        if user.is_authenticated else None,
    })


class CatalogPagination(PageNumberPagination):
    page_size = 12


class VehicleList(generics.ListAPIView):
    pagination_class = CatalogPagination
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.filter(is_available=True, archived_at__isnull=True).order_by("name", "pk")

    def list(self, request, *args, **kwargs):
        vehicles, _, dates = search_vehicles(request.query_params)
        if dates.is_bound and not dates.is_valid():
            return Response(dates.errors, status=400)
        rows = self.paginate_queryset(vehicles.annotate(review_average=Avg("feedback__rating", filter=Q(feedback__booking__isnull=False)), review_total=Count("feedback", filter=Q(feedback__booking__isnull=False))).order_by("name", "pk"))
        return self.get_paginated_response(self.get_serializer(rows, many=True).data)


@never_cache
@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def bookings(request):
    profile = rental_profile(request.user)
    if request.method == "GET":
        rows = Booking.objects.filter(user=profile).select_related("vehicle", "user", "review").order_by("-start_date", "-pk")
        return Response(BookingSerializer(rows, many=True, context={"request": request}).data)
    if not isinstance(request.data, Mapping):
        return Response({"detail": "Expected an object."}, status=status.HTTP_400_BAD_REQUEST)
    contact = None
    if request.data.get("checkout"):
        contact = CheckoutContactSerializer(data=request.data)
        if not contact.is_valid():
            return Response(contact.errors, status=400)
    vehicle_id = serializers.IntegerField(min_value=1)
    try:
        pk = vehicle_id.run_validation(request.data.get("vehicle_id"))
    except serializers.ValidationError as error:
        return Response({"vehicle_id": error.detail}, status=status.HTTP_400_BAD_REQUEST)
    vehicle = get_object_or_404(Vehicle, pk=pk)
    dates = BookingDatesForm(request.data)
    if not dates.is_valid():
        return Response(dates.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():
            booking = reserve_vehicle(profile.pk, vehicle.pk, **dates.cleaned_data)
            if contact is not None:
                for field in ("contact_name", "contact_phone", "pickup_notes"):
                    setattr(booking, field, contact.validated_data.get(field, ""))
                booking.save(update_fields=["contact_name", "contact_phone", "pickup_notes"])
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
    return Response(
        BookingSerializer(booking, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )

class FleetVehicleSerializer(VehicleSerializer):
    class Meta(VehicleSerializer.Meta):
        fields = (*VehicleSerializer.Meta.fields, "is_available", "archived_at")


class VehicleDetail(generics.RetrieveAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = VehicleSerializer
    queryset = VehicleList.queryset.select_related("owner")

    def retrieve(self, request, *args, **kwargs):
        vehicle = self.get_object()
        host_name = vehicle.owner.name.strip() if vehicle.owner else ""
        return Response({
            **self.get_serializer(vehicle).data,
            "host_name": host_name if "@" not in host_name else "",
            "unavailable": [
                *active_bookings().filter(vehicle=vehicle).values("start_date", "end_date"),
                *vehicle.maintenance_blocks.values("start_date", "end_date"),
            ],
            "reviews": list(Feedback.objects.filter(vehicle=vehicle, booking__isnull=False)
                            .order_by("-created_at").values("id", "rating", "comment")[:5]),
        })


class OwnerBookings(generics.ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return Booking.objects.filter(vehicle__owner__account=self.request.user).select_related(
            "vehicle", "user", "review"
        ).order_by("start_date", "pk")


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def booking_action(request, pk, action):
    actions = {
        "cancel": (Booking.Status.CANCELLED, (Booking.Status.PENDING, Booking.Status.CONFIRMED), False),
        "approve": (Booking.Status.CONFIRMED, (Booking.Status.PENDING,), True),
        "reject": (Booking.Status.REJECTED, (Booking.Status.PENDING,), True),
        "pickup": (Booking.Status.IN_PROGRESS, (Booking.Status.CONFIRMED,), True),
        "return": (Booking.Status.RETURNED, (Booking.Status.IN_PROGRESS,), True),
    }
    if action not in actions:
        raise Http404
    destination, allowed, owner = actions[action]
    try:
        booking = transition_booking(request.user, pk, destination, allowed, owner=owner)
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=409)
    return Response(BookingSerializer(booking, context={"request": request}).data)


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def fleet(request):
    owner = rental_profile(request.user)
    if request.method == "GET":
        vehicles = Vehicle.objects.filter(owner=owner).order_by("archived_at", "name", "pk")
        return Response(FleetVehicleSerializer(vehicles, many=True, context={"request": request}).data)
    form = VehicleForm(request.data, request.FILES)
    if not form.is_valid():
        return Response(form.errors, status=400)
    try:
        vehicle = create_listing(owner, form)
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=409)
    return Response(FleetVehicleSerializer(vehicle, context={"request": request}).data, status=201)


@api_view(["PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def fleet_vehicle(request, pk):
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(), pk=pk, owner__account=request.user,
        archived_at__isnull=True,
    )
    if request.method == "DELETE":
        try:
            archive_listing(vehicle)
        except ValidationError as error:
            return Response({"detail": error.messages[0]}, status=409)
        return Response(status=204)
    if set(request.data) == {"is_available"}:
        field = serializers.BooleanField()
        try:
            vehicle.is_available = field.run_validation(request.data["is_available"])
        except serializers.ValidationError as error:
            return Response({"is_available": error.detail}, status=400)
        vehicle.save(update_fields=["is_available"])
        return Response(FleetVehicleSerializer(vehicle, context={"request": request}).data)
    data = {field: request.data.get(field, getattr(vehicle, field)) for field in VehicleForm.Meta.fields
            if field != "vehicle_image"}
    form = VehicleForm(data, request.FILES, instance=vehicle)
    if not form.is_valid():
        return Response(form.errors, status=400)
    vehicle = form.save()
    return Response(FleetVehicleSerializer(vehicle, context={"request": request}).data)

@api_view(["GET", "POST", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def maintenance(request, pk, block_id=None):
    vehicles = Vehicle.objects.select_for_update() if request.method != "GET" else Vehicle.objects
    vehicle = get_object_or_404(vehicles, pk=pk, owner__account=request.user, archived_at__isnull=True)
    blocks = vehicle.maintenance_blocks.order_by("start_date", "pk")
    if request.method == "DELETE":
        get_object_or_404(blocks, pk=block_id).delete()
        return Response(status=204)
    if request.method == "GET":
        return Response(list(blocks.values("id", "start_date", "end_date", "reason")))
    form = MaintenanceForm(request.data)
    if not form.is_valid():
        return Response(form.errors, status=400)
    try:
        block = schedule_maintenance(vehicle, **form.cleaned_data)
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=409)
    return Response({"id": block.pk, **form.cleaned_data}, status=201)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def booking_values(request):
    form = ReportDatesForm(request.query_params)
    if not form.is_valid():
        return Response(form.errors, status=400)
    rows = completed_booking_values(rental_profile(request.user), form)
    for row in rows:
        row["value"] = str(row["value"])
    return Response(rows)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@transaction.atomic
def review(request, pk):
    booking = get_object_or_404(Booking.objects.select_for_update(), pk=pk,
                               user__account=request.user, status=Booking.Status.RETURNED)
    if Feedback.objects.filter(booking=booking).exists():
        return Response({"detail": "You have already reviewed this booking."}, status=409)
    form = FeedbackForm(request.data)
    if not form.is_valid():
        return Response(form.errors, status=400)
    Feedback.objects.create(booking=booking, vehicle_id=booking.vehicle_id,
                            user_id=booking.user_id, **form.cleaned_data)
    return Response(status=201)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def quote(request, pk):
    vehicle = get_object_or_404(VehicleList.queryset, pk=pk)
    form = BookingDatesForm(request.query_params)
    if not form.is_valid():
        return Response(form.errors, status=400)
    try:
        days, total = rental_quote(vehicle, **form.cleaned_data)
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=409)
    return Response({"days": days, "total_price": str(total)})


@api_view(["GET", "POST", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def favorites(request, pk=None):
    if request.method == "GET":
        rows = Vehicle.objects.filter(favorite__user=request.user, archived_at__isnull=True, is_available=True)
        return Response(VehicleSerializer(rows, many=True, context={"request": request}).data)
    vehicle = get_object_or_404(Vehicle, pk=pk, archived_at__isnull=True, is_available=True)
    if request.method == "DELETE":
        Favorite.objects.filter(user=request.user, vehicle=vehicle).delete()
        return Response(status=204)
    Favorite.objects.get_or_create(user=request.user, vehicle=vehicle)
    return Response({"saved": True})
