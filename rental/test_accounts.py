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
        self.assertIn("/app/reset-password/", mail.outbox[0].body)

    def test_headless_signup_email_verification_and_sign_in(self):
        import re
        from urllib.parse import unquote

        from allauth.account.models import EmailAddress
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        csrf = client.get(reverse("api_session"), secure=True).json()["csrf_token"]
        email = "new-renter@example.com"
        password = "Fresh-Rental-Example-246"
        data = {"email": email, "password": password}

        def submit(path, body):
            return client.post(
                f"/auth/browser/v1/auth/{path}", body, content_type="application/json",
                secure=True, HTTP_X_CSRFTOKEN=csrf, HTTP_REFERER="https://testserver/",
            )

        self.assertEqual(submit("signup", data).status_code, 401)
        self.assertFalse(EmailAddress.objects.get(email=email).verified)
        key = unquote(re.search(r"/app/verify-email/([^\s]+)", mail.outbox[0].body).group(1))
        verified = submit("email/verify", {"key": key})
        self.assertIn(verified.status_code, (200, 401), verified.content)
        self.assertTrue(EmailAddress.objects.get(email=email).verified)
        self.assertEqual(submit("login", data).status_code, 200)
        self.assertIsNotNone(client.get(reverse("api_session"), secure=True).json()["user"])

    def test_headless_reset_replaces_unusable_legacy_password(self):
        import re
        from urllib.parse import unquote

        from django.test import Client

        user = get_user_model().objects.create_user(
            username="legacy-reset", email="legacy-reset@example.com",
        )
        client = Client(enforce_csrf_checks=True)
        token = client.get(reverse("api_session"), secure=True).json()["csrf_token"]
        response = client.post(
            "/auth/browser/v1/auth/password/request", {"email": user.email},
            content_type="application/json", secure=True,
            HTTP_X_CSRFTOKEN=token, HTTP_REFERER="https://testserver/",
        )
        self.assertEqual(response.status_code, 200)
        key = unquote(re.search(r"/app/reset-password/([^\s]+)", mail.outbox[0].body).group(1))
        password = "Fresh-Rental-Reset-246"
        response = client.post(
            "/auth/browser/v1/auth/password/reset", {"key": key, "password": password},
            content_type="application/json", secure=True,
            HTTP_X_CSRFTOKEN=token, HTTP_REFERER="https://testserver/",
        )
        self.assertIn(response.status_code, (200, 401), response.content)
        user.refresh_from_db()
        self.assertTrue(user.check_password(password))
