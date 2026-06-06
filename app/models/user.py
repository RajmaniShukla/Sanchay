"""
Sanchay — User & Role Models
==============================
Authentication and authorization entities.
"""

import json
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampMixin
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.organization import Organization, Department
    from app.models.audit import AuditLog


class Role(Base, TimestampMixin):
    """
    User role defining permission sets.
    Seeded with: admin, manager, operator, viewer
    """
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    permissions_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="role")

    @property
    def permissions(self) -> dict:
        try:
            return json.loads(self.permissions_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @permissions.setter
    def permissions(self, value: dict) -> None:
        self.permissions_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Role name='{self.name}'>"


class User(BaseModel):
    """
    Application user account.
    One user = one login session on the desktop app.
    """
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Foreign keys
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id"), index=True)
    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id"), index=True)
    dept_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))

    # Relationships
    role: Mapped[Optional["Role"]] = relationship("Role", back_populates="users")
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    department: Mapped[Optional["Department"]] = relationship("Department")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")

    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else "unknown"

    def __repr__(self) -> str:
        return f"<User username='{self.username}' role='{self.role_name}'>"
