"""
Sanchay — Phase 2 Integration Tests
======================================
Tests org, dept, and person CRUD flows end-to-end through the service layer.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import config
config.DB_PATH = config.DATA_DIR / "test_phase2.db"
config.DB_URL  = f"sqlite:///{config.DB_PATH}"

import pytest
from app.core.database import init_db, _engine, _SessionFactory

# Reset singletons for test DB
import app.core.database as _db_mod
_db_mod._engine = None
_db_mod._SessionFactory = None

from app.core.security import current_session
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService, DepartmentService
from app.services.person_service import PersonService
from app.core.exceptions import (
    DuplicateEntryError, NotFoundError, ValidationError,
)


def setup_module():
    config.init_directories()
    init_db()
    auth = AuthService()
    auth.seed_default_roles()
    try:
        auth.create_user("testadmin", "Test Admin", "Admin@123", "admin")
    except Exception:
        pass
    current_session.login(1, "testadmin", "Test Admin", "admin", {"all": True})


def teardown_module():
    # Dispose engine to release SQLite file lock before deleting
    import app.core.database as _db_mod
    if _db_mod._engine:
        _db_mod._engine.dispose()
        _db_mod._engine = None
        _db_mod._SessionFactory = None
    import time; time.sleep(0.2)
    if config.DB_PATH.exists():
        try:
            config.DB_PATH.unlink()
        except PermissionError:
            pass  # Windows sometimes holds lock briefly; skip cleanup


# ── Organization Tests ────────────────────────────────────────────────────────

class TestOrganization:
    svc = OrganizationService()

    def test_create_org(self):
        org = self.svc.create(name="Test Corp", code="TC01", org_type="industry", city="Mumbai")
        assert org.id is not None
        assert org.code == "TC01"
        print(f"  [OK] Created org: {org.name} (id={org.id})")

    def test_duplicate_code_raises(self):
        with pytest.raises(DuplicateEntryError):
            self.svc.create(name="Another Corp", code="TC01")
        print("  [OK] Duplicate code raises DuplicateEntryError")

    def test_get_all(self):
        orgs = self.svc.get_all()
        assert len(orgs) >= 1
        print(f"  [OK] get_all: {len(orgs)} org(s)")

    def test_update_org(self):
        org = self.svc.get_all()[0]
        updated = self.svc.update(org.id, {"city": "Delhi", "phone": "+91-9999999999"})
        assert updated.city == "Delhi"
        print(f"  [OK] Updated org city to Delhi")

    def test_get_by_id_notfound(self):
        with pytest.raises(NotFoundError):
            self.svc.get_by_id(99999)
        print("  [OK] NotFoundError for unknown id")


# ── Department Tests ──────────────────────────────────────────────────────────

class TestDepartment:
    svc     = DepartmentService()
    org_svc = OrganizationService()

    def _get_org_id(self):
        return self.org_svc.get_all()[0].id

    def test_a_create_dept(self):
        org_id = self._get_org_id()
        dept = self.svc.create(org_id=org_id, name="Engineering", code="ENG")
        assert dept.id is not None
        assert dept.code == "ENG"
        print(f"  [OK] Created dept: {dept.name} (id={dept.id})")

    def test_b_create_child_dept(self):
        org_id   = self._get_org_id()
        depts    = self.svc.get_by_org(org_id)
        parent   = next(d for d in depts if d.code == "ENG")
        child    = self.svc.create(org_id=org_id, name="Backend Team",
                                   code="BE", parent_dept_id=parent.id)
        assert child.parent_dept_id == parent.id
        print(f"  [OK] Child dept '{child.name}' under '{parent.name}'")

    def test_duplicate_code_raises(self):
        org_id = self._get_org_id()
        with pytest.raises(DuplicateEntryError):
            self.svc.create(org_id=org_id, name="Eng Dup", code="ENG")
        print("  [OK] Duplicate dept code raises DuplicateEntryError")

    def test_get_by_org(self):
        org_id = self._get_org_id()
        depts  = self.svc.get_by_org(org_id)
        assert len(depts) >= 2
        print(f"  [OK] get_by_org: {len(depts)} dept(s)")

    def test_update_dept(self):
        org_id = self._get_org_id()
        dept   = self.svc.get_by_org(org_id)[0]
        updated = self.svc.update(dept.id, {"description": "Core engineering team"})
        assert updated.description == "Core engineering team"
        print(f"  [OK] Updated dept description")

    def test_c_delete_child_dept(self):
        org_id = self._get_org_id()
        child  = next(d for d in self.svc.get_by_org(org_id) if d.code == "BE")
        self.svc.delete(child.id)
        remaining = self.svc.get_by_org(org_id)
        assert not any(d.code == "BE" for d in remaining)
        print(f"  [OK] Child dept deleted")

    def test_delete_parent_with_children_raises(self):
        org_id = self._get_org_id()
        # Re-create child first
        parent = next(d for d in self.svc.get_by_org(org_id) if d.code == "ENG")
        self.svc.create(org_id=org_id, name="QA Team", code="QA",
                        parent_dept_id=parent.id)
        with pytest.raises(ValidationError):
            self.svc.delete(parent.id)
        print("  [OK] Deleting parent with children raises ValidationError")


# ── Person Tests ──────────────────────────────────────────────────────────────

class TestPerson:
    svc     = PersonService()
    org_svc = OrganizationService()
    dept_svc = DepartmentService()

    def _get_org_id(self):
        return self.org_svc.get_all()[0].id

    def _get_dept_id(self):
        org_id = self._get_org_id()
        depts  = self.dept_svc.get_by_org(org_id)
        return depts[0].id if depts else None

    def test_create_employee(self):
        p = self.svc.create(
            org_id=self._get_org_id(),
            first_name="Ravi",
            last_name="Sharma",
            person_type="employee",
            dept_id=self._get_dept_id(),
            designation="Senior Engineer",
            phone="+91-9876543210",
        )
        assert p.id is not None
        assert p.full_name == "Ravi Sharma"
        assert p.person_id_code.startswith("EMP-")
        print(f"  [OK] Employee created: {p.full_name} ({p.person_id_code})")

    def test_create_student(self):
        p = self.svc.create(
            org_id=self._get_org_id(),
            first_name="Priya",
            person_type="student",
            designation="B.Tech CSE 3rd Year",
        )
        assert p.person_id_code.startswith("STU-")
        print(f"  [OK] Student created: {p.full_name} ({p.person_id_code})")

    def test_search_by_name(self):
        results, total = self.svc.search(
            query="Ravi", org_id=self._get_org_id()
        )
        assert len(results) >= 1
        assert any(p.first_name == "Ravi" for p in results)
        print(f"  [OK] Search 'Ravi' returned {len(results)} result(s)")

    def test_toggle_status(self):
        p = self.svc.get_all(org_id=self._get_org_id())[0]
        new_status = self.svc.toggle_status(p.id)
        assert new_status == "inactive"
        restored   = self.svc.toggle_status(p.id)
        assert restored == "active"
        print(f"  [OK] Status toggle: active -> inactive -> active")

    def test_update_person(self):
        persons, _ = self.svc.search(query="Ravi", org_id=self._get_org_id())
        p          = persons[0]
        updated    = self.svc.update(p.id, {"designation": "Staff Engineer"})
        assert updated.designation == "Staff Engineer"
        print(f"  [OK] Person designation updated")

    def test_z_count_by_type(self):
        counts = self.svc.count_by_type(self._get_org_id())
        assert "employee" in counts
        print(f"  [OK] count_by_type: {counts}")

    def test_delete_person(self):
        persons, _ = self.svc.search(query="Priya", org_id=self._get_org_id())
        p          = persons[0]
        self.svc.delete(p.id)
        persons2, _ = self.svc.search(query="Priya", org_id=self._get_org_id())
        assert not any(x.first_name == "Priya" for x in persons2)
        print(f"  [OK] Person deleted")


if __name__ == "__main__":
    import traceback
    setup_module()
    suites = [TestOrganization, TestDepartment, TestPerson]
    passed = failed = 0
    for Suite in suites:
        print(f"\n--- {Suite.__name__} ---")
        obj = Suite()
        for name in [m for m in dir(obj) if m.startswith("test_")]:
            try:
                getattr(obj, name)()
                passed += 1
            except Exception as e:
                print(f"  [FAIL] {name}: {e}")
                traceback.print_exc()
                failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    teardown_module()
