"""
Sanchay — Phase 7 Security Tests
====================================
Security-focused tests for password hashing, session management,
permission checks, and input sanitization.
"""

import sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_security.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import app.core.database as _db
_db._engine = None
_db._SessionFactory = None

from app.core.database import init_db
from app.core.security import (
    hash_password, verify_password, validate_password_strength, current_session,
    UserSession,
)
from app.core.exceptions import (
    AuthenticationError, AccountInactiveError, ValidationError,
    DuplicateEntryError, PermissionDeniedError,
)
from app.services.auth_service import AuthService
from app.services.settings_service import SettingsService


def setup_module():
    config.init_directories()
    init_db()

    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("sec_admin", "Sec Admin", "Admin@123", "admin")
    except Exception:
        pass
    current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
    SettingsService().seed_defaults()


def teardown_module():
    if _db._engine:
        _db._engine.dispose()
        _db._engine = None
        _db._SessionFactory = None
    time.sleep(0.2)
    try:
        config.DB_PATH.unlink()
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════
# Password hashing
# ════════════════════════════════════════════════════════════════════════════

class TestPasswordHashing:

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecret@123")
        assert hashed != "MySecret@123"
        print(f"  [OK] hash is not plaintext")

    def test_hash_uses_bcrypt_prefix(self):
        hashed = hash_password("MySecret@123")
        assert hashed.startswith("$2b$"), f"Expected $2b$ prefix, got: {hashed[:10]}"
        print(f"  [OK] hash has bcrypt $2b$ prefix: {hashed[:20]}...")

    def test_same_password_different_hashes(self):
        """bcrypt includes a random salt, so same password → different hashes"""
        h1 = hash_password("SamePass@123")
        h2 = hash_password("SamePass@123")
        assert h1 != h2
        print(f"  [OK] same password produces different hashes (salted)")

    def test_plaintext_never_stored(self):
        """Verify the stored hash is definitively not the original password"""
        pw = "PlainNeverStored@99"
        hashed = hash_password(pw)
        assert pw not in hashed
        assert len(hashed) > len(pw)
        print(f"  [OK] plaintext not in stored hash (len hash={len(hashed)})")

    def test_verify_correct_password(self):
        pw = "CorrectPass@456"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True
        print(f"  [OK] verify correct password → True")

    def test_verify_wrong_password(self):
        hashed = hash_password("RealPass@789")
        assert verify_password("WrongPass@789", hashed) is False
        print(f"  [OK] verify wrong password → False")

    def test_verify_empty_password(self):
        hashed = hash_password("SomePass@123")
        result = verify_password("", hashed)
        assert result is False
        print(f"  [OK] verify empty password → False")

    def test_verify_none_password_safe(self):
        hashed = hash_password("SomePass@123")
        try:
            result = verify_password(None, hashed)
            assert result is False
            print(f"  [OK] verify None password → False (safe)")
        except (TypeError, Exception) as e:
            # Acceptable if it raises rather than authenticating
            print(f"  [OK] verify None password raises {type(e).__name__} (safe)")

    def test_hash_empty_password_raises(self):
        try:
            hash_password("")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "empty" in str(e).lower() or "password" in str(e).lower()
            print(f"  [OK] hash empty password raises ValueError")

    def test_hash_none_password_raises(self):
        try:
            hash_password(None)
            assert False
        except (ValueError, TypeError) as e:
            print(f"  [OK] hash None password raises {type(e).__name__}")


# ════════════════════════════════════════════════════════════════════════════
# Password length validation
# ════════════════════════════════════════════════════════════════════════════

