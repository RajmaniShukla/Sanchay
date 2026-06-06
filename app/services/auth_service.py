"""
Sanchay — Authentication Service
====================================
Handles login, logout, user creation, and password management.
All business rules for authentication live here.
"""

import json
from datetime import datetime
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import hash_password, verify_password, current_session
from app.core.exceptions import (
    AuthenticationError, AccountInactiveError, ValidationError,
    DuplicateEntryError, NotFoundError, PermissionDeniedError,
)
from app.models.user import User, Role
from app.models.audit import AuditLog
from app.repositories.user_repository import UserRepository, RoleRepository
from app.constants import UserRole, AuditAction


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
        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_username(username.strip().lower())

            if not user or not verify_password(password, user.password_hash):
                logger.warning(f"Failed login attempt for username='{username}'")
                raise AuthenticationError()

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
        Only admins can call this in the UI (enforced at controller level).
        """
        username = username.strip().lower()

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
                raise ValidationError(f"Invalid role: {role_name}", "role")

            user = User(
                username=username,
                full_name=full_name.strip(),
                email=email.strip() if email else None,
                password_hash=hash_password(password),
                role_id=role.id,
                org_id=org_id,
                dept_id=dept_id,
                is_active=True,
            )
            repo.create(user)

            self._write_audit(
                db, current_session.user_id, AuditAction.CREATE, "users", user.id,
                description=f"Created user '{username}' with role '{role_name}'.",
            )
            logger.info(f"Created user '{username}' (role={role_name})")
            return user

    def change_password(self, user_id: int, new_password: str) -> None:
        """Change a user's password."""
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
        """Enable or disable a user account. Returns new is_active state."""
        with get_db() as db:
            repo = UserRepository(db)
            user = repo.get_by_id(user_id)
            if not user:
                raise NotFoundError("User", str(user_id))

            # Guard: can't deactivate the last admin
            if user.role and user.role.name == "admin" and user.is_active:
                if repo.count_admins() <= 1:
                    raise ValidationError(
                        "Cannot deactivate the last admin account.", "is_active"
                    )

            user.is_active = not user.is_active
            action = "activated" if user.is_active else "deactivated"
            self._write_audit(
                db, current_session.user_id, AuditAction.UPDATE, "users", user_id,
                description=f"User '{user.username}' {action}.",
            )
            return user.is_active

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

    def get_all_users(self) -> list[User]:
        with get_db() as db:
            repo = UserRepository(db)
            return repo.get_active_users()

    def get_all_roles(self) -> list[Role]:
        with get_db() as db:
            repo = RoleRepository(db)
            return repo.get_all()

    @staticmethod
    def _write_audit(
        db, user_id: Optional[int], action, module: str,
        record_id: Optional[int], description: str = ""
    ) -> None:
        log = AuditLog(
            user_id=user_id,
            action=action.value if hasattr(action, "value") else action,
            module=module,
            record_id=record_id,
            description=description,
        )
        db.add(log)
        db.flush()
