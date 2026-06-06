"""
Sanchay â€” Phase 7.5 Lifecycle Tests
======================================
Full end-to-end lifecycle scenarios covering the entire asset management
workflow: org setup, asset journey, person journey, org hierarchy,
backup/restore, reports, and settings persistence.
"""

import sys, os, shutil, time, traceback, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_lifecycle.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db
_db._engine = None
_db._SessionFactory = None

from app.core.database import init_db, drop_all_tables
from app.core.security import current_session
from app.core.exceptions import (
    ValidationError, DuplicateEntryError, NotFoundError,
    AssetNotAvailableError, PersonInactiveError,
)
from app.core.security import hash_password as _hash_pw
from app.services.auth_service import AuthService
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.person_service import PersonService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.transaction_service import TransactionService
from app.services.settings_service import SettingsService
from app.services.backup_service import BackupService
from app.services.report_service import ReportService
from app.constants import AssetStatus


def _bootstrap_admin(username: str, full_name: str, password: str) -> None:
    """Create the first admin user directly via ORM (bypasses require_authenticated)."""
    from app.core.database import get_db
    from app.models.user import User
    from app.repositories.user_repository import RoleRepository, UserRepository
    with get_db() as db:
        role_repo = RoleRepository(db)
        role = role_repo.get_by_name("admin")
        if not role:
            return
        repo = UserRepository(db)
        if not repo.username_exists(username):
            user = User(
                username=username,
                full_name=full_name,
                password_hash=_hash_pw(password),
                role_id=role.id,
                is_active=True,
            )
            db.add(user)
            db.flush()

# â”€â”€ Test runner helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_PASS = []
_FAIL = []

def run(name, fn):
    try:
        fn()
        _PASS.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        _FAIL.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()


# â”€â”€ Module setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def setup():
    config.init_directories()
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    _bootstrap_admin("lc_admin", "Lifecycle Admin", "Admin@123")
    auth.login("lc_admin", "Admin@123")
    SettingsService().seed_defaults()


def teardown():
    if _db._engine:
        _db._engine.dispose()
        _db._engine = None
        _db._SessionFactory = None
    time.sleep(0.2)
    try:
        if config.DB_PATH.exists():
            config.DB_PATH.unlink()
    except Exception:
        pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 1 â€” Full Asset Journey
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc1_org_id   = None
_lc1_dept_id  = None
_lc1_cat_id   = None
_lc1_p1_id    = None
_lc1_p2_id    = None
_lc1_asset_id = None

def lc1_setup():
    global _lc1_org_id, _lc1_dept_id, _lc1_cat_id, _lc1_p1_id, _lc1_p2_id, _lc1_asset_id

    org  = OrganizationService().create("LC1 Org",  "LC1ORG")
    dept = DepartmentService().create(org.id, "LC1 Dept", "LC1DEPT")
    cat  = AssetCategoryService().create("LC1 Category", "LC1CAT", org_id=org.id)

    _lc1_org_id  = org.id
    _lc1_dept_id = dept.id
    _lc1_cat_id  = cat.id

    p1 = PersonService().create(org.id, "Alice",  dept_id=dept.id, person_id_code="LC1P001")
    p2 = PersonService().create(org.id, "Bob",    dept_id=dept.id, person_id_code="LC1P002")
    _lc1_p1_id = p1.id
    _lc1_p2_id = p2.id

    asset = AssetService().create(
        name="Laptop LC1", org_id=org.id,
        dept_id=dept.id, category_id=cat.id,
    )
    _lc1_asset_id = asset.id

def lc1_01_asset_initial_status_available():
    """After creation, asset status is 'available'."""
    asset = AssetService().get_by_id(_lc1_asset_id)
    assert asset.status == AssetStatus.AVAILABLE.value, f"Expected available, got {asset.status}"

def lc1_02_issue_to_person1():
    """Issue asset to Alice; status becomes 'issued'."""
    txn = TransactionService()
    txn.issue_asset(_lc1_asset_id, _lc1_p1_id, org_id=_lc1_org_id)
    asset = AssetService().get_by_id(_lc1_asset_id)
    assert asset.status == AssetStatus.ISSUED.value

