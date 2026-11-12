from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('book/<int:vehicle_id>/', views.book_vehicle, name='book_vehicle'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('return-vehicle/<int:booking_id>/', views.return_vehicle, name='return_vehicle'),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path('download-receipt/<int:booking_id>/', views.download_receipt, name='download_receipt'),
    path('add-vehicle/', views.add_vehicle, name='add_vehicle'),
    path('my-vehicles/', views.my_vehicles, name='my_vehicles'),
    path('toggle-vehicle/<int:vehicle_id>/', views.toggle_vehicle, name='toggle_vehicle'),
    path('delete-vehicle/<int:vehicle_id>/', views.delete_vehicle, name='delete_vehicle'),
    path('edit-vehicle/<int:vehicle_id>/', views.edit_vehicle, name='edit_vehicle'),
    path('owner-earnings/', views.owner_earnings, name='owner_earnings'),
    path('owner-bookings/', views.owner_bookings, name='owner_bookings'),
    path('approve-booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('reject-booking/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('feedback/<int:vehicle_id>/', views.add_feedback, name='add_feedback'),
    ]
