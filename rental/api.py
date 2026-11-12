from collections.abc import Mapping

from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import generics, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Vehicle
from .views import BookingDatesForm, rental_profile, reserve_vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ("id", "name", "vehicle_type", "fuel_type", "location", "price_per_day", "vehicle_image")


class BookingSerializer(serializers.ModelSerializer):
    vehicle = VehicleSerializer(read_only=True)
    status = serializers.CharField(source="display_status")

    class Meta:
        model = Booking
        fields = ("id", "vehicle", "start_date", "end_date", "status", "total_price", "quoted_daily_rate")


@never_cache
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def session(request):
    user = request.user
    return Response({
        "csrf_token": get_token(request),
        "user": {"id": user.pk, "name": user.get_full_name() or user.username}
        if user.is_authenticated else None,
    })


class VehicleList(generics.ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.filter(is_available=True, archived_at__isnull=True).order_by("name", "pk")


@never_cache
@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def bookings(request):
    profile = rental_profile(request.user)
    if request.method == "GET":
        rows = Booking.objects.filter(user=profile).select_related("vehicle").order_by("-start_date", "-pk")
        return Response(BookingSerializer(rows, many=True, context={"request": request}).data)
    if not isinstance(request.data, Mapping):
        return Response({"detail": "Expected an object."}, status=status.HTTP_400_BAD_REQUEST)
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
        booking = reserve_vehicle(profile.pk, vehicle.pk, **dates.cleaned_data)
    except ValidationError as error:
        return Response({"detail": error.messages[0]}, status=status.HTTP_409_CONFLICT)
    return Response(
        BookingSerializer(booking, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )
