"""
Sanchay â€” Settings Service
============================
Read / write the app_settings key-value table.
Provides typed getters/setters for every known setting key.
"""

import re
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.models.audit import AppSetting


# â”€â”€ Default values â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

DEFAULTS: dict[str, str] = {
    "app_name":           "Sanchay",
    "asset_code_prefix":  "AST",
    "auto_backup":        "false",
    "backup_location":    "",
    "auto_backup_days":   "1",
    "theme":              "light",
    "default_page_size":  "50",
}

# Validation
_PREFIX_RE = re.compile(r'^[A-Za-z0-9]{2,10}$')


class SettingsService:
    """
    CRUD layer for the app_settings table.

    Usage:
        svc = SettingsService()
        prefix = svc.get("asset_code_prefix", "AST")
        svc.set("asset_code_prefix", "LAP")
    """

    # â”€â”€ Core get / set â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get(self, key: str, default: str = "") -> str:
        """Return a setting value, falling back to the built-in default.
        
        Defensive: wraps the DB access in try/except so any database error
        returns the default value rather than propagating an exception.
        """
        fallback = DEFAULTS.get(key, default)
        try:
            with get_db() as db:
                row = db.query(AppSetting).filter(AppSetting.key == key).first()
                if row and row.value is not None:
                    return row.value
        except Exception as e:
            logger.warning(f"settings.get('{key}'): DB error, returning default: {e}")
        return fallback

    def set(self, key: str, value) -> None:
        """Create or update a setting, with validation for known keys.
        
        Defensive: key must be a non-empty string; value is coerced to str.
        """
        # Defensive: reject empty or non-string keys
        if not key or not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "Setting key must be a non-empty string.",
                "key",
            )
        key = key.strip()

        # Defensive: coerce value to string
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)

        # Validate specific keys
        if key == "asset_code_prefix":
            value = value.strip()
            if not _PREFIX_RE.match(value):
                raise ValidationError(
                    "Asset code prefix must be 2â€“10 alphanumeric characters (letters and digits only).",
                    "asset_code_prefix",
                )

        with get_db() as db:
            row = db.query(AppSetting).filter(AppSetting.key == key).first()
            if row:
                row.value = value
            else:
                db.add(AppSetting(key=key, value=value,
                                  description=DEFAULTS.get(key, "")))
        logger.debug(f"Setting '{key}' updated to '{value}'")

    def get_all(self) -> dict[str, str]:
        """Return all settings merged with defaults."""
        result = dict(DEFAULTS)
        try:
            with get_db() as db:
                rows = db.query(AppSetting).all()
                for row in rows:
                    if row.value is not None:
                        result[row.key] = row.value
        except Exception as e:
            logger.warning(f"settings.get_all(): DB error, returning defaults: {e}")
        return result

    def set_many(self, data: dict[str, str]) -> None:
        """Batch update multiple settings."""
        for key, value in data.items():
            self.set(key, value)

    # â”€â”€ Typed convenience helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Return a setting interpreted as a boolean."""
        return self.get(key, "true" if default else "false").lower() == "true"

    def set_bool(self, key: str, value: bool) -> None:
        """Store a boolean setting as 'true' or 'false'."""
        self.set(key, "true" if value else "false")

    def get_int(self, key: str, default: int = 0) -> int:
        """Return a setting interpreted as an integer, falling back to default."""
        try:
            return int(self.get(key, str(default)))
        except ValueError:
            return default

    # â”€â”€ Named setting accessors â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @property
    def app_name(self) -> str:
        """Return the application display name."""
        return self.get("app_name", "Sanchay")

    @property
    def asset_code_prefix(self) -> str:
        """Return the prefix used when auto-generating asset codes."""
        return self.get("asset_code_prefix", "AST")

    @property
    def auto_backup_enabled(self) -> bool:
        """Return True if automatic backups are enabled."""
        return self.get_bool("auto_backup", False)

    @property
    def backup_location(self) -> str:
        """Return the configured backup directory path."""
        from app.config import config
        return self.get("backup_location") or str(config.BACKUPS_DIR)

    @property
    def auto_backup_days(self) -> int:
        """Return the auto-backup interval in days."""
        return self.get_int("auto_backup_days", 1)

    @property
    def theme(self) -> str:
        """Return the current UI theme name."""
        return self.get("theme", "light")

    def seed_defaults(self) -> None:
        """Ensure all default keys exist in the DB (idempotent / INSERT OR IGNORE).
        
        Safe to call multiple times â€” only adds keys that don't already exist.
        """
        with get_db() as db:
            existing = {r.key for r in db.query(AppSetting).all()}
            for key, value in DEFAULTS.items():
                if key not in existing:
                    db.add(AppSetting(key=key, value=value))
        logger.info("App settings defaults seeded.")

    def reset_to_defaults(self) -> None:
        """Clear all settings from the DB and re-seed with factory defaults.
        
        âš ï¸  DESTRUCTIVE: all customised settings are permanently removed.
        A warning is logged before any data is deleted.
        """
        # Defensive: log a warning because this is a destructive operation
        logger.warning(
            "reset_to_defaults: ALL application settings are being cleared and "
            "reset to factory defaults. This cannot be undone."
        )
        with get_db() as db:
            db.query(AppSetting).delete()
        # Re-seed fresh defaults
        self.seed_defaults()
        logger.info("Settings reset to factory defaults complete.")

    def validate_asset_code_prefix(self, prefix: str) -> str:
        """Validate and normalise an asset code prefix.
        
        Rules:
          - Must not be empty (raises ValidationError)
          - Stripped and uppercased
          - Must be 2â€“10 alphanumeric characters
          
        Returns:
            The validated, normalised prefix.
            
        Raises:
            ValidationError: If the prefix is empty or doesn't match the rules.
        """
        if not prefix or not prefix.strip():
            raise ValidationError(
                "Asset code prefix cannot be empty.",
                "asset_code_prefix",
            )
        prefix = prefix.strip().upper()
        if not _PREFIX_RE.match(prefix):
            raise ValidationError(
                "Asset code prefix must be 2â€“10 alphanumeric characters "
                "(letters and digits only, no spaces or symbols).",
                "asset_code_prefix",
            )
        return prefix

