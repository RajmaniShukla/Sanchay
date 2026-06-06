"""
Sanchay â€” Phase 7.5 Permission / RBAC Tests
=============================================
Tests role-based access control at the SERVICE layer.
Creates users with each role and calls service methods from their session.

Key findings are documented with:
  # SECURITY_GAP: <method> does not check role permissions
"""

import sys, os, traceback, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_permissions.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db
_db._engine = None
_db._SessionFactory = None

from app.core.database import init_db
from app.core.security import current_session
from app.core.security import hash_password as _hash_pw
from app.core.exceptions import (
    ValidationError, DuplicateEntryError, NotFoundError,
    PermissionDeniedError, AuthenticationError, AccountInactiveError,
)
from app.services.auth_service import AuthService


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
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.person_service import PersonService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.transaction_service import TransactionService
from app.services.settings_service import SettingsService
from app.services.backup_service import BackupService
from app.services.report_service import ReportService

# â”€â”€ Test runner helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_PASS = []
_FAIL = []
_SECURITY_GAPS = []

def run(name, fn):
    try:
        fn()
        _PASS.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        _FAIL.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()

def note_gap(method, detail=""):
    msg = f"SECURITY_GAP: {method} does not check role permissions"
    if detail:
        msg += f" ({detail})"
    if msg not in _SECURITY_GAPS:
        _SECURITY_GAPS.append(msg)


# â”€â”€ Shared state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_users = {}      # role -> user object
_org_id = None
_dept_id = None
_test_asset_id = None
_test_person_id = None


def _login_as(role: str):
    """Login as the user with the given role."""
    AuthService().login(f"perm_{role}", "Passw0rd!")


def setup():
    global _users, _org_id, _dept_id, _test_asset_id, _test_person_id

    config.init_directories()
    if config.DB_PATH.exists():
        config.DB_PATH.unlink()
    init_db()

    auth = AuthService()
    auth.seed_default_roles()

    # Bootstrap admin user directly via ORM (bypasses require_authenticated)
    _bootstrap_admin("perm_admin", "Perm Admin", "Passw0rd!")
    auth.login("perm_admin", "Passw0rd!")
    _users["admin"] = auth.get_user_by_id(current_session.user_id)

    for role in ("manager", "operator", "viewer"):
        try:
            u = auth.create_user(f"perm_{role}", f"Perm {role.capitalize()}", "Passw0rd!", role)
        except DuplicateEntryError:
            from app.core.database import get_db
            from app.models.user import User
            with get_db() as db:
                u = db.query(User).filter(User.username == f"perm_{role}").first()
        _users[role] = u

    SettingsService().seed_defaults()

    # Create shared org, dept, asset, person using admin
    org  = OrganizationService().create("Perm Org", "PERMORG")
    dept = DepartmentService().create(org.id, "Perm Dept", "PERMDEPT")
    _org_id  = org.id
    _dept_id = dept.id

    person = PersonService().create(org.id, "PermPerson", dept_id=dept.id)
    _test_person_id = person.id

    asset = AssetService().create("Perm Asset", org_id=org.id)
    _test_asset_id = asset.id


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
# SESSION MANAGEMENT TESTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def sess_01_login_sets_authenticated():
    """Login populates session.is_authenticated = True."""
    _login_as("admin")
    assert current_session.is_authenticated, "Expected is_authenticated=True after login"

def sess_02_logout_clears_authenticated():
    """Logout clears session."""
    _login_as("admin")
    AuthService().logout()
    assert not current_session.is_authenticated, "Expected is_authenticated=False after logout"

def sess_03_wrong_password_raises_auth_error():
    """Login with wrong password raises AuthenticationError."""
    try:
        AuthService().login("perm_admin", "WRONGPASSWORD")
        raise AssertionError("Expected AuthenticationError")
    except AuthenticationError:
        pass

def sess_04_wrong_password_session_unchanged():
    """After failed login, session state unchanged (user stays logged out)."""
    _login_as("admin")
    AuthService().logout()
    try:
        AuthService().login("perm_admin", "WRONGPASSWORD")
    except AuthenticationError:
        pass
    assert not current_session.is_authenticated

