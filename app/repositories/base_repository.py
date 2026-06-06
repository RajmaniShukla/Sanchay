"""
Sanchay — Base Repository
============================
Generic CRUD repository providing common operations for all models.
Concrete repositories inherit and extend this base.
"""

from typing import Generic, TypeVar, Optional, Type
from sqlalchemy.orm import Session
from app.models.base import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Generic repository with CRUD + soft-delete operations.
    
    Usage:
        class AssetRepository(BaseRepository[Asset]):
            model = Asset
    """

    model: Type[T]

    def __init__(self, db: Session):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, record_id: int) -> Optional[T]:
        """Get a single record by primary key (excludes soft-deleted)."""
        return (
            self.db.query(self.model)
            .filter(self.model.id == record_id, self.model.is_deleted == False)
            .first()
        )

    def get_all(self, limit: int = 500, offset: int = 0) -> list[T]:
        """Get all active (non-deleted) records."""
        return (
            self.db.query(self.model)
            .filter(self.model.is_deleted == False)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        """Count all active records."""
        return (
            self.db.query(self.model)
            .filter(self.model.is_deleted == False)
            .count()
        )

    def exists(self, record_id: int) -> bool:
        """Check if a record exists and is not deleted."""
        return self.get_by_id(record_id) is not None

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, obj: T) -> T:
        """Persist a new record."""
        self.db.add(obj)
        self.db.flush()  # Get the id without committing
        self.db.refresh(obj)
        return obj

    def update(self, obj: T, data: dict) -> T:
        """Apply a dict of field updates to an existing record."""
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """Soft delete: sets is_deleted = True."""
        obj.is_deleted = True
        self.db.flush()

    def hard_delete(self, obj: T) -> None:
        """Permanently remove a record. USE WITH CAUTION."""
        self.db.delete(obj)
        self.db.flush()

    def save(self) -> None:
        """Flush pending changes to the DB (within transaction)."""
        self.db.flush()
