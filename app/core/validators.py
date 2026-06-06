"""
Sanchay — Input Validation Helpers
=====================================
Centralised validation functions used by all service layers.
All raise ValidationError on failure; return sanitised value on success.
"""

import re
from typing import Optional
from app.core.exceptions import ValidationError

# ── Compiled patterns ─────────────────────────────────────────────────────────

_EMAIL_RE  = re.compile(r'^[^@\s]{1,64}@[^@\s]{1,253}\.[^@\s]{2,10}$')
_PHONE_RE  = re.compile(r'^[\d\s\+\-\(\)\.]{6,20}$')
_CODE_RE   = re.compile(r'^[A-Z0-9][A-Z0-9_\-]{1,19}$')  # 2-20, starts alnum
_USER_RE   = re.compile(r'^[a-z0-9][a-z0-9_\-]{2,49}$')  # 3-50, lowercase
_ALNUM_RE  = re.compile(r'^[A-Za-z0-9_\-]+$')


# ── String sanitisers ─────────────────────────────────────────────────────────

def sanitise_str(value: Optional[str], field: str = "field",
                 required: bool = False, max_len: int = 500) -> Optional[str]:
    """Strip whitespace; raise ValidationError if required and empty."""
    if value is None:
        if required:
            raise ValidationError(f"'{field}' is required.", field)
        return None
    cleaned = value.strip()
    if required and not cleaned:
        raise ValidationError(f"'{field}' is required.", field)
    if cleaned and len(cleaned) > max_len:
        raise ValidationError(
            f"'{field}' must not exceed {max_len} characters "
            f"(got {len(cleaned)}).", field
        )
    return cleaned or None


def require_str(value: Optional[str], field: str,
                min_len: int = 1, max_len: int = 500) -> str:
    """Return stripped, non-empty string or raise ValidationError."""
    cleaned = sanitise_str(value, field, required=True, max_len=max_len)
    if cleaned and len(cleaned) < min_len:
        raise ValidationError(
            f"'{field}' must be at least {min_len} character(s).", field
        )
    return cleaned  # type: ignore[return-value]


# ── Format validators ─────────────────────────────────────────────────────────

def validate_email(email: Optional[str], field: str = "email") -> Optional[str]:
    """Validate email format if provided; return stripped value."""
    if not email:
        return None
    cleaned = email.strip().lower()
    if not _EMAIL_RE.match(cleaned):
        raise ValidationError(
            f"'{cleaned}' is not a valid email address.", field
        )
    return cleaned


def validate_phone(phone: Optional[str], field: str = "phone") -> Optional[str]:
    """Validate phone format if provided; return stripped value."""
    if not phone:
        return None
    cleaned = phone.strip()
    if not _PHONE_RE.match(cleaned):
        raise ValidationError(
            f"Phone number must be 6-20 digits/spaces/+/-/(). Got: '{cleaned}'",
            field,
        )
    return cleaned


def validate_code(code: str, field: str = "code",
                  min_len: int = 2, max_len: int = 20) -> str:
    """Validate a short alphanumeric code (asset code, org code, etc.)."""
    cleaned = code.strip().upper()
    if len(cleaned) < min_len:
        raise ValidationError(
            f"'{field}' must be at least {min_len} characters.", field
        )
    if len(cleaned) > max_len:
        raise ValidationError(
            f"'{field}' must not exceed {max_len} characters.", field
        )
    if not _ALNUM_RE.match(cleaned):
        raise ValidationError(
            f"'{field}' must contain only letters, digits, underscores, and hyphens.",
            field,
        )
    return cleaned


def validate_username(username: str) -> str:
    """Validate a login username (3-50 chars, lowercase alphanumeric + _-)."""
    cleaned = username.strip().lower()
    if len(cleaned) < 3:
        raise ValidationError("Username must be at least 3 characters.", "username")
    if len(cleaned) > 50:
        raise ValidationError("Username must not exceed 50 characters.", "username")
    if not _USER_RE.match(cleaned):
        raise ValidationError(
            "Username must start with a letter or digit and contain only "
            "lowercase letters, digits, underscores, or hyphens.",
            "username",
        )
    return cleaned


def validate_positive_decimal(
    value, field: str = "value", allow_zero: bool = True
) -> Optional[float]:
    """Validate a numeric value is non-negative."""
    if value is None:
        return None
    try:
        fval = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a number.", field)
    if not allow_zero and fval == 0:
        raise ValidationError(f"'{field}' must be greater than zero.", field)
    if fval < 0:
        raise ValidationError(f"'{field}' must not be negative.", field)
    return fval


def validate_date_order(start, end, start_field: str, end_field: str) -> None:
    """Raise ValidationError if end < start (when both are provided)."""
    if start and end and end < start:
        raise ValidationError(
            f"'{end_field}' must not be earlier than '{start_field}'.",
            end_field,
        )


