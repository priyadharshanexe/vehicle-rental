from django.urls import path

from . import api

urlpatterns = [
    path("session/", api.session, name="api_session"),
    path("vehicles/", api.VehicleList.as_view(), name="api_vehicle_list"),
    path("vehicles/<int:pk>/quote/", api.quote, name="api_quote"),
    path("vehicles/<int:pk>/", api.VehicleDetail.as_view(), name="api_vehicle_detail"),
    path("owner/bookings/", api.OwnerBookings.as_view(), name="api_owner_bookings"),
    path("owner/fleet/", api.fleet, name="api_fleet"),
    path("owner/fleet/<int:pk>/", api.fleet_vehicle, name="api_fleet_vehicle"),
    path("owner/fleet/<int:pk>/maintenance/", api.maintenance, name="api_maintenance"),
    path("owner/fleet/<int:pk>/maintenance/<int:block_id>/", api.maintenance, name="api_maintenance_block"),
    path("owner/value/", api.booking_values, name="api_booking_values"),
    path("bookings/<int:pk>/review/", api.review, name="api_review"),
    path("bookings/<int:pk>/<str:action>/", api.booking_action, name="api_booking_action"),
    path("bookings/", api.bookings, name="api_bookings"),
]
