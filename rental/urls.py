from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("download-receipt/<int:booking_id>/", views.download_receipt, name="download_receipt"),
]
