"""
Sanchay — Authentication Service
====================================
Handles login, logout, user creation, and password management.
All business rules for authentication live here.
"""

import json
import re
from datetime import datetime
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password, current_session,
    require_authenticated, require_role,
)
from app.core.exceptions import (
    AuthenticationError, AccountInactiveError, ValidationError,
    DuplicateEntryError, NotFoundError, PermissionDeniedError,
)
from app.models.user import User, Role
from app.models.audit import AuditLog
from app.repositories.user_repository import UserRepository, RoleRepository
from app.constants import UserRole, AuditAction


# ── Validation patterns ────────────────────────────────────────────────────────

EMAIL_RE    = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
USERNAME_RE = re.compile(r'^[a-z0-9_]{1,64}$')


def _validate_email(email: str) -> None:
    """Raise ValidationError if email format is invalid."""
    if email and not EMAIL_RE.match(email):
        raise ValidationError(
            f"The email address '{email}' doesn't look right. "
            "Please use a format like user@example.com.",
            "email",
        )


def _validate_username(username: str) -> None:
    """Raise ValidationError if username contains invalid characters or spaces."""
    if not USERNAME_RE.match(username):
        raise ValidationError(
            "Username must be lowercase, contain only letters, digits, or underscores, "
            "and have no spaces.",
            "username",
        )


# ── Default role permissions ──────────────────────────────────────────────────

ROLE_PERMISSIONS = {
    UserRole.ADMIN.value: {"all": True},
    UserRole.MANAGER.value: {
        "assets": "rw", "persons": "rw",
        "departments": "rw", "reports": "r",
        "transactions": "rw", "settings": "r",
    },
    UserRole.OPERATOR.value: {
        "assets": "r", "persons": "r",
        "transactions": "rw",
    },
    UserRole.VIEWER.value: {
        "assets": "r", "persons": "r",
        "reports": "r", "transactions": "r",
    },
}


