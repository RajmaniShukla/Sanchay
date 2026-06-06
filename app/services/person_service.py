"""
Sanchay — Person Service
==========================
Business logic for employee, student, contractor, and candidate management.
"""

from typing import Optional
from loguru import logger

from app.core.database import get_db
from app.core.security import current_session
from app.core.exceptions import (
    ValidationError, DuplicateEntryError, NotFoundError,
)
from app.models.person import Person
from app.models.audit import AuditLog
from app.repositories.person_repository import PersonRepository
from app.constants import PersonType, PersonStatus, AuditAction


class PersonService:

    def get_all(self, org_id: Optional[int] = None, person_type: Optional[str] = None) -> list[Person]:
        with get_db() as db:
            repo = PersonRepository(db)
            if org_id:
                return repo.get_by_org(org_id, person_type)
            return repo.get_all()

    def get_active(self, org_id: int) -> list[Person]:
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.get_active_by_org(org_id)

    def get_by_id(self, person_id: int) -> Person:
        with get_db() as db:
            repo = PersonRepository(db)
            p = repo.get_by_id(person_id)
            if not p:
                raise NotFoundError("Person", str(person_id))
            return p

    def search(self, **kwargs) -> tuple[list[Person], int]:
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
        id_proof_type: Optional[str] = None,
        id_proof_number: Optional[str] = None,
        notes: Optional[str] = None,
        person_id_code: Optional[str] = None,
    ) -> Person:
        if not first_name or not first_name.strip():
            raise ValidationError("First name is required.", "first_name")
        if person_type not in [t.value for t in PersonType]:
            raise ValidationError(f"Invalid person type: {person_type}", "person_type")

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
                first_name=first_name.strip(),
                last_name=last_name.strip() if last_name else None,
                email=email.strip() if email else None,
                phone=phone,
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
        with get_db() as db:
            repo = PersonRepository(db)
            person = repo.get_by_id(person_id)
            if not person:
                raise NotFoundError("Person", str(person_id))
            old = person.to_dict()
            repo.update(person, data)
            self._audit(db, AuditAction.UPDATE, "persons", person_id,
                        old_values=old, description=f"Person '{person.full_name}' updated.")
            return person

    def toggle_status(self, person_id: int) -> str:
        """Toggle between active/inactive. Returns new status."""
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
                    f"Cannot delete '{person.full_name}' — they have active asset issues.",
                    "person_id",
                )
            repo.delete(person)
            self._audit(db, AuditAction.DELETE, "persons", person_id,
                        description=f"Person '{person.full_name}' deleted.")

    def count_by_type(self, org_id: Optional[int] = None) -> dict:
        with get_db() as db:
            repo = PersonRepository(db)
            return repo.count_by_type(org_id)

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
