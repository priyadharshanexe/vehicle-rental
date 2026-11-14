from django.conf import settings
from django.db import models
from django.utils import timezone


class CustomUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="rental_profile",
        null=True, blank=True,
    )

    def __str__(self):
        return self.email

class Vehicle(models.Model):

    VEHICLE_TYPE_CHOICES = [
        ('Bike', 'Bike'),
        ('Car', 'Car'),
    ]

    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES)
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    fuel_type = models.CharField(max_length=50)
    location = models.CharField(max_length=100, null=True, blank=True)
    vehicle_image = models.ImageField(upload_to='vehicles/')
    description = models.TextField(blank=True, max_length=3000)
    transmission = models.CharField(max_length=30, blank=True)
    seats = models.PositiveSmallIntegerField(null=True, blank=True)
    model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    pickup_instructions = models.TextField(blank=True, max_length=1000)
    is_available = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return self.name

class Booking(models.Model):

    class Status(models.TextChoices):
        PENDING = "Pending"
        CONFIRMED = "Confirmed"
        REJECTED = "Rejected"
        EXPIRED = "Expired"
        CANCELLED = "Cancelled"
        IN_PROGRESS = "In progress"
        RETURNED = "Returned"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    contact_name = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    pickup_notes = models.CharField(max_length=1000, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    quoted_daily_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    picked_up_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="booking_dates_in_order"),
            models.CheckConstraint(
                condition=models.Q(status__in=["Pending", "Confirmed", "Rejected", "Expired",
                                               "Cancelled", "In progress", "Returned"]),
                name="booking_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["vehicle", "status", "start_date"]),
            models.Index(fields=["user", "status"]),
        ]

    @property
    def display_status(self):
        if self.status == self.Status.PENDING and (
            self.start_date < timezone.localdate()
            or (self.expires_at and self.expires_at <= timezone.now())
        ):
            return self.Status.EXPIRED
        return self.status

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.user.name} - {self.vehicle.name}"

class MaintenanceBlock(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_blocks")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="maintenance_dates_in_order"),
        ]


class Feedback(models.Model):
    booking = models.OneToOneField(
        Booking, on_delete=models.CASCADE, null=True, blank=True, related_name="review",
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.vehicle.name}"

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "vehicle"], name="unique_saved_vehicle")]
