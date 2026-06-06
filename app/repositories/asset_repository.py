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


class AssetCategoryRepository(BaseRepository[AssetCategory]):
    model = AssetCategory

    def get_by_org(self, org_id: int) -> list[AssetCategory]:
        return (
            self.db.query(AssetCategory)
            .filter(AssetCategory.org_id == org_id, AssetCategory.is_deleted == False)
            .order_by(AssetCategory.name)
            .all()
        )

    def get_root_categories(self, org_id: Optional[int] = None) -> list[AssetCategory]:
        q = self.db.query(AssetCategory).filter(
            AssetCategory.parent_category_id == None,
            AssetCategory.is_deleted == False,
        )
        if org_id:
            q = q.filter(AssetCategory.org_id == org_id)
        return q.order_by(AssetCategory.name).all()

    def code_exists(self, code: str, org_id: Optional[int] = None, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(AssetCategory).filter(
            AssetCategory.code == code, AssetCategory.is_deleted == False
        )
        if org_id:
            q = q.filter(AssetCategory.org_id == org_id)
        if exclude_id:
            q = q.filter(AssetCategory.id != exclude_id)
        return q.count() > 0


class AssetRepository(BaseRepository[Asset]):
    model = Asset

    def get_by_org(self, org_id: int, include_deleted: bool = False) -> list[Asset]:
        q = self.db.query(Asset).filter(Asset.org_id == org_id)
        if not include_deleted:
            q = q.filter(Asset.is_deleted == False)
        return q.order_by(Asset.name).all()

    def get_by_dept(self, dept_id: int) -> list[Asset]:
        return (
            self.db.query(Asset)
            .filter(Asset.dept_id == dept_id, Asset.is_deleted == False)
            .order_by(Asset.name)
            .all()
        )

    def get_by_status(self, status: str, org_id: Optional[int] = None) -> list[Asset]:
        q = self.db.query(Asset).filter(
            Asset.status == status, Asset.is_deleted == False
        )
        if org_id:
            q = q.filter(Asset.org_id == org_id)
        return q.order_by(Asset.name).all()

    def get_by_category(self, category_id: int) -> list[Asset]:
        return (
            self.db.query(Asset)
            .filter(Asset.category_id == category_id, Asset.is_deleted == False)
            .order_by(Asset.name)
            .all()
        )

    def search(
        self,
        query: str,
        org_id: Optional[int] = None,
        status: Optional[str] = None,
        category_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Asset], int]:
        """Full-text search across asset fields. Returns (results, total_count)."""
        q = self.db.query(Asset).filter(Asset.is_deleted == False)

        if query:
            pattern = f"%{query}%"
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
        return (
            self.db.query(Asset)
            .filter(Asset.asset_code == asset_code, Asset.is_deleted == False)
            .first()
        )

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Asset).filter(
            Asset.asset_code == code, Asset.is_deleted == False
        )
        if exclude_id:
            q = q.filter(Asset.id != exclude_id)
        return q.count() > 0

    def count_by_status(self, org_id: Optional[int] = None) -> dict:
        """Returns dict of {status: count} for dashboard."""
        q = self.db.query(Asset.status, func.count(Asset.id)).filter(
            Asset.is_deleted == False
        )
        if org_id:
            q = q.filter(Asset.org_id == org_id)
        rows = q.group_by(Asset.status).all()
        return {row[0]: row[1] for row in rows}

    def generate_next_code(self, prefix: str = "AST") -> str:
        """Generate the next sequential asset code."""
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
        return f"{prefix}-{num:04d}"
