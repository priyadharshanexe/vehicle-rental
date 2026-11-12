from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Vehicle


class BookingApiTests(TestCase):
    def test_booking_requires_session_and_csrf_and_reuses_overlap_check(self):
        client = Client(enforce_csrf_checks=True)
        url = reverse("api_bookings")
        self.assertEqual(client.get(url, secure=True).status_code, 403)
        vehicle = Vehicle.objects.create(name="Car", vehicle_type="Car", price_per_day=125)
        user = get_user_model().objects.create_user(username="renter")
        client.force_login(user)
        today = timezone.localdate().isoformat()
        data = {"vehicle_id": vehicle.pk, "start_date": today, "end_date": today}
        self.assertEqual(client.post(url, data, secure=True).status_code, 403)
        csrf = client.get(reverse("api_session"), secure=True).json()["csrf_token"]
        response = client.post(url, data, secure=True, HTTP_X_CSRFTOKEN=csrf,
                               HTTP_REFERER="https://testserver/")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["total_price"], "125.00")
        response = client.post(url, data, secure=True, HTTP_X_CSRFTOKEN=csrf,
                               HTTP_REFERER="https://testserver/")
        self.assertEqual(response.status_code, 409)
