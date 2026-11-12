from django.db import models


class CustomUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    password = models.CharField(max_length=255)

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
    is_available = models.BooleanField(default=True)


    def __str__(self):
        return self.name

class Booking(models.Model):

    STATUS_CHOICES = [
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
    max_length=20,
    default="Pending"
)

    def __str__(self):
        return f"{self.user.name} - {self.vehicle.name}"

class Feedback(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.vehicle.name}"