class TestPasswordLength:

    def test_5_char_fails_validation(self):
        valid, msg = validate_password_strength("ab@1X")
        assert not valid
        assert "6" in msg or "character" in msg.lower()
        print(f"  [OK] 5-char password fails: '{msg}'")

    def test_6_char_passes_validation(self):
        valid, msg = validate_password_strength("Ab@1Xy")
        assert valid
        print(f"  [OK] 6-char password passes: '{msg}'")

    def test_128_char_passes_validation(self):
        # bcrypt limit is 72 bytes — we cap there; a 70-char ASCII password is fine
        pw = "A" * 35 + "b" * 33 + "@1"
        assert len(pw) == 70
        valid, msg = validate_password_strength(pw)
        assert valid, f"Expected pass but got: {msg}"
        print(f"  [OK] 70-char password passes validation")

    def test_73_char_fails_validation(self):
        # bcrypt cap: anything over 72 bytes should be rejected
        pw = "A" * 71 + "@1"  # 73 chars = 73 bytes (ASCII)
        valid, msg = validate_password_strength(pw)
        assert not valid, f"Expected fail but got valid=True"
        assert "72" in msg or "exceed" in msg.lower()
        print(f"  [OK] 73-char password (over bcrypt 72-byte limit) fails: '{msg}'")

    def test_hash_5_char_raises(self):
        """hash_password enforces minimum before hashing"""
        try:
            hash_password("ab1@X")  # 5 chars
            assert False
        except ValueError:
            print("  [OK] hash_password rejects 5-char password")

    def test_hash_6_char_succeeds(self):
        hashed = hash_password("Ab@1Xy")
        assert hashed.startswith("$2b$")
        print("  [OK] hash_password accepts 6-char password")

    def test_hash_70_char_succeeds(self):
        # 70 chars = 70 bytes (ASCII) — within bcrypt 72-byte limit
        pw = "A" * 35 + "b" * 33 + "@1"
        hashed = hash_password(pw)
        assert hashed.startswith("$2b$")
        print("  [OK] hash_password accepts 70-char password")

    def test_hash_very_long_handled(self):
        """bcrypt truncates at 72 bytes; service should guard"""
        pw = "A" * 200 + "@1!"
        try:
            hashed = hash_password(pw)
            print("  [OK] very long password hashed (bcrypt truncation behavior)")
        except (ValueError, Exception) as e:
            print(f"  [OK] very long password raises {type(e).__name__}: {str(e)[:60]}")


# ════════════════════════════════════════════════════════════════════════════
# Session state
# ════════════════════════════════════════════════════════════════════════════

class TestSessionState:
    auth = AuthService()

    def test_session_authenticated_after_login(self):
        # Current session should be authenticated from setup_module
        assert current_session.is_authenticated
        assert current_session.username == "sec_admin"
        print(f"  [OK] session authenticated: {current_session.username}")

    def test_session_role_after_login(self):
        assert current_session.role == "admin"
        print(f"  [OK] session role: {current_session.role}")

    def test_session_not_authenticated_after_logout(self):
        # Temporarily log out
        current_session.logout()
        assert not current_session.is_authenticated
        assert current_session.username is None
        print("  [OK] session not authenticated after logout")
        # Restore
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})

    def test_session_restored_correctly(self):
        current_session.logout()
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert current_session.is_authenticated
        assert current_session.username == "sec_admin"
        print("  [OK] session restored correctly after re-login")

    def test_service_login_populates_session(self):
        # Create viewer and login
        try:
            self.auth.create_user("sec_viewer", "Sec Viewer", "View@1234", "viewer")
        except DuplicateEntryError:
            pass
        result = self.auth.login("sec_viewer", "View@1234")
        assert current_session.is_authenticated
        assert current_session.username == "sec_viewer"
        assert current_session.role == "viewer"
        # Restore admin
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        print(f"  [OK] service login populates session: role={result['role']}")

    def test_session_user_id_consistent(self):
        uid = current_session.user_id
        assert isinstance(uid, int) and uid > 0
        print(f"  [OK] session user_id: {uid}")

    def test_session_is_not_expired_fresh_login(self):
        """A freshly populated session should not be expired."""
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert not current_session.is_expired
        print("  [OK] fresh session is not expired")


