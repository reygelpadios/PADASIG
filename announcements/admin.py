from django.contrib import admin
from accounts.admin import ReadOnlyAdmin
from accounts.models import ChangeLog
from .models import Announcement, InclusionRecord, AnnouncementRead


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "benefit", "post_type", "publish_date", "payout_date", "is_published"]
    list_filter = ["benefit", "post_type", "is_published"]
    search_fields = ["title", "body"]
    readonly_fields = ["created_by", "updated_at"]
    # No attachment link: beneficiary PDFs must never use a public media URL.
    exclude = ["pdf_file"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InclusionRecord)
class InclusionAdmin(admin.ModelAdmin):
    list_display = ["senior", "announcement", "status", "updated_by", "updated_at"]
    list_filter = ["status", "announcement__benefit"]
    search_fields = ["senior__senior_id", "senior__full_name", "announcement__title"]
    readonly_fields = ["updated_by", "updated_at"]
    autocomplete_fields = ["senior", "announcement"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        ChangeLog.objects.create(senior=obj.senior, action="inclusion_updated", details={
            "record_id": obj.pk, "announcement_id": obj.announcement_id,
            "status": obj.status, "staff_user_id": request.user.pk,
        })

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(ReadOnlyAdmin):
    list_display = ["senior", "announcement", "read_at"]
    search_fields = ["senior__senior_id", "announcement__title"]
