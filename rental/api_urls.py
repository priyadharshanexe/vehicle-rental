from django.urls import path

from . import api

urlpatterns = [
    path("session/", api.session, name="api_session"),
    path("vehicles/", api.VehicleList.as_view(), name="api_vehicle_list"),
    path("bookings/", api.bookings, name="api_bookings"),
]
