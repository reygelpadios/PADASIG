from django.db import models


class Benefit(models.Model):
    name = models.CharField(max_length=150, unique=True)  # Stable program label; unique avoids duplicate demo programs.
    description = models.TextField(blank=True)  # Program description, not eligibility logic.
    is_active = models.BooleanField(default=True)  # Program administration flag.

    def __str__(self):
        return self.name
