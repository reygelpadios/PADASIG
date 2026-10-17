from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AnnouncementQuerySet(models.QuerySet):
    def active_main(self, on_date=None):
        """Display window only; never determines eligibility."""
        on_date = on_date or timezone.localdate()
        return self.filter(is_published=True, post_type="main", publish_date__lte=on_date, payout_date__gte=on_date)

    def not_in_list(self, senior, on_date=None):
        return self.active_main(on_date).exclude(inclusion_records__senior=senior)

    def no_active_benefit(self, on_date=None):
        return not self.active_main(on_date).exists()


class Announcement(models.Model):
    benefit = models.ForeignKey("benefits.Benefit", on_delete=models.PROTECT, related_name="announcements")  # Associated program.
    post_type = models.CharField(max_length=8, choices=[("main", "Main"), ("reminder", "Reminder")], default="main")  # Reminders cannot carry inclusion records.
    title = models.CharField(max_length=200)  # Post heading.
    body = models.TextField()  # Official announcement content.
    pdf_file = models.FileField(upload_to="beneficiary_pdfs/%Y/%m/", blank=True)  # Staff-only beneficiary attachment; not public media.
    publish_date = models.DateField()  # Scheduled date; future-dated posts are excluded from active queries.
    payout_date = models.DateField(null=True, blank=True)  # Display activity ends after this date; null is unscheduled.
    payout_start_time = models.TimeField(null=True, blank=True)  # Local claiming start time.
    payout_end_time = models.TimeField(null=True, blank=True)  # Local claiming end time.
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Published amount, never a float.
    venue = models.CharField(max_length=250, blank=True)  # Payout venue.
    required_documents = models.TextField(blank=True)  # One requirement per line.
    proxy_requirements = models.TextField(blank=True)  # Separate proxy instructions.
    is_published = models.BooleanField(default=False)  # Explicit staff publishing gate.
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_announcements")  # Authoring staff account.
    updated_at = models.DateTimeField(auto_now=True)  # Post changes, not inclusion status changes.
    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        ordering = ["-publish_date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__isnull=True) | models.Q(amount__gte=0), name="announcement_nonnegative_amount"),
            models.CheckConstraint(condition=(models.Q(payout_start_time__isnull=True, payout_end_time__isnull=True) | models.Q(payout_start_time__isnull=False, payout_end_time__isnull=False, payout_end_time__gt=models.F("payout_start_time"))), name="announcement_valid_payout_times"),
        ]

    def clean(self):
        super().clean()
        if self.created_by_id and not self.created_by.is_staff:
            raise ValidationError("Only staff may author announcements.")
        if self.pk and self.post_type != "main" and self.inclusion_records.exists():
            raise ValidationError("A post with inclusion records cannot become a reminder.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class InclusionRecord(models.Model):
    senior = models.ForeignKey("accounts.Senior", on_delete=models.PROTECT, related_name="inclusion_records")  # Exact registered senior match.
    announcement = models.ForeignKey(Announcement, on_delete=models.PROTECT, related_name="inclusion_records", limit_choices_to={"post_type": "main"})  # Main post only.
    status = models.CharField(max_length=8, choices=[("included", "Included"), ("pending", "Pending"), ("claimed", "Claimed")])  # Staff-confirmed display status; no eligibility calculation.
    updated_at = models.DateTimeField(auto_now=True)  # Source of 'Updated by OSCA on [date]' for this status.
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_inclusion_records")  # Added review attribution; required authorized staff.

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["senior", "announcement"], name="unique_senior_announcement"),
            models.CheckConstraint(condition=models.Q(status__in=["included", "pending", "claimed"]), name="valid_inclusion_status"),
        ]

    def clean(self):
        super().clean()
        if self.announcement_id and self.announcement.post_type != "main":
            raise ValidationError({"announcement": "Reminder posts cannot have inclusion records."})
        if self.updated_by_id and not self.updated_by.is_staff:
            raise ValidationError({"updated_by": "An authorized staff account must confirm this record."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.senior.senior_id}: {self.announcement.title} ({self.status})"


class AnnouncementRead(models.Model):
    senior = models.ForeignKey("accounts.Senior", on_delete=models.PROTECT, related_name="announcement_reads")  # Reader; no row means unread.
    announcement = models.ForeignKey(Announcement, on_delete=models.PROTECT, related_name="read_receipts")  # Read post.
    read_at = models.DateTimeField(default=timezone.now)  # First read time.

    class Meta:
        constraints = [models.UniqueConstraint(fields=["senior", "announcement"], name="unique_announcement_read")]
