"""
Sanchay — Asset Service
=========================
Business logic for asset catalog, categories, and lifecycle management.
"""

from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session
from app.core.exceptions import (
    ValidationError, DuplicateEntryError, NotFoundError,
)
from app.models.asset import Asset, AssetCategory
from app.models.audit import AuditLog
from app.repositories.asset_repository import AssetRepository, AssetCategoryRepository
from app.constants import AssetStatus, AssetCondition, AuditAction


class AssetCategoryService:

    def get_all(self, org_id: Optional[int] = None) -> list[AssetCategory]:
        with get_db() as db:
            repo = AssetCategoryRepository(db)
            if org_id:
                return repo.get_by_org(org_id)
            return repo.get_all()

    def get_root_categories(self, org_id: Optional[int] = None) -> list[AssetCategory]:
        with get_db() as db:
            repo = AssetCategoryRepository(db)
            return repo.get_root_categories(org_id)

    def get_by_id(self, cat_id: int) -> AssetCategory:
        with get_db() as db:
            repo = AssetCategoryRepository(db)
            cat = repo.get_by_id(cat_id)
            if not cat:
                raise NotFoundError("Asset Category", str(cat_id))
            return cat

    def create(
        self,
        name: str,
        code: str,
        org_id: Optional[int] = None,
        parent_category_id: Optional[int] = None,
        description: Optional[str] = None,
        depreciation_rate: Optional[float] = None,
        useful_life_years: Optional[int] = None,
    ) -> AssetCategory:
        name = name.strip()
        code = code.strip().upper()

        if not name:
            raise ValidationError("Category name is required.", "name")
        if not code:
            raise ValidationError("Category code is required.", "code")

        with get_db() as db:
            repo = AssetCategoryRepository(db)
            if repo.code_exists(code, org_id):
                raise DuplicateEntryError("AssetCategory", "code", code)

            cat = AssetCategory(
                name=name, code=code, org_id=org_id,
                parent_category_id=parent_category_id,
                description=description,
                depreciation_rate=depreciation_rate,
                useful_life_years=useful_life_years,
            )
            repo.create(cat)
            self._audit(db, AuditAction.CREATE, "asset_categories", cat.id,
                        description=f"Category '{name}' created.")
            logger.info(f"Asset category '{name}' created.")
            return cat

    def update(self, cat_id: int, data: dict) -> AssetCategory:
        with get_db() as db:
            repo = AssetCategoryRepository(db)
            cat = repo.get_by_id(cat_id)
            if not cat:
                raise NotFoundError("Asset Category", str(cat_id))
            if "code" in data:
                data["code"] = data["code"].strip().upper()
                if repo.code_exists(data["code"], cat.org_id, exclude_id=cat_id):
                    raise DuplicateEntryError("AssetCategory", "code", data["code"])
            old = cat.to_dict()
            repo.update(cat, data)
            self._audit(db, AuditAction.UPDATE, "asset_categories", cat_id,
                        old_values=old, description=f"Category '{cat.name}' updated.")
            return cat

    def delete(self, cat_id: int) -> None:
        with get_db() as db:
            repo = AssetCategoryRepository(db)
            cat = repo.get_by_id(cat_id)
            if not cat:
                raise NotFoundError("Asset Category", str(cat_id))
            # Check if assets use this category
            asset_repo = AssetRepository(db)
            assets = asset_repo.get_by_category(cat_id)
            if assets:
                raise ValidationError(
                    f"Cannot delete category '{cat.name}' — {len(assets)} asset(s) use it.",
                    "category_id",
                )
            repo.delete(cat)
            self._audit(db, AuditAction.DELETE, "asset_categories", cat_id,
                        description=f"Category '{cat.name}' deleted.")


