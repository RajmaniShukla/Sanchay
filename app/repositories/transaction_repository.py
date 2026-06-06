"""
Sanchay — Transaction Repository
===================================
Data access for AssetIssue and AssetReturn records.
"""

from typing import Optional
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.transaction import AssetIssue, AssetReturn
from app.models.asset import Asset
from app.models.person import Person


class TransactionRepository:
    """Data access for asset issue and return records."""

    def __init__(self, db: Session):
        """Initialise with an open SQLAlchemy session."""
        self.db = db

    # ── Issues ────────────────────────────────────────────────────────────────

    def create_issue(self, issue: AssetIssue) -> AssetIssue:
        """Persist a new issue record and return it with its generated id."""
        self.db.add(issue)
        self.db.flush()
        self.db.refresh(issue)
        return issue

    def get_issue_by_id(self, issue_id: int) -> Optional[AssetIssue]:
        """Return an issue by primary key with all relationships eagerly loaded."""
        return (
            self.db.query(AssetIssue)
            .options(
                joinedload(AssetIssue.asset),
                joinedload(AssetIssue.person),
                joinedload(AssetIssue.issued_by),
                joinedload(AssetIssue.returns),
            )
            .filter(AssetIssue.id == issue_id)
            .first()
        )

    def get_active_issue_for_asset(self, asset_id: int) -> Optional[AssetIssue]:
        """Return the active (unresolved) issue for an asset, if any."""
        return (
            self.db.query(AssetIssue)
            .filter(
                AssetIssue.asset_id == asset_id,
                AssetIssue.status == "active",
            )
            .first()
        )

    def _with_joins(self, q):
        """Apply eager-loads for issue queries so relationships are safe outside session."""
        return q.options(
            joinedload(AssetIssue.asset),
            joinedload(AssetIssue.person),
            joinedload(AssetIssue.issued_by),
            joinedload(AssetIssue.returns),
        )

    def get_issues_for_person(
        self, person_id: int, status: Optional[str] = None
    ) -> list[AssetIssue]:
        """Return all issue records for a person, optionally filtered by status."""
        q = self._with_joins(
            self.db.query(AssetIssue).filter(AssetIssue.person_id == person_id)
        )
        if status:
            q = q.filter(AssetIssue.status == status)
        return q.order_by(AssetIssue.issue_date.desc()).all()

    def get_active_issues_count_for_person(self, person_id: int) -> int:
        """Return the count of currently active issues held by a person.
        
        Returns 0 immediately for invalid person_id values (None, 0, negative)
        without hitting the database.
        """
        # Defensive: reject invalid person IDs
        if person_id is None:
            return 0
        try:
            person_id = int(person_id)
        except (TypeError, ValueError):
            return 0
        if person_id <= 0:
            return 0

        return (
            self.db.query(func.count(AssetIssue.id))
            .filter(
                AssetIssue.person_id == person_id,
                AssetIssue.status == "active",
            )
            .scalar() or 0
        )

    def get_issues_for_asset(self, asset_id: int) -> list[AssetIssue]:
        """Return all issue records for an asset, most recent first."""
        return (
            self._with_joins(
                self.db.query(AssetIssue)
                .filter(AssetIssue.asset_id == asset_id)
            )
            .order_by(AssetIssue.issue_date.desc())
            .all()
        )

    def get_all_issues(
        self,
        org_id: Optional[int] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[AssetIssue], int]:
        """Return paginated issue records with optional filters. Returns (results, total).
        
        Defensive: if both from_date and to_date are provided but are in the
        wrong order, they are silently swapped so the query still works.
        """
        # Defensive: swap dates if from_date > to_date
        if from_date is not None and to_date is not None and from_date > to_date:
            from_date, to_date = to_date, from_date

        q = self._with_joins(self.db.query(AssetIssue))
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        if status:
            q = q.filter(AssetIssue.status == status)
        if from_date:
            q = q.filter(AssetIssue.issue_date >= from_date)
        if to_date:
            q = q.filter(AssetIssue.issue_date <= to_date)
        total = q.count()
        results = q.order_by(AssetIssue.issue_date.desc()).offset(offset).limit(limit).all()
        return results, total

    def get_overdue_issues(self, org_id: Optional[int] = None) -> list[AssetIssue]:
        """Return active issues where expected_return_date is before today.
        
        Both conditions are explicitly checked in the query:
          - status == "active"
          - expected_return_date < today
        This prevents partially-processed records from appearing as overdue.
        """
        today = date.today()
        q = self._with_joins(
            self.db.query(AssetIssue).filter(
                AssetIssue.status == "active",
                AssetIssue.expected_return_date != None,  # noqa: E711
                AssetIssue.expected_return_date < today,
            )
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.order_by(AssetIssue.expected_return_date).all()

    def update_issue_status(self, issue_id: int, status: str) -> None:
        """Update the status of an issue record."""
        issue = self.get_issue_by_id(issue_id)
        if issue:
            issue.status = status
            self.db.flush()

    # ── Returns ───────────────────────────────────────────────────────────────

    def create_return(self, asset_return: AssetReturn) -> AssetReturn:
        """Persist a new return record and return it with its generated id."""
        self.db.add(asset_return)
        self.db.flush()
        self.db.refresh(asset_return)
        return asset_return

    def get_return_by_id(self, return_id: int) -> Optional[AssetReturn]:
        """Return a return record by primary key."""
        return (
            self.db.query(AssetReturn)
            .options(
                joinedload(AssetReturn.asset),
                joinedload(AssetReturn.person),
                joinedload(AssetReturn.returned_to),
            )
            .filter(AssetReturn.id == return_id)
            .first()
        )

    def get_returns_for_issue(self, issue_id: int) -> list[AssetReturn]:
        """Return all return records for a specific issue."""
        return (
            self.db.query(AssetReturn)
            .filter(AssetReturn.issue_id == issue_id)
            .order_by(AssetReturn.return_date.desc())
            .all()
        )

    def get_all_returns(
        self,
        org_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[AssetReturn], int]:
        """
        Return paginated return records with optional filters.
        
        Eagerly loads asset, person, and returned_to relationships.
        Returns (results, total).
        
        Defensive: if both from_date and to_date are provided but are in the
        wrong order, they are silently swapped so the query still works.
        """
        # Defensive: swap dates if from_date > to_date
        if from_date is not None and to_date is not None and from_date > to_date:
            from_date, to_date = to_date, from_date

        q = (
            self.db.query(AssetReturn)
            .options(
                joinedload(AssetReturn.asset),
                joinedload(AssetReturn.person),
                joinedload(AssetReturn.returned_to),
            )
        )
        if org_id:
            q = q.filter(AssetReturn.org_id == org_id)
        if from_date:
            q = q.filter(AssetReturn.return_date >= from_date)
        if to_date:
            q = q.filter(AssetReturn.return_date <= to_date)
        total = q.count()
        results = q.order_by(AssetReturn.return_date.desc()).offset(offset).limit(limit).all()
        return results, total

    # ── Statistics ────────────────────────────────────────────────────────────

    def count_active_issues(self, org_id: Optional[int] = None) -> int:
        """Return the count of currently active issues."""
        q = self.db.query(func.count(AssetIssue.id)).filter(
            AssetIssue.status == "active"
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.scalar() or 0

    def count_overdue(self, org_id: Optional[int] = None) -> int:
        """Return the count of active issues that are past their expected return date."""
        q = self.db.query(func.count(AssetIssue.id)).filter(
            AssetIssue.status == "active",
            AssetIssue.expected_return_date < date.today(),
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.scalar() or 0
