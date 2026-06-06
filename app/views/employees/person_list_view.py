"""
Sanchay — Person List View
============================
Unified management page for Employees, Students, Contractors, Candidates.
Tabs filter by person type; search + department filter inline.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabBar, QStackedWidget, QDialog, QTableWidgetItem,
    QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut

from app.services.person_service import PersonService
from app.services.organization_service import DepartmentService
from app.core.exceptions import SanchayError
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.person import Person
from app.constants import PersonType, PersonStatus
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.employees.person_form_dialog import PersonFormDialog
from loguru import logger


# Tab definitions: (label, person_type or None=All)
PERSON_TABS = [
    ("All",          None),
    ("Employees",    "employee"),
    ("Students",     "student"),
    ("Contractors",  "contractor"),
    ("Candidates",   "candidate"),
]


class PersonListView(QWidget):
    """
    Person management page with type tabs, search, and department filter.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._person_service = PersonService()
        self._dept_service   = DepartmentService()
        self._persons: list[Person] = []
        self._active_type: str | None = None  # current tab filter
        self._build_ui()
        self._load_dept_filter()
        self._load()

        app_signals.person_created.connect(lambda _: self._load())
        app_signals.person_updated.connect(lambda _: self._load())
        app_signals.person_deleted.connect(lambda _: self._load())

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(self._on_create)
        QShortcut(QKeySequence("F5"),     self).activated.connect(self._load)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self._search.setFocus()
        )

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Tab bar ────────────────────────────────────────────────────────────
        tab_frame = QFrame()
        tab_frame.setStyleSheet(
            "background: white; border-bottom: 1px solid #E2E8F0;"
        )
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(24, 0, 24, 0)
        tab_layout.setSpacing(0)

        self._tab_btns: list[QPushButton] = []
        for label, ptype in PERSON_TABS:
            btn = QPushButton(label)
            btn.setFixedHeight(44)
            btn.setCheckable(True)
            btn.setProperty("ptype", ptype)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent; border: none;
                    border-bottom: 3px solid transparent;
                    color: #64748B; font-weight: 500; font-size: 13px;
                    padding: 0 18px; border-radius: 0;
                }
                QPushButton:hover { color: #374151; }
                QPushButton:checked {
                    color: #2563EB; font-weight: 600;
                    border-bottom: 3px solid #2563EB;
                }
            """)
            btn.clicked.connect(lambda _, t=ptype: self._on_tab_click(t))
            self._tab_btns.append(btn)
            tab_layout.addWidget(btn)

        tab_layout.addStretch()
        layout.addWidget(tab_frame)
        self._tab_btns[0].setChecked(True)  # All tab active

        # ── Toolbar ────────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        toolbar.setFixedHeight(60)
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(24, 10, 24, 10)
        t_layout.setSpacing(10)

        self._search = SearchBar("Search by name, ID, email, phone…")
        self._search.set_min_width(300)
        self._search.search_changed.connect(self._on_search)

        # Department filter
        self._dept_filter = QComboBox()
        self._dept_filter.setFixedHeight(36)
        self._dept_filter.setMinimumWidth(170)
        self._dept_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 12px; color: #374151;
            }
            QComboBox::drop-down { border: none; width: 16px; }
        """)
        self._dept_filter.currentIndexChanged.connect(lambda _: self._load())

        # Status filter
        self._status_filter = QComboBox()
        self._status_filter.setFixedHeight(36)
        self._status_filter.setMinimumWidth(130)
        self._status_filter.setStyleSheet(self._dept_filter.styleSheet())
        self._status_filter.addItem("All Status", None)
        self._status_filter.addItem("Active",   "active")
        self._status_filter.addItem("Inactive", "inactive")
        self._status_filter.currentIndexChanged.connect(lambda _: self._load())

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        add_btn = QPushButton("+ Add Person")
        add_btn.setFixedHeight(36)
        add_btn.setToolTip("Add a new person (Ctrl+N)")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #2563EB; color: white; border-radius: 6px;
                font-weight: 600; padding: 0 18px;
            }
            QPushButton:hover { background: #1D4ED8; }
        """)
        add_btn.clicked.connect(self._on_create)

        t_layout.addWidget(self._search)
        t_layout.addWidget(self._dept_filter)
        t_layout.addWidget(self._status_filter)
        t_layout.addWidget(self._count_lbl)
        t_layout.addStretch()
        t_layout.addWidget(add_btn)
        layout.addWidget(toolbar)

        # ── Table ──────────────────────────────────────────────────────────────
        cols = ["#", "ID Code", "Name", "Type", "Department", "Designation", "Phone", "Status", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths({0: 45, 1: 100, 3: 100, 4: 150, 5: 140, 6: 130, 7: 90, 8: 160})
        self._table.row_double_clicked.connect(self._on_row_double_click)

        content = QWidget()
        content.setStyleSheet("background: #F8FAFC;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.addWidget(self._table)
        layout.addWidget(content, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_dept_filter(self) -> None:
        """Populate the department filter dropdown."""
        try:
            org_id = current_session.org_id
            self._dept_filter.blockSignals(True)
            self._dept_filter.clear()
            self._dept_filter.addItem("All Departments", None)
            if org_id:
                depts = self._dept_service.get_by_org(org_id)
                for d in depts:
                    self._dept_filter.addItem(d.name, d.id)
            self._dept_filter.blockSignals(False)
        except Exception as e:
            logger.error(f"Failed to load dept filter: {e}")

    def _load(self) -> None:
        """Reload persons with current filters."""
        self._count_lbl.setText("Loading…")
        try:
            org_id    = current_session.org_id
            query     = self._search.text()
            dept_id   = self._dept_filter.currentData()
            status    = self._status_filter.currentData()
            ptype     = self._active_type

            persons, total = self._person_service.search(
                query=query,
                org_id=org_id,
                person_type=ptype,
                status=status,
                dept_id=dept_id,
                limit=200,
            )
            self._persons = persons
            self._render(total)
        except Exception as e:
            logger.error(f"Person list load error: {e}")
            self._count_lbl.setText("Error loading data")

    def _render(self, total: int) -> None:
        self._table.setRowCount(0)

        type_colors = {
            "employee":   ("#DBEAFE", "#1D4ED8"),
            "student":    ("#DCFCE7", "#15803D"),
            "contractor": ("#FEF3C7", "#B45309"),
            "candidate":  ("#F3E8FF", "#7C3AED"),
        }

        for i, p in enumerate(self._persons):
            self._table.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            dept_name = p.department.name if p.department else "—"
            bg, fg = type_colors.get(p.person_type, ("#F1F5F9", "#374151"))

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(p.display_code))
            self._table.setItem(i, 2, _item(p.full_name))
            self._table.add_badge_cell(i, 3, p.person_type.capitalize(), bg, fg)
            self._table.setItem(i, 4, _item(dept_name))
            self._table.setItem(i, 5, _item(p.designation))
            self._table.setItem(i, 6, _item(p.phone))

            if p.status == "active":
                self._table.add_badge_cell(i, 7, "Active", "#DCFCE7", "#15803D")
            else:
                self._table.add_badge_cell(i, 7, "Inactive", "#F1F5F9", "#64748B")

            pid = p.id
            is_active = p.status == "active"
            self._table.add_action_cell(i, 8, [
                ("Edit",   "✏️", lambda _, x=pid: self._on_edit(x)),
                ("Deactivate" if is_active else "Activate",
                 "🔄",         lambda _, x=pid: self._on_toggle(x)),
                ("Delete", "🗑️", lambda _, x=pid: self._on_delete(x)),
            ])

        shown = len(self._persons)
        suffix = f" of {total}" if total > shown else ""
        self._count_lbl.setText(f"{shown}{suffix} person{'s' if shown != 1 else ''}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_tab_click(self, ptype: str | None) -> None:
        self._active_type = ptype
        for btn in self._tab_btns:
            btn.setChecked(btn.property("ptype") == ptype)
        self._load()

    def _on_search(self, _: str) -> None:
        self._load()

    def _on_create(self) -> None:
        initial_type = self._active_type or "employee"
        try:
            dlg = PersonFormDialog(initial_type=initial_type, parent=self)
            if dlg.exec() == QDialog.Accepted:
                app_signals.show_notification.emit(
                    "Success", "Person added successfully.", "success"
                )
                app_signals.refresh_dashboard.emit()
        except SanchayError as e:
            app_signals.show_notification.emit("Error", e.message, "error")
        except Exception as e:
            logger.exception(f"Unexpected error in {self.__class__.__name__}._on_create")
            app_signals.show_notification.emit(
                "Error", "An unexpected error occurred. Please try again.", "error"
            )

    def _on_edit(self, person_id: int) -> None:
        person = next((p for p in self._persons if p.id == person_id), None)
        if not person:
            return
        try:
            dlg = PersonFormDialog(person=person, parent=self)
            if dlg.exec() == QDialog.Accepted:
                app_signals.show_notification.emit("Success", "Person updated.", "success")
        except SanchayError as e:
            app_signals.show_notification.emit("Error", e.message, "error")
        except Exception as e:
            logger.exception(f"Unexpected error in {self.__class__.__name__}._on_edit")
            app_signals.show_notification.emit(
                "Error", "An unexpected error occurred. Please try again.", "error"
            )

    def _on_toggle(self, person_id: int) -> None:
        person = next((p for p in self._persons if p.id == person_id), None)
        if not person:
            return
        action = "deactivate" if person.status == "active" else "activate"
        dlg = ConfirmDialog(
            title=f"{'Deactivate' if person.status == 'active' else 'Activate'} Person",
            message=f"Are you sure you want to {action} '{person.full_name}'?",
            confirm_label=action.capitalize(),
            danger=(person.status == "active"),
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                new_status = self._person_service.toggle_status(person_id)
                app_signals.person_updated.emit(person_id)
                app_signals.show_notification.emit(
                    "Done", f"'{person.full_name}' is now {new_status}.", "info"
                )
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_delete(self, person_id: int) -> None:
        person = next((p for p in self._persons if p.id == person_id), None)
        if not person:
            return
        dlg = ConfirmDialog(
            title="Delete Person",
            message=f"Permanently delete '{person.full_name}' ({person.display_code})?\n\n"
                    "This cannot be undone. The person must have no active asset issues.",
            confirm_label="Delete",
            danger=True,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._person_service.delete(person_id)
                app_signals.person_deleted.emit(person_id)
                app_signals.show_notification.emit(
                    "Deleted", f"'{person.full_name}' removed.", "info"
                )
                app_signals.refresh_dashboard.emit()
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._persons):
            self._on_edit(self._persons[row].id)
