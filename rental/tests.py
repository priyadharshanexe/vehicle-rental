from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Booking, CustomUser, Vehicle


class BookingPermissionsTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create(email="owner@example.com", name="Owner")
        self.renter = CustomUser.objects.create(email="renter@example.com", name="Renter")
        vehicle = Vehicle.objects.create(
            owner=self.owner, name="Car", vehicle_type="Car", price_per_day=100
        )
        self.booking = Booking.objects.create(
            user=self.renter, vehicle=vehicle, start_date=timezone.localdate(),
            end_date=timezone.localdate(), total_price=100
        )

    def sign_in(self, user):
        account = get_user_model().objects.create_user(
            username=user.email, email=user.email,
        ) if user.account_id is None else user.account
        user.account = account
        user.save(update_fields=["account"])
        self.client.force_login(account)

    def test_get_cannot_approve_booking(self):
        self.sign_in(self.owner)
        url = reverse("approve_booking", args=[self.booking.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "Pending")

    def test_only_vehicle_owner_can_approve(self):
        url = reverse("approve_booking", args=[self.booking.pk])
        self.sign_in(self.renter)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.sign_in(self.owner)
        self.assertRedirects(self.client.post(url), reverse("owner_bookings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "Confirmed")

    def test_only_renter_can_download_booking_pdf(self):
        url = reverse("download_receipt", args=[self.booking.pk])
        self.sign_in(self.owner)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.sign_in(self.renter)
        self.assertEqual(self.client.get(url)["Content-Type"], "application/pdf")

    def test_booking_rejects_invalid_dates_and_unavailable_vehicle(self):
        self.sign_in(self.renter)
        vehicle = self.booking.vehicle
        url = reverse("book_vehicle", args=[vehicle.pk])
        self.assertContains(self.client.post(url, {"start_date": "invalid"}), "Enter a valid date")
        vehicle.is_available = False
        vehicle.save(update_fields=["is_available"])
        today = timezone.localdate().isoformat()
        response = self.client.post(url, {"start_date": today, "end_date": today})
        self.assertContains(response, "This vehicle is no longer available.")
        self.assertEqual(Booking.objects.count(), 1)

    def test_booking_rejects_overlap_and_prices_one_day(self):
        self.sign_in(self.renter)
        today = timezone.localdate()
        self.booking.start_date = self.booking.end_date = today
        self.booking.save(update_fields=["start_date", "end_date"])
        url = reverse("book_vehicle", args=[self.booking.vehicle_id])
        response = self.client.post(url, {"start_date": today, "end_date": today})
        self.assertContains(response, "Vehicle already booked for these dates.")
        tomorrow = today + timedelta(days=1)
        response = self.client.post(url, {"start_date": tomorrow, "end_date": tomorrow})
        self.assertRedirects(response, reverse("my_bookings"))
        self.assertEqual(Booking.objects.get(start_date=tomorrow).total_price, 100)

    def test_only_owner_can_record_pickup_and_return_in_order(self):
        pickup = reverse("pickup_vehicle", args=[self.booking.pk])
        dropoff = reverse("return_vehicle", args=[self.booking.pk])
        self.booking.status = Booking.Status.CONFIRMED
        self.booking.save(update_fields=["status"])

        self.sign_in(self.renter)
        self.assertEqual(self.client.post(pickup).status_code, 404)
        self.sign_in(self.owner)
        self.client.post(dropoff)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.CONFIRMED)

        self.assertRedirects(self.client.post(pickup), reverse("owner_bookings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.IN_PROGRESS)
        self.assertIsNotNone(self.booking.picked_up_at)

        self.assertRedirects(self.client.post(dropoff), reverse("owner_bookings"))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.RETURNED)
        self.assertGreaterEqual(self.booking.returned_at, self.booking.picked_up_at)
