"""
Sanchay — Organization & Department Repository
================================================
Data access for Organization and Department entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.organization import Organization, Department
from app.repositories.base_repository import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    def get_active(self) -> list[Organization]:
        return (
            self.db.query(Organization)
            .filter(Organization.is_active == True, Organization.is_deleted == False)
            .order_by(Organization.name)
            .all()
        )

    def get_by_code(self, code: str) -> Optional[Organization]:
        return (
            self.db.query(Organization)
            .filter(Organization.code == code, Organization.is_deleted == False)
            .first()
        )

    def code_exists(self, code: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Organization).filter(
            Organization.code == code, Organization.is_deleted == False
        )
        if exclude_id:
            q = q.filter(Organization.id != exclude_id)
        return q.count() > 0


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    def get_by_org(self, org_id: int, include_inactive: bool = False) -> list[Department]:
        q = self.db.query(Department).filter(
            Department.org_id == org_id, Department.is_deleted == False
        )
        if not include_inactive:
            q = q.filter(Department.is_active == True)
        return q.order_by(Department.name).all()

    def get_root_departments(self, org_id: int) -> list[Department]:
        """Returns top-level departments (no parent)."""
        return (
            self.db.query(Department)
            .filter(
                Department.org_id == org_id,
                Department.parent_dept_id == None,
                Department.is_deleted == False,
                Department.is_active == True,
            )
            .order_by(Department.name)
            .all()
        )

    def get_children(self, parent_dept_id: int) -> list[Department]:
        return (
            self.db.query(Department)
            .filter(
                Department.parent_dept_id == parent_dept_id,
                Department.is_deleted == False,
            )
            .order_by(Department.name)
            .all()
        )

    def code_exists(self, code: str, org_id: int, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(Department).filter(
            Department.code == code,
            Department.org_id == org_id,
            Department.is_deleted == False,
        )
        if exclude_id:
            q = q.filter(Department.id != exclude_id)
        return q.count() > 0

    def count_by_org(self, org_id: int) -> int:
        return (
            self.db.query(func.count(Department.id))
            .filter(Department.org_id == org_id, Department.is_deleted == False)
            .scalar() or 0
        )
