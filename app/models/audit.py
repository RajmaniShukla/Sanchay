"""
Sanchay — Audit Log Model
============================
Immutable audit trail for all data mutations and key events.
Every CREATE, UPDATE, DELETE, LOGIN, ISSUE, RETURN is recorded here.
"""

import json
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(Base):
    """
    Append-only audit trail.
    Records are never updated or deleted.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    table_name: Mapped[Optional[str]] = mapped_column(String(100))
    record_id: Mapped[Optional[int]] = mapped_column(Integer)
    old_values_json: Mapped[Optional[str]] = mapped_column(Text)
    new_values_json: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now(), index=True
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")

    @property
    def old_values(self) -> Optional[dict]:
        if self.old_values_json:
            try:
                return json.loads(self.old_values_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @old_values.setter
    def old_values(self, value: Optional[dict]) -> None:
        self.old_values_json = json.dumps(value) if value else None

    @property
    def new_values(self) -> Optional[dict]:
        if self.new_values_json:
            try:
                return json.loads(self.new_values_json)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @new_values.setter
    def new_values(self, value: Optional[dict]) -> None:
        self.new_values_json = json.dumps(value) if value else None

    @property
    def username(self) -> str:
        return self.user.username if self.user else "system"

    def __repr__(self) -> str:
        return f"<AuditLog action='{self.action}' user='{self.username}' @ {self.timestamp}>"


class AppSetting(Base):
    """
    Key-value store for application-wide settings.
    Persisted in database so they survive restarts.
    """
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AppSetting key='{self.key}' value='{self.value}'>"
