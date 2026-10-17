from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import LoginThrottle


class Command(BaseCommand):
    help = "Delete expired login counters; never clear an active lockout."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(seconds=settings.LOGIN_LOCK_SECONDS)
        rows = LoginThrottle.objects.filter(window_started_at__lte=cutoff).exclude(locked_until__gt=timezone.now())
        count, unused = rows.delete()
        self.stdout.write(f"Deleted {count} expired counters.")