def lc1_03_person1_has_one_holding():
    """Alice holds exactly 1 asset."""
    holdings = TransactionService().get_holdings_for_person(_lc1_p1_id)
    assert len(holdings) == 1

def lc1_04_asset_not_in_available_list():
    """Issued asset does NOT appear in available list."""
    available = AssetService().get_available_assets(_lc1_org_id)
    ids = [a.id for a in available]
    assert _lc1_asset_id not in ids

def lc1_05_return_asset():
    """Return the asset; status reverts to 'available'."""
    txn = TransactionService()
    holdings = txn.get_holdings_for_person(_lc1_p1_id)
    assert holdings, "No active holding to return"
    txn.return_asset(holdings[0].id)
    asset = AssetService().get_by_id(_lc1_asset_id)
    assert asset.status == AssetStatus.AVAILABLE.value

def lc1_06_issue_again_to_person2():
    """Re-issue asset to Bob â€” asset can be issued multiple times."""
    TransactionService().issue_asset(_lc1_asset_id, _lc1_p2_id, org_id=_lc1_org_id)
    asset = AssetService().get_by_id(_lc1_asset_id)
    assert asset.status == AssetStatus.ISSUED.value

def lc1_07_return_again_history_has_two():
    """Return again; verify 2 return records exist for this asset."""
    txn = TransactionService()
    holdings = txn.get_holdings_for_person(_lc1_p2_id)
    assert holdings
    txn.return_asset(holdings[0].id)
    history = txn.get_issue_history_for_asset(_lc1_asset_id)
    returned = [h for h in history if h.status == "returned"]
    assert len(returned) == 2, f"Expected 2 returns, got {len(returned)}"

def lc1_08_set_maintenance_cannot_issue():
    """Set asset to maintenance; issuing raises AssetNotAvailableError."""
    AssetService().update(_lc1_asset_id, {"status": AssetStatus.MAINTENANCE.value})
    try:
        TransactionService().issue_asset(_lc1_asset_id, _lc1_p1_id, org_id=_lc1_org_id)
        raise AssertionError("Expected AssetNotAvailableError not raised")
    except AssetNotAvailableError:
        pass

def lc1_09_restore_available_can_issue():
    """Restore to available; asset can be issued again."""
    AssetService().update(_lc1_asset_id, {"status": AssetStatus.AVAILABLE.value})
    txn = TransactionService()
    txn.issue_asset(_lc1_asset_id, _lc1_p1_id, org_id=_lc1_org_id)
    asset = AssetService().get_by_id(_lc1_asset_id)
    assert asset.status == AssetStatus.ISSUED.value
    # Return it so we can delete
    holdings = txn.get_holdings_for_person(_lc1_p1_id)
    txn.return_asset(holdings[0].id)

def lc1_10_soft_delete_raises_notfound():
    """Soft-delete asset; get_by_id raises NotFoundError."""
    AssetService().delete(_lc1_asset_id)
    try:
        AssetService().get_by_id(_lc1_asset_id)
        raise AssertionError("Expected NotFoundError not raised")
    except NotFoundError:
        pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 2 â€” Person Journey
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc2_org_id    = None
_lc2_person_id = None
_lc2_asset_ids = []

def lc2_setup():
    global _lc2_org_id, _lc2_person_id, _lc2_asset_ids

    org  = OrganizationService().create("LC2 Org", "LC2ORG")
    dept = DepartmentService().create(org.id, "LC2 Dept", "LC2DEPT")
    _lc2_org_id = org.id

    person = PersonService().create(org.id, "Charlie", dept_id=dept.id, person_id_code="LC2P001")
    _lc2_person_id = person.id

    _lc2_asset_ids.clear()
    for i in range(3):
        a = AssetService().create(f"LC2 Asset {i+1}", org_id=org.id)
        _lc2_asset_ids.append(a.id)

def lc2_01_issue_three_assets():
    """Issue 3 different assets to the same person."""
    txn = TransactionService()
    for aid in _lc2_asset_ids:
        txn.issue_asset(aid, _lc2_person_id, org_id=_lc2_org_id)
    holdings = txn.get_holdings_for_person(_lc2_person_id)
    assert len(holdings) == 3, f"Expected 3, got {len(holdings)}"

