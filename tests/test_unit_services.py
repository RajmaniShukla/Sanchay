"""
Sanchay — Phase 7 Unit Tests: All Services
=============================================
Isolated, per-method unit tests for every service.
Tests use letter-prefixed names to enforce execution order.
"""

import sys, os, shutil, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Override DB path BEFORE any app import ──────────────────────────────────
from app.config import config
config.DB_PATH = config.DATA_DIR / "test_unit.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db
_db._engine = None
_db._SessionFactory = None

from app.core.database import init_db
from app.core.security import current_session
from app.core.exceptions import (
    AuthenticationError, AccountInactiveError, ValidationError,
    DuplicateEntryError, NotFoundError, AssetNotAvailableError,
    PersonInactiveError, ActiveIssueExistsError, NoActiveIssueError,
    BackupError,
)
from app.services.auth_service import AuthService
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.person_service import PersonService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.transaction_service import TransactionService
from app.services.settings_service import SettingsService
from app.services.backup_service import BackupService
from app.constants import UserRole, PersonType, AssetStatus

BACKUP_DIR = config.DATA_DIR / "test_unit_backups"


def setup_module():
    config.init_directories()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    config.BACKUPS_DIR = BACKUP_DIR
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("utest_admin", "UTest Admin", "Admin@123", "admin")
    except Exception:
        pass

    current_session.login(1, "utest_admin", "UTest Admin", "admin", {"all": True})
    SettingsService().seed_defaults()


def teardown_module():
    if _db._engine:
        _db._engine.dispose()
        _db._engine = None
        _db._SessionFactory = None
    time.sleep(0.2)
    for p in [config.DB_PATH, BACKUP_DIR]:
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
# AuthService
# Tests use a-z prefixes to enforce execution order
# ════════════════════════════════════════════════════════════════════════════

class TestAuthService:
    svc = AuthService()

    def test_a_seed_roles_idempotent(self):
        self.svc.seed_default_roles()
        roles = self.svc.get_all_roles()
        names = [r.name for r in roles]
        for role in ("admin", "manager", "operator", "viewer"):
            assert role in names, f"Expected role '{role}' to exist"
        print(f"  [OK] seed_default_roles: {names}")

    def test_b_get_all_roles(self):
        roles = self.svc.get_all_roles()
        assert len(roles) >= 4
        print(f"  [OK] get_all_roles: {len(roles)} roles")

    def test_c_create_user_admin(self):
        u = self.svc.create_user("ut_admin2", "Admin Two", "Admin@123", "admin")
        assert u.id is not None
        assert u.role_name == "admin"
        print(f"  [OK] create_user admin: id={u.id}")

    def test_d_create_user_manager(self):
        u = self.svc.create_user("ut_manager", "Test Mgr", "Mgr@1234", "manager")
        assert u.role_name == "manager"
        print(f"  [OK] create_user manager: {u.username}")

    def test_e_create_user_operator(self):
        u = self.svc.create_user("ut_operator", "Test Opr", "Opr@1234", "operator")
        assert u.role_name == "operator"
        print(f"  [OK] create_user operator: {u.username}")

    def test_f_create_user_viewer(self):
        u = self.svc.create_user("ut_viewer", "Test Viewer", "View@1234", "viewer")
        assert u.role_name == "viewer"
        print(f"  [OK] create_user viewer: {u.username}")

    def test_g_create_user_duplicate_raises(self):
        try:
            self.svc.create_user("ut_manager", "Dup Mgr", "Dup@1234", "manager")
            assert False, "Should have raised DuplicateEntryError"
        except DuplicateEntryError as e:
            assert "ut_manager" in str(e)
            print("  [OK] duplicate username raises DuplicateEntryError")

    def test_h_create_user_invalid_role_raises(self):
        try:
            self.svc.create_user("ut_badrole", "Bad Role", "Bad@1234", "superuser")
            assert False, "Should raise ValidationError"
        except ValidationError:
            print("  [OK] invalid role raises ValidationError")

    def test_i_login_success(self):
        result = self.svc.login("ut_manager", "Mgr@1234")
        assert result["username"] == "ut_manager"
        assert result["role"] == "manager"
        current_session.login(1, "utest_admin", "UTest Admin", "admin", {"all": True})
        print("  [OK] login success")

    def test_j_login_wrong_password_raises(self):
        try:
            self.svc.login("ut_manager", "wrong_password")
            assert False
        except AuthenticationError:
            print("  [OK] wrong password raises AuthenticationError")

    def test_k_login_unknown_user_raises(self):
        try:
            self.svc.login("no_such_user_xyz", "whatever")
            assert False
        except AuthenticationError:
            print("  [OK] unknown user raises AuthenticationError")

    def test_l_change_password(self):
        users = self.svc.get_all_users()
        viewer = next(u for u in users if u.username == "ut_viewer")
        self.svc.change_password(viewer.id, "NewView@789")
        result = self.svc.login("ut_viewer", "NewView@789")
        assert result["username"] == "ut_viewer"
        current_session.login(1, "utest_admin", "UTest Admin", "admin", {"all": True})
        print("  [OK] change_password works")

    def test_m_change_password_not_found_raises(self):
        try:
            self.svc.change_password(99999, "Pass@123")
            assert False
        except NotFoundError:
            print("  [OK] change_password nonexistent user raises NotFoundError")

    def test_n_toggle_active_deactivate_reactivate(self):
        users = self.svc.get_all_users()
        opr = next(u for u in users if u.username == "ut_operator")
        state = self.svc.toggle_user_active(opr.id)
        assert state is False
        state2 = self.svc.toggle_user_active(opr.id)
        assert state2 is True
        print("  [OK] toggle_active: active->inactive->active")

    def test_o_toggle_active_deactivated_user_cannot_login(self):
        users = self.svc.get_all_users()
        viewer = next(u for u in users if u.username == "ut_viewer")
        self.svc.toggle_user_active(viewer.id)  # deactivate
        try:
            self.svc.login("ut_viewer", "NewView@789")
            assert False
        except AccountInactiveError:
            print("  [OK] deactivated user login raises AccountInactiveError")
        finally:
            self.svc.toggle_user_active(viewer.id)  # restore

    def test_p_get_all_users(self):
        users = self.svc.get_all_users()
        assert len(users) >= 1
        print(f"  [OK] get_all_users: {len(users)} users")


