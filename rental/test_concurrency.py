from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from .models import Booking, CustomUser, Vehicle
from .views import reserve_vehicle


class ReservationConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_requests_leave_one_reservation(self):
        owner = CustomUser.objects.create(email="owner@example.com", name="Owner")
        renters = [
            CustomUser.objects.create(email=f"renter{i}@example.com", name=f"Renter {i}")
            for i in range(2)
        ]
        vehicle = Vehicle.objects.create(
            owner=owner, name="Car", vehicle_type="Car", price_per_day=100,
        )
        results = self.reserve_in_parallel([(renter.pk, vehicle.pk) for renter in renters])
        self.assertCountEqual(results, ["reserved", "Vehicle already booked for these dates."])
        self.assertEqual(Booking.objects.filter(vehicle=vehicle).count(), 1)

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_requests_respect_renter_limit(self):
        renter = CustomUser.objects.create(email="renter@example.com", name="Renter")
        vehicles = [Vehicle.objects.create(name=f"Car {i}", vehicle_type="Car", price_per_day=100)
                    for i in range(4)]
        today = timezone.localdate()
        for vehicle in vehicles[:2]:
            reserve_vehicle(renter.pk, vehicle.pk, today, today)
        results = self.reserve_in_parallel([(renter.pk, vehicle.pk) for vehicle in vehicles[2:]])
        self.assertCountEqual(results, ["reserved", "You can only have 3 active bookings at a time."])
        self.assertEqual(Booking.objects.filter(user=renter).count(), 3)

    def reserve_in_parallel(self, requests):
        barrier = Barrier(2)
        rental_date = timezone.localdate() + timedelta(days=1)

        def reserve(request):
            renter_id, vehicle_id = request
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                reserve_vehicle(renter_id, vehicle_id, rental_date, rental_date)
                return "reserved"
            except ValidationError as error:
                return error.messages[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(reserve, requests))

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_listings_respect_owner_limit(self):
        from io import BytesIO
        from tempfile import TemporaryDirectory

        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import Client, override_settings
        from django.urls import reverse
        from PIL import Image

        account = get_user_model().objects.create_user(username="listing-owner")
        owner = CustomUser.objects.create(account=account, name="Owner", email="owner@example.com")
        for name in ("Existing car", "Existing bike"):
            Vehicle.objects.create(owner=owner, name=name, vehicle_type="Car", price_per_day=100)
        barrier = Barrier(2)
        image = BytesIO()
        Image.new("RGB", (20, 20), "white").save(image, format="PNG")

        def publish(name):
            close_old_connections()
            try:
                client = Client()
                client.force_login(account)
                barrier.wait(timeout=10)
                response = client.post(reverse("add_vehicle"), {
                    "name": name, "vehicle_type": "Car", "fuel_type": "Petrol",
                    "price_per_day": "100.00", "location": "Madurai",
                    "vehicle_image": SimpleUploadedFile("car.png", image.getvalue(), "image/png"),
                }, secure=True)
                return response.status_code, response.content
            finally:
                connections.close_all()

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(publish, ["New listing A", "New listing B"]))
        self.assertCountEqual([status for status, _ in results], [200, 302])
        self.assertIn(b"You can list up to three vehicles at a time.", next(
            body for status, body in results if status == 200
        ))
        self.assertEqual(Vehicle.objects.filter(owner=owner, archived_at__isnull=True).count(), 3)