def sess_05_login_inactive_user_raises():
    """Login with inactive user raises AccountInactiveError."""
    _login_as("admin")
    # Create a new user and deactivate them
    auth = AuthService()
    try:
        auth.create_user("inactive_perm_user", "Inactive", "Passw0rd!", "viewer")
    except DuplicateEntryError:
        pass
    # Get user id
    from app.core.database import get_db
    from app.models.user import User
    with get_db() as db:
        u = db.query(User).filter(User.username == "inactive_perm_user").first()
        if u:
            u.is_active = False

    try:
        AuthService().login("inactive_perm_user", "Passw0rd!")
        raise AssertionError("Expected AccountInactiveError")
    except AccountInactiveError:
        pass

def sess_06_has_permission_assets_write_admin():
    """Admin has_permission('assets:w') returns True."""
    _login_as("admin")
    assert current_session.has_permission("assets:w"), "Admin should have assets:w"

def sess_07_has_permission_assets_write_viewer_false():
    """Viewer has_permission('assets:w') returns False."""
    _login_as("viewer")
    assert not current_session.has_permission("assets:w"), "Viewer should NOT have assets:w"
    _login_as("admin")  # restore

def sess_08_has_permission_users_rw_operator_false():
    """Operator has_permission('users:rw') returns False."""
    _login_as("operator")
    assert not current_session.has_permission("users:rw"), "Operator should NOT have users:rw"
    _login_as("admin")

def sess_09_is_admin_true_for_admin():
    """is_admin() returns True for admin role."""
    _login_as("admin")
    assert current_session.is_admin()

def sess_10_is_admin_false_for_manager():
    """is_admin() returns False for manager role."""
    _login_as("manager")
    assert not current_session.is_admin()
    _login_as("admin")

def sess_11_is_manager_true_for_manager():
    """is_manager() returns True for manager (includes admin)."""
    _login_as("manager")
    assert current_session.is_manager()
    _login_as("admin")

def sess_12_is_manager_false_for_viewer():
    """is_manager() returns False for viewer."""
    _login_as("viewer")
    assert not current_session.is_manager()
    _login_as("admin")

def sess_13_is_operator_true_for_operator():
    """is_operator() returns True for operator."""
    _login_as("operator")
    assert current_session.is_operator()
    _login_as("admin")

def sess_14_is_operator_false_for_viewer():
    """is_operator() returns False for viewer."""
    _login_as("viewer")
    assert not current_session.is_operator()
    _login_as("admin")

def sess_15_unauthenticated_is_false():
    """Unauthenticated session: all is_* return False."""
    AuthService().logout()
    assert not current_session.is_authenticated
    assert not current_session.is_admin()
    assert not current_session.is_manager()
    assert not current_session.is_operator()
    _login_as("admin")

def sess_16_after_logout_user_id_is_none():
    """After logout, user_id is None."""
    _login_as("admin")
    AuthService().logout()
    assert current_session.user_id is None
    _login_as("admin")

def sess_17_role_consistent_with_created_role():
    """Session role matches the role used at creation."""
    for role in ("manager", "operator", "viewer"):
        _login_as(role)
        assert current_session.role == role, (
            f"Expected role='{role}', got '{current_session.role}'"
        )
    _login_as("admin")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# PERMISSION MATRIX TESTS
# Each test checks whether non-admin roles can call a service method.
# Services that don't check permissions are documented as SECURITY_GAP.
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â”€â”€ create_user â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_01_admin_can_create_user():
    """Admin: create_user succeeds."""
    _login_as("admin")
    try:
        AuthService().create_user("perm_new1", "New User 1", "Passw0rd!", "viewer")
    except DuplicateEntryError:
        pass  # already exists from prior run â€” that's fine

def perm_02_manager_create_user():
    """Manager: create_user â€” discover if permission is enforced."""
    _login_as("manager")
    try:
        AuthService().create_user("perm_mgr_new", "Mgr New", "Passw0rd!", "viewer")
        # SECURITY_GAP: create_user does not check if caller is admin
        note_gap("AuthService.create_user", "manager can create users")
    except PermissionDeniedError:
        pass  # Properly enforced
    finally:
        _login_as("admin")

