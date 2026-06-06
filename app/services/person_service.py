"""
Sanchay — Person Service
==========================
Business logic for employee, student, contractor, and candidate management.
"""

import re
from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session, require_authenticated
from app.core.exceptions import (
    ValidationError, DuplicateEntryError, NotFoundError,
)
from app.models.person import Person
from app.models.audit import AuditLog
from app.repositories.person_repository import PersonRepository
from app.constants import PersonType, PersonStatus, AuditAction


# ── Validation patterns ────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PHONE_RE = re.compile(r'^[\d\s\+\-\(\)\.]{6,20}$')


def _validate_email(email: str) -> None:
    """Raise ValidationError if email format is invalid."""
    if email and not EMAIL_RE.match(email):
        raise ValidationError(
            f"The email address '{email}' doesn't look right. "
            "Please use a format like user@example.com.",
            "email",
        )


def _validate_phone(phone: str) -> None:
    """Raise ValidationError if phone contains unexpected characters."""
    if phone and not PHONE_RE.match(phone):
        raise ValidationError(
            f"Phone number '{phone}' contains invalid characters. "
            "Use digits, spaces, +, -, (, ), or . only (6–20 characters).",
            "phone",
        )


def _validate_name(value: str, field: str) -> str:
    """Strip, check length, reject pure-whitespace. Returns stripped value."""
    value = value.strip()
    if not value:
        raise ValidationError(
            f"'{field.replace('_', ' ').title()}' cannot be blank.", field
        )
    if len(value) > 100:
        raise ValidationError(
            f"'{field.replace('_', ' ').title()}' must be 100 characters or fewer.", field
        )
    return value


