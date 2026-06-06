"""
Sanchay — Organization Service
=================================
Business logic for organization and department management.
"""

import re
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session, require_authenticated
from app.core.exceptions import ValidationError, DuplicateEntryError, NotFoundError
from app.core.validators import validate_email, validate_phone
from app.models.organization import Organization, Department
from app.models.audit import AuditLog
from app.repositories.organization_repository import OrganizationRepository, DepartmentRepository
from app.constants import OrgType, AuditAction


# ── Validation patterns ────────────────────────────────────────────────────────

ORG_CODE_RE  = re.compile(r'^[A-Z0-9][A-Z0-9_\-]{1,9}$')  # 2-10, alphanumeric + dash/underscore
DEPT_CODE_RE = re.compile(r'^[A-Z0-9_\-]{2,20}$')    # 2-20, alphanumeric + dash/underscore


def _validate_org_code(code: str) -> None:
    """Raise ValidationError if org code format is invalid."""
    if not ORG_CODE_RE.match(code):
        raise ValidationError(
            f"Organisation code '{code}' is invalid. "
            "Use 2–10 uppercase letters or digits only (no spaces or special characters).",
            "code",
        )


def _validate_dept_code(code: str) -> None:
    """Raise ValidationError if department code format is invalid."""
    if not DEPT_CODE_RE.match(code):
        raise ValidationError(
            f"Department code '{code}' is invalid. "
            "Use 2–20 uppercase letters, digits, hyphens (-), or underscores (_).",
            "code",
        )


class OrganizationService:
    """Business logic for organisation management."""

    def get_all(self, active_only: bool = True) -> list[Organization]:
        """Return all organisations. Pass active_only=False to include inactive."""
        with get_db() as db:
            repo = OrganizationRepository(db)
            return repo.get_active() if active_only else repo.get_all()

    def get_by_id(self, org_id: int) -> Organization:
        """Return an organisation by ID, raising NotFoundError if absent."""
        with get_db() as db:
            repo = OrganizationRepository(db)
            org = repo.get_by_id(org_id)
            if not org:
                raise NotFoundError("Organization", str(org_id))
            return org

    def get_department_count(self, org_id: int) -> int:
        """Return the number of active departments in the given organisation."""
        logger.debug(f"Counting departments for org_id={org_id}")
        with get_db() as db:
            repo = DepartmentRepository(db)
            depts = repo.get_by_org(org_id)
            return len(depts)

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
        """Create a new organisation with validated code and name.

        Requires: authenticated session.
        """
        require_authenticated()

        name = name.strip()
        code = code.strip().upper()

        if not name or len(name) < 2:
            raise ValidationError(
                "Organisation name must be at least 2 characters long.", "name"
            )
        if not code:
            raise ValidationError("Organisation code is required.", "code")

        _validate_org_code(code)

        # Validate contact fields
        if email:
            email = validate_email(email, "email")
        if phone:
            phone = validate_phone(phone, "phone")
        if website:
            website = website.strip()
            if website and not (website.startswith("http://") or website.startswith("https://")):
                raise ValidationError(
                    "Website URL must start with http:// or https://.", "website"
                )
        if description:
            description = description.strip()[:2000] or None

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
        """Update an existing organisation.

        Requires: authenticated session.
        """
        require_authenticated()

        # Validate contact fields in update payload
        if "email" in data and data["email"]:
            data["email"] = validate_email(data["email"], "email")
        if "phone" in data and data["phone"]:
            data["phone"] = validate_phone(data["phone"], "phone")
        if "website" in data and data["website"]:
            ws = data["website"].strip()
            if ws and not (ws.startswith("http://") or ws.startswith("https://")):
                raise ValidationError(
                    "Website URL must start with http:// or https://.", "website"
                )
            data["website"] = ws
        if "description" in data and data["description"]:
            data["description"] = data["description"].strip()[:2000] or None

        with get_db() as db:
            repo = OrganizationRepository(db)
            org = repo.get_by_id(org_id)
            if not org:
                raise NotFoundError("Organization", str(org_id))
            if "name" in data:
                data["name"] = data["name"].strip()
                if len(data["name"]) < 2:
                    raise ValidationError(
                        "Organisation name must be at least 2 characters long.", "name"
                    )
            if "code" in data:
                data["code"] = data["code"].strip().upper()
                _validate_org_code(data["code"])
                if repo.code_exists(data["code"], exclude_id=org_id):
                    raise DuplicateEntryError("Organization", "code", data["code"])
            old = org.to_dict()
            repo.update(org, data)
            self._audit(db, AuditAction.UPDATE, "organizations", org_id,
                        old_values=old, description=f"Organization '{org.name}' updated.")
            return org

    def delete(self, org_id: int) -> None:
        """Soft-delete an organisation.

        Requires: authenticated session.
        """
        require_authenticated()

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
        """Write an audit log entry within the current DB session."""
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
    """Business logic for department management."""

    def get_by_org(self, org_id: int) -> list[Department]:
        """Return all departments for an organisation."""
        with get_db() as db:
            repo = DepartmentRepository(db)
            return repo.get_by_org(org_id)

    def get_by_id(self, dept_id: int) -> Department:
        """Return a department by ID, raising NotFoundError if absent."""
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
        """Create a new department with validated code."""
        name = name.strip()
        code = code.strip().upper()

        if not name:
            raise ValidationError("Department name is required.", "name")
        if not code:
            raise ValidationError("Department code is required.", "code")

        _validate_dept_code(code)

        logger.debug(f"Creating department '{name}' ({code}) in org {org_id}")

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
        """Update an existing department."""
        with get_db() as db:
            repo = DepartmentRepository(db)
            dept = repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError("Department", str(dept_id))
            if "code" in data:
                data["code"] = data["code"].strip().upper()
                _validate_dept_code(data["code"])
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
        """Soft-delete a department (fails if it has sub-departments)."""
        with get_db() as db:
            repo = DepartmentRepository(db)
            dept = repo.get_by_id(dept_id)
            if not dept:
                raise NotFoundError("Department", str(dept_id))
            children = repo.get_children(dept_id)
            if children:
                raise ValidationError(
                    f"Cannot delete '{dept.name}' — it has {len(children)} sub-department(s). "
                    "Please delete or re-parent them first.",
                    "parent_dept_id",
                )
            repo.delete(dept)
            OrganizationService._audit(
                db, AuditAction.DELETE, "departments", dept_id,
                description=f"Department '{dept.name}' deleted.",
            )
