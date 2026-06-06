"""
Sanchay — User Form Dialog
============================
Create / Edit a user account.
Password is required on create; optional on edit (blank = no change).
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QFormLayout, QWidget, QLabel, QCheckBox,
)
from PySide6.QtCore import Qt

from app.views.widgets.form_dialog import FormDialog
from app.services.auth_service import AuthService
from app.core.security import current_session
from app.models.user import User
from app.constants import UserRole


class UserFormDialog(FormDialog):
    """Create or edit a user account."""

    def __init__(self, user: Optional[User] = None, parent=None):
        self._user    = user
        self._service = AuthService()
        mode     = "Edit User" if user else "New User Account"
        subtitle = (f"Editing: {user.username}" if user
                    else "Create a login account for a team member")
        super().__init__(mode, subtitle, "Save User", parent,
                         min_width=500, min_height=440)
        if user:
            self._populate(user)

    def _build_form(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self.make_section("Account Information"))

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Full name
        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("e.g. Rajmani Shukla")
        self.f_name.setFixedHeight(38)
        self._si(self.f_name)

        # Username
        self.f_user = QLineEdit()
        self.f_user.setPlaceholderText("e.g. rajmani (lowercase, no spaces)")
        self.f_user.setFixedHeight(38)
        self._si(self.f_user)
        if self._user:
            self.f_user.setReadOnly(True)
            self.f_user.setStyleSheet("""
                QLineEdit {
                    border:1px solid #E2E8F0; border-radius:6px;
                    padding:0 10px; font-size:13px; background:#F8FAFC; color:#64748B;
                }
            """)

        # Email
        self.f_email = QLineEdit()
        self.f_email.setPlaceholderText("email@example.com (optional)")
        self.f_email.setFixedHeight(38)
        self._si(self.f_email)

        # Role
        self.f_role = QComboBox()
        self.f_role.setFixedHeight(38)
        self._sc(self.f_role)
        for r in UserRole:
            self.f_role.addItem(r.label(), r.value)
        # Non-admins can't create admins
        if not current_session.is_admin():
            for i in range(self.f_role.count()):
                if self.f_role.itemData(i) == "admin":
                    from PySide6.QtCore import Qt as _Qt
                    item = self.f_role.model().item(i)
                    if item:
                        item.setFlags(item.flags() & ~_Qt.ItemIsEnabled)

        form.addRow(self.make_label("Full Name",  required=True), self.f_name)
        form.addRow(self.make_label("Username",   required=True), self.f_user)
        form.addRow(self.make_label("Email"),                     self.f_email)
        form.addRow(self.make_label("Role",       required=True), self.f_role)
        layout.addLayout(form)

        layout.addWidget(self.make_divider())

        # ── Password section ───────────────────────────────────────────────────
        pw_title = "Set Password" if not self._user else "Change Password (optional)"
        layout.addWidget(self.make_section(pw_title))

        if self._user:
            hint = QLabel("Leave both fields blank to keep the current password.")
            hint.setStyleSheet("color:#64748B; font-size:12px;")
            layout.addWidget(hint)

        pw_form = QFormLayout()
        pw_form.setSpacing(14)
        pw_form.setLabelAlignment(Qt.AlignLeft)
        pw_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_pw = QLineEdit()
        self.f_pw.setEchoMode(QLineEdit.Password)
        self.f_pw.setPlaceholderText("Minimum 6 characters")
        self.f_pw.setFixedHeight(38)
        self._si(self.f_pw)

        self.f_pw2 = QLineEdit()
        self.f_pw2.setEchoMode(QLineEdit.Password)
        self.f_pw2.setPlaceholderText("Re-enter password")
        self.f_pw2.setFixedHeight(38)
        self._si(self.f_pw2)

        req_star = not bool(self._user)  # required only for create
        pw_form.addRow(self.make_label("Password",         required=req_star), self.f_pw)
        pw_form.addRow(self.make_label("Confirm Password", required=req_star), self.f_pw2)
        layout.addLayout(pw_form)
        layout.addStretch()

    def _populate(self, user: User) -> None:
        self.f_name.setText(user.full_name or "")
        self.f_user.setText(user.username or "")
        self.f_email.setText(user.email or "")
        for i in range(self.f_role.count()):
            if self.f_role.itemData(i) == user.role_name:
                self.f_role.setCurrentIndex(i)
                break

    def _collect_data(self) -> Optional[dict]:
        name = self.f_name.text().strip()
        user = self.f_user.text().strip().lower()
        pw   = self.f_pw.text()
        pw2  = self.f_pw2.text()

        if not name:
            self.set_error("Full name is required.")
            self.f_name.setFocus(); return None
        if not user:
            self.set_error("Username is required.")
            self.f_user.setFocus(); return None
        if len(user) < 3:
            self.set_error("Username must be at least 3 characters.")
            self.f_user.setFocus(); return None

        # Password validation
        if not self._user:              # Create: password required
            if not pw:
                self.set_error("Password is required.")
                self.f_pw.setFocus(); return None
        if pw:                          # If provided (create or edit)
            if len(pw) < 6:
                self.set_error("Password must be at least 6 characters.")
                self.f_pw.setFocus(); return None
            if pw != pw2:
                self.set_error("Passwords do not match.")
                self.f_pw2.setFocus(); return None

        return {
            "full_name": name,
            "username":  user,
            "email":     self.f_email.text().strip() or None,
            "role_name": self.f_role.currentData(),
            "password":  pw or None,
        }

    def _on_save(self, data: dict) -> None:
        if self._user:
            # Update: only change provided fields
            update = {
                "full_name": data["full_name"],
                "email":     data["email"],
            }
            # Role change
            from app.core.database import get_db
            from app.repositories.user_repository import UserRepository, RoleRepository
            with get_db() as db:
                role_repo = RoleRepository(db)
                role = role_repo.get_by_name(data["role_name"])
                if role:
                    update["role_id"] = role.id
                repo = UserRepository(db)
                user = repo.get_by_id(self._user.id)
                if user:
                    repo.update(user, update)
            # Password change if provided
            if data["password"]:
                self._service.change_password(self._user.id, data["password"])
        else:
            self._service.create_user(
                username=data["username"],
                full_name=data["full_name"],
                password=data["password"],
                role_name=data["role_name"],
                email=data["email"],
            )
        self.accept()

    @staticmethod
    def _si(w) -> None:
        w.setStyleSheet("""
            QLineEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; color:#0F172A; background:white;
            }
            QLineEdit:focus { border:2px solid #2563EB; padding:0 9px; }
        """)

    @staticmethod
    def _sc(w) -> None:
        w.setStyleSheet("""
            QComboBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QComboBox:focus { border:2px solid #2563EB; }
            QComboBox::drop-down { border:none; width:20px; }
        """)