def lc2_02_deactivate_person_with_active_issues_fails():
    """Deactivating a person with active issues raises ValidationError."""
    try:
        PersonService().toggle_status(_lc2_person_id)
        raise AssertionError("Expected ValidationError not raised")
    except ValidationError as e:
        assert "active" in e.message.lower() or "issue" in e.message.lower()

def lc2_03_return_all_assets():
    """Return all 3 assets."""
    txn = TransactionService()
    holdings = txn.get_holdings_for_person(_lc2_person_id)
    for h in holdings:
        txn.return_asset(h.id)
    holdings_after = txn.get_holdings_for_person(_lc2_person_id)
    assert len(holdings_after) == 0

def lc2_04_deactivate_person_succeeds():
    """Deactivate person after all assets returned â€” succeeds."""
    new_status = PersonService().toggle_status(_lc2_person_id)
    assert new_status == "inactive", f"Expected inactive, got {new_status}"

def lc2_05_issue_to_inactive_person_fails():
    """Issuing to an inactive person raises PersonInactiveError."""
    try:
        TransactionService().issue_asset(
            _lc2_asset_ids[0], _lc2_person_id, org_id=_lc2_org_id
        )
        raise AssertionError("Expected PersonInactiveError not raised")
    except PersonInactiveError:
        pass

def lc2_06_reactivate_person_can_receive():
    """Reactivate person; they can receive assets again."""
    PersonService().toggle_status(_lc2_person_id)
    person = PersonService().get_by_id(_lc2_person_id)
    assert person.status == "active"
    TransactionService().issue_asset(
        _lc2_asset_ids[0], _lc2_person_id, org_id=_lc2_org_id
    )
    holdings = TransactionService().get_holdings_for_person(_lc2_person_id)
    assert len(holdings) == 1

def lc2_07_delete_person_with_active_issues_fails():
    """Delete person fails when they have active issues."""
    try:
        PersonService().delete(_lc2_person_id)
        raise AssertionError("Expected ValidationError not raised")
    except ValidationError:
        pass

def lc2_08_return_then_delete_succeeds():
    """Return asset, then person can be deleted."""
    txn = TransactionService()
    holdings = txn.get_holdings_for_person(_lc2_person_id)
    for h in holdings:
        txn.return_asset(h.id)
    PersonService().delete(_lc2_person_id)
    try:
        PersonService().get_by_id(_lc2_person_id)
        raise AssertionError("Expected NotFoundError not raised")
    except NotFoundError:
        pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 3 â€” Organization Hierarchy
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc3_org_id    = None
_lc3_dept_ids  = []
_lc3_subdept_ids = []

def lc3_setup():
    global _lc3_org_id, _lc3_dept_ids, _lc3_subdept_ids

    org = OrganizationService().create("LC3 Org", "LC3ORG")
    _lc3_org_id = org.id
    dept_svc = DepartmentService()

    _lc3_dept_ids.clear()
    for i in range(3):
        d = dept_svc.create(org.id, f"LC3 Dept {i+1}", f"LC3D{i+1}")
        _lc3_dept_ids.append(d.id)

    _lc3_subdept_ids.clear()
    for i in range(2):
        sd = dept_svc.create(
            org.id, f"LC3 Sub-Dept {i+1}", f"LC3SD{i+1}",
            parent_dept_id=_lc3_dept_ids[0]
        )
        _lc3_subdept_ids.append(sd.id)

def lc3_01_top_level_depts_exist():
    """3 top-level departments created successfully."""
    depts = DepartmentService().get_by_org(_lc3_org_id)
    assert len(depts) >= 3

def lc3_02_subdepts_created():
    """2 sub-departments created under dept[0]."""
    assert len(_lc3_subdept_ids) == 2

