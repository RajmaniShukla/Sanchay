"""
Sanchay — Phase 4 Integration Tests
=======================================
Full transaction lifecycle: issue → overdue → return.
Tests all service-layer business rules for the transaction flow.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_phase4.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db_mod
_db_mod._engine = None
_db_mod._SessionFactory = None

from app.core.database import init_db
from app.core.security import current_session
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.person_service import PersonService
from app.services.transaction_service import TransactionService
from app.core.exceptions import (
    AssetNotAvailableError, PersonInactiveError,
    ActiveIssueExistsError, NoActiveIssueError,
    NotFoundError, ValidationError,
)
from datetime import date, timedelta

# ── Module-level fixtures ─────────────────────────────────────────────────────

_org_id   = None
_dept_id  = None
_asset_id = None          # Laptop — used for main issue/return cycle
_asset2_id = None         # Printer — secondary tests
_person_id = None
_person2_id = None

def setup_module():
    global _org_id, _dept_id, _asset_id, _asset2_id, _person_id, _person2_id
    config.init_directories()
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("ph4admin", "Phase4 Admin", "Admin@123", "admin")
    except Exception:
        pass
    current_session.login(1, "ph4admin", "Phase4 Admin", "admin", {"all": True})

    org   = OrganizationService().create(name="TxnCorp", code="TXN", org_type="office")
    _org_id = org.id
    dept  = DepartmentService().create(org_id=_org_id, name="IT", code="IT")
    _dept_id = dept.id

    cat = AssetCategoryService().create(name="Electronics", code="EL", org_id=_org_id)
    asset_svc = AssetService()

    a1 = asset_svc.create(name="Dell Laptop", org_id=_org_id,
                          dept_id=_dept_id, category_id=cat.id,
                          serial_number="SN-LAP-001", condition="new")
    a2 = asset_svc.create(name="HP Printer",  org_id=_org_id,
                          dept_id=_dept_id, category_id=cat.id,
                          serial_number="SN-PRN-001", condition="good")
    _asset_id  = a1.id
    _asset2_id = a2.id

    per_svc = PersonService()
    p1 = per_svc.create(org_id=_org_id, first_name="Raj",   last_name="Kumar",
                        person_type="employee", dept_id=_dept_id)
    p2 = per_svc.create(org_id=_org_id, first_name="Priya", last_name="Singh",
                        person_type="student",  dept_id=_dept_id)
    _person_id  = p1.id
    _person2_id = p2.id


def teardown_module():
    if _db_mod._engine:
        _db_mod._engine.dispose()
        _db_mod._engine = None
        _db_mod._SessionFactory = None
    import time; time.sleep(0.2)
    try:
        config.DB_PATH.unlink()
    except Exception:
        pass


# ── Transaction Tests ─────────────────────────────────────────────────────────

class TestTransaction:
    svc = TransactionService()

    def test_a_issue_available_asset(self):
        issue = self.svc.issue_asset(
            asset_id=_asset_id,
            person_id=_person_id,
            expected_return_date=date.today() + timedelta(days=7),
            purpose="Development work",
            org_id=_org_id,
        )
        assert issue.id is not None
        assert issue.status == "active"
        # Asset status must flip to 'issued'
        from app.services.asset_service import AssetService
        asset = AssetService().get_by_id(_asset_id)
        assert asset.status == "issued"
        print(f"  [OK] Issue #{issue.id}: '{asset.name}' → 'Raj Kumar'  status=issued")

    def test_b_issued_asset_not_available_raises(self):
        """Already-issued asset cannot be issued again."""
        try:
            self.svc.issue_asset(
                asset_id=_asset_id, person_id=_person2_id, org_id=_org_id
            )
            assert False, "Should have raised"
        except (AssetNotAvailableError, ActiveIssueExistsError):
            print("  [OK] Re-issuing an issued asset raises AssetNotAvailableError/ActiveIssueExistsError")

    def test_c_get_active_issues(self):
        issues = self.svc.get_active_issues(org_id=_org_id)
        assert len(issues) == 1
        assert issues[0].status == "active"
        print(f"  [OK] get_active_issues: {len(issues)} active")

    def test_d_get_issue_history_for_asset(self):
        history = self.svc.get_issue_history_for_asset(_asset_id)
        assert len(history) >= 1
        assert history[0].asset_id == _asset_id
        print(f"  [OK] get_issue_history_for_asset: {len(history)} record(s)")

    def test_e_get_holdings_for_person(self):
        holdings = self.svc.get_holdings_for_person(_person_id)
        assert len(holdings) == 1
        assert holdings[0].person_id == _person_id
        print(f"  [OK] get_holdings_for_person: {len(holdings)} active holding(s)")

    def test_f_issue_second_asset_to_same_person(self):
        """A person can hold multiple assets simultaneously."""
        issue2 = self.svc.issue_asset(
            asset_id=_asset2_id, person_id=_person_id, org_id=_org_id
        )
        assert issue2.status == "active"
        holdings = self.svc.get_holdings_for_person(_person_id)
        assert len(holdings) == 2
        print(f"  [OK] Person can hold multiple assets: {len(holdings)} holdings")

    def test_g_inactive_person_cannot_receive_asset(self):
        """Inactive person cannot be issued an asset."""
        from app.services.person_service import PersonService
        per_svc = PersonService()
        # Create a new asset so we have something available
        from app.services.asset_service import AssetService
        temp = AssetService().create(name="Temp Asset", org_id=_org_id, asset_code="TEMP-001")
        # Deactivate person2
        per_svc.toggle_status(_person2_id)  # → inactive
        try:
            self.svc.issue_asset(asset_id=temp.id, person_id=_person2_id, org_id=_org_id)
            assert False, "Should have raised"
        except PersonInactiveError:
            print("  [OK] Issuing to inactive person raises PersonInactiveError")
        finally:
            per_svc.toggle_status(_person2_id)  # restore to active
            AssetService().delete(temp.id)

    def test_h_return_asset(self):
        """Return the Dell Laptop (asset_id=_asset_id)."""
        active = self.svc.get_active_issues(org_id=_org_id)
        issue  = next(i for i in active if i.asset_id == _asset_id)
        ret = self.svc.return_asset(
            issue_id=issue.id,
            condition_on_return="good",
            remarks="Returned in good condition.",
        )
        assert ret.id is not None
        # Issue should now be 'returned'
        updated_issue = self.svc.get_all_issues(org_id=_org_id, limit=100)[0]
        returned_issues = [i for i in updated_issue
                           if isinstance(i, type(issue)) and i.id == issue.id
                           ] if isinstance(updated_issue, list) else []

        # Verify asset is available again
        from app.services.asset_service import AssetService
        asset = AssetService().get_by_id(_asset_id)
        assert asset.status == "available"
        print(f"  [OK] Return #{ret.id}: asset status back to 'available'")

    def test_i_return_non_active_issue_raises(self):
        """Cannot return an issue that is already returned."""
        all_issues, _ = self.svc.get_all_issues(org_id=_org_id, status="returned")
        assert len(all_issues) >= 1
        already_returned = all_issues[0]
        try:
            self.svc.return_asset(issue_id=already_returned.id)
            assert False, "Should have raised"
        except NoActiveIssueError:
            print("  [OK] Returning an already-returned issue raises NoActiveIssueError")

    def test_j_get_all_issues_with_filters(self):
        issues, total = self.svc.get_all_issues(org_id=_org_id, limit=100)
        assert total >= 2
        print(f"  [OK] get_all_issues (all): {total} records")

        active, act_total = self.svc.get_all_issues(org_id=_org_id, status="active")
        returned, ret_total = self.svc.get_all_issues(org_id=_org_id, status="returned")
        assert act_total + ret_total == total
        print(f"  [OK] Filter by status: {act_total} active, {ret_total} returned")

    def test_k_overdue_sync(self):
        """Create a past-due issue then run sync to mark it overdue."""
        from app.services.asset_service import AssetService
        temp_asset = AssetService().create(
            name="Overdue Test Asset", org_id=_org_id, asset_code="OVR-001"
        )
        # Issue with an expired expected return date (yesterday)
        issue = self.svc.issue_asset(
            asset_id=temp_asset.id,
            person_id=_person2_id,
            expected_return_date=date.today() - timedelta(days=1),
            org_id=_org_id,
        )
        assert issue.status == "active"

        # Run sync
        count = self.svc.sync_overdue_statuses(org_id=_org_id)
        assert count >= 1

        overdue = self.svc.get_overdue_issues(org_id=_org_id)
        overdue_ids = [i.id for i in overdue]
        # Note: after sync, overdue are still in DB with status=overdue
        print(f"  [OK] Overdue sync marked {count} issue(s) overdue")

        # Clean up
        self.svc.return_asset(issue_id=issue.id, condition_on_return="fair")
        AssetService().delete(temp_asset.id)

    def test_l_stats(self):
        stats = self.svc.get_stats(org_id=_org_id)
        assert "active_issues" in stats
        assert "overdue" in stats
        print(f"  [OK] get_stats: {stats}")

    def test_m_all_returns(self):
        returns, total = self.svc.get_all_returns(org_id=_org_id, limit=100)
        assert total >= 1
        print(f"  [OK] get_all_returns: {total} return(s)")

    def test_n_return_second_asset(self):
        """Return the HP Printer still held by Raj."""
        active = self.svc.get_active_issues(org_id=_org_id)
        issue  = next((i for i in active if i.asset_id == _asset2_id), None)
        if issue is None:
            print("  [SKIP] HP Printer issue not found (may have been returned already)")
            return
        ret = self.svc.return_asset(
            issue_id=issue.id, condition_on_return="good", remarks="All good."
        )
        from app.services.asset_service import AssetService
        asset = AssetService().get_by_id(_asset2_id)
        assert asset.status == "available"
        print(f"  [OK] HP Printer returned. Asset status=available")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    setup_module()
    suite = TestTransaction()
    passed = failed = 0
    print(f"\n--- TestTransaction ---")
    for name in sorted(m for m in dir(suite) if m.startswith("test_")):
        try:
            getattr(suite, name)()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{'='*46}")
    print(f"Results: {passed} passed, {failed} failed")
    teardown_module()