# ════════════════════════════════════════════════════════════════════════════
# AssetCategoryService
# ════════════════════════════════════════════════════════════════════════════

class TestAssetCategoryService:
    svc = AssetCategoryService()

    def test_a_create_valid(self):
        cat = self.svc.create("Laptops", "CATLAP")
        assert cat.id is not None
        assert cat.name == "Laptops"
        assert cat.code == "CATLAP"
        print(f"  [OK] create category: id={cat.id}")

    def test_b_create_empty_name_raises(self):
        try:
            self.svc.create("", "CATEMPTY")
            assert False
        except ValidationError:
            print("  [OK] empty name raises ValidationError")

    def test_c_create_empty_code_raises(self):
        try:
            self.svc.create("Monitors", "")
            assert False
        except ValidationError:
            print("  [OK] empty code raises ValidationError")

    def test_d_create_duplicate_code_raises(self):
        try:
            self.svc.create("Laptops Dup", "CATLAP")
            assert False
        except DuplicateEntryError:
            print("  [OK] duplicate code raises DuplicateEntryError")

    def test_e_create_with_subcategory(self):
        parent = self.svc.create("Electronics", "CATELEC")
        child = self.svc.create("Phones", "CATPHO", parent_category_id=parent.id)
        assert child.parent_category_id == parent.id
        print(f"  [OK] create subcategory: parent={parent.id} child={child.id}")

    def test_f_get_all(self):
        cats = self.svc.get_all()
        assert len(cats) >= 1
        print(f"  [OK] get_all: {len(cats)} categories")

    def test_g_get_root_categories(self):
        roots = self.svc.get_root_categories()
        for c in roots:
            assert c.parent_category_id is None
        print(f"  [OK] get_root_categories: {len(roots)} roots")

    def test_h_get_by_id(self):
        cats = self.svc.get_all()
        cat = self.svc.get_by_id(cats[0].id)
        assert cat is not None
        assert cat.id == cats[0].id
        print(f"  [OK] get_by_id: {cat.name}")

    def test_i_get_by_id_not_found_raises(self):
        try:
            self.svc.get_by_id(999999)
            assert False
        except NotFoundError:
            print("  [OK] get_by_id not found raises NotFoundError")

    def test_j_update_category(self):
        cats = self.svc.get_all()
        cat = cats[0]
        updated = self.svc.update(cat.id, {"name": "Updated Name"})
        assert updated.name == "Updated Name"
        print(f"  [OK] update category: {updated.name}")

    def test_k_delete_empty_category(self):
        cat = self.svc.create("ToDelete", "CATDEL")
        self.svc.delete(cat.id)
        try:
            self.svc.get_by_id(cat.id)
            assert False
        except NotFoundError:
            print("  [OK] delete empty category works")

    def test_l_delete_category_with_assets_raises(self):
        cat = self.svc.create("CantDelete", "CATNODEL")
        asset_svc = AssetService()
        asset_svc.create("Blocking Asset", category_id=cat.id)
        try:
            self.svc.delete(cat.id)
            assert False
        except ValidationError as e:
            assert "asset" in str(e).lower()
            print("  [OK] delete category with assets raises ValidationError")