def lc3_03_assign_persons_and_assets():
    """Can assign persons and assets to each dept level."""
    person_svc = PersonService()
    asset_svc  = AssetService()

    for i, dept_id in enumerate(_lc3_dept_ids[:2]):
        person_svc.create(_lc3_org_id, f"DeptPerson{i}", dept_id=dept_id,
                          person_id_code=f"LC3DP{i+1:03d}")
        asset_svc.create(f"Asset for dept{i}", org_id=_lc3_org_id, dept_id=dept_id)

    for i, sd_id in enumerate(_lc3_subdept_ids):
        person_svc.create(_lc3_org_id, f"SubPerson{i}", dept_id=sd_id,
                          person_id_code=f"LC3SP{i+1:03d}")
        asset_svc.create(f"Sub-Asset {i}", org_id=_lc3_org_id, dept_id=sd_id)

def lc3_04_dept_assets_counted_correctly():
    """Department asset query returns assets for that dept."""
    asset_svc = AssetService()
    all_assets = asset_svc.get_all(_lc3_org_id)
    dept0_assets = [a for a in all_assets if a.dept_id == _lc3_dept_ids[0]]
    # dept0 itself + sub-depts each got 1 asset
    assert len(dept0_assets) >= 1

def lc3_05_delete_parent_dept_with_children_fails():
    """Deleting a parent department with children raises ValidationError."""
    try:
        DepartmentService().delete(_lc3_dept_ids[0])
        raise AssertionError("Expected ValidationError not raised")
    except ValidationError as e:
        assert "sub-department" in e.message.lower() or "children" in e.message.lower() or "delete" in e.message.lower()

def lc3_06_delete_leaf_dept_succeeds():
    """Deleting a leaf department (no children) succeeds."""
    leaf_id = _lc3_dept_ids[2]  # dept 3 has no children
    DepartmentService().delete(leaf_id)
    # Verify it's gone
    try:
        DepartmentService().get_by_id(leaf_id)
        raise AssertionError("Expected NotFoundError not raised")
    except NotFoundError:
        pass

