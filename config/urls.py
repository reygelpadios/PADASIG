from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("", include("accounts.urls"))]
admin.site.site_header = "PADASIG Administration"
admin.site.site_title = "PADASIG"
# Beneficiary PDFs remain private. There is no self-registration route.
