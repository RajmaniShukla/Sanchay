"""
Sanchay — Phase 6 Integration Tests
=======================================
Tests for Settings, User Management, and Backup & Restore.
"""

import sys, os, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_phase6.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db_mod
_db_mod._engine = None
_db_mod._SessionFactory = None

from app.core.database import init_db
from app.core.security import current_session
from app.services.auth_service import AuthService
from app.services.settings_service import SettingsService
from app.services.backup_service import BackupService
from app.core.exceptions import (
    AuthenticationError, DuplicateEntryError, ValidationError,
)

BACKUP_DIR = config.DATA_DIR / "test_backups_p6"


def setup_module():
    config.init_directories()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    config.BACKUPS_DIR = BACKUP_DIR     # redirect backups for tests
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("ph6admin", "Phase6 Admin", "Admin@123", "admin")
    except Exception:
        pass
    current_session.login(1, "ph6admin", "Phase6 Admin", "admin", {"all": True})

    SettingsService().seed_defaults()


def teardown_module():
    if _db_mod._engine:
        _db_mod._engine.dispose()
        _db_mod._engine = None
        _db_mod._SessionFactory = None
    import time; time.sleep(0.2)
    for p in [config.DB_PATH, BACKUP_DIR]:
        try:
            if p.is_file():  p.unlink()
            elif p.is_dir(): shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


# ── Settings Tests ────────────────────────────────────────────────────────────

class TestSettings:
    svc = SettingsService()

    def test_a_seed_defaults(self):
        self.svc.seed_defaults()
        val = self.svc.get("app_name")
        assert val == "Sanchay"
        print(f"  [OK] seed_defaults: app_name='{val}'")

    def test_b_get_existing(self):
        val = self.svc.get("asset_code_prefix", "AST")
        assert val in ("AST", "AST")
        print(f"  [OK] get: asset_code_prefix='{val}'")

    def test_c_get_missing_returns_default(self):
        val = self.svc.get("nonexistent_key", "MY_DEFAULT")
        assert val == "MY_DEFAULT"
        print("  [OK] get missing key returns default")

    def test_d_set_and_get(self):
        self.svc.set("asset_code_prefix", "LAP")
        val = self.svc.get("asset_code_prefix")
        assert val == "LAP"
        # restore
        self.svc.set("asset_code_prefix", "AST")
        print("  [OK] set → get round-trip works")

    def test_e_set_bool(self):
        self.svc.set_bool("auto_backup", True)
        assert self.svc.get_bool("auto_backup") is True
        self.svc.set_bool("auto_backup", False)
        assert self.svc.get_bool("auto_backup") is False
        print("  [OK] set_bool / get_bool works")

    def test_f_set_many(self):
        self.svc.set_many({
            "asset_code_prefix": "ASSET",
            "theme": "dark",
        })
        assert self.svc.get("asset_code_prefix") == "ASSET"
        assert self.svc.get("theme") == "dark"
        # restore
        self.svc.set_many({"asset_code_prefix": "AST", "theme": "light"})
        print("  [OK] set_many works for batch updates")

    def test_g_get_all_includes_defaults(self):
        all_settings = self.svc.get_all()
        assert "app_name" in all_settings
        assert "asset_code_prefix" in all_settings
        assert "auto_backup" in all_settings
        print(f"  [OK] get_all: {len(all_settings)} setting(s)")

    def test_h_named_properties(self):
        assert self.svc.app_name == "Sanchay"
        assert self.svc.asset_code_prefix == "AST"
        assert self.svc.auto_backup_enabled is False
        assert self.svc.theme == "light"
        print("  [OK] named property accessors work")


# ── User Management Tests ─────────────────────────────────────────────────────

