import os
from decimal import Decimal
from pathlib import Path

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from rental.models import CustomUser, Vehicle


class Command(BaseCommand):
    help = "Create a local demo renter, owner, and two vehicle listings."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.getenv("RENTAL_DEMO_PASSWORD")
        if not settings.DEBUG or not password or len(password) < 12:
            raise CommandError("Enable local debug and set RENTAL_DEMO_PASSWORD to at least 12 characters.")

        profiles = {}
        for role in ("owner", "renter"):
            username = f"rental-demo-{role}"
            email = f"{role}@rental-demo.example"
            account, created = get_user_model().objects.get_or_create(
                username=username, defaults={"email": email, "first_name": role.title()},
            )
            if not created and account.email != email:
                raise CommandError(f"The demo username {username} is already in use.")
            if created:
                account.set_password(password)
                account.save(update_fields=["password"])
            EmailAddress.objects.get_or_create(
                user=account, email=email, defaults={"primary": True, "verified": True},
            )
            profiles[role], _ = CustomUser.objects.get_or_create(
                account=account, defaults={"name": f"Demo {role.title()}", "email": email},
            )

        for name, kind, fuel, rate in (
            ("Hyundai i20", "Car", "Petrol", "1800.00"),
            ("Honda Activa", "Bike", "Petrol", "550.00"),
        ):
            vehicle, _ = Vehicle.objects.get_or_create(
                owner=profiles["owner"], name=name,
                defaults={"vehicle_type": kind, "fuel_type": fuel, "location": "Madurai",
                          "price_per_day": Decimal(rate)},
            )
            if not vehicle.vehicle_image:
                image = Path(__file__).resolve().parents[2] / "demo_images" / f"demo-{kind.lower()}.webp"
                vehicle.vehicle_image.save(image.name, ContentFile(image.read_bytes()))
        self.stdout.write(self.style.SUCCESS("Demo listings and accounts are ready."))
