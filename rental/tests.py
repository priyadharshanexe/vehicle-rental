from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Booking, CustomUser, Vehicle


class BookingPermissionsTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create(email="owner@example.com", name="Owner")
        self.renter = CustomUser.objects.create(email="renter@example.com", name="Renter")
        vehicle = Vehicle.objects.create(
            owner=self.owner, name="Car", vehicle_type="Car", price_per_day=100
        )
        self.booking = Booking.objects.create(
            user=self.renter, vehicle=vehicle, start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 1), total_price=100
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
