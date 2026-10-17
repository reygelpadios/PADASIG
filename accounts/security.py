from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import LoginThrottle
from .validators import normalize_senior_id


def throttle_key(kind, value):
    return salted_hmac("padasig-login", f"{kind}:{value}", algorithm="sha256").hexdigest()


def authenticate_senior(request, senior_id, password):
    """Lock both counters while checking credentials, including unknown IDs."""
    now = timezone.now()
    window = timedelta(seconds=settings.LOGIN_LOCK_SECONDS)
    id_key = throttle_key("id", normalize_senior_id(senior_id))
    keys = sorted([id_key, throttle_key("ip", request.META.get("REMOTE_ADDR", "unknown"))])
    with transaction.atomic():
        for key in keys:
            LoginThrottle.objects.get_or_create(key=key, defaults={"window_started_at": now})
        counters = list(LoginThrottle.objects.select_for_update().filter(key__in=keys).order_by("key"))
        if any(row.locked_until and row.locked_until > now for row in counters):
            return None
        for row in counters:
            if now - row.window_started_at >= window:
                row.failures, row.locked_until, row.window_started_at = 0, None, now
        user = authenticate(request, senior_id=senior_id, password=password)
        for row in counters:
            if user is None:
                row.failures += 1
                if row.failures >= settings.LOGIN_FAILURE_LIMIT:
                    row.locked_until = now + window
            elif row.key == id_key:
                row.failures, row.locked_until = 0, None
            row.save()
        return user
