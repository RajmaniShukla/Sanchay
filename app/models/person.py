"""
Sanchay — Person Model
========================
Unified model for employees, students, contractors, and candidates.
Uses person_type discriminator field to distinguish between them.
"""

from typing import Optional, TYPE_CHECKING
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.organization import Organization, Department
    from app.models.transaction import AssetIssue


class Person(BaseModel):
    """
    Represents any person in the organization who can hold assets.
    
    Types:
        - employee:   Full-time or part-time staff
        - student:    Students (colleges, training institutes)
        - contractor: Contractual/temporary workers
        - candidate:  Interview candidates (short-term)
    """
    __tablename__ = "persons"

    org_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    dept_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), index=True
    )

    # Type discriminator
    person_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="employee", index=True
    )

    # Identity
    person_id_code: Mapped[Optional[str]] = mapped_column(
        String(50), unique=True, index=True
    )  # e.g., EMP-001, STU-042
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Contact
    email: Mapped[Optional[str]] = mapped_column(String(150), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20))

    # Professional
    designation: Mapped[Optional[str]] = mapped_column(String(150))  # Job title / course

    # Address
    address: Mapped[Optional[str]] = mapped_column(Text)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))

    # Tenure
    date_of_joining: Mapped[Optional[date]] = mapped_column(Date)
    date_of_leaving: Mapped[Optional[date]] = mapped_column(Date)

    # ID Proof
    id_proof_type: Mapped[Optional[str]] = mapped_column(String(50))
    id_proof_number: Mapped[Optional[str]] = mapped_column(String(50))

    # Misc
    photo_path: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="persons"
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="persons",
        foreign_keys=[dept_id],
    )
    issues: Mapped[list["AssetIssue"]] = relationship(
        "AssetIssue",
        back_populates="person",
        foreign_keys="AssetIssue.person_id",
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p)

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def display_code(self) -> str:
        return self.person_id_code or f"#{self.id}"

    def __repr__(self) -> str:
        return f"<Person code='{self.display_code}' name='{self.full_name}' type='{self.person_type}'>"
