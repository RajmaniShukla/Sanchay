"""
Sanchay — Transaction Repository
===================================
Data access for AssetIssue and AssetReturn records.
"""

from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.transaction import AssetIssue, AssetReturn
from app.models.asset import Asset
from app.models.person import Person


class TransactionRepository:
    """Data access for asset issue and return records."""

    def __init__(self, db: Session):
        self.db = db

    # ── Issues ────────────────────────────────────────────────────────────────

    def create_issue(self, issue: AssetIssue) -> AssetIssue:
        self.db.add(issue)
        self.db.flush()
        self.db.refresh(issue)
        return issue

    def get_issue_by_id(self, issue_id: int) -> Optional[AssetIssue]:
        return self.db.query(AssetIssue).filter(AssetIssue.id == issue_id).first()

    def get_active_issue_for_asset(self, asset_id: int) -> Optional[AssetIssue]:
        """Returns the active (unresolved) issue for an asset, if any."""
        return (
            self.db.query(AssetIssue)
            .filter(
                AssetIssue.asset_id == asset_id,
                AssetIssue.status == "active",
            )
            .first()
        )

    def get_issues_for_person(
        self, person_id: int, status: Optional[str] = None
    ) -> list[AssetIssue]:
        q = self.db.query(AssetIssue).filter(AssetIssue.person_id == person_id)
        if status:
            q = q.filter(AssetIssue.status == status)
        return q.order_by(AssetIssue.issue_date.desc()).all()

    def get_issues_for_asset(self, asset_id: int) -> list[AssetIssue]:
        return (
            self.db.query(AssetIssue)
            .filter(AssetIssue.asset_id == asset_id)
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
        q = self.db.query(AssetIssue)
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
        """Returns active issues where expected_return_date < today."""
        q = self.db.query(AssetIssue).filter(
            AssetIssue.status == "active",
            AssetIssue.expected_return_date < date.today(),
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.order_by(AssetIssue.expected_return_date).all()

    def update_issue_status(self, issue_id: int, status: str) -> None:
        issue = self.get_issue_by_id(issue_id)
        if issue:
            issue.status = status
            self.db.flush()

    # ── Returns ───────────────────────────────────────────────────────────────

    def create_return(self, asset_return: AssetReturn) -> AssetReturn:
        self.db.add(asset_return)
        self.db.flush()
        self.db.refresh(asset_return)
        return asset_return

    def get_return_by_id(self, return_id: int) -> Optional[AssetReturn]:
        return self.db.query(AssetReturn).filter(AssetReturn.id == return_id).first()

    def get_returns_for_issue(self, issue_id: int) -> list[AssetReturn]:
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
        q = self.db.query(AssetReturn)
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
        q = self.db.query(func.count(AssetIssue.id)).filter(
            AssetIssue.status == "active"
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.scalar() or 0

    def count_overdue(self, org_id: Optional[int] = None) -> int:
        q = self.db.query(func.count(AssetIssue.id)).filter(
            AssetIssue.status == "active",
            AssetIssue.expected_return_date < date.today(),
        )
        if org_id:
            q = q.filter(AssetIssue.org_id == org_id)
        return q.scalar() or 0