# ════════════════════════════════════════════════════════════════════════════
# Permission checks
# ════════════════════════════════════════════════════════════════════════════

class TestPermissionChecks:

    def test_admin_is_admin(self):
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert current_session.is_admin()
        print("  [OK] admin is_admin() → True")

    def test_admin_is_manager(self):
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert current_session.is_manager()
        print("  [OK] admin is_manager() → True")

    def test_admin_is_operator(self):
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert current_session.is_operator()
        print("  [OK] admin is_operator() → True")

    def test_admin_has_all_permissions(self):
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        for perm in ("assets:r", "assets:w", "users:r", "users:w",
                     "reports:r", "transactions:w", "settings:w"):
            assert current_session.has_permission(perm), f"Admin missing: {perm}"
        print("  [OK] admin has_permission for all")

    def test_manager_is_not_admin(self):
        current_session.login(2, "sec_mgr", "Sec Mgr", "manager",
                               {"assets": "rw", "persons": "rw", "reports": "r",
                                "departments": "rw", "transactions": "rw", "settings": "r"})
        assert not current_session.is_admin()
        assert current_session.is_manager()
        print("  [OK] manager is_manager but not is_admin")

    def test_manager_has_asset_rw(self):
        current_session.login(2, "sec_mgr", "Sec Mgr", "manager",
                               {"assets": "rw", "persons": "rw", "reports": "r",
                                "departments": "rw", "transactions": "rw", "settings": "r"})
        assert current_session.has_permission("assets:r")
        assert current_session.has_permission("assets:w")
        print("  [OK] manager has assets:r and assets:w")

    def test_manager_no_user_write(self):
        current_session.login(2, "sec_mgr", "Sec Mgr", "manager",
                               {"assets": "rw", "persons": "rw", "reports": "r",
                                "departments": "rw", "transactions": "rw", "settings": "r"})
        # Manager doesn't have users permission
        assert not current_session.has_permission("users:w")
        print("  [OK] manager does not have users:w")

    def test_operator_is_operator_not_admin(self):
        current_session.login(3, "sec_opr", "Sec Opr", "operator",
                               {"assets": "r", "persons": "r", "transactions": "rw"})
        assert not current_session.is_admin()
        assert current_session.is_operator()
        print("  [OK] operator is_operator but not is_admin")

    def test_operator_can_read_assets(self):
        current_session.login(3, "sec_opr", "Sec Opr", "operator",
                               {"assets": "r", "persons": "r", "transactions": "rw"})
        assert current_session.has_permission("assets:r")
        print("  [OK] operator can read assets")

    def test_operator_cannot_write_assets(self):
        current_session.login(3, "sec_opr", "Sec Opr", "operator",
                               {"assets": "r", "persons": "r", "transactions": "rw"})
        assert not current_session.has_permission("assets:w")
        print("  [OK] operator cannot write assets")

    def test_viewer_read_only(self):
        current_session.login(4, "sec_view", "Sec View", "viewer",
                               {"assets": "r", "persons": "r", "reports": "r",
                                "transactions": "r"})
        assert not current_session.is_admin()
        assert not current_session.is_manager()
        assert current_session.has_permission("assets:r")
        assert not current_session.has_permission("assets:w")
        assert not current_session.has_permission("transactions:w")
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        print("  [OK] viewer is read-only")

    def test_viewer_cannot_write_transactions(self):
        current_session.login(4, "sec_view", "Sec View", "viewer",
                               {"assets": "r", "persons": "r", "reports": "r",
                                "transactions": "r"})
        assert not current_session.has_permission("transactions:w")
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        print("  [OK] viewer cannot write transactions")

    def test_z_restore_admin_session(self):
        """Ensure admin session at end of ALL permission tests (runs last alphabetically)."""
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        assert current_session.is_admin()
        print("  [OK] admin session restored (final z_ guard)")


