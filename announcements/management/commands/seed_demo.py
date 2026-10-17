from datetime import date, time, timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from accounts.models import Senior, Proxy, ChangeLog
from benefits.models import Benefit
from announcements.models import Announcement, InclusionRecord, AnnouncementRead

NAMES = [
    "Lourdes M. Santos", "Ernesto D. Rivera", "Carmelita R. Flores", "Rodolfo P. Mercado",
    "Teresita L. Ramos", "Benito C. Villanueva", "Rosalinda V. Cruz", "Arturo N. Reyes",
]
PROGRAMS = ["Pamaskong Handog", "Senior Wellness Support", "Birthday Incentive"]
POSTS = [
    (0, "Pamaskong Handog 2026", date(2026, 10, 11), date(2026, 12, 15), "main"),
    (1, "Senior Wellness Support", date(2026, 10, 9), date(2026, 11, 20), "main"),
    (2, "Birthday Incentive", date(2026, 10, 7), date(2026, 11, 25), "main"),
    (0, "Pamaskong Handog: Paalala", date(2026, 10, 5), None, "reminder"),
]


class Command(BaseCommand):
    help = "Create or refresh fictional PADASIG development records without duplicates."

    def add_arguments(self, parser):
        parser.add_argument("--demo-no-active", action="store_true", help="Move only these demo payouts into the past; rerun normally to restore.")
        parser.add_argument("--relative-dates", action="store_true", help="Shift demo dates together so October 11, 2026 becomes today.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is for DEBUG=True local development only.")
        User = get_user_model()
        author, created = User.objects.get_or_create(username="demo_seed_staff", defaults={"is_staff": True})
        if created:
            author.set_unusable_password()
            author.save()
        if not author.is_staff or hasattr(author, "senior"):
            raise CommandError("demo_seed_staff conflicts with an existing account.")
        programs = [Benefit.objects.get_or_create(name=name, defaults={"description": "Fictional demo program."})[0] for name in PROGRAMS]
        seniors = []
        for index, name in enumerate(NAMES):
            senior_id = str(10001 + index)
            username = f"demo_senior_{senior_id}"
            existing = Senior.objects.filter(senior_id=senior_id).select_related("user").first()
            if existing and existing.user.username != username:
                raise CommandError(f"Senior ID {senior_id} already belongs to a non-demo account; no changes committed.")
            user, new_user = User.objects.get_or_create(username=username)
            if new_user:
                user.set_password(settings.DEMO_PASSWORD)
                user.save()
            if user.is_staff:
                raise CommandError(f"{username} conflicts with a staff account.")
            senior, _ = Senior.objects.get_or_create(senior_id=senior_id, defaults={
                "user": user, "full_name": name, "date_of_birth": date(1950 + index, 3, 12),
                "barangay": ["Demo Barangay A", "Demo Barangay B", "Demo Barangay C"][index % 3],
                "benefit_category": "Demo registered senior", "address_details": "Demo address only",
                "mobile_number": "09XX-XXX-XXXX", "must_change_password": True,
            })
            if senior.user_id != user.pk:
                raise CommandError("Demo account/profile conflict; no changes committed.")
            seniors.append(senior)
        for index, proxy_name in enumerate(["Ana P. Navarro", "Miguel B. Lopez", "Elena T. Bautista"]):
            Proxy.objects.get_or_create(senior=seniors[index], defaults={
                "name": proxy_name, "mobile_number": "09XX-XXX-XXXX", "consent_on_file": True,
            })
        today = timezone.localdate()
        shift = today - date(2026, 10, 11) if options["relative_dates"] else timedelta()
        posts = []
        for benefit_index, title, published, payout, kind in POSTS:
            payout = payout + shift if payout else None
            if payout and options["demo_no_active"]:
                payout = today - timedelta(days=1)
            post, _ = Announcement.objects.update_or_create(
                created_by=author, title=title, defaults={
                    "benefit": programs[benefit_index], "post_type": kind,
                    "body": "Tingnan ang anunsiyo para sa iskedyul at mga kailangang dalhin.",
                    "publish_date": published + shift, "payout_date": payout,
                    "payout_start_time": time(8), "payout_end_time": time(11),
                    "amount": Decimal("3000.00"), "venue": "Demo Community Hall",
                    "required_documents": "Orihinal na Senior Citizen ID\nDalawang photocopy ng ID\nItim o asul na ballpen",
                    "proxy_requirements": "Authorization letter na pirmado ng senior\nValid government ID ng proxy",
                    "is_published": True,
                },
            )
            posts.append(post)
        # Senior 10005 deliberately has no record. Nothing is inferred from names.
        assignments = [(0, 0, "included"), (0, 1, "pending"), (1, 0, "included"),
                       (2, 1, "pending"), (3, 0, "claimed"), (5, 2, "included"),
                       (6, 2, "claimed"), (7, 0, "included"), (7, 2, "included")]
        for senior_index, post_index, status in assignments:
            senior = seniors[senior_index]
            post = posts[post_index]
            record, _ = InclusionRecord.objects.update_or_create(senior=senior, announcement=post, defaults={"status": status, "updated_by": author})
            ChangeLog.objects.get_or_create(senior=senior, action="demo_inclusion_confirmed", details={"record_id": record.pk, "staff_user_id": author.pk})
        for senior_index, post_index in [(0, 0), (1, 0), (2, 3)]:
            AnnouncementRead.objects.get_or_create(senior=seniors[senior_index], announcement=posts[post_index])
        self.stdout.write(self.style.SUCCESS("Demo ready: 8 seniors, 3 benefits, 4 announcements, 3 proxies. Existing passwords were preserved."))
        self.stdout.write("10001: multiple; 10002: included; 10003: pending; 10004: claimed; 10005: no inclusion record.")
        self.stdout.write("Open /portal/ after senior login. Create your own staff administrator with: python manage.py createsuperuser")
