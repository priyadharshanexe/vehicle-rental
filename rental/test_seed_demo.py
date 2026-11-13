from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import TestCase, override_settings

from .models import Booking, Feedback, MaintenanceBlock, Vehicle
from .views import active_bookings


class SeedDemoTests(TestCase):
    @patch.dict("os.environ", {"RENTAL_DEMO_PASSWORD": "local-test-demo-only"})
    @override_settings(DEBUG=True)
    def test_populates_consistent_records_without_duplicates_or_emails(self):
        real = get_user_model().objects.create_user("customer", "customer@example.com")
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            call_command("seed_demo")
            call_command("seed_demo")

        self.assertEqual(Vehicle.objects.count(), 10)
        self.assertEqual(Booking.objects.count(), 8)
        self.assertEqual(Feedback.objects.count(), 2)
        self.assertEqual(MaintenanceBlock.objects.count(), 3)
        self.assertEqual(active_bookings().count(), 3)
        owners = Vehicle.objects.values("owner").annotate(listings=Count("id"))
        self.assertEqual(len(owners), 4)
        self.assertTrue(all(owner["listings"] <= 3 for owner in owners))
        self.assertEqual(len(mail.outbox), 0)
        real.refresh_from_db()
        self.assertEqual(real.email, "customer@example.com")
        for booking in Booking.objects.all():
            self.assertEqual(booking.total_price, booking.quoted_daily_rate * booking.days)
            if booking.returned_at:
                self.assertLess(booking.picked_up_at, booking.returned_at)
        for review in Feedback.objects.select_related("booking"):
            self.assertEqual(review.booking.status, Booking.Status.RETURNED)
        for booking in active_bookings():
            overlaps = dict(start_date__lte=booking.end_date, end_date__gte=booking.start_date)
            self.assertFalse(active_bookings().filter(vehicle=booking.vehicle, **overlaps).exclude(pk=booking.pk).exists())
            self.assertFalse(booking.vehicle.maintenance_blocks.filter(**overlaps).exists())

    @patch.dict("os.environ", {"RENTAL_DEMO_PASSWORD": "local-test-demo-only"})
    @override_settings(DEBUG=False)
    def test_refuses_to_seed_outside_debug(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo")
