"""
Sanchay — User Repository
============================
Data access layer for User and Role entities.
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.repositories.base_repository import BaseRepository


class RoleRepository:
    """Data access for Role entities."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[Role]:
        return self.db.query(Role).all()

    def get_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name).first()

    def get_by_id(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()

    def create(self, role: Role) -> Role:
        self.db.add(role)
        self.db.flush()
        return role


class UserRepository(BaseRepository[User]):
    """Data access for User entities."""

    model = User

    def get_by_username(self, username: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.username == username, User.is_deleted == False)
            .first()
        )

    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email, User.is_deleted == False)
            .first()
        )

    def get_active_users(self) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.is_active == True, User.is_deleted == False)
            .order_by(User.full_name)
            .all()
        )

    def get_by_org(self, org_id: int) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.org_id == org_id, User.is_deleted == False)
            .all()
        )

    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(User).filter(
            User.username == username, User.is_deleted == False
        )
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        return q.count() > 0

    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        q = self.db.query(User).filter(
            User.email == email, User.is_deleted == False
        )
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        return q.count() > 0

    def count_admins(self) -> int:
        from sqlalchemy import func
        return (
            self.db.query(func.count(User.id))
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "admin", User.is_active == True, User.is_deleted == False)
            .scalar() or 0
        )
