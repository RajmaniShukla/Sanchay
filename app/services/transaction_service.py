"""
Sanchay — Transaction Service
================================
Business logic for asset issue and return workflows.
This is the most critical service — enforces all inventory rules.
"""

from typing import Optional
from datetime import datetime, date
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session, require_authenticated, require_role
from app.core.exceptions import (
    AssetNotAvailableError, PersonInactiveError, ActiveIssueExistsError,
    NoActiveIssueError, NotFoundError, ValidationError,
)
from app.models.transaction import AssetIssue, AssetReturn
from app.models.audit import AuditLog
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.asset_repository import AssetRepository
from app.repositories.person_repository import PersonRepository
from app.constants import AssetStatus, IssueStatus, AuditAction


# ── Condition severity ordering (lower index = better condition) ───────────────

_CONDITION_ORDER = ["excellent", "good", "fair", "poor", "damaged"]


def _condition_rank(condition: Optional[str]) -> int:
    """Return severity rank (lower = better). Unknown conditions rank as 0."""
    if not condition:
        return 0
    return _CONDITION_ORDER.index(condition.lower()) if condition.lower() in _CONDITION_ORDER else 0


class TransactionService:
    """
    Manages asset issue and return lifecycle.
    
    Rules enforced:
    - Only 'available' assets can be issued
    - Only 'active' persons can receive assets
    - An asset can have only one active issue at a time
    - Return always references an active issue
    """

    def issue_asset(
        self,
        asset_id: int,
        person_id: int,
        expected_return_date: Optional[date] = None,
        purpose: Optional[str] = None,
        notes: Optional[str] = None,
        org_id: Optional[int] = None,
    ) -> AssetIssue:
        """
        Issue an asset to a person.
        
        Requires: authenticated session + operator role (or above).

        Raises:
            AuthenticationError / SessionExpiredError: Not logged in.
            PermissionDeniedError: Insufficient role.
            AssetNotAvailableError: Asset is not in 'available' state.
            PersonInactiveError: Person is inactive.
            ActiveIssueExistsError: Asset already has an active issue.
            ValidationError: Invalid asset_id, person_id, or expected_return_date.
        """
        require_authenticated()
        require_role("operator")

        # Defensive ID checks
        if asset_id is None or asset_id <= 0:
            raise ValidationError("Invalid asset ID.", "asset_id")
        if person_id is None or person_id <= 0:
            raise ValidationError("Invalid person ID.", "person_id")

        # Validate expected_return_date
        if expected_return_date is not None:
            today = date.today()
            if expected_return_date < today:
                logger.warning(
                    f"issue_asset: expected_return_date {expected_return_date} is in the past "
                    f"(today={today}) for asset_id={asset_id}. Proceeding with past date."
                )
        else:
            logger.debug(
                f"Issue for asset_id={asset_id}: no expected_return_date set (open-ended issue)."
            )

        with get_db() as db:
            asset_repo = AssetRepository(db)
            person_repo = PersonRepository(db)
            txn_repo = TransactionRepository(db)

            # ── Validate asset ─────────────────────────────────────────────────
            asset = asset_repo.get_by_id(asset_id)
            if not asset:
                raise NotFoundError("Asset", str(asset_id))
            if asset.status != AssetStatus.AVAILABLE.value:
                raise AssetNotAvailableError(asset.name, asset.status)

            # ── Check for ghost active issues (data integrity guard) ────────────
            existing = txn_repo.get_active_issue_for_asset(asset_id)
            if existing:
                raise ActiveIssueExistsError(asset.name)

            # ── Validate person ────────────────────────────────────────────────
            person = person_repo.get_by_id(person_id)
            if not person:
                raise NotFoundError("Person", str(person_id))
            if not person.is_active:
                raise PersonInactiveError(person.full_name)

            # ── Create issue record ────────────────────────────────────────────
            issue = AssetIssue(
                asset_id=asset_id,
                person_id=person_id,
                issued_by_user_id=current_session.user_id,
                issue_date=datetime.now(),
                expected_return_date=expected_return_date,
                purpose=purpose,
                notes=notes,
                status=IssueStatus.ACTIVE.value,
                org_id=org_id or current_session.org_id,
            )
            txn_repo.create_issue(issue)

            # ── Update asset status ────────────────────────────────────────────
            asset.status = AssetStatus.ISSUED.value
            db.flush()

            # ── Audit ──────────────────────────────────────────────────────────
            no_return_note = "" if expected_return_date else " (no return date set)"
            self._audit(
                db, AuditAction.ISSUE, "asset_issues", issue.id,
                description=(
                    f"Asset '{asset.name}' ({asset.asset_code}) issued to "
                    f"'{person.full_name}' ({person.display_code}){no_return_note}."
                ),
            )
            logger.info(
                f"Asset '{asset.name}' issued to '{person.full_name}' "
                f"by '{current_session.username}'."
            )
            return issue

    def return_asset(
        self,
        issue_id: int,
        condition_on_return: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> AssetReturn:
        """
        Record the return of an issued asset.
        Updates asset condition if returned condition is worse than current.
        
        Requires: authenticated session + operator role (or above).

        Raises:
            AuthenticationError / SessionExpiredError: Not logged in.
            PermissionDeniedError: Insufficient role.
            NotFoundError: Issue record not found.
            NoActiveIssueError: Issue is already resolved.
        """
        require_authenticated()
        require_role("operator")

        with get_db() as db:
            txn_repo = TransactionRepository(db)
            asset_repo = AssetRepository(db)

            # ── Validate issue ─────────────────────────────────────────────────
            issue = txn_repo.get_issue_by_id(issue_id)
            if not issue:
                raise NotFoundError("Issue Record", str(issue_id))
            if issue.status not in (IssueStatus.ACTIVE.value, IssueStatus.OVERDUE.value):
                raise NoActiveIssueError(issue.asset_name)

            # ── Warn if overdue (elevated log severity) ─────────────────────────────
            if issue.status == IssueStatus.OVERDUE.value:
                logger.warning(
                    f"Overdue asset being returned: issue #{issue_id}, "
                    f"asset='{issue.asset_name}', person='{issue.person_name}', "
                    f"returned_by='{current_session.username}'."
                )

            # ── Create return record ───────────────────────────────────────────
            asset_return = AssetReturn(
                issue_id=issue_id,
                asset_id=issue.asset_id,
                person_id=issue.person_id,
                returned_to_user_id=current_session.user_id,
                return_date=datetime.now(),
                condition_on_return=condition_on_return or "good",
                remarks=remarks,
                org_id=issue.org_id,
            )
            txn_repo.create_return(asset_return)

            # ── Update issue status ────────────────────────────────────────────
            issue.status = IssueStatus.RETURNED.value
            db.flush()

            # ── Update asset status + condition ───────────────────────────────
            asset = asset_repo.get_by_id(issue.asset_id)
            if asset:
                asset.status = AssetStatus.AVAILABLE.value
                # Only downgrade condition — never upgrade automatically
                if condition_on_return:
                    current_rank = _condition_rank(asset.condition)
                    return_rank  = _condition_rank(condition_on_return)
                    if return_rank > current_rank:
                        logger.debug(
                            f"Asset '{asset.name}' condition downgraded: "
                            f"'{asset.condition}' → '{condition_on_return}'"
                        )
                        asset.condition = condition_on_return
                db.flush()

            # ── Audit ──────────────────────────────────────────────────────────
            self._audit(
                db, AuditAction.RETURN, "asset_returns", asset_return.id,
                description=(
                    f"Asset '{issue.asset_name}' returned by "
                    f"'{issue.person_name}'. Condition: {condition_on_return or 'good'}."
                ),
            )
            logger.info(f"Asset returned for issue #{issue_id}.")
            return asset_return

    def get_issue_by_id(self, issue_id: int) -> Optional[AssetIssue]:
        """Return an issue record by ID, or None if not found."""
        logger.debug(f"Fetching issue by id={issue_id}")
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_issue_by_id(issue_id)

    def get_all_issues(self, **kwargs) -> tuple[list[AssetIssue], int]:
        """Return paginated issue records with optional filters."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_all_issues(**kwargs)

    def get_active_issues(self, org_id: Optional[int] = None) -> list[AssetIssue]:
        """Return all currently active issues for an organisation."""
        with get_db() as db:
            repo = TransactionRepository(db)
            results, _ = repo.get_all_issues(org_id=org_id, status=IssueStatus.ACTIVE.value)
            return results

    def get_overdue_issues(self, org_id: Optional[int] = None) -> list[AssetIssue]:
        """Return issues that are past their expected return date."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_overdue_issues(org_id)

    def get_issue_history_for_asset(self, asset_id: int) -> list[AssetIssue]:
        """Return complete issue history for a specific asset."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_issues_for_asset(asset_id)

    def get_holdings_for_person(self, person_id: int) -> list[AssetIssue]:
        """Return all assets currently held by a person."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_issues_for_person(person_id, status=IssueStatus.ACTIVE.value)

    def get_all_returns(self, **kwargs) -> tuple:
        """Return paginated return records with optional filters."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return repo.get_all_returns(**kwargs)

    def get_stats(self, org_id: Optional[int] = None) -> dict:
        """Return summary statistics for the dashboard."""
        with get_db() as db:
            repo = TransactionRepository(db)
            return {
                "active_issues": repo.count_active_issues(org_id),
                "overdue": repo.count_overdue(org_id),
            }

    def sync_overdue_statuses(self, org_id: Optional[int] = None) -> int:
        """
        Scan active issues and mark overdue ones.
        Call this on application start.
        Returns count of newly marked overdue issues.
        """
        with get_db() as db:
            repo = TransactionRepository(db)
            overdue = repo.get_overdue_issues(org_id)
            count = 0
            for issue in overdue:
                if issue.status == IssueStatus.ACTIVE.value:
                    issue.status = IssueStatus.OVERDUE.value
                    count += 1
            if count:
                db.flush()
            logger.info(f"Marked {count} issue(s) as overdue.")
            return count

    @staticmethod
    def _audit(db, action, module: str, record_id: int, description: str = "") -> None:
        """Write an audit log entry within the current DB session."""
        import json
        log = AuditLog(
            user_id=current_session.user_id,
            action=action.value if hasattr(action, "value") else action,
            module=module,
            table_name=module,
            record_id=record_id,
            description=description,
        )
        db.add(log)
        db.flush()
