"""
Sanchay — Base Model Mixin
============================
Provides common columns (timestamps, soft delete) inherited
by all domain models. Keeps DRY and consistent.
"""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class TimestampMixin:
    """Adds created_at and updated_at timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds is_deleted for soft delete support."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    def soft_delete(self) -> None:
        self.is_deleted = True


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Abstract base for all domain models.
    Provides: primary key, timestamps, soft delete.
    """
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    def to_dict(self) -> dict:
        """
        Convert model to a JSON-safe dictionary (excludes relationships).
        datetime / date / Decimal values are serialised to safe Python types.
        """
        from datetime import datetime, date
        from decimal import Decimal
        result = {}
        for col in self.__table__.columns:
            val = getattr(self, col.key)
            if isinstance(val, (datetime, date)):
                result[col.key] = val.isoformat()
            elif isinstance(val, Decimal):
                result[col.key] = float(val)
            else:
                result[col.key] = val
        return result

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"
