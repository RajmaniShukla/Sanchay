"""
Sanchay — User List View
==========================
Admin-only page for managing user accounts.
Supports create, edit, deactivate, and password change.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QTableWidgetItem, QInputDialog, QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut

from app.services.auth_service import AuthService
from app.core.exceptions import SanchayError
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.user import User
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.settings.user_form_dialog import UserFormDialog
from loguru import logger


class UserListView(QWidget):
    """User account management — Admin only."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = AuthService()
        self._users: list[User] = []
        self._build_ui()
        self._load()

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_create)
        QShortcut(QKeySequence("F5"),     self).activated.connect(self._load)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self._search.setFocus()
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet("background:white; border-bottom:1px solid #E2E8F0;")
        toolbar.setFixedHeight(64)
        t_lay = QHBoxLayout(toolbar)
        t_lay.setContentsMargins(24, 12, 24, 12)
        t_lay.setSpacing(12)

        self._search = SearchBar("Search by username, name, email…")
        self._search.set_min_width(280)
        self._search.search_changed.connect(self._on_search)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        add_btn = QPushButton("+ Add User")
        add_btn.setFixedHeight(38)
        add_btn.setToolTip("Create a new user account (Ctrl+N)")
        add_btn.setStyleSheet("""
            QPushButton { background:#2563EB; color:white; border-radius:6px;
                          font-weight:600; padding:0 18px; }
            QPushButton:hover { background:#1D4ED8; }
        """)
        add_btn.clicked.connect(self._on_create)

        t_lay.addWidget(self._search)
        t_lay.addWidget(self._count_lbl)
        t_lay.addStretch()
        t_lay.addWidget(add_btn)
        layout.addWidget(toolbar)

        # ── Info strip ─────────────────────────────────────────────────────────
        info = QFrame()
        info.setStyleSheet("background:#FEF3C7; border-bottom:1px solid #FDE68A;")
        info.setFixedHeight(36)
        i_lay = QHBoxLayout(info)
        i_lay.setContentsMargins(24, 0, 24, 0)
        tip = QLabel(
            "⚠️  User management is restricted to Admins only. "
            "You cannot deactivate the last admin account or your own account."
        )
        tip.setStyleSheet("color:#B45309; font-size:12px;")
        i_lay.addWidget(tip)
        layout.addWidget(info)

        # ── Table ──────────────────────────────────────────────────────────────
        cols = ["#", "Username", "Full Name", "Role", "Email", "Status",
                "Last Login", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths(
            {0: 44, 1: 120, 3: 100, 4: 180, 5: 90, 6: 150, 7: 230}
        )
        self._table.row_double_clicked.connect(self._on_row_double_click)

        content = QWidget()
        content.setStyleSheet("background:#F8FAFC;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.addWidget(self._table)
        layout.addWidget(content, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self, query: str = "") -> None:
        try:
            all_users = self._service.get_all_users()
            if query:
                q = query.lower()
                all_users = [
                    u for u in all_users
                    if q in u.username.lower()
                    or q in u.full_name.lower()
                    or q in (u.email or "").lower()
                ]
            self._users = all_users
            self._render()
        except Exception as e:
            logger.error(f"User list load error: {e}")

    def _render(self) -> None:
        self._table.setRowCount(0)

        role_colors = {
            "admin":    ("#FEE2E2", "#B91C1C"),
            "manager":  ("#DBEAFE", "#1D4ED8"),
            "operator": ("#DCFCE7", "#15803D"),
            "viewer":   ("#F1F5F9", "#475569"),
        }

        for i, user in enumerate(self._users):
            self._table.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            role     = user.role_name
            rb, rf   = role_colors.get(role, ("#F1F5F9", "#374151"))
            is_self  = user.id == current_session.user_id
            last_log = (
                user.last_login.strftime("%d %b %Y  %H:%M")
                if user.last_login else "Never"
            )

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(
                f"{'🔑 ' if is_self else ''}{user.username}"
            ))
            self._table.setItem(i, 2, _item(user.full_name))
            self._table.add_badge_cell(i, 3, role.capitalize(), rb, rf)
            self._table.setItem(i, 4, _item(user.email))

            if user.is_active:
                self._table.add_badge_cell(i, 5, "Active", "#DCFCE7", "#15803D")
            else:
                self._table.add_badge_cell(i, 5, "Inactive", "#F1F5F9", "#64748B")

            self._table.setItem(i, 6, _item(last_log))

            uid       = user.id
            is_active = user.is_active
            actions = [
                ("Edit", "✏️", lambda _, x=uid: self._on_edit(x)),
                ("Password", "🔑", lambda _, x=uid: self._on_change_password(x)),
                ("Deactivate" if is_active else "Activate",
                 "🔄", lambda _, x=uid: self._on_toggle(x)),
            ]
            self._table.add_action_cell(i, 7, actions)

        cnt = len(self._users)
        self._count_lbl.setText(f"{cnt} user{'s' if cnt != 1 else ''}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_search(self, query: str) -> None:
        self._load(query)

    def _on_create(self) -> None:
        try:
            dlg = UserFormDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                self._load()
                app_signals.show_notification.emit(
                    "Success", "User account created.", "success"
                )
        except SanchayError as e:
            app_signals.show_notification.emit("Error", e.message, "error")
        except Exception as e:
            logger.exception(f"Unexpected error in {self.__class__.__name__}._on_create")
            app_signals.show_notification.emit(
                "Error", "An unexpected error occurred. Please try again.", "error"
            )

    def _on_edit(self, user_id: int) -> None:
        user = next((u for u in self._users if u.id == user_id), None)
        if not user:
            return
        try:
            dlg = UserFormDialog(user=user, parent=self)
            if dlg.exec() == QDialog.Accepted:
                self._load()
                app_signals.show_notification.emit("Success", "User updated.", "success")
        except SanchayError as e:
            app_signals.show_notification.emit("Error", e.message, "error")
        except Exception as e:
            logger.exception(f"Unexpected error in {self.__class__.__name__}._on_edit")
            app_signals.show_notification.emit(
                "Error", "An unexpected error occurred. Please try again.", "error"
            )

    def _on_change_password(self, user_id: int) -> None:
        """Prompt for a new password inline."""
        user = next((u for u in self._users if u.id == user_id), None)
        if not user:
            return

        # Simple two-step password dialog
        pw, ok = QInputDialog.getText(
            self, f"Change Password — {user.username}",
            "Enter new password (min 6 characters):",
            QLineEdit.Password,
        )
        if not ok or not pw:
            return
        pw2, ok2 = QInputDialog.getText(
            self, "Confirm Password", "Re-enter new password:",
            QLineEdit.Password,
        )
        if not ok2:
            return
        if pw != pw2:
            QMessageBox.warning(self, "Mismatch", "Passwords do not match.")
            return
        if len(pw) < 6:
            QMessageBox.warning(self, "Too Short",
                                "Password must be at least 6 characters.")
            return
        try:
            self._service.change_password(user_id, pw)
            app_signals.show_notification.emit(
                "Done",
                f"Password changed for '{user.username}'.",
                "success",
            )
        except Exception as e:
            app_signals.show_notification.emit("Error", str(e), "error")

    def _on_toggle(self, user_id: int) -> None:
        user = next((u for u in self._users if u.id == user_id), None)
        if not user:
            return
        if user.id == current_session.user_id:
            app_signals.show_notification.emit(
                "Not Allowed", "You cannot deactivate your own account.", "warning"
            )
            return
        action = "deactivate" if user.is_active else "activate"
        dlg = ConfirmDialog(
            title=f"{'Deactivate' if user.is_active else 'Activate'} User",
            message=(
                f"Are you sure you want to {action} '{user.username}'?\n\n"
                + ("The user will be unable to log in." if user.is_active
                   else "The user will be able to log in again.")
            ),
            confirm_label=action.capitalize(),
            danger=user.is_active,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                new_state = self._service.toggle_user_active(user_id)
                self._load()
                label = "activated" if new_state else "deactivated"
                app_signals.show_notification.emit(
                    "Done", f"'{user.username}' {label}.", "info"
                )
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._users):
            self._on_edit(self._users[row].id)
