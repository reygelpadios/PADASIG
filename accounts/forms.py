from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.db import transaction
from .models import Senior


class SeniorCreationForm(forms.ModelForm):
    initial_password = forms.CharField(widget=forms.PasswordInput, help_text="Give this temporary password to the senior in person. It is stored hashed.")

    class Meta:
        model = Senior
        exclude = ["user", "must_change_password", "consent_accepted_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.DEBUG and settings.INITIAL_SENIOR_PASSWORD:
            self.fields["initial_password"].initial = settings.INITIAL_SENIOR_PASSWORD
            self.fields["initial_password"].widget = forms.PasswordInput(render_value=True)

    def clean_initial_password(self):
        password = self.cleaned_data["initial_password"]
        password_validation.validate_password(password)
        return password

    def save(self, commit=True):
        senior = super().save(commit=False)
        if commit:
            with transaction.atomic():
                self.create_user(senior)
                senior.save()
                self.save_m2m()
        return senior

    def create_user(self, senior):
        senior.user = get_user_model().objects.create_user(
            username=f"senior_{senior.senior_id}", password=self.cleaned_data["initial_password"],
        )
        senior.must_change_password = True
        senior.consent_accepted_at = None