class AssetService:

    def get_all(self, org_id: Optional[int] = None) -> list[Asset]:
        with get_db() as db:
            repo = AssetRepository(db)
            if org_id:
                return repo.get_by_org(org_id)
            return repo.get_all()

    def get_by_id(self, asset_id: int) -> Asset:
        with get_db() as db:
            repo = AssetRepository(db)
            asset = repo.get_by_id(asset_id)
            if not asset:
                raise NotFoundError("Asset", str(asset_id))
            return asset

    def search(self, **kwargs) -> tuple[list[Asset], int]:
        with get_db() as db:
            repo = AssetRepository(db)
            return repo.search(**kwargs)

    def create(
        self,
        name: str,
        org_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        category_id: Optional[int] = None,
        serial_number: Optional[str] = None,
        model_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        supplier: Optional[str] = None,
        purchase_date=None,
        purchase_price=None,
        warranty_expiry_date=None,
        location: Optional[str] = None,
        description: Optional[str] = None,
        condition: str = "good",
        asset_code: Optional[str] = None,
    ) -> Asset:
        if not name or not name.strip():
            raise ValidationError("Asset name is required.", "name")

        with get_db() as db:
            repo = AssetRepository(db)

            # Auto-generate code if not provided
            if not asset_code:
                asset_code = repo.generate_next_code()

            if repo.code_exists(asset_code):
                raise DuplicateEntryError("Asset", "asset_code", asset_code)

            asset = Asset(
                name=name.strip(),
                asset_code=asset_code,
                org_id=org_id,
                dept_id=dept_id,
                category_id=category_id,
                serial_number=serial_number,
                model_number=model_number,
                manufacturer=manufacturer,
                supplier=supplier,
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                warranty_expiry_date=warranty_expiry_date,
                location=location,
                description=description,
                condition=condition,
                status=AssetStatus.AVAILABLE.value,
            )
            repo.create(asset)
            self._audit(db, AuditAction.CREATE, "assets", asset.id,
                        description=f"Asset '{name}' ({asset_code}) registered.")
            logger.info(f"Asset '{name}' created with code {asset_code}.")
            return asset

    def update(self, asset_id: int, data: dict) -> Asset:
        with get_db() as db:
            repo = AssetRepository(db)
            asset = repo.get_by_id(asset_id)
            if not asset:
                raise NotFoundError("Asset", str(asset_id))
            if "asset_code" in data and data["asset_code"] != asset.asset_code:
                if repo.code_exists(data["asset_code"], exclude_id=asset_id):
                    raise DuplicateEntryError("Asset", "asset_code", data["asset_code"])
            old = asset.to_dict()
            repo.update(asset, data)
            self._audit(db, AuditAction.UPDATE, "assets", asset_id,
                        old_values=old, description=f"Asset '{asset.name}' updated.")
            return asset

    def delete(self, asset_id: int) -> None:
        with get_db() as db:
            repo = AssetRepository(db)
            asset = repo.get_by_id(asset_id)
            if not asset:
                raise NotFoundError("Asset", str(asset_id))
            if asset.status == AssetStatus.ISSUED.value:
                raise ValidationError(
                    f"Cannot delete asset '{asset.name}' — it is currently issued.", "status"
                )
            repo.delete(asset)
            self._audit(db, AuditAction.DELETE, "assets", asset_id,
                        description=f"Asset '{asset.name}' soft-deleted.")

    def count_by_status(self, org_id: Optional[int] = None) -> dict:
        with get_db() as db:
            repo = AssetRepository(db)
            return repo.count_by_status(org_id)

    def get_available_assets(self, org_id: Optional[int] = None) -> list[Asset]:
        with get_db() as db:
            repo = AssetRepository(db)
            return repo.get_by_status(AssetStatus.AVAILABLE.value, org_id)

    @staticmethod
    def _audit(db, action, module: str, record_id: int,
               old_values: Optional[dict] = None, description: str = "") -> None:
        import json
        log = AuditLog(
            user_id=current_session.user_id,
            action=action.value if hasattr(action, "value") else action,
            module=module,
            table_name=module,
            record_id=record_id,
            old_values_json=json.dumps(old_values) if old_values else None,
            description=description,
        )
        db.add(log)
        db.flush()