# ════════════════════════════════════════════════════════════════════════════
# AssetService
# ════════════════════════════════════════════════════════════════════════════

class TestAssetService:
    svc = AssetService()

    def test_a_create_with_auto_code(self):
        asset = self.svc.create("Test Laptop")
        assert asset.id is not None
        assert asset.asset_code is not None
        assert asset.status == AssetStatus.AVAILABLE.value
        print(f"  [OK] create auto-code: {asset.asset_code}")

    def test_b_create_with_custom_code(self):
        asset = self.svc.create("Custom Asset", asset_code="CUST001")
        assert asset.asset_code == "CUST001"
        print(f"  [OK] create custom code: {asset.asset_code}")

    def test_c_create_duplicate_code_raises(self):
        try:
            self.svc.create("Dup Asset", asset_code="CUST001")
            assert False
        except DuplicateEntryError:
            print("  [OK] duplicate asset_code raises DuplicateEntryError")

    def test_d_create_missing_name_raises(self):
        try:
            self.svc.create("")
            assert False
        except ValidationError:
            print("  [OK] empty name raises ValidationError")

    def test_e_create_with_all_fields(self):
        from datetime import date
        cats = AssetCategoryService().get_all()
        cat_id = cats[0].id if cats else None
        asset = self.svc.create(
            name="Full Asset",
            category_id=cat_id,
            serial_number="SN001",
            purchase_price=50000.00,
            purchase_date=date(2024, 1, 15),
            location="Server Room",
            condition="new",
        )
        assert asset.purchase_price is not None
        print(f"  [OK] create with all fields: {asset.asset_code}")

    def test_f_get_by_id(self):
        assets = self.svc.get_all()
        asset = self.svc.get_by_id(assets[0].id)
        assert asset is not None
        print(f"  [OK] get_by_id: {asset.name}")

    def test_g_get_by_id_not_found_raises(self):
        try:
            self.svc.get_by_id(999999)
            assert False
        except NotFoundError:
            print("  [OK] get_by_id 999999 raises NotFoundError")

    def test_h_update_asset(self):
        assets = self.svc.get_all()
        asset = assets[0]
        updated = self.svc.update(asset.id, {"name": "Updated Asset Name", "location": "Room B"})
        assert updated.name == "Updated Asset Name"
        assert updated.location == "Room B"
        print(f"  [OK] update asset: {updated.name}")

    def test_i_delete_available_asset(self):
        asset = self.svc.create("TempAsset Delete", asset_code="TEMPDEL001")
        self.svc.delete(asset.id)
        try:
            self.svc.get_by_id(asset.id)
            assert False
        except NotFoundError:
            print("  [OK] delete available asset works")

    def test_j_count_by_status(self):
        counts = self.svc.count_by_status()
        assert isinstance(counts, dict)
        assert "available" in counts
        print(f"  [OK] count_by_status: {counts}")

    def test_k_get_available_assets(self):
        avail = self.svc.get_available_assets()
        for a in avail:
            assert a.status == AssetStatus.AVAILABLE.value
        print(f"  [OK] get_available_assets: {len(avail)} assets")

    def test_l_search_by_name(self):
        results, total = self.svc.search(query="Laptop")
        assert isinstance(results, list)
        print(f"  [OK] search by name: {total} results")

    def test_m_search_empty_returns_all(self):
        results, total = self.svc.search(query="")
        assert total >= 1
        print(f"  [OK] search empty: {total} total")

    def test_n_search_by_status(self):
        results, total = self.svc.search(query="", status="available")
        for r in results:
            assert r.status == "available"
        print(f"  [OK] search by status: {total}")


# ════════════════════════════════════════════════════════════════════════════
# PersonService
# ════════════════════════════════════════════════════════════════════════════