def perm_03_operator_create_user():
    """Operator: create_user â€” discover if permission is enforced."""
    _login_as("operator")
    try:
        AuthService().create_user("perm_op_new", "Op New", "Passw0rd!", "viewer")
        note_gap("AuthService.create_user", "operator can create users")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_04_viewer_create_user():
    """Viewer: create_user â€” discover if permission is enforced."""
    _login_as("viewer")
    try:
        AuthService().create_user("perm_vw_new", "Viewer New", "Passw0rd!", "viewer")
        note_gap("AuthService.create_user", "viewer can create users")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ toggle_user_active â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_05_admin_can_toggle_user_active():
    """Admin: toggle_user_active succeeds."""
    _login_as("admin")
    # Toggle viewer user active state
    viewer_id = _users["viewer"].id
    AuthService().toggle_user_active(viewer_id)
    AuthService().toggle_user_active(viewer_id)  # restore

def perm_06_manager_toggle_user():
    """Manager: toggle_user_active â€” discover if enforced."""
    _login_as("manager")
    viewer_id = _users["viewer"].id
    try:
        AuthService().toggle_user_active(viewer_id)
        note_gap("AuthService.toggle_user_active", "manager can toggle user active")
        # Restore
        _login_as("admin")
        AuthService().toggle_user_active(viewer_id)
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_07_operator_toggle_user():
    """Operator: toggle_user_active â€” discover if enforced."""
    _login_as("operator")
    viewer_id = _users["viewer"].id
    try:
        AuthService().toggle_user_active(viewer_id)
        note_gap("AuthService.toggle_user_active", "operator can toggle user active")
        _login_as("admin")
        AuthService().toggle_user_active(viewer_id)
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ create_org â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_08_admin_can_create_org():
    """Admin: create_org succeeds."""
    _login_as("admin")
    try:
        OrganizationService().create("PermOrg Admin", "PADMORG")
    except DuplicateEntryError:
        pass

def perm_09_manager_create_org():
    """Manager: create_org â€” discover if enforced."""
    _login_as("manager")
    try:
        OrganizationService().create("PermOrg Mgr", "PMGRORG")
        note_gap("OrganizationService.create", "manager can create orgs")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_10_operator_create_org():
    """Operator: create_org â€” discover if enforced."""
    _login_as("operator")
    try:
        OrganizationService().create("PermOrg Op", "POPORG")
        note_gap("OrganizationService.create", "operator can create orgs")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_11_viewer_create_org():
    """Viewer: create_org â€” discover if enforced."""
    _login_as("viewer")
    try:
        OrganizationService().create("PermOrg Vw", "PVWORG")
        note_gap("OrganizationService.create", "viewer can create orgs")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ create_asset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_12_admin_can_create_asset():
    """Admin: create_asset succeeds."""
    _login_as("admin")
    AssetService().create("Admin Asset", org_id=_org_id)

def perm_13_manager_can_create_asset():
    """Manager: create_asset â€” managers should be allowed."""
    _login_as("manager")
    try:
        AssetService().create("Manager Asset", org_id=_org_id)
        # Manager is expected to create assets per permission matrix
    except PermissionDeniedError:
        raise AssertionError("Manager should be able to create assets per design")
    finally:
        _login_as("admin")