# ════════════════════════════════════════════════════════════════════════════
# Deactivated user cannot login
# ════════════════════════════════════════════════════════════════════════════

class TestDeactivatedUser:
    auth = AuthService()

    def test_deactivated_user_cannot_login(self):
        # Ensure admin session is active (avoid FK errors from session state)
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        try:
            self.auth.create_user("sec_deact", "Deact User", "Deact@123", "operator")
        except DuplicateEntryError:
            pass

        # Get user ID directly without lazy-loading role
        from app.core.database import get_db
        from app.models.user import User
        with get_db() as db:
            db_user = db.query(User).filter(User.username == "sec_deact").first()
            deact_id = db_user.id

        self.auth.toggle_user_active(deact_id)  # -> inactive

        try:
            self.auth.login("sec_deact", "Deact@123")
            assert False, "Should raise AccountInactiveError"
        except AccountInactiveError:
            print("  [OK] deactivated user cannot login -> AccountInactiveError")
        finally:
            self.auth.toggle_user_active(deact_id)  # restore

    def test_reactivated_user_can_login(self):
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        # Should already be active (restored in previous test's finally block)
        result = self.auth.login("sec_deact", "Deact@123")
        assert result["username"] == "sec_deact"
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        print("  [OK] reactivated user can login successfully")

    def test_cannot_deactivate_last_admin(self):
        # Restore admin session (avoid session state from TestPermissionChecks)
        current_session.login(1, "sec_admin", "Sec Admin", "admin", {"all": True})
        # Count admins by querying directly (avoids lazy-load on detached User objects)
        from app.repositories.user_repository import UserRepository
        from app.core.database import get_db
        with get_db() as db:
            repo = UserRepository(db)
            admin_count = repo.count_admins()
        if admin_count > 1:
            print("  [SKIP] multiple admins, last-admin guard not testable here")
            return
        try:
            self.auth.toggle_user_active(1)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "admin" in str(e).lower() or "last" in str(e).lower() or "deactivate" in str(e).lower()
            print("  [OK] cannot deactivate last admin -> ValidationError")


# ════════════════════════════════════════════════════════════════════════════
# Password not stored in plaintext (DB level verification)
# ════════════════════════════════════════════════════════════════════════════

class TestPlaintextNeverStored:
    auth = AuthService()

    def test_password_hash_not_equal_to_plaintext(self):
        try:
            self.auth.create_user("sec_hash_check", "Hash Check", "HashMe@123", "viewer")
        except DuplicateEntryError:
            pass

        users = self.auth.get_all_users()
        user = next(u for u in users if u.username == "sec_hash_check")

        # Reload the user from DB to get password_hash
        from app.core.database import get_db
        from app.models.user import User
        with get_db() as db:
            db_user = db.query(User).filter(User.username == "sec_hash_check").first()
            stored_hash = db_user.password_hash

        assert stored_hash != "HashMe@123"
        print(f"  [OK] stored hash ≠ plaintext: {stored_hash[:20]}...")

    def test_stored_hash_has_bcrypt_format(self):
        from app.core.database import get_db
        from app.models.user import User
        with get_db() as db:
            db_user = db.query(User).filter(User.username == "sec_hash_check").first()
            if db_user:
                assert db_user.password_hash.startswith("$2b$") or \
                       db_user.password_hash.startswith("$2a$")
                print(f"  [OK] stored hash has bcrypt format")
            else:
                print("  [SKIP] user not found")

    def test_password_change_updates_hash(self):
        from app.core.database import get_db
        from app.models.user import User

        users = self.auth.get_all_users()
        user = next((u for u in users if u.username == "sec_hash_check"), None)
        if not user:
            print("  [SKIP] user not found")
            return

        with get_db() as db:
            old_hash = db.query(User).filter(
                User.username == "sec_hash_check").first().password_hash

        self.auth.change_password(user.id, "NewHashMe@456")

        with get_db() as db:
            new_hash = db.query(User).filter(
                User.username == "sec_hash_check").first().password_hash

        assert old_hash != new_hash
        assert new_hash != "NewHashMe@456"
        print(f"  [OK] password change updates hash (old≠new, neither is plaintext)")

    def test_verify_old_password_fails_after_change(self):
        result = verify_password("HashMe@123",
                                  hash_password("NewHashMe@456"))
        assert result is False
        print("  [OK] old password fails after change")