class TestPersonService:
    svc = PersonService()
    org_svc = OrganizationService()
    _org_id = None

    def _get_org_id(self):
        if TestPersonService._org_id is None:
            try:
                org = self.org_svc.create("PersonTest Org", "PTO001")
            except DuplicateEntryError:
                orgs = self.org_svc.get_all()
                org = next(o for o in orgs if o.code == "PTO001")
            TestPersonService._org_id = org.id
        return TestPersonService._org_id

    def test_a_create_employee(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "Alice", person_type="employee")
        assert p.id is not None
        assert p.person_type == "employee"
        assert p.person_id_code.startswith("EMP")
        print(f"  [OK] create employee: {p.person_id_code}")

    def test_b_create_student(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "Bob", person_type="student")
        assert p.person_id_code.startswith("STU")
        print(f"  [OK] create student: {p.person_id_code}")

    def test_c_create_contractor(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "Carol", person_type="contractor")
        assert p.person_id_code.startswith("CON")
        print(f"  [OK] create contractor: {p.person_id_code}")

    def test_d_create_candidate(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "Dave", person_type="candidate")
        assert p.person_id_code.startswith("CAN")
        print(f"  [OK] create candidate: {p.person_id_code}")

    def test_e_create_missing_first_name_raises(self):
        org_id = self._get_org_id()
        try:
            self.svc.create(org_id, "", person_type="employee")
            assert False
        except ValidationError:
            print("  [OK] missing first_name raises ValidationError")

    def test_f_create_invalid_person_type_raises(self):
        org_id = self._get_org_id()
        try:
            self.svc.create(org_id, "Eve", person_type="robot")
            assert False
        except ValidationError:
            print("  [OK] invalid person_type raises ValidationError")

    def test_g_auto_code_generation_unique(self):
        org_id = self._get_org_id()
        p1 = self.svc.create(org_id, "Gen1", person_type="employee")
        p2 = self.svc.create(org_id, "Gen2", person_type="employee")
        assert p1.person_id_code != p2.person_id_code
        print(f"  [OK] auto-codes unique: {p1.person_id_code}, {p2.person_id_code}")

    def test_h_get_by_id(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "FindMe")
        found = self.svc.get_by_id(p.id)
        assert found.id == p.id
        print(f"  [OK] get_by_id: {found.full_name}")

    def test_i_get_by_id_not_found_raises(self):
        try:
            self.svc.get_by_id(999999)
            assert False
        except NotFoundError:
            print("  [OK] get_by_id 999999 raises NotFoundError")

    def test_j_update_person(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "UpdateMe")
        updated = self.svc.update(p.id, {"first_name": "Updated", "designation": "Dev"})
        assert updated.first_name == "Updated"
        print(f"  [OK] update person: {updated.full_name}")

    def test_k_toggle_status(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "ToggleTest")
        new_status = self.svc.toggle_status(p.id)
        assert new_status == "inactive"
        restored = self.svc.toggle_status(p.id)
        assert restored == "active"
        print("  [OK] toggle_status: active->inactive->active")

    def test_l_delete_person(self):
        org_id = self._get_org_id()
        p = self.svc.create(org_id, "DeleteMe")
        self.svc.delete(p.id)
        try:
            self.svc.get_by_id(p.id)
            assert False
        except NotFoundError:
            print("  [OK] delete person works")

    def test_m_search_person(self):
        results, total = self.svc.search(query="Alice")
        assert isinstance(results, list)
        print(f"  [OK] search person: {total} results")

    def test_n_count_by_type(self):
        counts = self.svc.count_by_type()
        assert isinstance(counts, dict)
        print(f"  [OK] count_by_type: {counts}")


# ════════════════════════════════════════════════════════════════════════════
# OrganizationService
# Note: org codes must be [A-Z0-9]{2,10} — no dashes or underscores
# ════════════════════════════════════════════════════════════════════════════

