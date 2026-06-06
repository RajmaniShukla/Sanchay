"""
Sanchay — Asset Repository
============================
Data access for Asset and AssetCategory entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.asset import Asset, AssetCategory
from app.repositories.base_repository import BaseRepository

# All valid asset statuses — used to guarantee complete dicts even with zero counts
_ALL_STATUSES = ("available", "issued", "maintenance", "disposed", "lost")


class AssetCategoryRepository(BaseRepository[AssetCategory]):
    """Data access for AssetCategory entities."""

    model = AssetCategory

    def get_by_org(self, org_id: int) -> list[AssetCategory]:
        """Return all categories for the given organisation."""
        return (
            self.db.query(AssetCategory)
            .filter(AssetCategory.org_id == org_id, AssetCategory.is_deleted == False)
            .order_by(AssetCategory.name)
            .all()
        )

    def get_root_categories(self, org_id: Optional[int] = None) -> list[AssetCategory]:
        """Return top-level (parentless) categories, optionally filtered by org."""
        q = self.db.query(AssetCategory).filter(
            AssetCategory.parent_category_id == None,
            AssetCategory.is_deleted == False,
        )
        if org_id:
            q = q.filter(AssetCategory.org_id == org_id)
        return q.order_by(AssetCategory.name).all()

    def code_exists(self, code: str, org_id: Optional[int] = None, exclude_id: Optional[int] = None) -> bool:
        """Return True if a category with this code already exists (within the same org)."""
        q = self.db.query(AssetCategory).filter(
            AssetCategory.code == code, AssetCategory.is_deleted == False
        )
        if org_id:
            q = q.filter(AssetCategory.org_id == org_id)
        if exclude_id:
            q = q.filter(AssetCategory.id != exclude_id)
        return q.count() > 0


class AssetRepository(BaseRepository[Asset]):
    """Data access for Asset entities."""

    model = Asset

    def get_by_org(self, org_id: int, include_deleted: bool = False) -> list[Asset]:
        """Return all assets for the given organisation."""
        q = self.db.query(Asset).filter(Asset.org_id == org_id)
        if not include_deleted:
            q = q.filter(Asset.is_deleted == False)
        return q.order_by(Asset.name).all()

    def get_by_dept(self, dept_id: int) -> list[Asset]:
        """Return all assets assigned to a department."""
        return (
            self.db.query(Asset)
            .filter(Asset.dept_id == dept_id, Asset.is_deleted == False)
            .order_by(Asset.name)
            .all()
        )

    def get_by_status(self, status: str, org_id: Optional[int] = None) -> list[Asset]:
        """Return all assets with the given status, optionally filtered by org."""
        q = self.db.query(Asset).filter(
            Asset.status == status, Asset.is_deleted == False
        )
        if org_id:
            q = q.filter(Asset.org_id == org_id)
        return q.order_by(Asset.name).all()

    def get_by_category(self, category_id: int) -> list[Asset]:
        """Return all assets in the given category."""
        return (
            self.db.query(Asset)
            .filter(Asset.category_id == category_id, Asset.is_deleted == False)
            .order_by(Asset.name)
            .all()
        )

    def get_by_serial_number(self, serial: str) -> Optional[Asset]:
        """Return the asset with the exact serial number, or None if not found."""
        if not serial:
            return None
        return (
            self.db.query(Asset)
            .filter(Asset.serial_number == serial, Asset.is_deleted == False)
            .first()
        )

    def search(
        self,
        query: str = "",
        org_id: Optional[int] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Asset], int]:
        """
        Full-text search across asset fields.
        
        None or whitespace-only query returns all assets (respecting other filters).
        Returns (results, total_count).
        """
        q = self.db.query(Asset).filter(Asset.is_deleted == False)

        # Defensive: treat None as empty string; strip whitespace
        safe_query = (query or "").strip()

        # Only apply text filter when query is non-empty
        if safe_query:
            pattern = f"%{safe_query}%"
            q = q.filter(
                or_(
                    Asset.name.ilike(pattern),
                    Asset.asset_code.ilike(pattern),
                    Asset.serial_number.ilike(pattern),
                    Asset.manufacturer.ilike(pattern),
                    Asset.model_number.ilike(pattern),
                    Asset.location.ilike(pattern),
                )
            )
        if org_id:
            q = q.filter(Asset.org_id == org_id)
        if status:
            q = q.filter(Asset.status == status)
        if category_id:
            q = q.filter(Asset.category_id == category_id)
        if dept_id:
            q = q.filter(Asset.dept_id == dept_id)

        total = q.count()
        results = q.order_by(Asset.name).offset(offset).limit(limit).all()
        return results, total

    def get_by_code(self, asset_code: str) -> Optional[Asset]:
        """Return an asset by its unique asset_code, or None.
        
        Strips and uppercases the input before querying so minor formatting
        differences never cause missed lookups.
        """
        if not asset_code:
            return None
        # Defensive: normalise code before DB lookup
        asset_code = asset_code.strip().upper()
        return (
            self.db.query(Asset)
            .filter(Asset.asset_code == asset_code, Asset.is_deleted == False)
            .first()
        )

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        """Return True if an asset with this code already exists."""
        q = self.db.query(Asset).filter(
            Asset.asset_code == code, Asset.is_deleted == False
        )
        if exclude_id:
            q = q.filter(Asset.id != exclude_id)
        return q.count() > 0

    def count_by_status(self, org_id: Optional[int] = None) -> dict:
        """Return {status: count} dict for dashboard display.
        
        Always includes all five standard statuses even if their count is 0,
        so callers never need to guard against missing keys.
        """
        q = self.db.query(Asset.status, func.count(Asset.id)).filter(
            Asset.is_deleted == False
        )
        if org_id:
            q = q.filter(Asset.org_id == org_id)
        rows = q.group_by(Asset.status).all()

        # Merge query results onto a complete default dict
        result = {s: 0 for s in _ALL_STATUSES}
        for status, cnt in rows:
            if status is not None:
                result[status] = cnt
        return result

    def generate_next_code(self, prefix: str = "AST") -> str:
        """Generate the next sequential asset code using the given prefix.
        
        Guarantees uniqueness by incrementing until the generated code does
        not already exist in the database, so prefix changes or gaps in the
        sequence never produce a duplicate code.
        """
        # Defensive: normalise prefix
        prefix = (prefix or "AST").strip().upper()

        last = (
            self.db.query(Asset)
            .filter(Asset.asset_code.like(f"{prefix}-%"))
            .order_by(Asset.id.desc())
            .first()
        )
        if last:
            try:
                num = int(last.asset_code.split("-")[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1

        # Loop until we find a code that doesn't already exist
        for _ in range(100_000):  # safety cap to prevent infinite loop
            candidate = f"{prefix}-{num:04d}"
            if not self.code_exists(candidate):
                return candidate
            num += 1

        # Fallback: use timestamp-based suffix (should never reach here)
        import time
        return f"{prefix}-{int(time.time())}"
