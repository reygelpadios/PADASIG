from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from .models import Senior, PendingContactChange
from .validators import normalize_senior_id


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="internal_demo", password="ExamplePass123!")
        self.senior = Senior.objects.create(user=self.user, senior_id="00001", full_name="Lourdes M. Santos")

    def test_leading_zeros_and_initials(self):
        self.senior.refresh_from_db()
        self.assertEqual(self.senior.senior_id, "00001")
        self.assertEqual(self.senior.initials, "LMS")
        self.assertTrue(self.senior.must_change_password)
        self.assertIsNone(self.senior.consent_accepted_at)
        self.assertNotEqual(self.user.password, "ExamplePass123!")

    def test_normalization_does_not_guess_ocr_letters(self):
        self.assertEqual(normalize_senior_id(" ００ ０-０１ "), "00001")
        self.senior.senior_id = "1OOO1"
        with self.assertRaises(ValidationError):
            self.senior.save()

    def test_senior_id_auth_and_internal_username_rejection(self):
        self.assertEqual(authenticate(senior_id="00001", password="ExamplePass123!"), self.user)
        self.assertIsNone(authenticate(username="internal_demo", password="ExamplePass123!"))
        self.assertIsNone(authenticate(senior_id="00001", password="wrong"))
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(authenticate(senior_id="00001", password="ExamplePass123!"))

    def test_staff_has_username_without_senior_profile(self):
        staff = get_user_model().objects.create_user(username="osca_staff", password="ExamplePass123!", is_staff=True)
        self.assertEqual(authenticate(username="osca_staff", password="ExamplePass123!"), staff)
        self.assertFalse(Senior.objects.filter(user=staff).exists())

    def test_pending_contact_does_not_change_approved_contact(self):
        self.senior.mobile_number = "09XX-OLD-XXXX"
        self.senior.save()
        PendingContactChange.objects.create(senior=self.senior, field_name="mobile", old_value=self.senior.mobile_number, new_value="09XX-NEW-XXXX")
        self.senior.refresh_from_db()
        self.assertEqual(self.senior.mobile_number, "09XX-OLD-XXXX")

    def test_admin_can_create_senior_with_hashed_password(self):
        staff = get_user_model().objects.create_superuser(username="reviewer", password="ExamplePass123!")
        self.client.force_login(staff)
        response = self.client.post("/admin/accounts/senior/add/", {
            "senior_id": "00002", "full_name": "Demo Senior Two", "initial_password": "WelcomeSenior123!",
            "preferred_language": "fil", "text_size": "normal", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context and response.context["adminform"].form.errors)
        senior = Senior.objects.get(senior_id="00002")
        self.assertTrue(senior.user.check_password("WelcomeSenior123!"))
        self.assertTrue(senior.must_change_password)
        self.assertFalse(senior.user.is_staff)

    def test_login_available_but_pdfs_remain_private(self):
        self.assertEqual(self.client.get("/login/").status_code, 200)
        self.assertEqual(self.client.get("/media/beneficiary_pdfs/list.pdf").status_code, 404)