class AuthService:
    """
    Authentication and user management service.
    
    Usage:
        service = AuthService()
        service.login("admin", "password123")
    """

    def login(self, username: str, password: str) -> dict:
        """
        Authenticate a user and populate the global session.
        
        Args:
            username: Login username (case-insensitive).
            password: Plaintext password.
            
        Returns:
            Dict with user info on success.
            
        Raises:
            AuthenticationError: Bad credentials.
            AccountInactiveError: Account is deactivated.
        """
        username = username.strip().lower()
        logger.debug(f"Login attempt for username='{username}'")

        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_username(username)

            if not user or not verify_password(password, user.password_hash):
                logger.warning(f"Failed login attempt for username='{username}'")
                raise AuthenticationError(
                    "The username or password you entered is incorrect. Please try again."
                )

            if not user.is_active:
                raise AccountInactiveError()

            # Update last_login
            user.last_login = datetime.now()

            # Build permissions from role
            permissions = {}
            if user.role:
                permissions = user.role.permissions

            # Write to global session
            current_session.login(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role_name,
                permissions=permissions,
                org_id=user.org_id,
                dept_id=user.dept_id,
            )

            # Audit log
            self._write_audit(db, user.id, AuditAction.LOGIN, "users", user.id,
                              description=f"User '{user.username}' logged in.")

            logger.info(f"User '{username}' logged in successfully.")
            return {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role_name,
            }

    def logout(self) -> None:
        """Log out the current user."""
        if current_session.is_authenticated:
            with get_db() as db:
                self._write_audit(
                    db, current_session.user_id, AuditAction.LOGOUT, "users",
                    current_session.user_id,
                    description=f"User '{current_session.username}' logged out.",
                )
        current_session.logout()

    def create_user(
        self,
        username: str,
        full_name: str,
        password: str,
        role_name: str,
        email: Optional[str] = None,
        org_id: Optional[int] = None,
        dept_id: Optional[int] = None,
    ) -> User:
        """
        Create a new user account.

        Permission rules:
        - If an authenticated admin session exists, the request proceeds.
        - If NOT authenticated, creation is allowed ONLY when no admin users
          exist yet (bootstrap/first-run mode). This supports the initial
          setup flow without requiring a pre-existing admin.
        - Any other unauthenticated call raises AuthenticationError.
        """
        if not current_session.is_authenticated:
            # Bootstrap gate: allow only if no admin accounts exist yet
            with get_db() as _bdb:
                _rr = RoleRepository(_bdb)
                _ur = UserRepository(_bdb)
                _admin_role = _rr.get_by_name(UserRole.ADMIN.value)
                _admin_count = _ur.count_admins() if _admin_role else 0
            if _admin_count > 0:
                raise PermissionDeniedError("create users without logging in")
        else:
            require_role("admin")

        username  = username.strip().lower()
        full_name = full_name.strip()
        email     = email.strip() if email else None

        # Validate username format
        _validate_username(username)

        # Validate email if provided
        if email:
            _validate_email(email)

        if not full_name:
            raise ValidationError("Full name is required.", "full_name")

        if not password:
            raise ValidationError("Password is required.", "password")

        logger.debug(f"Creating user '{username}' with role '{role_name}'")

        with get_db() as db:
            repo = UserRepository(db)
            role_repo = RoleRepository(db)

            # Validate uniqueness
            if repo.username_exists(username):
                raise DuplicateEntryError("User", "username", username)
            if email and repo.email_exists(email):
                raise DuplicateEntryError("User", "email", email)

            # Validate role
            role = role_repo.get_by_name(role_name)
            if not role:
                raise ValidationError(
                    f"The role '{role_name}' does not exist. "
                    "Please choose a valid role (admin, manager, operator, viewer).",
                    "role",
                )

            user = User(
                username=username,
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role_id=role.id,
                org_id=org_id,
                dept_id=dept_id,
                is_active=True,
            )
            repo.create(user)

            # Eagerly load the role relationship before session closes
            _ = user.role

            self._write_audit(
                db, current_session.user_id, AuditAction.CREATE, "users", user.id,
                description=f"Created user '{username}' with role '{role_name}'.",
            )
            logger.info(f"Created user '{username}' (role={role_name})")
            return user

    def change_password(self, user_id: int, new_password: str) -> None:
        """Change a user's password.

        - Admins may change any user's password.
        - Non-admins may only change their own password.
        """
        require_authenticated()
        # Allow: admin changing anyone's, or user changing their own
        if current_session.role != "admin" and current_session.user_id != user_id:
            raise PermissionDeniedError("change another user's password")

        if not new_password or not new_password.strip():
            raise ValidationError("New password cannot be empty.", "new_password")

        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))
            user.password_hash = hash_password(new_password)
            self._write_audit(
                db, current_session.user_id, AuditAction.UPDATE, "users", user_id,
                description=f"Password changed for user '{user.username}'.",
            )

    def toggle_user_active(self, user_id: int) -> bool:
        """Enable or disable a user account. Returns new is_active state.

        Requires: authenticated session + admin role.
        """
        require_authenticated()
        require_role("admin")

        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))

            # Guard: can't deactivate the last admin
            if user.role and user.role.name == "admin" and user.is_active:
                if repo.count_admins() <= 1:
                    raise ValidationError(
                        "Cannot deactivate the last admin account. "
                        "At least one admin must remain active.",
                        "is_active",
                    )

            user.is_active = not user.is_active
            action = "activated" if user.is_active else "deactivated"
            self._write_audit(
                db, current_session.user_id, AuditAction.UPDATE, "users", user_id,
                description=f"User '{user.username}' {action}.",
            )
            return user.is_active

    def get_user_by_id(self, user_id: int) -> User:
        """Return a User by primary key, raising NotFoundError if absent."""
        logger.debug(f"Fetching user by id={user_id}")
        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))
            # Eagerly load role so it survives session close
            _ = user.role
            return user

    def seed_default_roles(self) -> None:
        """Create the four default roles if they don't exist. Called on first run."""
        with get_db() as db:
            repo = RoleRepository(db)
            for role_name, perms in ROLE_PERMISSIONS.items():
                if not repo.get_by_name(role_name):
                    role = Role(
                        name=role_name,
                        description=f"Built-in {role_name} role",
                        permissions_json=json.dumps(perms),
                    )
                    repo.create(role)
            logger.info("Default roles seeded.")

    def has_any_users(self) -> bool:
        """Return True if at least one user account exists in the database."""
        try:
            with get_db() as db:
                return db.query(User).limit(1).count() > 0
        except Exception:
            return False

    def get_all_users(self) -> list[User]:
        """Return all active users."""
        with get_db() as db:
            repo = UserRepository(db)
            return repo.get_active_users()

    def get_all_roles(self) -> list[Role]:
        """Return all roles."""
        with get_db() as db:
            repo = RoleRepository(db)
            return repo.get_all()

    @staticmethod
    def _write_audit(
        db, user_id: Optional[int], action, module: str,
        record_id: Optional[int], description: str = ""
    ) -> None:
        """Write an audit log entry within the current DB session."""
        log = AuditLog(
            user_id=user_id,
            action=action.value if hasattr(action, "value") else action,
            module=module,
            record_id=record_id,
            description=description,
        )
        db.add(log)
        db.flush()