class TestOrganizationService:
    svc = OrganizationService()

    def test_a_create_organization(self):
        org = self.svc.create("Test Corp", "TC001", org_type="office")
        assert org.id is not None
        assert org.code == "TC001"
        print(f"  [OK] create org: id={org.id}")

    def test_b_create_duplicate_code_raises(self):
        try:
            self.svc.create("Dup Corp", "TC001")
            assert False
        except DuplicateEntryError:
            print("  [OK] duplicate org code raises DuplicateEntryError")

    def test_c_create_empty_name_raises(self):
        try:
            self.svc.create("", "EMPTYORG")
            assert False
        except ValidationError:
            print("  [OK] empty org name raises ValidationError")

    def test_d_create_empty_code_raises(self):
        try:
            self.svc.create("Valid Name", "  ")
            assert False
        except ValidationError:
            print("  [OK] empty org code raises ValidationError")

    def test_e_get_all_orgs(self):
        orgs = self.svc.get_all()
        assert len(orgs) >= 1
        print(f"  [OK] get_all: {len(orgs)} orgs")

    def test_f_get_by_id(self):
        orgs = self.svc.get_all()
        org = self.svc.get_by_id(orgs[0].id)
        assert org is not None
        print(f"  [OK] get_by_id: {org.name}")

    def test_g_get_by_id_not_found_raises(self):
        try:
            self.svc.get_by_id(999999)
            assert False
        except NotFoundError:
            print("  [OK] get_by_id 999999 raises NotFoundError")

    def test_h_update_organization(self):
        orgs = self.svc.get_all()
        org = orgs[0]
        updated = self.svc.update(org.id, {"city": "Mumbai", "country": "India"})
        assert updated.city == "Mumbai"
        print(f"  [OK] update org: {updated.name}")

    def test_i_update_duplicate_code_raises(self):
        org2 = self.svc.create("Another Corp", "TC002")
        orgs = self.svc.get_all()
        org1 = next(o for o in orgs if o.code == "TC001")
        try:
            self.svc.update(org1.id, {"code": "TC002"})
            assert False
        except DuplicateEntryError:
            print("  [OK] update to duplicate code raises DuplicateEntryError")

    def test_j_delete_organization(self):
        org = self.svc.create("ToDelete Org", "TDORG")
        self.svc.delete(org.id)
        try:
            self.svc.get_by_id(org.id)
            assert False
        except NotFoundError:
            print("  [OK] delete org works")


# ════════════════════════════════════════════════════════════════════════════
# DepartmentService
# Note: dept codes support dashes/underscores: ^[A-Z0-9_\-]{2,20}$
# ════════════════════════════════════════════════════════════════════════════

class TestDepartmentService:
    svc = DepartmentService()
    org_svc = OrganizationService()
    _org_id = None

    def _get_org_id(self):
        if TestDepartmentService._org_id is None:
            try:
                org = self.org_svc.create("DeptTest Org", "DTORG01")
            except DuplicateEntryError:
                orgs = self.org_svc.get_all()
                org = next(o for o in orgs if o.code == "DTORG01")
            TestDepartmentService._org_id = org.id
        return TestDepartmentService._org_id

    def test_a_create_department(self):
        org_id = self._get_org_id()
        dept = self.svc.create(org_id, "IT Department", "IT")
        assert dept.id is not None
        assert dept.code == "IT"
        print(f"  [OK] create dept: id={dept.id}")

    def test_b_create_child_department(self):
        org_id = self._get_org_id()
        parent = self.svc.create(org_id, "Engineering", "ENG")
        child = self.svc.create(org_id, "Backend", "BKND", parent_dept_id=parent.id)
        assert child.parent_dept_id == parent.id
        print(f"  [OK] create child dept: parent={parent.id} child={child.id}")

    def test_c_create_duplicate_code_raises(self):
        org_id = self._get_org_id()
        try:
            self.svc.create(org_id, "IT Dup", "IT")
            assert False
        except DuplicateEntryError:
            print("  [OK] duplicate dept code raises DuplicateEntryError")

    def test_d_create_empty_name_raises(self):
        org_id = self._get_org_id()
        try:
            self.svc.create(org_id, "", "EMPTY")
            assert False
        except ValidationError:
            print("  [OK] empty dept name raises ValidationError")

    def test_e_get_by_org(self):
        org_id = self._get_org_id()
        depts = self.svc.get_by_org(org_id)
        assert len(depts) >= 1
        for d in depts:
            assert d.org_id == org_id
        print(f"  [OK] get_by_org: {len(depts)} depts")

    def test_f_get_by_id(self):
        org_id = self._get_org_id()
        depts = self.svc.get_by_org(org_id)
        dept = self.svc.get_by_id(depts[0].id)
        assert dept is not None
        print(f"  [OK] get_by_id: {dept.name}")

    def test_g_update_department(self):
        org_id = self._get_org_id()
        # Create a leaf to update
        leaf = self.svc.create(org_id, "UpdateDept", "UPDT")
        updated = self.svc.update(leaf.id, {"name": "Updated Dept Name"})
        assert updated.name == "Updated Dept Name"
        print(f"  [OK] update dept: {updated.name}")

    def test_h_delete_leaf_department(self):
        org_id = self._get_org_id()
        leaf = self.svc.create(org_id, "LeafDept", "LEAF")
        self.svc.delete(leaf.id)
        try:
            self.svc.get_by_id(leaf.id)
            assert False
        except NotFoundError:
            print("  [OK] delete leaf dept works")

    def test_i_delete_dept_with_children_raises(self):
        org_id = self._get_org_id()
        parent = self.svc.create(org_id, "ParentDept", "PAREN")
        child = self.svc.create(org_id, "ChildDept", "CHIL", parent_dept_id=parent.id)
        try:
            self.svc.delete(parent.id)
            assert False
        except ValidationError as e:
            assert "sub-department" in str(e).lower() or "children" in str(e).lower() or "sub" in str(e).lower()
            print("  [OK] delete dept with children raises ValidationError")
        # cleanup
        self.svc.delete(child.id)
        self.svc.delete(parent.id)