def perm_14_operator_create_asset():
    """Operator: create_asset â€” discover if enforced."""
    _login_as("operator")
    try:
        AssetService().create("Operator Asset", org_id=_org_id)
        note_gap("AssetService.create", "operator can create assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_15_viewer_create_asset():
    """Viewer: create_asset â€” discover if enforced."""
    _login_as("viewer")
    try:
        AssetService().create("Viewer Asset", org_id=_org_id)
        note_gap("AssetService.create", "viewer can create assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ issue_asset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_16_admin_can_issue_asset():
    """Admin: issue_asset succeeds."""
    _login_as("admin")
    asset = AssetService().create("Admin Issue Asset", org_id=_org_id)
    person = PersonService().create(_org_id, "AdminIssuePerson")
    TransactionService().issue_asset(asset.id, person.id, org_id=_org_id)

def perm_17_operator_can_issue_asset():
    """Operator: issue_asset â€” operators should be allowed."""
    _login_as("admin")
    asset = AssetService().create("Op Issue Asset", org_id=_org_id)
    person = PersonService().create(_org_id, "OpIssuePerson")
    _login_as("operator")
    try:
        TransactionService().issue_asset(asset.id, person.id, org_id=_org_id)
    except PermissionDeniedError:
        raise AssertionError("Operator should be able to issue assets per design")
    finally:
        _login_as("admin")

def perm_18_viewer_issue_asset():
    """Viewer: issue_asset â€” discover if enforced."""
    _login_as("admin")
    asset = AssetService().create("Viewer Issue Asset", org_id=_org_id)
    person = PersonService().create(_org_id, "ViewerIssuePerson")
    _login_as("viewer")
    try:
        TransactionService().issue_asset(asset.id, person.id, org_id=_org_id)
        note_gap("TransactionService.issue_asset", "viewer can issue assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ return_asset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_19_admin_can_return_asset():
    """Admin: return_asset succeeds."""
    _login_as("admin")
    asset  = AssetService().create("Admin Return Asset", org_id=_org_id)
    person = PersonService().create(_org_id, "AdminReturnPerson")
    TransactionService().issue_asset(asset.id, person.id, org_id=_org_id)
    holdings = TransactionService().get_holdings_for_person(person.id)
    TransactionService().return_asset(holdings[0].id)

def perm_20_viewer_return_asset():
    """Viewer: return_asset â€” discover if enforced."""
    _login_as("admin")
    asset  = AssetService().create("Viewer Return Asset", org_id=_org_id)
    person = PersonService().create(_org_id, "ViewerReturnPerson")
    TransactionService().issue_asset(asset.id, person.id, org_id=_org_id)
    holdings = TransactionService().get_holdings_for_person(person.id)
    issue_id = holdings[0].id
    _login_as("viewer")
    try:
        TransactionService().return_asset(issue_id)
        note_gap("TransactionService.return_asset", "viewer can return assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ generate_report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_21_admin_can_generate_report():
    """Admin: generate_report succeeds."""
    _login_as("admin")
    data = ReportService().generate("asset_inventory", org_id=_org_id)
    assert data is not None

def perm_22_viewer_can_generate_report():
    """Viewer: generate_report â€” viewers should be allowed (read-only)."""
    _login_as("viewer")
    try:
        data = ReportService().generate("asset_inventory", org_id=_org_id)
        assert data is not None
    except PermissionDeniedError:
        raise AssertionError("Viewer should be able to generate reports per design")
    finally:
        _login_as("admin")

def perm_23_operator_generate_report():
    """Operator: generate_report â€” discover if enforced (should be denied per matrix)."""
    _login_as("operator")
    try:
        ReportService().generate("asset_inventory", org_id=_org_id)
        # Per the permission matrix operators are NOT supposed to generate reports
        # but the service may not enforce it
        note_gap("ReportService.generate", "operator can generate reports (matrix says NO)")
    except PermissionDeniedError:
        pass  # Properly enforced
    finally:
        _login_as("admin")

# â”€â”€ create_backup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_24_admin_can_create_backup():
    """Admin: create_backup succeeds."""
    _login_as("admin")
    bp = BackupService().create_backup()
    assert bp.exists()

def perm_25_manager_create_backup():
    """Manager: create_backup â€” discover if enforced."""
    _login_as("manager")
    try:
        bp = BackupService().create_backup()
        note_gap("BackupService.create_backup", "manager can create backups")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_26_operator_create_backup():
    """Operator: create_backup â€” discover if enforced."""
    _login_as("operator")
    try:
        BackupService().create_backup()
        note_gap("BackupService.create_backup", "operator can create backups")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_27_viewer_create_backup():
    """Viewer: create_backup â€” discover if enforced."""
    _login_as("viewer")
    try:
        BackupService().create_backup()
        note_gap("BackupService.create_backup", "viewer can create backups")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ delete_asset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_28_admin_can_delete_asset():
    """Admin: delete_asset succeeds."""
    _login_as("admin")
    asset = AssetService().create("Admin Delete Asset", org_id=_org_id)
    AssetService().delete(asset.id)

def perm_29_manager_delete_asset():
    """Manager: delete_asset â€” managers should be allowed per matrix."""
    _login_as("admin")
    asset = AssetService().create("Mgr Delete Asset", org_id=_org_id)
    _login_as("manager")
    try:
        AssetService().delete(asset.id)
        # Expected per permission matrix
    except PermissionDeniedError:
        raise AssertionError("Manager should be able to delete assets per design")
    finally:
        _login_as("admin")

def perm_30_operator_delete_asset():
    """Operator: delete_asset â€” discover if enforced."""
    _login_as("admin")
    asset = AssetService().create("Op Delete Asset", org_id=_org_id)
    _login_as("operator")
    try:
        AssetService().delete(asset.id)
        note_gap("AssetService.delete", "operator can delete assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

def perm_31_viewer_delete_asset():
    """Viewer: delete_asset â€” discover if enforced."""
    _login_as("admin")
    asset = AssetService().create("Vw Delete Asset", org_id=_org_id)
    _login_as("viewer")
    try:
        AssetService().delete(asset.id)
        note_gap("AssetService.delete", "viewer can delete assets")
    except PermissionDeniedError:
        pass
    finally:
        _login_as("admin")

# â”€â”€ has_permission comprehensive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def perm_32_manager_has_assets_rw():
    """Manager has assets:rw permission."""
    _login_as("manager")
    assert current_session.has_permission("assets:r"), "Manager should have assets:r"
    assert current_session.has_permission("assets:w"), "Manager should have assets:w"
    _login_as("admin")

def perm_33_viewer_has_reports_r_not_w():
    """Viewer has reports:r but not assets:w."""
    _login_as("viewer")
    assert current_session.has_permission("reports:r"), "Viewer should have reports:r"
    assert not current_session.has_permission("reports:w"), "Viewer should NOT have reports:w"
    _login_as("admin")

def perm_34_operator_has_transactions_rw():
    """Operator has transactions:rw permission."""
    _login_as("operator")
    assert current_session.has_permission("transactions:r"), "Operator should have transactions:r"
    assert current_session.has_permission("transactions:w"), "Operator should have transactions:w"
    _login_as("admin")

def perm_35_admin_has_all_permissions():
    """Admin has_permission for any module."""
    _login_as("admin")
    for perm in ("assets:r", "assets:w", "persons:rw", "reports:r",
                 "transactions:w", "settings:r", "users:rw"):
        assert current_session.has_permission(perm), f"Admin missing {perm}"


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Main runner
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

if __name__ == "__main__":
    setup()

    print("\nâ”€â”€ Session Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    for fn, label in [
        (sess_01_login_sets_authenticated,          "SESS-01 login sets authenticated"),
        (sess_02_logout_clears_authenticated,       "SESS-02 logout clears authenticated"),
        (sess_03_wrong_password_raises_auth_error,  "SESS-03 wrong password â†’ AuthError"),
        (sess_04_wrong_password_session_unchanged,  "SESS-04 failed login session unchanged"),
        (sess_05_login_inactive_user_raises,        "SESS-05 inactive user â†’ AccountInactiveError"),
        (sess_06_has_permission_assets_write_admin, "SESS-06 admin has assets:w"),
        (sess_07_has_permission_assets_write_viewer_false, "SESS-07 viewer lacks assets:w"),
        (sess_08_has_permission_users_rw_operator_false,   "SESS-08 operator lacks users:rw"),
        (sess_09_is_admin_true_for_admin,           "SESS-09 is_admin() admin"),
        (sess_10_is_admin_false_for_manager,        "SESS-10 is_admin() manager=False"),
        (sess_11_is_manager_true_for_manager,       "SESS-11 is_manager() manager=True"),
        (sess_12_is_manager_false_for_viewer,       "SESS-12 is_manager() viewer=False"),
        (sess_13_is_operator_true_for_operator,     "SESS-13 is_operator() operator=True"),
        (sess_14_is_operator_false_for_viewer,      "SESS-14 is_operator() viewer=False"),
        (sess_15_unauthenticated_is_false,          "SESS-15 unauthenticated all is_* False"),
        (sess_16_after_logout_user_id_is_none,      "SESS-16 logout â†’ user_id=None"),
        (sess_17_role_consistent_with_created_role, "SESS-17 role consistent with creation"),
    ]:
        run(label, fn)

    print("\nâ”€â”€ Permission Matrix â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€")
    for fn, label in [
        (perm_01_admin_can_create_user,             "PERM-01 admin create_user"),
        (perm_02_manager_create_user,               "PERM-02 manager create_user"),
        (perm_03_operator_create_user,              "PERM-03 operator create_user"),
        (perm_04_viewer_create_user,                "PERM-04 viewer create_user"),
        (perm_05_admin_can_toggle_user_active,      "PERM-05 admin toggle_user_active"),
        (perm_06_manager_toggle_user,               "PERM-06 manager toggle_user_active"),
        (perm_07_operator_toggle_user,              "PERM-07 operator toggle_user_active"),
        (perm_08_admin_can_create_org,              "PERM-08 admin create_org"),
        (perm_09_manager_create_org,                "PERM-09 manager create_org"),
        (perm_10_operator_create_org,               "PERM-10 operator create_org"),
        (perm_11_viewer_create_org,                 "PERM-11 viewer create_org"),
        (perm_12_admin_can_create_asset,            "PERM-12 admin create_asset"),
        (perm_13_manager_can_create_asset,          "PERM-13 manager create_asset"),
        (perm_14_operator_create_asset,             "PERM-14 operator create_asset"),
        (perm_15_viewer_create_asset,               "PERM-15 viewer create_asset"),
        (perm_16_admin_can_issue_asset,             "PERM-16 admin issue_asset"),
        (perm_17_operator_can_issue_asset,          "PERM-17 operator issue_asset"),
        (perm_18_viewer_issue_asset,                "PERM-18 viewer issue_asset"),
        (perm_19_admin_can_return_asset,            "PERM-19 admin return_asset"),
        (perm_20_viewer_return_asset,               "PERM-20 viewer return_asset"),
        (perm_21_admin_can_generate_report,         "PERM-21 admin generate_report"),
        (perm_22_viewer_can_generate_report,        "PERM-22 viewer generate_report"),
        (perm_23_operator_generate_report,          "PERM-23 operator generate_report"),
        (perm_24_admin_can_create_backup,           "PERM-24 admin create_backup"),
        (perm_25_manager_create_backup,             "PERM-25 manager create_backup"),
        (perm_26_operator_create_backup,            "PERM-26 operator create_backup"),
        (perm_27_viewer_create_backup,              "PERM-27 viewer create_backup"),
        (perm_28_admin_can_delete_asset,            "PERM-28 admin delete_asset"),
        (perm_29_manager_delete_asset,              "PERM-29 manager delete_asset"),
        (perm_30_operator_delete_asset,             "PERM-30 operator delete_asset"),
        (perm_31_viewer_delete_asset,               "PERM-31 viewer delete_asset"),
        (perm_32_manager_has_assets_rw,             "PERM-32 manager has assets:rw"),
        (perm_33_viewer_has_reports_r_not_w,        "PERM-33 viewer has reports:r not w"),
        (perm_34_operator_has_transactions_rw,      "PERM-34 operator has transactions:rw"),
        (perm_35_admin_has_all_permissions,         "PERM-35 admin has all perms"),
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
    print(f"\n  SECURITY GAPS FOUND: {len(_SECURITY_GAPS)}")
    for gap in _SECURITY_GAPS:
        print(f"    âš   {gap}")
    print(f"{'='*60}")
    sys.exit(0 if not _FAIL else 1)

