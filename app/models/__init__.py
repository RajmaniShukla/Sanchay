"""
Sanchay Models Package
========================
Import all models here so SQLAlchemy's metadata is populated
when init_db() is called from database.py.
"""

from app.models.base import BaseModel, TimestampMixin, SoftDeleteMixin
from app.models.user import User, Role
from app.models.organization import Organization, Department
from app.models.person import Person
from app.models.asset import Asset, AssetCategory
from app.models.transaction import AssetIssue, AssetReturn
from app.models.audit import AuditLog, AppSetting

__all__ = [
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "User",
    "Role",
    "Organization",
    "Department",
    "Person",
    "Asset",
    "AssetCategory",
    "AssetIssue",
    "AssetReturn",
    "AuditLog",
    "AppSetting",
]
