from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountFlowTests(TestCase):
    def test_recovery_sends_link_for_legacy_account_without_usable_password(self):
        user = get_user_model().objects.create_user(
            username="legacy-renter", email="legacy-renter@example.com",
        )
        self.assertFalse(user.has_usable_password())
        response = self.client.get(reverse("account_reset_password"), secure=True)
        self.assertContains(response, "Password Reset")
        self.assertContains(response, "marketplace.css")
        response = self.client.post(
            reverse("account_reset_password"), {"email": user.email}, secure=True,
        )
        self.assertRedirects(response, reverse("account_reset_password_done"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        self.assertIn("/accounts/password/reset/key/", mail.outbox[0].body)
