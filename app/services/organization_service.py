"""
Sanchay — Organization Service
=================================
Business logic for organization and department management.
"""

from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session
from app.core.exceptions import ValidationError, DuplicateEntryError, NotFoundError
from app.models.organization import Organization, Department
from app.models.audit import AuditLog
from app.repositories.organization_repository import OrganizationRepository, DepartmentRepository
from app.constants import OrgType, AuditAction


class OrganizationService:

    def get_all(self, active_only: bool = True) -> list[Organization]:
        with get_db() as db:
            repo = OrganizationRepository(db)
            return repo.get_active() if active_only else repo.get_all()

    def get_by_id(self, org_id: int) -> Organization:
        with get_db() as db:
            repo = OrganizationRepository(db)
            org = repo.get_by_id(org_id)
            if not org:
                raise NotFoundError("Organization", str(org_id))
            return org

    def create(
        self,
        name: str,
        code: str,
        org_type: str = "office",
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
        country: str = "India",
        phone: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Organization:
        name = name.strip()
        code = code.strip().upper()

        if not name:
            raise ValidationError("Organization name is required.", "name")
        if not code:
            raise ValidationError("Organization code is required.", "code")

        with get_db() as db:
            repo = OrganizationRepository(db)
            if repo.code_exists(code):
                raise DuplicateEntryError("Organization", "code", code)

            org = Organization(
                name=name, code=code, org_type=org_type,
                address=address, city=city, state=state,
                pincode=pincode, country=country,
                phone=phone, email=email, website=website,
                description=description, is_active=True,
            )
            repo.create(org)
            self._audit(db, AuditAction.CREATE, "organizations", org.id,
                        description=f"Organization '{name}' ({code}) created.")
            logger.info(f"Organization '{name}' created.")
            return org

    def update(self, org_id: int, data: dict) -> Organization:
        with get_db() as db:
            repo = OrganizationRepository(db)
            org = repo.get_by_id(org_id)
            if not org:
                raise NotFoundError("Organization", str(org_id))
            if "code" in data:
                data["code"] = data["code"].strip().upper()
                if repo.code_exists(data["code"], exclude_id=org_id):
                    raise DuplicateEntryError("Organization", "code", data["code"])
            old = org.to_dict()
            repo.update(org, data)
            self._audit(db, AuditAction.UPDATE, "organizations", org_id,
                        old_values=old, description=f"Organization '{org.name}' updated.")
            return org

    def delete(self, org_id: int) -> None:
        with get_db() as db:
            repo = OrganizationRepository(db)
            org = repo.get_by_id(org_id)
            if not org:
                raise NotFoundError("Organization", str(org_id))
            repo.delete(org)
            self._audit(db, AuditAction.DELETE, "organizations", org_id,
                        description=f"Organization '{org.name}' deleted.")

    @staticmethod
    def _audit(db, action, module, record_id, old_values=None, description=""):
        import json
        log = AuditLog(
            user_id=current_session.user_id,
            action=action.value,
            module=module,
            table_name=module,
            record_id=record_id,
            old_values_json=json.dumps(old_values) if old_values else None,
            description=description,
        )
        db.add(log)
        db.flush()


class DepartmentService:

    def get_by_org(self, org_id: int) -> list[Department]:
        with get_db() as db:
            repo = DepartmentRepository(db)
            return repo.get_by_org(org_id)

    def get_by_id(self, dept_id: int) -> Department:
        with get_db() as db:
            repo = DepartmentRepository(db)
            dept = repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError("Department", str(dept_id))
            return dept

    def create(
        self,
        org_id: int,
        name: str,
        code: str,
        parent_dept_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Department:
        name = name.strip()
        code = code.strip().upper()

        if not name:
            raise ValidationError("Department name is required.", "name")
        if not code:
            raise ValidationError("Department code is required.", "code")

        with get_db() as db:
            repo = DepartmentRepository(db)
            if repo.code_exists(code, org_id):
                raise DuplicateEntryError("Department", "code", code)

            dept = Department(
                org_id=org_id, name=name, code=code,
                parent_dept_id=parent_dept_id,
                description=description, is_active=True,
            )
            repo.create(dept)
            OrganizationService._audit(
                db, AuditAction.CREATE, "departments", dept.id,
                description=f"Department '{name}' created in org #{org_id}.",
            )
            return dept

    def update(self, dept_id: int, data: dict) -> Department:
        with get_db() as db:
            repo = DepartmentRepository(db)
            dept = repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError("Department", str(dept_id))
            if "code" in data:
                data["code"] = data["code"].strip().upper()
                if repo.code_exists(data["code"], dept.org_id, exclude_id=dept_id):
                    raise DuplicateEntryError("Department", "code", data["code"])
            old = dept.to_dict()
            repo.update(dept, data)
            OrganizationService._audit(
                db, AuditAction.UPDATE, "departments", dept_id, old_values=old,
                description=f"Department '{dept.name}' updated.",
            )
            return dept

    def delete(self, dept_id: int) -> None:
        with get_db() as db:
            repo = DepartmentRepository(db)
            dept = repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError("Department", str(dept_id))
            children = repo.get_children(dept_id)
            if children:
                raise ValidationError(
                    f"Cannot delete '{dept.name}' — it has {len(children)} sub-department(s).",
                    "parent_dept_id",
                )
            repo.delete(dept)
            OrganizationService._audit(
                db, AuditAction.DELETE, "departments", dept_id,
                description=f"Department '{dept.name}' deleted.",
            )
