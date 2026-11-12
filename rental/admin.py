from django.contrib import admin
from .models import CustomUser, Vehicle

admin.site.register(CustomUser)
admin.site.register(Vehicle)