# ── Phase 7.5 — Additional validators ──────────────────────────────────────────

_ORG_CODE_RE   = re.compile(r'^[A-Z0-9][A-Z0-9_\-]{1,9}$')    # 2–10 chars
_DEPT_CODE_RE  = re.compile(r'^[A-Z0-9][A-Z0-9_\-]{1,19}$')   # 2–20 chars
_ASSET_CODE_RE = re.compile(r'^[A-Z0-9][A-Z0-9_\-]{1,49}$')   # 2–50 chars


def validate_org_code(code: str, field: str = "code") -> str:
    """
    Validate an organisation code.
    Rules: 2–10 chars, uppercase alphanumeric + dash/underscore, starts with alnum.
    Returns the uppercased, stripped value on success.
    """
    if not code:
        raise ValidationError(f"'{field}' is required.", field)
    cleaned = code.strip().upper()
    if len(cleaned) < 2 or len(cleaned) > 10:
        raise ValidationError(
            "Organisation code must be 2–10 characters long.", field
        )
    if not _ORG_CODE_RE.match(cleaned):
        raise ValidationError(
            "Organisation code must contain only uppercase letters, digits, "
            "hyphens, or underscores, and start with a letter or digit.",
            field,
        )
    return cleaned


def validate_dept_code(code: str, field: str = "code") -> str:
    """
    Validate a department code.
    Rules: 2–20 chars, uppercase alphanumeric + dash/underscore, starts with alnum.
    Returns the uppercased, stripped value on success.
    """
    if not code:
        raise ValidationError(f"'{field}' is required.", field)
    cleaned = code.strip().upper()
    if len(cleaned) < 2 or len(cleaned) > 20:
        raise ValidationError(
            "Department code must be 2–20 characters long.", field
        )
    if not _DEPT_CODE_RE.match(cleaned):
        raise ValidationError(
            "Department code must contain only uppercase letters, digits, "
            "hyphens, or underscores, and start with a letter or digit.",
            field,
        )
    return cleaned


def validate_asset_code(code: str, field: str = "asset_code") -> str:
    """
    Validate an asset code.
    Rules: 2–50 chars, uppercase alphanumeric + dash/underscore, starts with alnum.
    Returns the uppercased, stripped value on success.
    """
    if not code:
        raise ValidationError(f"'{field}' is required.", field)
    cleaned = code.strip().upper()
    if len(cleaned) < 2 or len(cleaned) > 50:
        raise ValidationError(
            "Asset code must be 2–50 characters long.", field
        )
    if not _ASSET_CODE_RE.match(cleaned):
        raise ValidationError(
            "Asset code must contain only uppercase letters, digits, "
            "hyphens, or underscores, and start with a letter or digit.",
            field,
        )
    return cleaned


def validate_name(
    value: Optional[str],
    field: str,
    min_len: int = 2,
    max_len: int = 200,
) -> str:
    """
    Strip and validate a name/label field.
    Rejects None, whitespace-only, too-short, or too-long values.
    Returns the stripped value on success.
    """
    if value is None:
        raise ValidationError(f"'{field}' is required.", field)
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"'{field}' cannot be blank.", field)
    if len(cleaned) < min_len:
        raise ValidationError(
            f"'{field}' must be at least {min_len} character(s) long.", field
        )
    if len(cleaned) > max_len:
        raise ValidationError(
            f"'{field}' must not exceed {max_len} characters.", field
        )
    return cleaned


def validate_date_not_future(d, field: str) -> None:
    """
    Raise ValidationError if `d` is after today.
    Useful for joining dates, birth dates, etc.
    Accepts date or datetime objects; None is silently ignored.
    """
    from datetime import date as _date  # local import to keep top-level clean
    if d is None:
        return
    today = _date.today()
    check = d.date() if hasattr(d, "date") else d
    if check > today:
        raise ValidationError(
            f"'{field}' cannot be set to a future date.", field
        )


def validate_decimal_range(
    value,
    field: str,
    min_val: float = 0,
    max_val: float = 99_999_999,
) -> Optional[float]:
    """
    Validate a Decimal/float/int value is within [min_val, max_val].
    Returns None if value is None; raises ValidationError otherwise.
    """
    if value is None:
        return None
    try:
        fval = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a valid number.", field)
    if fval < min_val:
        raise ValidationError(
            f"'{field}' must be at least {min_val:,}.", field
        )
    if fval > max_val:
        raise ValidationError(
            f"'{field}' must not exceed {max_val:,}.", field
        )
    return fval


def sanitize_search_query(query: Optional[str]) -> str:
    """
    Sanitize a free-text search query.
    - Returns "" if None or whitespace-only.
    - Strips surrounding whitespace.
    - Caps the result at 200 characters.
    """
    if not query:
        return ""
    cleaned = query.strip()
    if not cleaned:
        return ""
    return cleaned[:200]
