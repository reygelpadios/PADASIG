from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from .validators import normalize_senior_id, validate_senior_id


class User(AbstractUser):
    """Django credentials and permissions; staff do not need a Senior ID.

    Inherits username, hashed password, is_active, is_staff, is_superuser,
    groups, user_permissions, date_joined, and last_login from AbstractUser.
    Seniors use an internal username; public senior login uses Senior.senior_id.
    """


class LoginThrottle(models.Model):
    """Short-lived counters; keys conceal IDs and network addresses."""
    key = models.CharField(max_length=64, unique=True)
    failures = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)


class Senior(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="senior")  # Login credentials.
    senior_id = models.CharField(max_length=5, unique=True, validators=[validate_senior_id])  # Text preserves leading zeros; unique adds an index.
    full_name = models.CharField(max_length=200)  # Registered display name; never a matching key.
    date_of_birth = models.DateField(null=True, blank=True)  # Staff-reviewed date; nullable for incomplete records.
    barangay = models.CharField(max_length=100, blank=True)  # Staff-maintained barangay.
    benefit_category = models.CharField(max_length=100, blank=True)  # Descriptive category, not an eligibility rule.
    address_details = models.TextField(blank=True)  # Senior-editable address details in a later phase.
    mobile_number = models.CharField(max_length=30, blank=True)  # Current approved contact.
    preferred_language = models.CharField(max_length=3, choices=[("fil", "Filipino"), ("en", "English")], default="fil")  # Interface language.
    text_size = models.CharField(max_length=6, choices=[("normal", "Normal"), ("large", "Large"), ("xlarge", "Extra large")], default="normal")  # Interface font preference.
    must_change_password = models.BooleanField(default=True)  # Future first-login/password-reset gate.
    consent_accepted_at = models.DateTimeField(null=True, blank=True)  # Future privacy-notice acceptance time.
    date_created = models.DateTimeField(auto_now_add=True)  # Profile creation time.

    class Meta:
        ordering = ["senior_id"]
        constraints = [models.CheckConstraint(condition=models.Q(senior_id__regex=r"^[0-9]{5}$"), name="senior_five_ascii_digits")]

    @property
    def initials(self):
        return "".join(part[0].upper() for part in self.full_name.split() if part)[:3]

    def clean(self):
        super().clean()
        self.senior_id = normalize_senior_id(self.senior_id)
        validate_senior_id(self.senior_id)
        if self.user_id and self.user.is_staff:
            raise ValidationError("Staff accounts must not be linked to a senior profile.")

    def save(self, *args, **kwargs):
        self.senior_id = normalize_senior_id(self.senior_id)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.senior_id} - {self.full_name}"


class Proxy(models.Model):
    senior = models.OneToOneField(Senior, on_delete=models.PROTECT, related_name="proxy")  # One proxy per senior, no login.
    name = models.CharField(max_length=200)  # Authorized proxy's name.
    mobile_number = models.CharField(max_length=30, blank=True)  # Approved proxy contact.
    consent_on_file = models.BooleanField(default=False)  # Written proxy consent recorded by staff.

    def __str__(self):
        return f"Proxy for {self.senior.senior_id}"


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class PendingContactChange(models.Model):
    senior = models.ForeignKey(Senior, on_delete=models.PROTECT, related_name="contact_changes")  # Request owner.
    field_name = models.CharField(max_length=12, choices=[("mobile", "Mobile"), ("proxy_name", "Proxy name"), ("proxy_mobile", "Proxy mobile")])  # Contact field to review.
    old_value = models.CharField(max_length=200, blank=True)  # Snapshot; remains active until approval.
    new_value = models.CharField(max_length=200)  # Proposed replacement.
    status = models.CharField(max_length=8, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)  # Staff review result.
    requested_at = models.DateTimeField(auto_now_add=True)  # Request time.
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="contact_reviews")  # Reviewing staff account.
    reviewed_at = models.DateTimeField(null=True, blank=True)  # Review time.

    class Meta:
        constraints = [models.UniqueConstraint(fields=["senior", "field_name"], condition=models.Q(status="pending"), name="one_pending_contact_per_field")]


class CorrectionRequest(models.Model):
    senior = models.ForeignKey(Senior, on_delete=models.PROTECT, related_name="correction_requests")  # Request owner.
    field_name = models.CharField(max_length=16, choices=[("date_of_birth", "Date of birth"), ("barangay", "Barangay"), ("benefit_category", "Benefit category")])  # Staff-maintained field.
    requested_value = models.CharField(max_length=200)  # Proposed correction; no automatic changes.
    reason = models.TextField()  # Senior's explanation.
    status = models.CharField(max_length=8, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)  # Staff review result.
    requested_at = models.DateTimeField(auto_now_add=True)  # Creation timestamp.
    updated_at = models.DateTimeField(auto_now=True)  # Most recent request edit.


class ChangeLog(models.Model):
    senior = models.ForeignKey(Senior, on_delete=models.PROTECT, related_name="change_logs")  # Affected profile.
    action = models.CharField(max_length=100)  # Short audit event name.
    details = models.JSONField(default=dict)  # Structured audit metadata; never passwords.
    created_at = models.DateTimeField(auto_now_add=True)  # Event time.

    class Meta:
        ordering = ["-created_at"]
