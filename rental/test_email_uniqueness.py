from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase


class EmailUniquenessTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.first = users.create_user(username="first")
        self.second = users.create_user(username="second")

    def test_only_one_primary_address_per_user(self):
        EmailAddress.objects.create(user=self.first, email="first@example.com", primary=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EmailAddress.objects.create(user=self.first, email="other@example.com", primary=True)
        EmailAddress.objects.create(user=self.first, email="other@example.com")

    def test_only_one_verified_owner_per_address(self):
        email = "shared@example.com"
        EmailAddress.objects.create(user=self.first, email=email, verified=True)
        pending = EmailAddress.objects.create(user=self.second, email=email)
        pending.verified = True
        with self.assertRaises(IntegrityError), transaction.atomic():
            pending.save(update_fields=["verified"])
