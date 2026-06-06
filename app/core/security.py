"""
Sanchay — Security Utilities
==============================
Password hashing, verification, and session management.
Uses bcrypt for hashing — never stores plaintext passwords.
"""

import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from app.config import config


# ── Password Hashing ──────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        plain_password: The plaintext password to hash.
        
    Returns:
        A bcrypt hashed password string.
    """
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    if len(plain_password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    salt = bcrypt.gensalt(rounds=config.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    
    Args:
        plain_password: The plaintext password to check.
        hashed_password: The stored bcrypt hash.
        
    Returns:
        True if the password matches, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum security requirements.
    
    Returns:
        (is_valid, message) tuple.
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    return True, "Password is valid."


# ── Session Management ────────────────────────────────────────────────────────

class UserSession:
    """
    Lightweight in-memory session for the currently logged-in user.
    Stored as a module-level singleton — one user per desktop instance.
    """

    def __init__(self):
        self._user_id: Optional[int] = None
        self._username: Optional[str] = None
        self._full_name: Optional[str] = None
        self._role: Optional[str] = None
        self._org_id: Optional[int] = None
        self._dept_id: Optional[int] = None
        self._login_time: Optional[datetime] = None
        self._permissions: dict = {}

    def login(
        self,
        user_id: int,
        username: str,
        full_name: str,
        role: str,
        permissions: dict,
        org_id: Optional[int] = None,
        dept_id: Optional[int] = None,
    ) -> None:
        """Populate session after successful authentication."""
        self._user_id   = user_id
        self._username  = username
        self._full_name = full_name
        self._role      = role
        self._org_id    = org_id
        self._dept_id   = dept_id
        self._login_time = datetime.now()
        self._permissions = permissions
        logger.info(f"Session started for user '{username}' (role={role})")

    def logout(self) -> None:
        """Clear all session data."""
        username = self._username
        self.__init__()
        logger.info(f"Session ended for user '{username}'")

    @property
    def is_authenticated(self) -> bool:
        return self._user_id is not None

    @property
    def is_expired(self) -> bool:
        if not self._login_time:
            return True
        expiry = self._login_time + timedelta(minutes=config.SESSION_TIMEOUT_MINUTES)
        return datetime.now() > expiry

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def full_name(self) -> Optional[str]:
        return self._full_name

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def org_id(self) -> Optional[int]:
        return self._org_id

    @property
    def dept_id(self) -> Optional[int]:
        return self._dept_id

    def has_permission(self, permission: str) -> bool:
        """
        Check if the current user has a specific permission.
        Admin has all permissions.
        
        Args:
            permission: e.g. 'assets:write', 'users:read'
        """
        if self._role == "admin":
            return True
        perms = self._permissions
        if perms.get("all"):
            return True
        # Check module-level permission
        parts = permission.split(":")
        if len(parts) == 2:
            module, access = parts
            module_perm = perms.get(module, "")
            if access == "r" and "r" in module_perm:
                return True
            if access == "w" and "w" in module_perm:
                return True
        return False

    def is_admin(self) -> bool:
        return self._role == "admin"

    def is_manager(self) -> bool:
        return self._role in ("admin", "manager")

    def is_operator(self) -> bool:
        return self._role in ("admin", "manager", "operator")

    def __repr__(self) -> str:
        return f"<UserSession user='{self._username}' role='{self._role}'>"


# ── Module-level session singleton ────────────────────────────────────────────
# Import this everywhere: from app.core.security import current_session
current_session = UserSession()
