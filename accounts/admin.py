from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import transaction
from .forms import SeniorCreationForm
from .models import User, Senior, Proxy, PendingContactChange, CorrectionRequest, ChangeLog


@admin.register(User)
class StaffUserAdmin(UserAdmin):
    list_display = ["username", "is_staff", "is_active", "last_login"]
    search_fields = ["username", "senior__senior_id", "senior__full_name"]

    def user_change_password(self, request, id, form_url=""):
        with transaction.atomic():
            user = self.get_object(request, id)
            previous_hash = user.password if user else None
            response = super().user_change_password(request, id, form_url)
            if user and request.method == "POST" and response.status_code == 302:
                user.refresh_from_db()
                senior = Senior.objects.filter(user=user).first()
                if senior and user.password != previous_hash:
                    Senior.objects.filter(pk=senior.pk).update(must_change_password=True)
                    ChangeLog.objects.create(senior=senior, action="staff_password_reset", details={"staff_id": request.user.pk})
            return response


@admin.register(Senior)
class SeniorAdmin(admin.ModelAdmin):
    list_display = ["senior_id", "full_name", "barangay", "must_change_password"]
    search_fields = ["senior_id", "full_name"]
    list_filter = ["barangay", "preferred_language", "must_change_password"]
    readonly_fields = ["user", "date_created", "must_change_password", "consent_accepted_at"]

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = SeniorCreationForm
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            form.create_user(obj)
        super().save_model(request, obj, form, change)


@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ["senior", "name", "consent_on_file"]
    search_fields = ["senior__senior_id", "name"]


class ReadOnlyAdmin(admin.ModelAdmin):
    """Approval services will be implemented later; editing status here is unsafe."""
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PendingContactChange)
class PendingContactAdmin(ReadOnlyAdmin):
    list_display = ["senior", "field_name", "status", "requested_at", "reviewed_at"]
    list_filter = ["status", "field_name"]
    search_fields = ["senior__senior_id", "senior__full_name"]


@admin.register(CorrectionRequest)
class CorrectionAdmin(ReadOnlyAdmin):
    list_display = ["senior", "field_name", "status", "requested_at"]
    list_filter = ["status"]
    search_fields = ["senior__senior_id", "senior__full_name"]


@admin.register(ChangeLog)
class ChangeLogAdmin(ReadOnlyAdmin):
    list_display = ["senior", "action", "created_at"]
    search_fields = ["senior__senior_id", "action"]
