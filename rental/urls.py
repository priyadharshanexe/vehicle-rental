from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('book/<int:vehicle_id>/', views.book_vehicle, name='book_vehicle'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('pickup-vehicle/<int:booking_id>/', views.pickup_vehicle, name='pickup_vehicle'),
    path('return-vehicle/<int:booking_id>/', views.return_vehicle, name='return_vehicle'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path('download-receipt/<int:booking_id>/', views.download_receipt, name='download_receipt'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('my-vehicles/', views.my_vehicles, name='my_vehicles'),
    path('toggle-vehicle/<int:vehicle_id>/', views.toggle_vehicle, name='toggle_vehicle'),
    path('archive-vehicle/<int:vehicle_id>/', views.archive_vehicle, name='archive_vehicle'),
    path('edit-vehicle/<int:vehicle_id>/', views.edit_vehicle, name='edit_vehicle'),
    path('owner-earnings/', views.owner_earnings, name='owner_earnings'),
    path('owner-bookings/', views.owner_bookings, name='owner_bookings'),
    path('approve-booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('reject-booking/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('vehicles/<int:vehicle_id>/maintenance/', views.vehicle_maintenance, name='vehicle_maintenance'),
    path('feedback/<int:booking_id>/', views.add_feedback, name='add_feedback'),
    ]
