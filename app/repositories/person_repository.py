"""
Sanchay — Person Repository
=============================
Data access for Person entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models.person import Person
from app.repositories.base_repository import BaseRepository


class PersonRepository(BaseRepository[Person]):
    model = Person

    def get_by_org(self, org_id: int, person_type: Optional[str] = None) -> list[Person]:
        q = self.db.query(Person).filter(
            Person.org_id == org_id, Person.is_deleted == False
        )
        if person_type:
            q = q.filter(Person.person_type == person_type)
        return q.order_by(Person.first_name).all()

    def get_active_by_org(self, org_id: int) -> list[Person]:
        return (
            self.db.query(Person)
            .filter(
                Person.org_id == org_id,
                Person.status == "active",
                Person.is_deleted == False,
            )
            .order_by(Person.first_name)
            .all()
        )

    def get_by_dept(self, dept_id: int) -> list[Person]:
        return (
            self.db.query(Person)
            .filter(Person.dept_id == dept_id, Person.is_deleted == False)
            .order_by(Person.first_name)
            .all()
        )

    def get_by_code(self, code: str) -> Optional[Person]:
        return (
            self.db.query(Person)
            .filter(Person.person_id_code == code, Person.is_deleted == False)
            .first()
        )

    def search(
        self,
        query: str,
        org_id: Optional[int] = None,
        person_type: Optional[str] = None,
        status: Optional[str] = None,
        dept_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Person], int]:
        """Search persons. Returns (results, total_count)."""
        q = self.db.query(Person).filter(Person.is_deleted == False)

        if query:
            pattern = f"%{query}%"
            q = q.filter(
                or_(
                    Person.first_name.ilike(pattern),
                    Person.last_name.ilike(pattern),
                    Person.email.ilike(pattern),
                    Person.phone.ilike(pattern),
                    Person.person_id_code.ilike(pattern),
                    Person.designation.ilike(pattern),
                )
            )
        if org_id:
            q = q.filter(Person.org_id == org_id)
        if person_type:
            q = q.filter(Person.person_type == person_type)
        if status:
            q = q.filter(Person.status == status)
        if dept_id:
            q = q.filter(Person.dept_id == dept_id)

        total = q.count()
        results = q.order_by(Person.first_name).offset(offset).limit(limit).all()
        return results, total

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Person).filter(
            Person.person_id_code == code, Person.is_deleted == False
        )
        if exclude_id:
            q = q.filter(Person.id != exclude_id)
        return q.count() > 0

    def generate_next_code(self, person_type: str, org_id: int) -> str:
        """Generate next sequential person ID code."""
        prefixes = {
            "employee": "EMP", "student": "STU",
            "contractor": "CON", "candidate": "CAN",
        }
        prefix = prefixes.get(person_type, "PER")
        last = (
            self.db.query(Person)
            .filter(
                Person.org_id == org_id,
                Person.person_id_code.like(f"{prefix}-%"),
            )
            .order_by(Person.id.desc())
            .first()
        )
        if last and last.person_id_code:
            try:
                num = int(last.person_id_code.split("-")[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"{prefix}-{num:04d}"

    def count_by_type(self, org_id: Optional[int] = None) -> dict:
        q = self.db.query(Person.person_type, func.count(Person.id)).filter(
            Person.is_deleted == False, Person.status == "active"
        )
        if org_id:
            q = q.filter(Person.org_id == org_id)
        rows = q.group_by(Person.person_type).all()
        return {row[0]: row[1] for row in rows}