# ════════════════════════════════════════════════════════════════════════════
# TransactionService
# ════════════════════════════════════════════════════════════════════════════

class TestTransactionService:
    svc = TransactionService()
    asset_svc = AssetService()
    person_svc = PersonService()
    org_svc = OrganizationService()
    _org_id = None
    _person_id = None

    def _setup_org_and_person(self):
        if TestTransactionService._org_id is None:
            try:
                org = self.org_svc.create("TxnTest Org", "TXNORG")
            except DuplicateEntryError:
                orgs = self.org_svc.get_all()
                org = next(o for o in orgs if o.code == "TXNORG")
            TestTransactionService._org_id = org.id
        if TestTransactionService._person_id is None:
            try:
                p = self.person_svc.create(
                    TestTransactionService._org_id, "TxnPerson",
                    person_type="employee",
                    person_id_code="TXNP001"
                )
            except DuplicateEntryError:
                # Person already exists — look them up
                from app.core.database import get_db
                from app.models.person import Person
                with get_db() as db:
                    p = db.query(Person).filter(
                        Person.person_id_code == "TXNP001"
                    ).first()
            TestTransactionService._person_id = p.id
        return TestTransactionService._org_id, TestTransactionService._person_id

    def test_a_issue_available_asset(self):
        org_id, person_id = self._setup_org_and_person()
        asset = self.asset_svc.create("TxnAsset1", asset_code="TXNA001")
        issue = self.svc.issue_asset(asset.id, person_id, org_id=org_id)
        assert issue.id is not None
        assert issue.status == "active"
        updated = self.asset_svc.get_by_id(asset.id)
        assert updated.status == AssetStatus.ISSUED.value
        print(f"  [OK] issue_asset: issue#{issue.id}")

    def test_b_return_asset(self):
        org_id, person_id = self._setup_org_and_person()
        asset = self.asset_svc.create("TxnAsset2", asset_code="TXNA002")
        issue = self.svc.issue_asset(asset.id, person_id, org_id=org_id)
        ret = self.svc.return_asset(issue.id, condition_on_return="good")
        assert ret.id is not None
        updated = self.asset_svc.get_by_id(asset.id)
        assert updated.status == AssetStatus.AVAILABLE.value
        print(f"  [OK] return_asset: return#{ret.id}")

    def test_c_double_issue_raises(self):
        org_id, person_id = self._setup_org_and_person()
        asset = self.asset_svc.create("TxnAsset3", asset_code="TXNA003")
        self.svc.issue_asset(asset.id, person_id, org_id=org_id)
        try:
            self.svc.issue_asset(asset.id, person_id, org_id=org_id)
            assert False
        except AssetNotAvailableError:
            print("  [OK] double-issue raises AssetNotAvailableError")

    def test_d_issue_nonexistent_asset_raises(self):
        _, person_id = self._setup_org_and_person()
        try:
            self.svc.issue_asset(999999, person_id)
            assert False
        except NotFoundError:
            print("  [OK] issue nonexistent asset raises NotFoundError")

    def test_e_issue_nonexistent_person_raises(self):
        asset = self.asset_svc.create("TxnAsset4", asset_code="TXNA004")
        try:
            self.svc.issue_asset(asset.id, 999999)
            assert False
        except NotFoundError:
            print("  [OK] issue to nonexistent person raises NotFoundError")

    def test_f_issue_to_inactive_person_raises(self):
        org_id, _ = self._setup_org_and_person()
        inactive_p = self.person_svc.create(org_id, "InactivePerson",
                                             person_id_code="TXNINACT01")
        self.person_svc.toggle_status(inactive_p.id)  # -> inactive
        asset = self.asset_svc.create("TxnAsset5", asset_code="TXNA005")
        try:
            self.svc.issue_asset(asset.id, inactive_p.id)
            assert False
        except PersonInactiveError:
            print("  [OK] issue to inactive person raises PersonInactiveError")
        self.person_svc.toggle_status(inactive_p.id)  # restore

    def test_g_return_nonexistent_issue_raises(self):
        try:
            self.svc.return_asset(999999)
            assert False
        except NotFoundError:
            print("  [OK] return nonexistent issue raises NotFoundError")

    def test_h_return_already_returned_raises(self):
        org_id, person_id = self._setup_org_and_person()
        asset = self.asset_svc.create("TxnAsset6", asset_code="TXNA006")
        issue = self.svc.issue_asset(asset.id, person_id, org_id=org_id)
        self.svc.return_asset(issue.id)
        try:
            self.svc.return_asset(issue.id)
            assert False
        except NoActiveIssueError:
            print("  [OK] return already-returned raises NoActiveIssueError")

    def test_i_get_stats(self):
        stats = self.svc.get_stats()
        assert "active_issues" in stats
        assert "overdue" in stats
        print(f"  [OK] get_stats: {stats}")

    def test_j_get_all_issues(self):
        issues, total = self.svc.get_all_issues()
        assert isinstance(issues, list)
        print(f"  [OK] get_all_issues: {total} total")

    def test_k_get_all_returns(self):
        returns, total = self.svc.get_all_returns()
        assert isinstance(returns, list)
        print(f"  [OK] get_all_returns: {total} total")

    def test_l_sync_overdue_statuses(self):
        count = self.svc.sync_overdue_statuses()
        assert isinstance(count, int)
        print(f"  [OK] sync_overdue_statuses: {count} marked")

    def test_m_toggle_status_blocked_when_issued(self):
        org_id, _ = self._setup_org_and_person()
        person = self.person_svc.create(org_id, "BlockedPerson",
                                        person_id_code="TXNBLK001")
        asset = self.asset_svc.create("BlockAsset", asset_code="BLKA001")
        self.svc.issue_asset(asset.id, person.id, org_id=org_id)
        try:
            self.person_svc.toggle_status(person.id)
            assert False
        except ValidationError:
            print("  [OK] toggle_status blocked when asset issued")
        # cleanup: return asset first
        issues, _ = self.svc.get_all_issues()
        active = next((i for i in issues if i.person_id == person.id and i.status == "active"), None)
        if active:
            self.svc.return_asset(active.id)
        self.person_svc.toggle_status(person.id)

    def test_n_delete_asset_blocked_when_issued(self):
        org_id, person_id = self._setup_org_and_person()
        asset = self.asset_svc.create("DelBlockAsset", asset_code="TXNDEL001")
        self.svc.issue_asset(asset.id, person_id, org_id=org_id)
        try:
            self.asset_svc.delete(asset.id)
            assert False
        except ValidationError:
            print("  [OK] delete issued asset raises ValidationError")


