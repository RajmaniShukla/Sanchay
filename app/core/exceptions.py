"""
Sanchay — Custom Exceptions
==============================
Domain-specific exception hierarchy for clean error handling
across service and controller layers.
"""


class SanchayError(Exception):
    """Base exception for all Sanchay application errors."""

    def __init__(self, message: str, code: str = "GENERIC_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Authentication Errors ─────────────────────────────────────────────────────

class AuthenticationError(SanchayError):
    """Raised when login credentials are invalid."""
    def __init__(self, message: str = "Invalid username or password."):
        super().__init__(message, "AUTH_ERROR")


class SessionExpiredError(SanchayError):
    """Raised when the user session has expired."""
    def __init__(self):
        super().__init__("Your session has expired. Please log in again.", "SESSION_EXPIRED")


class PermissionDeniedError(SanchayError):
    """Raised when a user lacks permission for an action."""
    def __init__(self, action: str = "perform this action"):
        super().__init__(f"You do not have permission to {action}.", "PERMISSION_DENIED")


class AccountInactiveError(SanchayError):
    """Raised when a deactivated account attempts to log in."""
    def __init__(self):
        super().__init__("This account has been deactivated. Contact an administrator.", "ACCOUNT_INACTIVE")


# ── Validation Errors ─────────────────────────────────────────────────────────

class ValidationError(SanchayError):
    """Raised when input data fails business rule validation."""
    def __init__(self, message: str, field: str = ""):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field


class DuplicateEntryError(SanchayError):
    """Raised when a unique constraint would be violated."""
    def __init__(self, entity: str, field: str, value: str):
        super().__init__(
            f"{entity} with {field} '{value}' already exists.",
            "DUPLICATE_ENTRY",
        )
        self.entity = entity
        self.field = field
        self.value = value


class RequiredFieldError(ValidationError):
    """Raised when a required field is missing."""
    def __init__(self, field: str):
        super().__init__(f"'{field}' is required.", field)


# ── Not Found Errors ──────────────────────────────────────────────────────────

class NotFoundError(SanchayError):
    """Raised when a requested record does not exist."""
    def __init__(self, entity: str, identifier: str = ""):
        msg = f"{entity} not found."
        if identifier:
            msg = f"{entity} '{identifier}' not found."
        super().__init__(msg, "NOT_FOUND")
        self.entity = entity


# ── Business Logic Errors ─────────────────────────────────────────────────────

class AssetNotAvailableError(SanchayError):
    """Raised when trying to issue an asset that is not available."""
    def __init__(self, asset_name: str, current_status: str):
        super().__init__(
            f"Asset '{asset_name}' cannot be issued. Current status: {current_status}.",
            "ASSET_NOT_AVAILABLE",
        )


class PersonInactiveError(SanchayError):
    """Raised when trying to issue an asset to an inactive person."""
    def __init__(self, person_name: str):
        super().__init__(
            f"Cannot issue asset to '{person_name}' — person is inactive.",
            "PERSON_INACTIVE",
        )


class ActiveIssueExistsError(SanchayError):
    """Raised when an asset already has an active issue."""
    def __init__(self, asset_name: str):
        super().__init__(
            f"Asset '{asset_name}' is already issued. It must be returned before issuing again.",
            "ACTIVE_ISSUE_EXISTS",
        )


class NoActiveIssueError(SanchayError):
    """Raised when trying to return an asset that has no active issue."""
    def __init__(self, asset_name: str):
        super().__init__(
            f"Asset '{asset_name}' has no active issue to return.",
            "NO_ACTIVE_ISSUE",
        )


# ── Database Errors ───────────────────────────────────────────────────────────

class DatabaseError(SanchayError):
    """Raised when a database operation fails unexpectedly."""
    def __init__(self, message: str = "A database error occurred."):
        super().__init__(message, "DB_ERROR")


class BackupError(SanchayError):
    """Raised when a backup or restore operation fails."""
    def __init__(self, message: str):
        super().__init__(message, "BACKUP_ERROR")


# ── Report Errors ─────────────────────────────────────────────────────────────

class ReportError(SanchayError):
    """Raised when report generation fails."""
    def __init__(self, message: str):
        super().__init__(message, "REPORT_ERROR")