class TestUserManagement:
    svc = AuthService()

    def test_a_create_manager(self):
        u = self.svc.create_user(
            username="mgr_test", full_name="Test Manager",
            password="Manager@123", role_name="manager",
            email="mgr@test.com",
        )
        assert u.id is not None
        assert u.role_name == "manager"
        print(f"  [OK] Created manager: {u.username} (id={u.id})")

    def test_b_create_operator(self):
        u = self.svc.create_user(
            username="opr_test", full_name="Test Operator",
            password="Operator@123", role_name="operator",
        )
        assert u.role_name == "operator"
        print(f"  [OK] Created operator: {u.username}")

    def test_c_duplicate_username_raises(self):
        try:
            self.svc.create_user("mgr_test", "Dup", "pass123", "viewer")
            assert False, "Should have raised"
        except DuplicateEntryError:
            print("  [OK] Duplicate username raises DuplicateEntryError")

    def test_d_get_all_users(self):
        users = self.svc.get_all_users()
        assert len(users) >= 3   # admin + mgr + opr
        print(f"  [OK] get_all_users: {len(users)} users")

    def test_e_login_new_user(self):
        result = self.svc.login("mgr_test", "Manager@123")
        assert result["username"] == "mgr_test"
        assert result["role"] == "manager"
        # Restore admin session
        current_session.login(1, "ph6admin", "Phase6 Admin", "admin", {"all": True})
        print("  [OK] New user can log in with correct credentials")

    def test_f_wrong_password_raises(self):
        try:
            self.svc.login("mgr_test", "WrongPassword!")
            assert False, "Should have raised"
        except AuthenticationError:
            print("  [OK] Wrong password raises AuthenticationError")

    def test_g_change_password(self):
        users = self.svc.get_all_users()
        mgr   = next(u for u in users if u.username == "mgr_test")
        self.svc.change_password(mgr.id, "NewPass@456")
        result = self.svc.login("mgr_test", "NewPass@456")
        assert result["username"] == "mgr_test"
        current_session.login(1, "ph6admin", "Phase6 Admin", "admin", {"all": True})
        print("  [OK] Password changed and new password works")

    def test_h_toggle_user_active(self):
        users  = self.svc.get_all_users()
        opr    = next(u for u in users if u.username == "opr_test")
        state  = self.svc.toggle_user_active(opr.id)
        assert state is False    # deactivated
        state2 = self.svc.toggle_user_active(opr.id)
        assert state2 is True    # reactivated
        print("  [OK] toggle_user_active: active → inactive → active")

    def test_i_deactivate_last_admin_raises(self):
        users = self.svc.get_all_users()
        admin = next(u for u in users if u.username == "ph6admin")
        try:
            self.svc.toggle_user_active(admin.id)
            # should raise because ph6admin is the only admin
            assert False, "Should have raised"
        except ValidationError:
            print("  [OK] Deactivating last admin raises ValidationError")

    def test_j_login_inactive_user_raises(self):
        # Deactivate operator and try to login
        users = self.svc.get_all_users()
        opr   = next(u for u in users if u.username == "opr_test")
        self.svc.toggle_user_active(opr.id)     # → inactive
        try:
            self.svc.login("opr_test", "Operator@123")
            assert False, "Should have raised"
        except Exception as e:
            assert "deactivated" in str(e).lower() or "inactive" in str(e).lower()
            print("  [OK] Login with inactive account raises AccountInactiveError")
        finally:
            self.svc.toggle_user_active(opr.id) # restore


# ── Backup & Restore Tests ────────────────────────────────────────────────────

class TestBackup:
    svc = BackupService()

    def test_a_create_backup(self):
        path = self.svc.create_backup(BACKUP_DIR)
        assert path.exists()
        assert path.suffix == ".db"
        assert path.stat().st_size > 0
        print(f"  [OK] Backup created: {path.name} ({path.stat().st_size} bytes)")

    def test_b_list_backups(self):
        backups = self.svc.list_backups()
        assert len(backups) >= 1
        bk = backups[0]
        assert "name" in bk
        assert "size_kb" in bk
        assert "created_at" in bk
        assert "path" in bk
        print(f"  [OK] list_backups: {len(backups)} backup(s)")

    def test_c_create_multiple_backups(self):
        import time
        self.svc.create_backup(BACKUP_DIR)
        time.sleep(0.05)
        self.svc.create_backup(BACKUP_DIR)
        backups = self.svc.list_backups()
        assert len(backups) >= 3
        print(f"  [OK] Multiple backups: {len(backups)} total")

    def test_d_cleanup_old_backups(self):
        deleted = self.svc.cleanup_old_backups(keep=1)
        backups = self.svc.list_backups()
        assert len(backups) <= 1
        print(f"  [OK] Cleanup: deleted {deleted}, kept {len(backups)}")

    def test_e_delete_backup(self):
        # Create a fresh backup, then delete it
        path = self.svc.create_backup(BACKUP_DIR)
        assert path.exists()
        self.svc.delete_backup(path)
        assert not path.exists()
        print(f"  [OK] Backup deleted: {path.name}")

    def test_f_restore_from_backup(self):
        # Create backup, then restore it
        path = self.svc.create_backup(BACKUP_DIR)
        self.svc.restore_backup(path)
        # DB should still be accessible
        from app.core.database import check_connection
        assert check_connection()
        print(f"  [OK] Restore from backup works, DB accessible")


# ── Runner ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import traceback
    setup_module()
    passed = failed = 0
    for Suite in [TestSettings, TestUserManagement, TestBackup]:
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
    print(f"\n{'='*48}")
    print(f"Results: {passed} passed, {failed} failed")
    teardown_module()
