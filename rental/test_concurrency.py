from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import TransactionTestCase, skipUnlessDBFeature

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
        barrier = Barrier(2)
        rental_date = date(2030, 1, 1)

        def reserve(renter_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                reserve_vehicle(renter_id, vehicle.pk, rental_date, rental_date)
                return "reserved"
            except ValidationError as error:
                return error.messages[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, [renter.pk for renter in renters]))

        self.assertCountEqual(results, ["reserved", "Vehicle already booked for these dates."])
        self.assertEqual(Booking.objects.filter(vehicle=vehicle).count(), 1)