# ════════════════════════════════════════════════════════════════════════════
# SettingsService
# ════════════════════════════════════════════════════════════════════════════

class TestSettingsService:
    svc = SettingsService()

    def test_a_seed_defaults_idempotent(self):
        self.svc.seed_defaults()
        self.svc.seed_defaults()  # second call should be safe
        val = self.svc.get("app_name")
        assert val == "Sanchay"
        print("  [OK] seed_defaults idempotent")

    def test_b_get_existing_key(self):
        val = self.svc.get("theme", "light")
        assert val in ("light", "dark")
        print(f"  [OK] get theme='{val}'")

    def test_c_get_missing_key_returns_default(self):
        val = self.svc.get("no_such_key_xyz", "MY_DEFAULT")
        assert val == "MY_DEFAULT"
        print("  [OK] get missing key returns default")

    def test_d_set_and_get_round_trip(self):
        self.svc.set("asset_code_prefix", "UNITTEST")
        val = self.svc.get("asset_code_prefix")
        assert val == "UNITTEST"
        self.svc.set("asset_code_prefix", "AST")  # restore
        print("  [OK] set->get round trip")

    def test_e_set_many(self):
        self.svc.set_many({"theme": "dark", "default_page_size": "100"})
        assert self.svc.get("theme") == "dark"
        assert self.svc.get("default_page_size") == "100"
        self.svc.set_many({"theme": "light", "default_page_size": "50"})
        print("  [OK] set_many batch update")

    def test_f_get_bool_true(self):
        self.svc.set("auto_backup", "true")
        assert self.svc.get_bool("auto_backup") is True
        print("  [OK] get_bool true")

    def test_g_get_bool_false(self):
        self.svc.set("auto_backup", "false")
        assert self.svc.get_bool("auto_backup") is False
        print("  [OK] get_bool false")

    def test_h_set_bool(self):
        self.svc.set_bool("auto_backup", True)
        assert self.svc.get("auto_backup") == "true"
        self.svc.set_bool("auto_backup", False)
        print("  [OK] set_bool works")

    def test_i_get_int(self):
        self.svc.set("auto_backup_days", "7")
        val = self.svc.get_int("auto_backup_days")
        assert val == 7
        print(f"  [OK] get_int={val}")

    def test_j_get_int_fallback_on_invalid(self):
        self.svc.set("auto_backup_days", "notanumber")
        val = self.svc.get_int("auto_backup_days", default=3)
        assert val == 3
        self.svc.set("auto_backup_days", "1")
        print("  [OK] get_int fallback on invalid string")

    def test_k_get_all_includes_all_defaults(self):
        all_s = self.svc.get_all()
        for key in ("app_name", "asset_code_prefix", "auto_backup", "theme"):
            assert key in all_s
        print(f"  [OK] get_all: {len(all_s)} settings")

    def test_l_named_property_app_name(self):
        assert self.svc.app_name == "Sanchay"
        print("  [OK] named property app_name")

    def test_m_named_property_asset_code_prefix(self):
        val = self.svc.asset_code_prefix
        assert isinstance(val, str) and len(val) > 0
        print(f"  [OK] asset_code_prefix='{val}'")

    def test_n_named_property_theme(self):
        assert self.svc.theme in ("light", "dark")
        print("  [OK] theme property")

    def test_o_named_property_backup_location(self):
        loc = self.svc.backup_location
        assert isinstance(loc, str)
        print(f"  [OK] backup_location='{loc}'")