def lc3_07_dept_assets_report_row_count():
    """dept_assets report row count matches number of depts."""
    report_svc = ReportService()
    data = report_svc.generate("dept_assets", org_id=_lc3_org_id)
    depts = DepartmentService().get_by_org(_lc3_org_id)
    assert data.row_count == len(depts), (
        f"Report rows {data.row_count} != dept count {len(depts)}"
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 4 â€” Backup and Restore Cycle
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc4_org_id    = None
_lc4_backup_path = None
_original_person_count = 0

def lc4_setup():
    global _lc4_org_id, _lc4_backup_path, _original_person_count

    org  = OrganizationService().create("LC4 Org", "LC4ORG")
    dept = DepartmentService().create(org.id, "LC4 Dept", "LC4DEPT")
    _lc4_org_id = org.id

    person_svc = PersonService()
    asset_svc  = AssetService()

    persons = []
    for i in range(5):
        p = person_svc.create(org.id, f"LC4Person{i+1}", dept_id=dept.id,
                              person_id_code=f"LC4P{i+1:03d}")
        persons.append(p)

    assets = []
    for i in range(5):
        a = asset_svc.create(f"LC4 Asset {i+1}", org_id=org.id)
        assets.append(a)

    # Issue 2 assets
    txn = TransactionService()
    txn.issue_asset(assets[0].id, persons[0].id, org_id=org.id)
    txn.issue_asset(assets[1].id, persons[1].id, org_id=org.id)

    _original_person_count = len(persons)

def lc4_01_create_backup():
    """Backup creation succeeds and returns a path."""
    global _lc4_backup_path
    backup_svc = BackupService()
    _lc4_backup_path = backup_svc.create_backup()
    assert _lc4_backup_path.exists(), "Backup file does not exist"
    assert _lc4_backup_path.stat().st_size > 0, "Backup file is empty"

def lc4_02_add_persons_after_backup():
    """Add 3 more persons after backup."""
    org_id = _lc4_org_id
    depts = DepartmentService().get_by_org(org_id)
    dept_id = depts[0].id if depts else None
    ps = PersonService()
    for i in range(3):
        ps.create(org_id, f"PostBackup{i+1}", dept_id=dept_id,
                  person_id_code=f"LC4PB{i+1:03d}")
    persons_after = PersonService().get_all(org_id=org_id)
    assert len(persons_after) == _original_person_count + 3

def lc4_03_restore_backup():
    """Restore backup. Engine disposed BEFORE restore to release WAL locks."""
    # Dispose engine first so SQLite WAL file is not locked during file copy
    if _db._engine:
        _db._engine.dispose()
    _db._engine = None
    _db._SessionFactory = None
    import time; time.sleep(0.1)   # let OS release file handles
    backup_svc = BackupService()
    backup_svc.restore_backup(_lc4_backup_path)
def lc4_04_only_original_persons_exist():
    """After restore, only original 5 persons remain."""
    persons = PersonService().get_all(org_id=_lc4_org_id)
    assert len(persons) == _original_person_count, (
        f"Expected {_original_person_count}, got {len(persons)}"
    )

def lc4_05_db_connection_works_after_restore():
    """DB is accessible and functional after restore."""
    from app.services.asset_service import AssetService
    assets = AssetService().get_all(_lc4_org_id)
    assert isinstance(assets, list)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 5 â€” Report Completeness
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc5_org_id   = None
_lc5_org_name = "LC5 Org"

def lc5_setup():
    global _lc5_org_id

    org_svc   = OrganizationService()
    dept_svc  = DepartmentService()
    person_svc = PersonService()
    asset_svc  = AssetService()

    org = org_svc.create(_lc5_org_name, "LC5ORG")
    _lc5_org_id = org.id

    # 3 depts
    depts = []
    for i in range(3):
        d = dept_svc.create(org.id, f"LC5 Dept {i+1}", f"LC5D{i+1}")
        depts.append(d)

    # 10 persons
    persons = []
    for i in range(10):
        p = person_svc.create(org.id, f"LC5Person{i+1}", dept_id=depts[i % 3].id,
                              person_id_code=f"LC5P{i+1:03d}")
        persons.append(p)

    # 10 assets
    assets = []
    for i in range(10):
        a = asset_svc.create(f"LC5 Asset {i+1}", org_id=org.id, dept_id=depts[i % 3].id)
        assets.append(a)

    # Issue 4 assets
    txn = TransactionService()
    for i in range(4):
        txn.issue_asset(assets[i].id, persons[i].id, org_id=org.id)

    # Return 2 of them
    for i in range(2):
        holdings = txn.get_holdings_for_person(persons[i].id)
        for h in holdings:
            txn.return_asset(h.id)

def lc5_01_asset_inventory_report():
    """asset_inventory report: row count = 10 assets."""
    data = ReportService().generate("asset_inventory", org_id=_lc5_org_id)
    assert data.row_count == 10, f"Expected 10, got {data.row_count}"

def lc5_02_dept_assets_report():
    """dept_assets report: row count = 3 depts."""
    data = ReportService().generate("dept_assets", org_id=_lc5_org_id)
    assert data.row_count == 3, f"Expected 3, got {data.row_count}"

def lc5_03_issue_history_report():
    """issue_history report: row count = 4 issues."""
    data = ReportService().generate("issue_history", org_id=_lc5_org_id)
    assert data.row_count == 4, f"Expected 4, got {data.row_count}"

def lc5_04_return_history_report():
    """return_history report: row count = 2 returns."""
    data = ReportService().generate("return_history", org_id=_lc5_org_id)
    assert data.row_count == 2, f"Expected 2, got {data.row_count}"

def lc5_05_person_holdings_report():
    """person_holdings report: row count = 2 active holdings."""
    data = ReportService().generate("person_holdings", org_id=_lc5_org_id)
    assert data.row_count == 2, f"Expected 2, got {data.row_count}"

def lc5_06_export_pdf_exists_nonzero():
    """Export asset_inventory to PDF; file exists and size > 0."""
    export_dir = config.EXPORTS_DIR / "test_lifecycle"
    export_dir.mkdir(parents=True, exist_ok=True)
    data = ReportService().generate("asset_inventory", org_id=_lc5_org_id)
    fp = export_dir / "lc5_inventory.pdf"
    ReportService().export_pdf(data, fp)
    assert fp.exists()
    assert fp.stat().st_size > 0

def lc5_07_export_excel_exists_nonzero():
    """Export issue_history to Excel; file exists and size > 0."""
    export_dir = config.EXPORTS_DIR / "test_lifecycle"
    data = ReportService().generate("issue_history", org_id=_lc5_org_id)
    fp = export_dir / "lc5_issues.xlsx"
    ReportService().export_excel(data, fp)
    assert fp.exists()
    assert fp.stat().st_size > 0

def lc5_08_export_csv_exists_nonzero():
    """Export return_history to CSV; file exists and size > 0."""
    export_dir = config.EXPORTS_DIR / "test_lifecycle"
    data = ReportService().generate("return_history", org_id=_lc5_org_id)
    fp = export_dir / "lc5_returns.csv"
    ReportService().export_csv(data, fp)
    assert fp.exists()
    assert fp.stat().st_size > 0

def lc5_09_csv_row_count_matches_data():
    """CSV row count (data rows) matches ReportData.row_count."""
    import csv
    export_dir = config.EXPORTS_DIR / "test_lifecycle"
    data = ReportService().generate("asset_inventory", org_id=_lc5_org_id)
    fp = export_dir / "lc5_csv_check.csv"
    ReportService().export_csv(data, fp)

    data_rows = 0
    with open(fp, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Find the header row (first row matching columns), then count data rows
    col_row_idx = None
    for i, row in enumerate(rows):
        if row and row[0] == data.columns[0]:
            col_row_idx = i
            break

    if col_row_idx is not None:
        # Count non-empty rows after header until blank/summary
        for row in rows[col_row_idx + 1:]:
            if not any(cell.strip() for cell in row):
                break
            data_rows += 1

    assert data_rows == data.row_count, (
        f"CSV data rows {data_rows} != ReportData.row_count {data.row_count}"
    )


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# LIFECYCLE 6 â€” Settings Persistence
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

_lc6_org_id = None

# Counter for LC6 person codes
_lc6_person_counter = 0

def lc6_setup():
    global _lc6_org_id
    org = OrganizationService().create("LC6 Org", "LC6ORG")
    _lc6_org_id = org.id

def lc6_01_set_custom_prefix():
    """Set asset code prefix to 'MYCO' and verify it's stored."""
    SettingsService().set("asset_code_prefix", "MYCO")
    prefix = SettingsService().asset_code_prefix
    assert prefix == "MYCO", f"Expected MYCO, got {prefix}"

def lc6_02_new_asset_uses_custom_prefix():
    """New asset auto-generated code starts with 'MYCO-' or 'MYCO'."""
    asset = AssetService().create("LC6 Asset No Code", org_id=_lc6_org_id)
    assert asset.asset_code.upper().startswith("MYCO"), (
        f"Expected code starting with MYCO, got {asset.asset_code}"
    )

def lc6_03_reset_to_defaults_restores_prefix():
    """Reset settings to defaults; prefix returns to 'AST'."""
    SettingsService().reset_to_defaults()
    prefix = SettingsService().asset_code_prefix
    assert prefix == "AST", f"Expected AST after reset, got {prefix}"

def lc6_04_new_asset_after_reset_uses_ast():
    """Asset code after prefix reset starts with 'AST'."""
    asset = AssetService().create("LC6 Asset After Reset", org_id=_lc6_org_id)
    assert asset.asset_code.upper().startswith("AST"), (
        f"Expected code starting with AST, got {asset.asset_code}"
    )

def lc6_05_invalid_prefix_raises_validation_error():
    """Setting an invalid prefix (spaces/special chars) raises ValidationError."""
    try:
        SettingsService().set("asset_code_prefix", "HAS SPACE")
        raise AssertionError("Expected ValidationError not raised")
    except ValidationError:
        pass

def lc6_06_prefix_too_short_raises_validation_error():
    """Prefix of 1 char is too short â€” raises ValidationError."""
    try:
        SettingsService().set("asset_code_prefix", "X")
        raise AssertionError("Expected ValidationError not raised")
    except ValidationError:
        pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Additional edge-case lifecycle tests
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def lc_extra_01_org_code_duplicate_raises():
    """Creating two orgs with the same code raises DuplicateEntryError."""
    OrganizationService().create("Extra Org 1", "DUPORGX")
    try:
        OrganizationService().create("Extra Org 2", "DUPORGX")
        raise AssertionError("Expected DuplicateEntryError")
    except DuplicateEntryError:
        pass

def lc_extra_02_asset_code_duplicate_raises():
    """Creating two assets with the same code raises DuplicateEntryError."""
    org = OrganizationService().create("Extra Org 3", "EX3ORG")
    AssetService().create("Extra Asset 1", asset_code="DUPCODE1", org_id=org.id)
    try:
        AssetService().create("Extra Asset 2", asset_code="DUPCODE1", org_id=org.id)
        raise AssertionError("Expected DuplicateEntryError")
    except DuplicateEntryError:
        pass

def lc_extra_03_delete_issued_asset_fails():
    """Deleting a currently issued asset raises ValidationError."""
    org    = OrganizationService().create("Extra Org 4", "EX4ORG")
    person = PersonService().create(org.id, "ExtraPerson", person_id_code="EXTRAP001")
    asset  = AssetService().create("Extra Asset Del", org_id=org.id)
    TransactionService().issue_asset(asset.id, person.id, org_id=org.id)
    try:
        AssetService().delete(asset.id)
        raise AssertionError("Expected ValidationError")
    except ValidationError:
        pass

def lc_extra_04_asset_category_with_assets_cannot_be_deleted():
    """Category used by assets cannot be deleted."""
    org = OrganizationService().create("Extra Org 5", "EX5ORG")
    cat = AssetCategoryService().create("Extra Cat", "EXTRACAT", org_id=org.id)
    AssetService().create("Asset Using Cat", org_id=org.id, category_id=cat.id)
    try:
        AssetCategoryService().delete(cat.id)
        raise AssertionError("Expected ValidationError")
    except ValidationError:
        pass

def lc_extra_05_person_not_found_raises():
    """get_by_id for nonexistent person raises NotFoundError."""
    try:
        PersonService().get_by_id(999999)
        raise AssertionError("Expected NotFoundError")
    except NotFoundError:
        pass

def lc_extra_06_org_not_found_raises():
    """get_by_id for nonexistent org raises NotFoundError."""
    try:
        OrganizationService().get_by_id(999999)
        raise AssertionError("Expected NotFoundError")
    except NotFoundError:
        pass


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Main runner
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

if __name__ == "__main__":
    setup()

    print("\nâ”€â”€ Lifecycle 1: Full Asset Journey â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc1_setup()
    for fn, label in [
        (lc1_01_asset_initial_status_available,    "LC1-01 initial status available"),
        (lc1_02_issue_to_person1,                  "LC1-02 issue to person1"),
        (lc1_03_person1_has_one_holding,            "LC1-03 person1 has 1 holding"),
        (lc1_04_asset_not_in_available_list,        "LC1-04 not in available list"),
        (lc1_05_return_asset,                       "LC1-05 return asset"),
        (lc1_06_issue_again_to_person2,             "LC1-06 re-issue to person2"),
        (lc1_07_return_again_history_has_two,       "LC1-07 history has 2 returns"),
        (lc1_08_set_maintenance_cannot_issue,       "LC1-08 maintenance blocks issue"),
        (lc1_09_restore_available_can_issue,        "LC1-09 restore available â†’ can issue"),
        (lc1_10_soft_delete_raises_notfound,        "LC1-10 soft-delete â†’ NotFoundError"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Lifecycle 2: Person Journey â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc2_setup()
    for fn, label in [
        (lc2_01_issue_three_assets,                 "LC2-01 issue 3 assets"),
        (lc2_02_deactivate_person_with_active_issues_fails, "LC2-02 deactivate with active issues fails"),
        (lc2_03_return_all_assets,                  "LC2-03 return all assets"),
        (lc2_04_deactivate_person_succeeds,         "LC2-04 deactivate succeeds"),
        (lc2_05_issue_to_inactive_person_fails,     "LC2-05 issue to inactive fails"),
        (lc2_06_reactivate_person_can_receive,      "LC2-06 reactivate can receive"),
        (lc2_07_delete_person_with_active_issues_fails, "LC2-07 delete with active issues fails"),
        (lc2_08_return_then_delete_succeeds,        "LC2-08 return then delete succeeds"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Lifecycle 3: Organization Hierarchy â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc3_setup()
    for fn, label in [
        (lc3_01_top_level_depts_exist,              "LC3-01 3 top-level depts"),
        (lc3_02_subdepts_created,                   "LC3-02 sub-depts created"),
        (lc3_03_assign_persons_and_assets,          "LC3-03 assign persons and assets"),
        (lc3_04_dept_assets_counted_correctly,      "LC3-04 dept assets counted"),
        (lc3_05_delete_parent_dept_with_children_fails, "LC3-05 delete parent fails"),
        (lc3_06_delete_leaf_dept_succeeds,          "LC3-06 delete leaf succeeds"),
        (lc3_07_dept_assets_report_row_count,       "LC3-07 dept_assets report rows"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Lifecycle 4: Backup and Restore â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc4_setup()
    for fn, label in [
        (lc4_01_create_backup,                      "LC4-01 create backup"),
        (lc4_02_add_persons_after_backup,           "LC4-02 add persons post-backup"),
        (lc4_03_restore_backup,                     "LC4-03 restore backup"),
        (lc4_04_only_original_persons_exist,        "LC4-04 only original persons after restore"),
        (lc4_05_db_connection_works_after_restore,  "LC4-05 DB works after restore"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Lifecycle 5: Report Completeness â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc5_setup()
    for fn, label in [
        (lc5_01_asset_inventory_report,             "LC5-01 asset_inventory rows=10"),
        (lc5_02_dept_assets_report,                 "LC5-02 dept_assets rows=3"),
        (lc5_03_issue_history_report,               "LC5-03 issue_history rows=4"),
        (lc5_04_return_history_report,              "LC5-04 return_history rows=2"),
        (lc5_05_person_holdings_report,             "LC5-05 person_holdings rows=2"),
        (lc5_06_export_pdf_exists_nonzero,          "LC5-06 PDF export exists nonzero"),
        (lc5_07_export_excel_exists_nonzero,        "LC5-07 Excel export exists nonzero"),
        (lc5_08_export_csv_exists_nonzero,          "LC5-08 CSV export exists nonzero"),
        (lc5_09_csv_row_count_matches_data,         "LC5-09 CSV row count matches"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Lifecycle 6: Settings Persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    lc6_setup()
    for fn, label in [
        (lc6_01_set_custom_prefix,                  "LC6-01 set custom prefix MYCO"),
        (lc6_02_new_asset_uses_custom_prefix,       "LC6-02 new asset uses MYCO prefix"),
        (lc6_03_reset_to_defaults_restores_prefix,  "LC6-03 reset restores AST"),
        (lc6_04_new_asset_after_reset_uses_ast,     "LC6-04 new asset uses AST"),
        (lc6_05_invalid_prefix_raises_validation_error, "LC6-05 invalid prefix raises"),
        (lc6_06_prefix_too_short_raises_validation_error, "LC6-06 short prefix raises"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Extra Lifecycle Tests â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    for fn, label in [
        (lc_extra_01_org_code_duplicate_raises,     "EXTRA-01 org code duplicate"),
        (lc_extra_02_asset_code_duplicate_raises,   "EXTRA-02 asset code duplicate"),
        (lc_extra_03_delete_issued_asset_fails,     "EXTRA-03 delete issued asset fails"),
        (lc_extra_04_asset_category_with_assets_cannot_be_deleted, "EXTRA-04 category with assets"),
        (lc_extra_05_person_not_found_raises,       "EXTRA-05 person not found"),
        (lc_extra_06_org_not_found_raises,          "EXTRA-06 org not found"),
    ]:
        run(label, fn)

    teardown()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{'='*60}")
    print(f"  RESULTS: {len(_PASS)}/{total} passed, {len(_FAIL)} failed")
    if _FAIL:
        print("\n  Failed tests:")
        for name, err in _FAIL:
            print(f"    âœ— {name}: {err}")
    print(f"{'='*60}")
    sys.exit(0 if not _FAIL else 1)

