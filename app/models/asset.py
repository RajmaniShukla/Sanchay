"""
Sanchay — Asset & Category Models
====================================
Core asset catalog with hierarchical categories.
"""

from typing import Optional, TYPE_CHECKING
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization, Department
    from app.models.transaction import AssetIssue


class AssetCategory(BaseModel):
    """
    Hierarchical asset category tree.
    Examples: Electronics > Laptops, Furniture > Chairs
    """
    __tablename__ = "asset_categories"

    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    parent_category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("asset_categories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    depreciation_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    useful_life_years: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="asset_categories"
    )
    parent: Mapped[Optional["AssetCategory"]] = relationship(
        "AssetCategory",
        remote_side="AssetCategory.id",
        back_populates="children",
        foreign_keys=[parent_category_id],
    )
    children: Mapped[list["AssetCategory"]] = relationship(
        "AssetCategory",
        back_populates="parent",
        foreign_keys=[parent_category_id],
    )
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="category")

    @property
    def full_path(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def __repr__(self) -> str:
        return f"<AssetCategory code='{self.code}' name='{self.name}'>"


class Asset(BaseModel):
    """
    Physical or digital asset tracked by the system.
    
    Lifecycle: Available → Issued → Returned → Maintenance → Disposed
    """
    __tablename__ = "assets"

    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    dept_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("asset_categories.id"), index=True
    )

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    model_number: Mapped[Optional[str]] = mapped_column(String(100))
    manufacturer: Mapped[Optional[str]] = mapped_column(String(150), index=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(150))

    # Financials
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    current_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    warranty_expiry_date: Mapped[Optional[date]] = mapped_column(Date)

    # Physical
    location: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available", index=True
    )
    condition: Mapped[str] = mapped_column(String(20), nullable=False, default="good")

    # Media
    photo_path: Mapped[Optional[str]] = mapped_column(String(500))
    qr_code_path: Mapped[Optional[str]] = mapped_column(String(500))  # Future use

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="assets"
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department", back_populates="assets"
    )
    category: Mapped[Optional["AssetCategory"]] = relationship(
        "AssetCategory", back_populates="assets"
    )
    issues: Mapped[list["AssetIssue"]] = relationship(
        "AssetIssue",
        back_populates="asset",
        foreign_keys="AssetIssue.asset_id",
    )

    @property
    def is_available(self) -> bool:
        return self.status == "available"

    @property
    def category_name(self) -> str:
        return self.category.name if self.category else "Uncategorized"

    @property
    def dept_name(self) -> str:
        return self.department.name if self.department else "—"

    @property
    def warranty_status(self) -> str:
        """Returns 'valid', 'expired', or 'none'."""
        from datetime import date as dt
        if not self.warranty_expiry_date:
            return "none"
        return "valid" if self.warranty_expiry_date >= dt.today() else "expired"

    def __repr__(self) -> str:
        return f"<Asset code='{self.asset_code}' name='{self.name}' status='{self.status}'>"
