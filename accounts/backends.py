from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from .models import Senior
from .validators import normalize_senior_id, validate_senior_id


class SeniorIDBackend(ModelBackend):
    """Step 2 will call authenticate(senior_id=..., password=...)."""
    def authenticate(self, request, senior_id=None, password=None, **kwargs):
        if senior_id is None or password is None:
            return None
        try:
            senior_id = normalize_senior_id(senior_id)
            validate_senior_id(senior_id)
            senior = Senior.objects.select_related("user").get(senior_id=senior_id)
        except (ValidationError, Senior.DoesNotExist):
            get_user_model()().set_password(password)
            return None
        user = senior.user
        if not user.is_staff and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class StaffUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username=username, password=password, **kwargs)
        return user if user is not None and user.is_staff else None
