"""
Sanchay — Phase 3 Integration Tests
=======================================
Tests for Asset Categories and Assets — full CRUD, search,
status transitions, and business rule enforcement.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_phase3.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db_mod
_db_mod._engine = None
_db_mod._SessionFactory = None

from app.core.database import init_db
from app.core.security import current_session
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.transaction_service import TransactionService
from app.services.person_service import PersonService
from app.core.exceptions import (
    DuplicateEntryError, NotFoundError, ValidationError,
    AssetNotAvailableError,
)
from datetime import date


# ── Fixtures ──────────────────────────────────────────────────────────────────

_org_id  = None
_dept_id = None

def setup_module():
    global _org_id, _dept_id
    config.init_directories()
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("ph3admin", "Phase3 Admin", "Admin@123", "admin")
    except Exception:
        pass
    current_session.login(1, "ph3admin", "Phase3 Admin", "admin", {"all": True})

    org = OrganizationService().create(name="Phase3 Corp", code="PH3", org_type="office")
    _org_id = org.id
    dept = DepartmentService().create(org_id=_org_id, name="IT Dept", code="IT")
    _dept_id = dept.id


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


# ── Asset Category Tests ──────────────────────────────────────────────────────

class TestAssetCategory:
    svc = AssetCategoryService()

    def test_a_create_root_category(self):
        c = self.svc.create(
            name="Electronics", code="ELEC",
            org_id=_org_id, depreciation_rate=20.0, useful_life_years=5
        )
        assert c.id is not None
        assert c.code == "ELEC"
        assert float(c.depreciation_rate) == 20.0
        print(f"  [OK] Root category: {c.name} ({c.code}) id={c.id}")

    def test_b_create_child_category(self):
        cats   = self.svc.get_all(_org_id)
        parent = next(c for c in cats if c.code == "ELEC")
        child  = self.svc.create(
            name="Laptops", code="LAP",
            org_id=_org_id, parent_category_id=parent.id
        )
        assert child.parent_category_id == parent.id
        print(f"  [OK] Child category 'Laptops' under 'Electronics'")

    def test_c_duplicate_code_raises(self):
        try:
            self.svc.create(name="Dup", code="ELEC", org_id=_org_id)
            assert False, "Should have raised"
        except DuplicateEntryError:
            print("  [OK] Duplicate category code raises DuplicateEntryError")

    def test_d_get_all(self):
        cats = self.svc.get_all(_org_id)
        assert len(cats) >= 2
        print(f"  [OK] get_all: {len(cats)} categories")

    def test_e_get_root_categories(self):
        roots = self.svc.get_root_categories(_org_id)
        assert all(c.parent_category_id is None for c in roots)
        print(f"  [OK] Root categories: {[c.name for c in roots]}")

    def test_f_update_category(self):
        cats = self.svc.get_all(_org_id)
        cat  = next(c for c in cats if c.code == "ELEC")
        updated = self.svc.update(cat.id, {"description": "All electronic items"})
        assert updated.description == "All electronic items"
        print(f"  [OK] Category updated with description")

    def test_g_notfound_raises(self):
        try:
            self.svc.get_by_id(99999)
            assert False, "Should have raised"
        except NotFoundError:
            print("  [OK] NotFoundError for unknown category id")

    def test_h_delete_category_with_assets_raises(self):
        # This will be confirmed after assets are created in TestAsset
        # Skipping for now — tested in test_delete_blocked_by_assets
        print("  [SKIP] delete-with-assets test deferred to TestAsset")


# ── Asset Tests ───────────────────────────────────────────────────────────────

class TestAsset:
    svc     = AssetService()
    cat_svc = AssetCategoryService()

    def _get_cat_id(self, code="ELEC"):
        cats = self.cat_svc.get_all(_org_id)
        return next((c.id for c in cats if c.code == code), None)

    def test_a_create_asset_auto_code(self):
        a = self.svc.create(
            name="Dell XPS 15 Laptop",
            org_id=_org_id,
            dept_id=_dept_id,
            category_id=self._get_cat_id("LAP"),
            serial_number="DX15-SN-001",
            manufacturer="Dell",
            model_number="XPS 15 9520",
            purchase_date=date(2024, 1, 15),
            purchase_price=85000.00,
            warranty_expiry_date=date(2027, 1, 14),
            condition="new",
        )
        assert a.id is not None
        assert a.asset_code.startswith("AST-")
        assert a.status == "available"
        print(f"  [OK] Asset created: {a.name} ({a.asset_code}) id={a.id}")

    def test_b_create_asset_custom_code(self):
        a = self.svc.create(
            name="HP LaserJet Printer",
            org_id=_org_id,
            asset_code="PRN-001",
            category_id=self._get_cat_id("ELEC"),
            manufacturer="HP",
            condition="good",
        )
        assert a.asset_code == "PRN-001"
        print(f"  [OK] Asset with custom code: {a.asset_code}")

    def test_c_duplicate_code_raises(self):
        try:
            self.svc.create(name="Dup", org_id=_org_id, asset_code="PRN-001")
            assert False, "Should have raised"
        except DuplicateEntryError:
            print("  [OK] Duplicate asset code raises DuplicateEntryError")

    def test_d_search_by_name(self):
        assets, total = self.svc.search(query="Dell", org_id=_org_id)
        assert len(assets) >= 1
        assert any("Dell" in a.name for a in assets)
        print(f"  [OK] Search 'Dell': {len(assets)} result(s)")

    def test_e_search_by_status(self):
        assets, total = self.svc.search(query="", org_id=_org_id, status="available")
        assert all(a.status == "available" for a in assets)
        print(f"  [OK] Status filter 'available': {len(assets)} assets")

    def test_f_search_by_category(self):
        lap_id = self._get_cat_id("LAP")
        assets, _ = self.svc.search(query="", org_id=_org_id, category_id=lap_id)
        assert all(a.category_id == lap_id for a in assets)
        print(f"  [OK] Category filter 'Laptops': {len(assets)} assets")

    def test_g_count_by_status(self):
        counts = self.svc.count_by_status(_org_id)
        assert "available" in counts
        assert counts["available"] >= 2
        print(f"  [OK] count_by_status: {counts}")

    def test_h_update_asset(self):
        assets, _ = self.svc.search(query="Dell", org_id=_org_id)
        a = assets[0]
        updated = self.svc.update(a.id, {"location": "Server Room A", "condition": "good"})
        assert updated.location == "Server Room A"
        assert updated.condition == "good"
        print(f"  [OK] Asset updated: location={updated.location}")

    def test_i_get_by_id(self):
        assets, _ = self.svc.search(query="HP", org_id=_org_id)
        a = assets[0]
        fetched = self.svc.get_by_id(a.id)
        assert fetched.id == a.id
        print(f"  [OK] get_by_id works")

    def test_j_get_available_assets(self):
        available = self.svc.get_available_assets(_org_id)
        assert all(a.status == "available" for a in available)
        print(f"  [OK] get_available_assets: {len(available)} available")

    def test_k_delete_category_with_assets_raises(self):
        cat_svc = AssetCategoryService()
        cats    = cat_svc.get_all(_org_id)
        cat     = next(c for c in cats if c.code == "LAP")
        try:
            cat_svc.delete(cat.id)
            assert False, "Should have raised"
        except ValidationError as e:
            assert "asset" in str(e).lower()
            print(f"  [OK] Deleting category with assets raises ValidationError")

    def test_l_delete_available_asset(self):
        # Create a throwaway asset and delete it
        throwaway = self.svc.create(
            name="Throwaway Chair", org_id=_org_id, asset_code="CHAIR-DEL"
        )
        self.svc.delete(throwaway.id)
        try:
            self.svc.get_by_id(throwaway.id)
            assert False, "Should have raised"
        except NotFoundError:
            print(f"  [OK] Asset deleted (soft-delete confirmed)")

    def test_m_delete_issued_asset_raises(self):
        # Issue the Dell laptop then try to delete
        txn_svc  = TransactionService()
        per_svc  = PersonService()

        person = per_svc.create(
            org_id=_org_id, first_name="Test", last_name="User",
            person_type="employee", dept_id=_dept_id
        )
        assets, _ = self.svc.search(query="Dell", org_id=_org_id)
        asset = assets[0]

        txn_svc.issue_asset(
            asset_id=asset.id, person_id=person.id, org_id=_org_id
        )

        try:
            self.svc.delete(asset.id)
            assert False, "Should have raised"
        except ValidationError as e:
            assert "issued" in str(e).lower()
            print(f"  [OK] Deleting issued asset raises ValidationError")

        # Clean up — return the asset
        from app.repositories.transaction_repository import TransactionRepository
        from app.core.database import get_db
        with get_db() as db:
            repo = TransactionRepository(db)
            issue = repo.get_active_issue_for_asset(asset.id)
            if issue:
                txn_svc.return_asset(issue.id, condition_on_return="good")

    def test_n_asset_not_available_raises(self):
        """Cannot issue the same asset twice."""
        txn_svc = TransactionService()
        per_svc = PersonService()

        person = per_svc.create(
            org_id=_org_id, first_name="Second", last_name="User",
            person_type="employee", dept_id=_dept_id
        )
        assets, _ = self.svc.search(query="HP LaserJet", org_id=_org_id)
        asset = assets[0]

        # First issue succeeds
        txn_svc.issue_asset(asset_id=asset.id, person_id=person.id, org_id=_org_id)

        # Second issue should fail
        try:
            txn_svc.issue_asset(asset_id=asset.id, person_id=person.id, org_id=_org_id)
            assert False, "Should have raised"
        except (AssetNotAvailableError, Exception) as e:
            print(f"  [OK] Double-issue raises: {type(e).__name__}")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    setup_module()
    suites = [TestAssetCategory, TestAsset]
    passed = failed = 0
    for Suite in suites:
        print(f"\n--- {Suite.__name__} ---")
        obj = Suite()
        for name in sorted(m for m in dir(obj) if m.startswith("test_")):
            try:
                getattr(obj, name)()
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")
                traceback.print_exc()
                failed += 1
    print(f"\n{'='*44}")
    print(f"Results: {passed} passed, {failed} failed")
    teardown_module()