class PersonService:
    """Business logic for person (employee / student / contractor) management."""

    def get_all(self, org_id: Optional[int] = None, person_type: Optional[str] = None) -> list[Person]:
        """Return all persons, optionally filtered by org and type."""
        with get_db() as db:
            repo = PersonRepository(db)
            if org_id:
                return repo.get_by_org(org_id, person_type)
            return repo.get_all()

    def get_active(self, org_id: int) -> list[Person]:
        """Return all active persons for an organisation."""
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.get_active_by_org(org_id)

    def get_by_id(self, person_id: int) -> Person:
        """Return a person by ID, raising NotFoundError if absent."""
        with get_db() as db:
            repo = PersonRepository(db)
            p = repo.get_by_id(person_id)
            if not p:
                raise NotFoundError("Person", str(person_id))
            return p

    def get_by_department(self, dept_id: int) -> list[Person]:
        """Return all persons belonging to the given department."""
        logger.debug(f"Fetching persons for dept_id={dept_id}")
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.get_by_department(dept_id)

    def search(self, **kwargs) -> tuple[list[Person], int]:
        """Search persons with arbitrary filter kwargs. Returns (results, total)."""
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.search(**kwargs)

    def create(
        self,
        org_id: int,
        first_name: str,
        person_type: str = "employee",
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        dept_id: Optional[int] = None,
        designation: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        date_of_joining=None,
        date_of_leaving=None,
        id_proof_type: Optional[str] = None,
        id_proof_number: Optional[str] = None,
        notes: Optional[str] = None,
        person_id_code: Optional[str] = None,
    ) -> Person:
        """Create a new person record with full validation.

        Requires: authenticated session.
        """
        require_authenticated()

        # Sanitize optional text fields
        if designation is not None:
            designation = designation.strip()[:150] or None
        if address is not None:
            address = address.strip()[:500] or None
        if id_proof_number is not None:
            id_proof_number = id_proof_number.strip()[:50] or None
        if notes is not None:
            notes = notes.strip()[:2000] or None

        # Validate and clean names
        first_name = _validate_name(first_name, "first_name")
        if last_name is not None:
            last_name = last_name.strip()
            if last_name:
                last_name = _validate_name(last_name, "last_name")
            else:
                last_name = None

        if person_type not in [t.value for t in PersonType]:
            raise ValidationError(
                f"Person type '{person_type}' is not valid. "
                "Choose from: employee, student, contractor, candidate.",
                "person_type",
            )

        # Validate email and phone
        if email:
            email = email.strip()
            _validate_email(email)

        if phone:
            phone = phone.strip()
            _validate_phone(phone)

        # Validate joining/leaving dates
        if date_of_joining and date_of_leaving:
            if date_of_leaving < date_of_joining:
                raise ValidationError(
                    "Date of leaving must be on or after the date of joining.",
                    "date_of_leaving",
                )

        logger.debug(f"Creating person '{first_name}' ({person_type}) in org {org_id}")

        with get_db() as db:
            repo = PersonRepository(db)

            # Auto-generate person code
            if not person_id_code:
                person_id_code = repo.generate_next_code(person_type, org_id)

            if repo.code_exists(person_id_code):
                raise DuplicateEntryError("Person", "ID code", person_id_code)

            person = Person(
                org_id=org_id,
                dept_id=dept_id,
                person_type=person_type,
                person_id_code=person_id_code,
                first_name=first_name,
                last_name=last_name,
                email=email or None,
                phone=phone or None,
                designation=designation,
                address=address,
                city=city,
                state=state,
                date_of_joining=date_of_joining,
                id_proof_type=id_proof_type,
                id_proof_number=id_proof_number,
                notes=notes,
                status=PersonStatus.ACTIVE.value,
            )
            repo.create(person)
            self._audit(db, AuditAction.CREATE, "persons", person.id,
                        description=f"{person_type.capitalize()} '{person.full_name}' "
                                    f"({person_id_code}) created.")
            logger.info(f"Person '{person.full_name}' created.")
            return person

    def update(self, person_id: int, data: dict) -> Person:
        """Update fields of an existing person record.

        Requires: authenticated session.
        """
        require_authenticated()

        # Sanitize optional text fields in payload
        if "designation" in data and data["designation"] is not None:
            data["designation"] = data["designation"].strip()[:150] or None
        if "address" in data and data["address"] is not None:
            data["address"] = data["address"].strip()[:500] or None
        if "id_proof_number" in data and data["id_proof_number"] is not None:
            data["id_proof_number"] = data["id_proof_number"].strip()[:50] or None
        if "notes" in data and data["notes"] is not None:
            data["notes"] = data["notes"].strip()[:2000] or None

        # Validate names in update payload
        for name_field in ("first_name", "last_name"):
            if name_field in data and data[name_field] is not None:
                data[name_field] = _validate_name(data[name_field], name_field)

        if "email" in data and data["email"]:
            data["email"] = data["email"].strip()
            _validate_email(data["email"])

        if "phone" in data and data["phone"]:
            data["phone"] = data["phone"].strip()
            _validate_phone(data["phone"])

        with get_db() as db:
            repo = PersonRepository(db)
            person = repo.get_by_id(person_id)
            if not person:
                raise NotFoundError("Person", str(person_id))

            # Validate leaving date
            doj = data.get("date_of_joining", person.date_of_joining)
            dol = data.get("date_of_leaving", getattr(person, "date_of_leaving", None))
            if doj and dol and dol < doj:
                raise ValidationError(
                    "Date of leaving must be on or after the date of joining.",
                    "date_of_leaving",
                )

            old = person.to_dict()
            repo.update(person, data)
            self._audit(db, AuditAction.UPDATE, "persons", person_id,
                        old_values=old, description=f"Person '{person.full_name}' updated.")
            return person

    def toggle_status(self, person_id: int) -> str:
        """Toggle between active/inactive. Returns new status.

        Requires: authenticated session.
        """
        require_authenticated()

        with get_db() as db:
            repo = PersonRepository(db)
            person = repo.get_by_id(person_id)
            if not person:
                raise NotFoundError("Person", str(person_id))

            # Check if person has active issues before deactivating
            if person.status == PersonStatus.ACTIVE.value:
                from app.repositories.transaction_repository import TransactionRepository
                txn_repo = TransactionRepository(db)
                active = txn_repo.get_issues_for_person(person_id, status="active")
                if active:
                    raise ValidationError(
                        f"Cannot deactivate '{person.full_name}' — they have "
                        f"{len(active)} active asset issue(s). Return assets first.",
                        "status",
                    )
                person.status = PersonStatus.INACTIVE.value
            else:
                person.status = PersonStatus.ACTIVE.value

            db.flush()
            self._audit(db, AuditAction.UPDATE, "persons", person_id,
                        description=f"Person '{person.full_name}' status → {person.status}.")
            return person.status

    def delete(self, person_id: int) -> None:
        """Soft-delete a person (fails if they have active asset issues).

        Requires: authenticated session.
        """
        require_authenticated()

        with get_db() as db:
            repo = PersonRepository(db)
            person = repo.get_by_id(person_id)
            if not person:
                raise NotFoundError("Person", str(person_id))
            # Check active issues
            from app.repositories.transaction_repository import TransactionRepository
            txn_repo = TransactionRepository(db)
            active = txn_repo.get_issues_for_person(person_id, status="active")
            if active:
                raise ValidationError(
                    f"Cannot delete '{person.full_name}' — they have active asset issues. "
                    "Return all assets first.",
                    "person_id",
                )
            repo.delete(person)
            self._audit(db, AuditAction.DELETE, "persons", person_id,
                        description=f"Person '{person.full_name}' deleted.")

    def count_by_type(self, org_id: Optional[int] = None) -> dict:
        """Return a dict of {person_type: count} for dashboard use."""
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.count_by_type(org_id)

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
