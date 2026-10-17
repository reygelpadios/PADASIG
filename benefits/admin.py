from django.contrib import admin
from .models import Benefit


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
