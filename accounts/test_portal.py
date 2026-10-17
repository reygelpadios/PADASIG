from datetime import timedelta
from django.contrib.auth import authenticate, get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from .models import ChangeLog, LoginThrottle, Senior


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PortalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="senior_internal", password="TemporaryPass123!")
        self.senior = Senior.objects.create(user=self.user, senior_id="00001", full_name="Lourdes M. Santos")

    def sign_in(self, client=None, **kwargs):
        return (client or self.client).post("/login/", {"senior_id": "00001", "password": "TemporaryPass123!"}, **kwargs)

    def complete_setup(self):
        self.sign_in()
        self.client.post("/setup/password/", {"new_password1": "DifferentSecure456!", "new_password2": "DifferentSecure456!"})
        return self.client.post("/setup/privacy/")

    def test_public_login_and_help(self):
        response = self.client.get("/login/")
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'maxlength="5"')
        self.assertContains(response, "OSCA Help Desk")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertContains(self.client.get("/help/password/"), "OSCA Help Desk")

    def test_login_ui_is_filipino_with_empty_inputs_and_compact_help(self):
        response = self.client.get("/login/")
        self.assertNotContains(response, "MALIGAYANG PAGDATING")
        self.assertContains(response, "PUMASOK")
        self.assertNotContains(response, "WELCOME")
        self.assertContains(response, 'placeholder="Halimbawa: 10001"')
        self.assertNotContains(response, 'value="10001"')
        self.assertNotContains(response, 'value="ChangeMe123!"')
        self.assertNotContains(response, 'class="language-picker"')
        self.assertNotContains(response, 'data-login-size')
        self.assertContains(response, 'id="login-help"')
        self.assertContains(response, 'images/osca-login.png')
        self.assertContains(response, 'id="login-privacy"')

    def test_error_ui_marks_both_fields_without_revealing_account(self):
        response = self.client.post("/login/", {"senior_id": "99999", "password": "wrong"})
        self.assertContains(response, "Mali ang Senior ID o password. Subukan muli.")
        self.assertNotContains(response, "login-loading")
        self.assertNotIn("login_loading_pending", self.client.session)
        self.assertNotContains(response, "Incorrect Senior ID or password. Please try again.")
        self.assertContains(response, 'aria-invalid="true"', count=2)
        self.assertNotContains(response, 'value="99999"')

    def test_unknown_wrong_inactive_and_internal_username_get_same_error(self):
        for senior_id, password in [("99999", "wrong"), ("00001", "wrong"), ("senior_internal", "TemporaryPass123!")]:
            response = self.client.post("/login/", {"senior_id": senior_id, "password": password})
            self.assertContains(response, "Mali ang Senior ID o password. Subukan muli.")
        self.user.is_active = False
        self.user.save()
        self.assertContains(self.sign_in(), "Mali ang Senior ID o password. Subukan muli.")

    def test_password_then_privacy_then_portal_gates(self):
        for path in ["/portal/", "/setup/password/", "/setup/privacy/"]:
            self.assertRedirects(self.client.get(path), "/login/")
        self.assertRedirects(self.sign_in(), "/setup/password/")
        self.assertRedirects(self.client.get("/portal/"), "/setup/password/")
        self.assertRedirects(self.client.post("/setup/privacy/"), "/setup/password/")
        response = self.client.post("/setup/password/", {"new_password1": "DifferentSecure456!", "new_password2": "DifferentSecure456!"})
        self.assertRedirects(response, "/setup/privacy/")
        self.assertIsNone(authenticate(senior_id="00001", password="TemporaryPass123!"))
        self.assertIsNotNone(authenticate(senior_id="00001", password="DifferentSecure456!"))
        self.assertRedirects(self.client.get("/portal/"), "/setup/privacy/")
        self.senior.refresh_from_db()
        self.assertFalse(self.senior.must_change_password)
        self.assertIsNone(self.senior.consent_accepted_at)
        self.client.get("/setup/privacy/")
        self.senior.refresh_from_db()
        self.assertIsNone(self.senior.consent_accepted_at)
        self.assertRedirects(self.client.post("/setup/privacy/"), "/login/loading/", fetch_redirect_response=False)
        self.assertContains(self.client.get("/login/loading/"), 'aria-label="Binubuksan ang PADASIG Portal"')
        self.assertRedirects(self.client.get("/login/loading/"), "/portal/")
        self.senior.refresh_from_db()
        accepted = self.senior.consent_accepted_at
        self.client.post("/setup/privacy/")
        self.senior.refresh_from_db()
        self.assertEqual(accepted, self.senior.consent_accepted_at)
        self.assertEqual(ChangeLog.objects.filter(action="privacy_notice_accepted").count(), 1)
        self.assertNotIn("DifferentSecure456!", str(list(ChangeLog.objects.values())))

    def test_password_validation_and_same_password(self):
        self.sign_in()
        for first, second in [("short", "short"), ("DifferentSecure456!", "Mismatch456!"), ("TemporaryPass123!", "TemporaryPass123!"), ("12345678", "12345678")]:
            response = self.client.post("/setup/password/", {"new_password1": first, "new_password2": second})
            self.assertEqual(response.status_code, 200)
            self.senior.refresh_from_db()
            self.assertTrue(self.senior.must_change_password)

    def test_csrf_on_login_password_consent_logout_language_and_touch(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.sign_in(client).status_code, 403)
        client.get("/login/")
        token = client.cookies["csrftoken"].value
        self.assertEqual(self.sign_in(client, HTTP_X_CSRFTOKEN=token).status_code, 302)
        for path in ["/setup/password/", "/setup/privacy/", "/logout/", "/language/", "/portal/text-size/", "/session/touch/"]:
            self.assertEqual(client.post(path).status_code, 403, path)

    def test_lockout_after_five_failures_even_with_correct_password(self):
        for unused in range(5):
            self.client.post("/login/", {"senior_id": "00001", "password": "wrong"})
        self.assertContains(self.sign_in(), "Mali ang Senior ID o password. Subukan muli.")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(LoginThrottle.objects.filter(failures=5).count(), 2)
        LoginThrottle.objects.update(window_started_at=timezone.now() - timedelta(minutes=16), locked_until=timezone.now() - timedelta(seconds=1))
        self.assertRedirects(self.sign_in(), "/setup/password/")

    def test_ip_limit_also_blocks_rotating_ids(self):
        for senior_id in ["99991", "99992", "99993", "99994", "99995"]:
            self.client.post("/login/", {"senior_id": senior_id, "password": "wrong"})
        self.assertContains(self.sign_in(), "Mali ang Senior ID o password. Subukan muli.")
        self.assertRedirects(self.sign_in(REMOTE_ADDR="192.0.2.20"), "/setup/password/")

    def test_language_toggle_and_safe_destination(self):
        self.client.post("/language/", {"language": "en", "destination": "login"})
        response = self.client.get("/login/")
        self.assertNotContains(response, "MALIGAYANG PAGDATING")
        self.assertNotContains(response, 'class="language-picker"')
        self.assertRedirects(self.client.post("/language/", {"language": "bad", "destination": "https://example.com"}), "/login/")
        self.assertEqual(self.client.session["portal_language"], "en")
        self.sign_in()
        self.assertContains(self.client.get("/setup/password/"), "Create a new password")

    def test_logout_post_only_and_no_open_redirect(self):
        self.sign_in()
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertRedirects(self.client.post("/login/?next=https://example.com", {"senior_id": "00001", "password": "TemporaryPass123!"}), "/setup/password/")

    def test_server_idle_timeout_and_poll_does_not_renew(self):
        self.sign_in()
        session = self.client.session
        activity = timezone.now().timestamp() - 550
        session["senior_activity"] = activity
        session.save()
        response = self.client.get("/session/status/")
        self.assertLessEqual(response.json()["remaining"], 50)
        self.assertEqual(self.client.session["senior_activity"], activity)
        self.assertEqual(self.client.post("/session/touch/").status_code, 200)
        self.assertGreater(self.client.session["senior_activity"], activity)
        session = self.client.session
        session["senior_activity"] = timezone.now().timestamp() - 601
        session.save()
        self.assertEqual(self.client.post("/session/touch/").status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_expired_page_returns_login(self):
        self.sign_in()
        session = self.client.session
        session["senior_activity"] = 0
        session.save()
        self.assertRedirects(self.client.get("/portal/"), "/login/?expired=1")

    def test_staff_cannot_use_senior_pages(self):
        staff = get_user_model().objects.create_superuser(username="staff", password="StaffPassword123!")
        self.client.force_login(staff)
        self.assertRedirects(self.client.get("/portal/"), "/login/")
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_returning_senior_skips_setup_and_text_preference_applies(self):
        self.complete_setup()
        self.client.post("/logout/")
        Senior.objects.filter(pk=self.senior.pk).update(text_size="xlarge")
        response = self.client.post("/login/", {"senior_id": "00001", "password": "DifferentSecure456!"})
        self.assertRedirects(response, "/login/loading/", fetch_redirect_response=False)
        loading = self.client.get("/login/loading/")
        self.assertContains(loading, 'data-destination="/portal/"')
        self.assertContains(loading, 'class="loading-full-logo"')
        self.assertContains(loading, 'role="status"')
        self.assertNotContains(loading, "Sandali lang po...")
        self.assertContains(self.client.get("/portal/"), 'class="text-xlarge portal-page"')

    def test_loading_screen_requires_a_successful_login_and_is_one_time(self):
        self.assertRedirects(self.client.get("/login/loading/"), "/login/")
        self.complete_setup()
        self.client.get("/login/loading/")
        self.client.post("/logout/")
        self.assertRedirects(
            self.client.post("/login/", {"senior_id": "00001", "password": "DifferentSecure456!"}),
            "/login/loading/",
            fetch_redirect_response=False,
        )
        self.assertContains(self.client.get("/login/loading/"), 'class="loading-full-logo"')
        self.assertRedirects(self.client.get("/login/loading/"), "/portal/")
        self.assertNotIn("login_loading_pending", self.client.session)

    def test_admin_password_reset_forces_setup_and_invalidates_old_session(self):
        self.complete_setup()
        staff = get_user_model().objects.create_superuser(username="admin", password="StaffPassword123!")
        admin_client = Client()
        admin_client.force_login(staff)
        response = admin_client.post(f"/admin/accounts/user/{self.user.pk}/password/", {"password1": "ResetTemporary789!", "password2": "ResetTemporary789!", "usable_password": "true"})
        self.assertEqual(response.status_code, 302)
        self.senior.refresh_from_db()
        self.assertTrue(self.senior.must_change_password)
        self.assertEqual(ChangeLog.objects.filter(action="staff_password_reset").count(), 1)
        self.assertRedirects(self.client.get("/portal/"), "/login/")
        response = self.client.post("/login/", {"senior_id": "00001", "password": "ResetTemporary789!"})
        self.assertRedirects(response, "/setup/password/")
