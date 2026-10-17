from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from announcements.models import Announcement, InclusionRecord
from benefits.models import Benefit
from .models import Senior


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DashboardTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="senior_one", password="Password123!")
        self.senior = Senior.objects.create(
            user=user, senior_id="00001", full_name="Demo One",
            must_change_password=False, consent_accepted_at=timezone.now(),
        )
        other_user = get_user_model().objects.create_user(username="senior_two")
        self.other = Senior.objects.create(user=other_user, senior_id="00002", full_name="Demo Two")
        self.staff = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.benefit = Benefit.objects.create(name="Program One")
        self.today = timezone.localdate()
        self.client.force_login(user)
        session = self.client.session
        session["senior_activity"] = timezone.now().timestamp()
        session.save()

    def post(self, title="Post One", **overrides):
        values = {
            "benefit": self.benefit, "title": title, "body": "Public body",
            "publish_date": self.today, "payout_date": self.today + timedelta(days=5),
            "is_published": True, "created_by": self.staff,
            "required_documents": "ID\nAuthorization letter", "venue": "Demo Hall",
        }
        values.update(overrides)
        return Announcement.objects.create(**values)

    def test_only_own_confirmed_record_is_shown(self):
        post = self.post()
        InclusionRecord.objects.create(senior=self.other, announcement=post, status="claimed", updated_by=self.staff)
        response = self.client.get("/portal/")
        self.assertContains(response, "Makipag-ugnayan sa OSCA.")
        self.assertNotContains(response, "Demo Two")
        self.assertNotContains(response, "Nakuha na")
        self.assertNotContains(response, 'class="payout-grid"')
        self.assertNotContains(response, "Authorization letter")
        record = InclusionRecord.objects.create(senior=self.senior, announcement=post, status="included", updated_by=self.staff)
        response = self.client.get("/portal/")
        self.assertContains(response, "Kasama sa talaan")
        self.assertContains(response, f'Updated by OSCA on {timezone.localtime(record.updated_at).strftime("%B %-d, %Y")}')
        self.assertContains(response, "Demo Hall")
        self.assertNotContains(response, "beneficiary_pdfs")

    def test_pending_hides_payout_and_multiple_posts_render(self):
        first = self.post()
        second = self.post("Post Two", venue="Another Hall")
        InclusionRecord.objects.create(senior=self.senior, announcement=first, status="pending", updated_by=self.staff)
        InclusionRecord.objects.create(senior=self.senior, announcement=second, status="claimed", updated_by=self.staff)
        response = self.client.get("/portal/")
        self.assertContains(response, "Post One")
        self.assertContains(response, "Post Two")
        self.assertContains(response, "Naghihintay ng kumpirmasyon")
        self.assertContains(response, "Nakuha na")
        self.assertContains(response, "Another Hall")
        self.assertNotContains(response, "Makipag-ugnayan sa OSCA.")

    def test_unpublished_future_and_expired_posts_are_not_active(self):
        self.post("Private post", is_published=False)
        self.post("Future post", publish_date=self.today + timedelta(days=1))
        self.post("Expired post", payout_date=self.today - timedelta(days=1))
        response = self.client.get("/portal/")
        self.assertContains(response, "Walang aktibong benepisyo")
        self.assertNotContains(response, "Private post")
        self.assertNotContains(response, "Future post")
        self.assertContains(response, "Expired post")
        self.assertNotContains(response, 'class="benefit-panel"')

    def test_text_size_is_post_only_and_restricted(self):
        self.assertEqual(self.client.get("/portal/text-size/").status_code, 405)
        self.client.post("/portal/text-size/", {"text_size": "huge"})
        self.senior.refresh_from_db()
        self.assertEqual(self.senior.text_size, "normal")
        self.assertRedirects(self.client.post("/portal/text-size/", {"text_size": "xlarge"}), "/portal/")
        self.senior.refresh_from_db()
        self.assertEqual(self.senior.text_size, "xlarge")
        self.assertContains(self.client.get("/portal/"), 'class="text-xlarge portal-page"')
