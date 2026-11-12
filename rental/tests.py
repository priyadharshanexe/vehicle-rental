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

    def test_archive_preserves_booking_history_and_rejects_open_rentals(self):
        self.sign_in(self.owner)
        vehicle = self.booking.vehicle
        url = reverse("archive_vehicle", args=[vehicle.pk])
        self.assertRedirects(self.client.post(url), reverse("my_vehicles"))
        vehicle.refresh_from_db()
        self.assertIsNone(vehicle.archived_at)

        self.booking.status = Booking.Status.RETURNED
        self.booking.save(update_fields=["status"])
        self.assertRedirects(self.client.post(url), reverse("my_vehicles"))
        vehicle.refresh_from_db()
        self.assertIsNotNone(vehicle.archived_at)
        self.assertFalse(vehicle.is_available)
        self.assertTrue(Booking.objects.filter(pk=self.booking.pk, vehicle=vehicle).exists())

    def test_expired_request_cannot_be_approved_and_releases_vehicle(self):
        self.booking.expires_at = timezone.now() - timedelta(seconds=1)
        self.booking.save(update_fields=["expires_at"])
        self.sign_in(self.owner)
        self.client.post(reverse("approve_booking", args=[self.booking.pk]))
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.display_status, Booking.Status.EXPIRED)

        self.sign_in(self.renter)
        today = timezone.localdate()
        response = self.client.post(reverse("book_vehicle", args=[self.booking.vehicle_id]), {
            "start_date": today, "end_date": today,
        })
        self.assertRedirects(response, reverse("my_bookings"))
        quote = Booking.objects.exclude(pk=self.booking.pk).get()
        vehicle = self.booking.vehicle
        vehicle.price_per_day = 200
        vehicle.save(update_fields=["price_per_day"])
        quote.refresh_from_db()
        self.assertEqual(quote.quoted_daily_rate, 100)
        self.assertEqual(quote.total_price, 100)

    def test_maintenance_blocks_search_and_reservation(self):
        self.booking.status = Booking.Status.REJECTED
        self.booking.save(update_fields=["status"])
        self.sign_in(self.owner)
        today = timezone.localdate()
        dates = {"start_date": today, "end_date": today}
        vehicle_id = self.booking.vehicle_id
        maintenance = reverse("vehicle_maintenance", args=[vehicle_id])
        self.assertRedirects(self.client.post(maintenance, {**dates, "reason": "Service"}), maintenance)
        self.sign_in(self.renter)
        self.assertNotContains(self.client.get(reverse("vehicle_list"), dates), "View Car")
        response = self.client.post(reverse("book_vehicle", args=[vehicle_id]), dates)
        self.assertContains(response, "scheduled maintenance")

    def test_only_renter_can_review_completed_booking_once(self):
        from .models import Feedback

        url = reverse("add_feedback", args=[self.booking.pk])
        data = {"rating": 5, "comment": "Easy pickup"}
        self.sign_in(self.renter)
        self.assertEqual(self.client.post(url, data).status_code, 404)
        self.booking.status = Booking.Status.RETURNED
        self.booking.save(update_fields=["status"])
        self.sign_in(self.owner)
        self.assertEqual(self.client.post(url, data).status_code, 404)
        self.sign_in(self.renter)
        self.assertRedirects(self.client.post(url, data), reverse("my_bookings"))
        self.assertRedirects(self.client.post(url, data), reverse("my_bookings"))
        self.assertEqual(Feedback.objects.filter(booking=self.booking).count(), 1)