# ════════════════════════════════════════════════════════════════════════════
# BackupService
# ════════════════════════════════════════════════════════════════════════════

class TestBackupService:
    svc = BackupService()

    def test_a_create_backup(self):
        path = self.svc.create_backup(BACKUP_DIR)
        assert path.exists()
        assert path.suffix == ".db"
        assert path.stat().st_size > 0
        print(f"  [OK] create_backup: {path.name}")

    def test_b_list_backups(self):
        backups = self.svc.list_backups()
        assert len(backups) >= 1
        bk = backups[0]
        for key in ("name", "path", "size_kb", "created_at"):
            assert key in bk
        print(f"  [OK] list_backups: {len(backups)}")

    def test_c_create_multiple_backups(self):
        for _ in range(3):
            self.svc.create_backup(BACKUP_DIR)
            time.sleep(0.02)
        backups = self.svc.list_backups()
        assert len(backups) >= 4
        print(f"  [OK] create multiple backups: {len(backups)}")

    def test_d_delete_backup(self):
        path = self.svc.create_backup(BACKUP_DIR)
        assert path.exists()
        self.svc.delete_backup(path)
        assert not path.exists()
        print("  [OK] delete_backup works")

    def test_e_cleanup_old_backups(self):
        # Create several
        for _ in range(3):
            self.svc.create_backup(BACKUP_DIR)
            time.sleep(0.02)
        deleted = self.svc.cleanup_old_backups(keep=2)
        remaining = self.svc.list_backups()
        assert len(remaining) <= 2
        print(f"  [OK] cleanup_old_backups: kept {len(remaining)}, deleted {deleted}")

    def test_f_backup_no_db_raises(self):
        import tempfile
        from pathlib import Path
        fake_config_path = config.DB_PATH
        config.DB_PATH = Path(tempfile.gettempdir()) / "nonexistent_sanchay.db"
        try:
            self.svc.create_backup(BACKUP_DIR)
            assert False, "Should have raised BackupError"
        except BackupError as e:
            assert "No database found" in str(e)
            print("  [OK] backup with no DB raises BackupError")
        finally:
            config.DB_PATH = fake_config_path


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    setup_module()
    passed = failed = 0
    suites = [
        TestAuthService,
        TestAssetCategoryService,
        TestAssetService,
        TestPersonService,
        TestOrganizationService,
        TestDepartmentService,
        TestTransactionService,
        TestSettingsService,
        TestBackupService,
    ]
    for Suite in suites:
        print(f"\n{'-'*56}")
        print(f"  {Suite.__name__}")
        print(f"{'-'*56}")
        obj = Suite()
        for name in sorted(m for m in dir(obj) if m.startswith("test_")):
            try:
                getattr(obj, name)()
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")
                traceback.print_exc()
                failed += 1
    print(f"\n{'='*56}")
    print(f"Results: {passed} passed, {failed} failed")
    teardown_module()
