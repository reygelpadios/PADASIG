from datetime import date, time, timedelta
from io import StringIO
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from accounts.models import Senior, Proxy, ChangeLog
from benefits.models import Benefit
from .models import Announcement, InclusionRecord, AnnouncementRead


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AnnouncementTests(TestCase):
    def setUp(self):
        self.day = date(2026, 10, 11)
        self.staff = get_user_model().objects.create_user(username="staff", is_staff=True)
        self.user = get_user_model().objects.create_user(username="senior")
        self.senior = Senior.objects.create(user=self.user, senior_id="00001", full_name="Demo Senior")
        self.benefit = Benefit.objects.create(name="Demo benefit")
        self.post = Announcement.objects.create(benefit=self.benefit, title="Demo post", body="Example", publish_date=self.day, payout_date=self.day, is_published=True, created_by=self.staff)

    def test_active_and_missing_record_states(self):
        self.assertFalse(Announcement.objects.no_active_benefit(self.day))
        self.assertTrue(Announcement.objects.not_in_list(self.senior, self.day).exists())
        record = InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="pending", updated_by=self.staff)
        self.assertFalse(Announcement.objects.not_in_list(self.senior, self.day).exists())
        self.assertEqual(record.updated_by, self.staff)
        self.assertTrue(Announcement.objects.no_active_benefit(self.day + timedelta(days=1)))

    def test_future_publication_and_unscheduled_posts_are_not_active(self):
        self.post.publish_date = self.day + timedelta(days=1)
        self.post.save()
        self.assertTrue(Announcement.objects.no_active_benefit(self.day))
        self.post.publish_date = self.day
        self.post.payout_date = None
        self.post.save()
        self.assertTrue(Announcement.objects.no_active_benefit(self.day))

    def test_reminder_and_nonstaff_cannot_create_inclusion(self):
        self.post.post_type = "reminder"
        self.post.save()
        with self.assertRaises(ValidationError):
            InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="included", updated_by=self.staff)
        self.post.post_type = "main"
        self.post.save()
        with self.assertRaises(ValidationError):
            InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="included", updated_by=self.user)

    def test_duplicate_record_and_reminder_conversion_are_rejected(self):
        InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="included", updated_by=self.staff)
        with self.assertRaises(ValidationError):
            InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="claimed", updated_by=self.staff)
        self.post.post_type = "reminder"
        with self.assertRaises(ValidationError):
            self.post.save()

    def test_database_rejects_invalid_times_and_negative_amount(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Announcement.objects.filter(pk=self.post.pk).update(amount=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Announcement.objects.filter(pk=self.post.pk).update(payout_start_time=time(11), payout_end_time=time(8))

    def test_database_guards_bulk_writes(self):
        self.post.post_type = "reminder"
        self.post.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            InclusionRecord.objects.bulk_create([InclusionRecord(senior=self.senior, announcement=self.post, status="included", updated_by=self.staff)])
        self.post.post_type = "main"
        self.post.save()
        record = InclusionRecord.objects.create(senior=self.senior, announcement=self.post, status="included", updated_by=self.staff)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Announcement.objects.filter(pk=self.post.pk).update(post_type="reminder")
        with self.assertRaises(IntegrityError), transaction.atomic():
            InclusionRecord.objects.filter(pk=record.pk).update(updated_by=self.user)

    def test_database_preserves_leading_zero_id_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Senior.objects.filter(pk=self.senior.pk).update(senior_id="12O45")

    def test_admin_tracks_staff_and_audit_event(self):
        self.staff.is_superuser = True
        self.staff.save()
        self.client.force_login(self.staff)
        response = self.client.post("/admin/announcements/inclusionrecord/add/", {
            "senior": self.senior.pk, "announcement": self.post.pk, "status": "included", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context and response.context["adminform"].form.errors)
        self.assertTrue(ChangeLog.objects.filter(senior=self.senior, action="inclusion_updated").exists())


@override_settings(DEBUG=True, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class SeedTests(TestCase):
    def test_seed_is_repeatable_and_covers_states(self):
        call_command("seed_demo", stdout=StringIO())
        user = Senior.objects.get(senior_id="10001").user
        user.set_password("ChangedPassword123!")
        user.save()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Senior.objects.count(), 8)
        self.assertEqual(Benefit.objects.count(), 3)
        self.assertEqual(Announcement.objects.count(), 4)
        self.assertEqual(InclusionRecord.objects.count(), 9)
        self.assertEqual(Proxy.objects.count(), 3)
        self.assertEqual(AnnouncementRead.objects.count(), 3)
        user.refresh_from_db()
        self.assertTrue(user.check_password("ChangedPassword123!"))
        self.assertEqual(set(InclusionRecord.objects.values_list("status", flat=True)), {"included", "pending", "claimed"})
        self.assertEqual(InclusionRecord.objects.filter(senior__senior_id="10001").count(), 2)
        self.assertFalse(InclusionRecord.objects.filter(senior__senior_id="10005").exists())
        for proxy in Proxy.objects.select_related("senior"):
            self.assertNotEqual(proxy.name, proxy.senior.full_name)

    def test_no_active_flag_is_reversible(self):
        call_command("seed_demo", demo_no_active=True, stdout=StringIO())
        self.assertTrue(Announcement.objects.no_active_benefit())
        call_command("seed_demo", relative_dates=True, stdout=StringIO())
        self.assertFalse(Announcement.objects.no_active_benefit())

    @override_settings(DEBUG=False)
    def test_seed_refuses_production_settings(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
