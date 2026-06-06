"""
Sanchay — Organization & Department Models
============================================
Multi-organization hierarchy with nested departments.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.person import Person
    from app.models.asset import Asset, AssetCategory
    from app.models.user import User


class Organization(BaseModel):
    """
    Top-level organizational entity.
    All assets, people, and departments belong to an org.
    """
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    org_type: Mapped[str] = mapped_column(String(50), nullable=False, default="office")
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    pincode: Mapped[Optional[str]] = mapped_column(String(10))
    country: Mapped[str] = mapped_column(String(100), default="India")
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(150))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    logo_path: Mapped[Optional[str]] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    departments: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="organization",
        foreign_keys="Department.org_id",
    )
    persons: Mapped[list["Person"]] = relationship("Person", back_populates="organization")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="organization")
    asset_categories: Mapped[list["AssetCategory"]] = relationship(
        "AssetCategory", back_populates="organization"
    )

    @property
    def full_address(self) -> str:
        parts = [self.address, self.city, self.state, self.pincode, self.country]
        return ", ".join(p for p in parts if p)

    def __repr__(self) -> str:
        return f"<Organization code='{self.code}' name='{self.name}'>"


class Department(BaseModel):
    """
    Department within an organization.
    Supports nested hierarchy via parent_dept_id.
    """
    __tablename__ = "departments"

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    parent_dept_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    head_person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("persons.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="departments",
        foreign_keys=[org_id],
    )
    parent: Mapped[Optional["Department"]] = relationship(
        "Department",
        remote_side="Department.id",
        back_populates="children",
        foreign_keys=[parent_dept_id],
    )
    children: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="parent",
        foreign_keys=[parent_dept_id],
    )
    head_person: Mapped[Optional["Person"]] = relationship(
        "Person",
        foreign_keys=[head_person_id],
    )
    persons: Mapped[list["Person"]] = relationship(
        "Person",
        back_populates="department",
        foreign_keys="Person.dept_id",
    )
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="department")

    @property
    def full_path(self) -> str:
        """Returns 'ParentDept > ChildDept' path."""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def __repr__(self) -> str:
        return f"<Department code='{self.code}' name='{self.name}'>"
