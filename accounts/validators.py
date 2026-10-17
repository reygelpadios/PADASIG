import re
import unicodedata
from django.conf import settings
from django.core.exceptions import ValidationError


def normalize_senior_id(value):
    """Normalize spacing, dashes, and decimal digits; never fix OCR letters."""
    result = []
    for character in str(value).strip():
        if character.isspace() or unicodedata.category(character) == "Pd":
            continue
        try:
            result.append(str(unicodedata.decimal(character)))
        except ValueError:
            result.append(character)
    return "".join(result)


def validate_senior_id(value):
    if not re.fullmatch(r"[0-9]{5}", value) or not re.fullmatch(settings.SENIOR_ID_PATTERN, value):
        raise ValidationError("Senior ID must contain exactly five digits.")
