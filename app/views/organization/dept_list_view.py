"""
Sanchay — Department List View
=================================
Department management page with create, edit, delete and hierarchy support.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QComboBox, QTableWidgetItem,
)
from PySide6.QtCore import Qt

from app.services.organization_service import OrganizationService, DepartmentService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.organization import Department, Organization
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.organization.dept_form_dialog import DeptFormDialog
from loguru import logger


class DeptListView(QWidget):
    """Department management for the selected organization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dept_service  = DepartmentService()
        self._org_service   = OrganizationService()
        self._depts: list[Department] = []
        self._orgs:  list[Organization] = []
        self._selected_org_id: int | None = current_session.org_id
        self._build_ui()
        self._load_orgs()

        app_signals.dept_created.connect(lambda _: self._load_depts())
        app_signals.dept_updated.connect(lambda _: self._load_depts())
        app_signals.dept_deleted.connect(lambda _: self._load_depts())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ────────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        toolbar.setFixedHeight(64)
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(24, 12, 24, 12)
        t_layout.setSpacing(12)

        # Org picker (admin sees all orgs)
        if current_session.is_admin():
            org_lbl = QLabel("Org:")
            org_lbl.setStyleSheet("color: #374151; font-weight: 600; font-size: 12px;")
            self._org_combo = QComboBox()
            self._org_combo.setFixedHeight(36)
            self._org_combo.setMinimumWidth(200)
            self._org_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #D1D5DB; border-radius: 6px;
                    padding: 0 10px; font-size: 13px;
                }
                QComboBox::drop-down { border: none; width: 20px; }
            """)
            self._org_combo.currentIndexChanged.connect(self._on_org_changed)
            t_layout.addWidget(org_lbl)
            t_layout.addWidget(self._org_combo)

        self._search = SearchBar("Search departments…")
        self._search.set_min_width(240)
        self._search.search_changed.connect(self._on_search)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        add_btn = QPushButton("+ New Department")
        add_btn.setFixedHeight(38)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #2563EB; color: white; border-radius: 6px;
                font-weight: 600; padding: 0 18px;
            }
            QPushButton:hover { background: #1D4ED8; }
        """)
        add_btn.clicked.connect(self._on_create)

        t_layout.addWidget(self._search)
        t_layout.addWidget(self._count_lbl)
        t_layout.addStretch()
        t_layout.addWidget(add_btn)
        layout.addWidget(toolbar)

        # ── Table ──────────────────────────────────────────────────────────────
        cols = ["#", "Name", "Code", "Parent Dept.", "Description", "Status", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths({0: 50, 2: 90, 3: 160, 5: 100, 6: 160})
        self._table.row_double_clicked.connect(self._on_row_double_click)

        content = QWidget()
        content.setStyleSheet("background: #F8FAFC;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.addWidget(self._table)
        layout.addWidget(content, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_orgs(self) -> None:
        try:
            self._orgs = self._org_service.get_all()
            if current_session.is_admin() and hasattr(self, "_org_combo"):
                self._org_combo.blockSignals(True)
                self._org_combo.clear()
                for org in self._orgs:
                    self._org_combo.addItem(f"{org.name} ({org.code})", org.id)
                # Select current session org if set
                if self._selected_org_id:
                    for i in range(self._org_combo.count()):
                        if self._org_combo.itemData(i) == self._selected_org_id:
                            self._org_combo.setCurrentIndex(i)
                            break
                self._org_combo.blockSignals(False)
            self._load_depts()
        except Exception as e:
            logger.error(f"Failed to load orgs for dept view: {e}")

    def _load_depts(self, query: str = "") -> None:
        if not self._selected_org_id:
            self._depts = []
            self._render()
            return
        try:
            all_depts = self._dept_service.get_by_org(self._selected_org_id)
            if query:
                q = query.lower()
                self._depts = [
                    d for d in all_depts
                    if q in d.name.lower() or q in d.code.lower()
                ]
            else:
                self._depts = all_depts
            self._render()
        except Exception as e:
            logger.error(f"Failed to load departments: {e}")

    def _render(self) -> None:
        self._table.setRowCount(0)
        for i, dept in enumerate(self._depts):
            self._table.insertRow(i)

            def _item(val):
                item = QTableWidgetItem(str(val) if val else "—")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                return item

            parent_name = dept.parent.name if dept.parent else "—"
            desc_short = (dept.description or "")[:60]
            if len(dept.description or "") > 60:
                desc_short += "…"

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(dept.name))
            self._table.setItem(i, 2, _item(dept.code))
            self._table.setItem(i, 3, _item(parent_name))
            self._table.setItem(i, 4, _item(desc_short))

            if dept.is_active:
                self._table.add_badge_cell(i, 5, "Active", "#DCFCE7", "#15803D")
            else:
                self._table.add_badge_cell(i, 5, "Inactive", "#F1F5F9", "#64748B")

            dept_id = dept.id
            is_active = dept.is_active
            self._table.add_action_cell(i, 6, [
                ("Edit",   "✏️", lambda _, did=dept_id: self._on_edit(did)),
                ("Delete", "🗑️", lambda _, did=dept_id: self._on_delete(did)),
            ])

        self._count_lbl.setText(f"{len(self._depts)} department{'s' if len(self._depts) != 1 else ''}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_org_changed(self) -> None:
        if hasattr(self, "_org_combo"):
            self._selected_org_id = self._org_combo.currentData()
        self._load_depts()

    def _on_search(self, query: str) -> None:
        self._load_depts(query)

    def _on_create(self) -> None:
        if not self._selected_org_id:
            app_signals.show_notification.emit("Warning", "Please select an organization first.", "warning")
            return
        dlg = DeptFormDialog(org_id=self._selected_org_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit("Success", "Department created.", "success")

    def _on_edit(self, dept_id: int) -> None:
        dept = next((d for d in self._depts if d.id == dept_id), None)
        if not dept:
            return
        dlg = DeptFormDialog(org_id=self._selected_org_id, dept=dept, parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit("Success", "Department updated.", "success")

    def _on_delete(self, dept_id: int) -> None:
        dept = next((d for d in self._depts if d.id == dept_id), None)
        if not dept:
            return
        dlg = ConfirmDialog(
            title="Delete Department",
            message=f"Are you sure you want to delete '{dept.name}'?\n"
                    "This cannot be undone. All persons and assets in this "
                    "department must be reassigned first.",
            confirm_label="Delete",
            danger=True,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._dept_service.delete(dept_id)
                app_signals.dept_deleted.emit(dept_id)
                app_signals.show_notification.emit("Deleted", f"'{dept.name}' removed.", "info")
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._depts):
            self._on_edit(self._depts[row].id)
