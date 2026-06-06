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

# Absolute limits for get_all pagination
_MAX_LIMIT  = 10_000
_MIN_LIMIT  = 1
_MIN_OFFSET = 0


class BaseRepository(Generic[T]):
    """
    Generic repository with CRUD + soft-delete operations.
    
    Usage:
        class AssetRepository(BaseRepository[Asset]):
            model = Asset
    """

    model: Type[T]

    def __init__(self, db: Session):
        """Initialise with an open SQLAlchemy session."""
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, record_id) -> Optional[T]:
        """Get a single record by primary key (excludes soft-deleted).
        
        Returns None immediately for None, zero, or negative record_id values
        so callers never hit the database with invalid keys.
        """
        # Defensive: reject None, 0, or negative ids without hitting the DB
        if record_id is None:
            return None
        try:
            record_id = int(record_id)
        except (TypeError, ValueError):
            return None
        if record_id <= 0:
            return None
        return (
            self.db.query(self.model)
            .filter(self.model.id == record_id, self.model.is_deleted == False)
            .first()
        )

    def get_by_ids(self, ids: list[int]) -> list[T]:
        """Return all active records whose id is in the given list."""
        if not ids:
            return []
        return (
            self.db.query(self.model)
            .filter(self.model.id.in_(ids), self.model.is_deleted == False)
            .all()
        )

    def get_all(self, limit: int = 500, offset: int = 0) -> list[T]:
        """Get all active (non-deleted) records.
        
        Clamps limit to [1, 10000] and offset to [0, ∞) so bad callers can't
        accidentally fetch an unbounded result set or produce a DB error.
        """
        # Defensive: clamp limit and offset to safe ranges
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 500
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = 0

        limit  = max(_MIN_LIMIT,  min(limit, _MAX_LIMIT))
        offset = max(_MIN_OFFSET, offset)

        return (
            self.db.query(self.model)
            .filter(self.model.is_deleted == False)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_paginated(self, page: int, page_size: int) -> tuple[list[T], int]:
        """
        Return one page of active records and the total active count.
        
        Args:
            page:      1-based page index.
            page_size: Number of records per page.
            
        Returns:
            (records, total_count)
        """
        page = max(1, page)
        page_size = max(1, page_size)
        q = self.db.query(self.model).filter(self.model.is_deleted == False)
        total = q.count()
        records = q.offset((page - 1) * page_size).limit(page_size).all()
        return records, total

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

    def exists_by_id(self, record_id: int) -> bool:
        """Convenience alias: return True if the record exists and is not deleted.
        
        Returns False immediately for invalid ids (None, 0, negative).
        """
        if record_id is None:
            return False
        try:
            record_id = int(record_id)
        except (TypeError, ValueError):
            return False
        if record_id <= 0:
            return False
        return (
            self.db.query(self.model)
            .filter(self.model.id == record_id, self.model.is_deleted == False)
            .count()
        ) > 0

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, obj: T) -> T:
        """Persist a new record."""
        self.db.add(obj)
        self.db.flush()  # Get the id without committing
        self.db.refresh(obj)
        return obj

    def update(self, obj: T, data: dict) -> T:
        """Apply a dict of field updates to an existing record.
        
        Silently ignores keys that are not valid columns on the model so that
        passing extra/unknown fields never raises an AttributeError.
        """
        for field, value in data.items():
            # Only set attributes that actually exist on the model instance
            if hasattr(obj, field):
                setattr(obj, field, value)
        self.db.flush()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """Soft delete: sets is_deleted = True.
        
        Safely no-ops if obj is None.
        """
        if obj is None:
            return
        obj.is_deleted = True
        self.db.flush()

    def hard_delete(self, obj: T) -> None:
        """Permanently remove a record. USE WITH CAUTION."""
        self.db.delete(obj)
        self.db.flush()

    def save(self) -> None:
        """Flush pending changes to the DB (within transaction)."""
        self.db.flush()
