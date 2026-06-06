"""
Sanchay — Asset Transaction Models
=====================================
Issue and Return records form the complete asset lifecycle audit trail.
Every change in asset custody is recorded here permanently.
"""

from typing import Optional, TYPE_CHECKING
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.person import Person
    from app.models.user import User
    from app.models.organization import Organization


class AssetIssue(Base, TimestampMixin):
    """
    Records an asset being issued (lent) to a person.
    
    A new record is created every time an asset is issued.
    The status field tracks the lifecycle of this particular issue event.
    """
    __tablename__ = "asset_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"), nullable=False, index=True
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id"), nullable=False, index=True
    )
    issued_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), index=True
    )

    # Timing
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
    expected_return_date: Mapped[Optional[date]] = mapped_column(Date)

    # Context
    purpose: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )  # active / returned / overdue

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="issues")
    person: Mapped["Person"] = relationship(
        "Person", back_populates="issues", foreign_keys=[person_id]
    )
    issued_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[issued_by_user_id]
    )
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    returns: Mapped[list["AssetReturn"]] = relationship(
        "AssetReturn", back_populates="issue"
    )

    @property
    def is_overdue(self) -> bool:
        if not self.expected_return_date:
            return False
        from datetime import date as dt
        return self.status == "active" and self.expected_return_date < dt.today()

    @property
    def asset_name(self) -> str:
        return self.asset.name if self.asset else "—"

    @property
    def person_name(self) -> str:
        return self.person.full_name if self.person else "—"

    def __repr__(self) -> str:
        return f"<AssetIssue id={self.id} asset='{self.asset_name}' status='{self.status}'>"


class AssetReturn(Base, TimestampMixin):
    """
    Records an asset being returned by a person.
    
    Linked to the original AssetIssue record.
    Immutable — returns are never edited, only appended.
    """
    __tablename__ = "asset_returns"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    org_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    issue_id: Mapped[int] = mapped_column(
        ForeignKey("asset_issues.id"), nullable=False, index=True
    )
    asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id"), index=True
    )
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("persons.id"), index=True
    )
    returned_to_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id")
    )

    # Timing
    return_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    # Condition
    condition_on_return: Mapped[Optional[str]] = mapped_column(String(20))
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    issue: Mapped["AssetIssue"] = relationship("AssetIssue", back_populates="returns")
    asset: Mapped[Optional["Asset"]] = relationship("Asset")
    person: Mapped[Optional["Person"]] = relationship("Person")
    returned_to: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[returned_to_user_id]
    )

    def __repr__(self) -> str:
        return f"<AssetReturn id={self.id} issue_id={self.issue_id}>"