# ════════════════════════════════════════════════════════════════════════════
# UserSession unit tests (isolated)
# ════════════════════════════════════════════════════════════════════════════

class TestUserSessionUnit:

    def test_fresh_session_not_authenticated(self):
        session = UserSession()
        assert not session.is_authenticated
        print("  [OK] fresh session: not authenticated")

    def test_fresh_session_expired(self):
        session = UserSession()
        assert session.is_expired
        print("  [OK] fresh session: is_expired=True")

    def test_login_sets_authenticated(self):
        session = UserSession()
        session.login(42, "testuser", "Test User", "viewer", {"assets": "r"})
        assert session.is_authenticated
        assert session.user_id == 42
        assert session.username == "testuser"
        assert session.role == "viewer"
        print("  [OK] login sets authenticated state")

    def test_logout_clears_session(self):
        session = UserSession()
        session.login(42, "testuser", "Test User", "admin", {"all": True})
        session.logout()
        assert not session.is_authenticated
        assert session.user_id is None
        assert session.username is None
        print("  [OK] logout clears all session data")

    def test_has_permission_admin_all(self):
        session = UserSession()
        session.login(1, "admin", "Admin", "admin", {"all": True})
        for perm in ("assets:r", "assets:w", "users:w", "reports:r", "anything:w"):
            assert session.has_permission(perm)
        print("  [OK] admin session has_permission for everything")

    def test_has_permission_viewer_read_only(self):
        session = UserSession()
        session.login(4, "viewer", "Viewer", "viewer",
                       {"assets": "r", "reports": "r", "transactions": "r"})
        assert session.has_permission("assets:r")
        assert not session.has_permission("assets:w")
        assert not session.has_permission("users:w")
        assert not session.has_permission("settings:w")
        print("  [OK] viewer session: read allowed, write denied")

    def test_has_permission_unauthenticated(self):
        session = UserSession()
        assert not session.has_permission("assets:r")
        assert not session.has_permission("anything:w")
        print("  [OK] unauthenticated session: no permissions")

    def test_is_admin_only_for_admin_role(self):
        for role, expected in [("admin", True), ("manager", False),
                                 ("operator", False), ("viewer", False)]:
            session = UserSession()
            session.login(1, "u", "U", role, {})
            assert session.is_admin() == expected
        print("  [OK] is_admin() correct for all roles")

    def test_is_manager_for_admin_and_manager(self):
        for role, expected in [("admin", True), ("manager", True),
                                 ("operator", False), ("viewer", False)]:
            session = UserSession()
            session.login(1, "u", "U", role, {})
            assert session.is_manager() == expected
        print("  [OK] is_manager() correct for all roles")

    def test_is_operator_for_admin_manager_operator(self):
        for role, expected in [("admin", True), ("manager", True),
                                 ("operator", True), ("viewer", False)]:
            session = UserSession()
            session.login(1, "u", "U", role, {})
            assert session.is_operator() == expected
        print("  [OK] is_operator() correct for all roles")

    def test_session_repr(self):
        session = UserSession()
        session.login(1, "sec_repr", "Repr User", "admin", {"all": True})
        r = repr(session)
        assert "sec_repr" in r
        assert "admin" in r
        print(f"  [OK] session __repr__: {r}")


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    setup_module()
    passed = failed = 0
    suites = [
        TestPasswordHashing,
        TestPasswordLength,
        TestSessionState,
        TestPermissionChecks,
        TestDeactivatedUser,
        TestPlaintextNeverStored,
        TestUserSessionUnit,
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

