"""
Sanchay — Organization List View
===================================
Admin-only page showing all organizations with CRUD actions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog,
)
from PySide6.QtCore import Qt

from app.services.organization_service import OrganizationService
from app.core.signals import app_signals
from app.models.organization import Organization
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.organization.org_form_dialog import OrgFormDialog
from loguru import logger


class OrgListView(QWidget):
    """
    Organization management page (Admin only).
    Shows all organizations; supports create, edit, toggle-active.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = OrganizationService()
        self._orgs: list[Organization] = []
        self._build_ui()
        self._load()

        # Refresh when org data changes
        app_signals.org_created.connect(lambda _: self._load())
        app_signals.org_updated.connect(lambda _: self._load())
        app_signals.org_deleted.connect(lambda _: self._load())

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

        self._search = SearchBar("Search organizations…")
        self._search.set_min_width(280)
        self._search.search_changed.connect(self._on_search)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        add_btn = QPushButton("+ New Organization")
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
        cols = ["#", "Name", "Code", "Type", "City", "Phone", "Status", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths({0: 50, 2: 90, 3: 130, 4: 120, 5: 140, 6: 100, 7: 180})
        self._table.row_double_clicked.connect(self._on_row_double_click)

        content = QWidget()
        content.setStyleSheet("background: #F8FAFC;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(24, 20, 24, 20)
        c_layout.addWidget(self._table)
        layout.addWidget(content, 1)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self, query: str = "") -> None:
        try:
            all_orgs = self._service.get_all(active_only=False)
            if query:
                q = query.lower()
                self._orgs = [
                    o for o in all_orgs
                    if q in o.name.lower() or q in o.code.lower()
                    or q in (o.city or "").lower()
                ]
            else:
                self._orgs = all_orgs
            self._render()
        except Exception as e:
            logger.error(f"Failed to load organizations: {e}")

    def _render(self) -> None:
        self._table.setRowCount(0)
        for i, org in enumerate(self._orgs):
            self._table.insertRow(i)

            from PySide6.QtWidgets import QTableWidgetItem
            from PySide6.QtCore import Qt

            def _item(val):
                item = QTableWidgetItem(str(val) if val else "—")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                return item

            org_type_labels = {
                "college": "College", "industry": "Industry",
                "factory": "Factory", "ngo": "NGO",
                "office": "Office", "institute": "Institute", "other": "Other",
            }

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(org.name))
            self._table.setItem(i, 2, _item(org.code))
            self._table.setItem(i, 3, _item(org_type_labels.get(org.org_type, org.org_type)))
            self._table.setItem(i, 4, _item(org.city))
            self._table.setItem(i, 5, _item(org.phone))

            # Status badge
            if org.is_active:
                self._table.add_badge_cell(i, 6, "Active", "#DCFCE7", "#15803D")
            else:
                self._table.add_badge_cell(i, 6, "Inactive", "#F1F5F9", "#64748B")

            # Action buttons
            org_id = org.id
            is_active = org.is_active
            self._table.add_action_cell(i, 7, [
                ("Edit", "✏️", lambda _, oid=org_id: self._on_edit(oid)),
                ("Deactivate" if is_active else "Activate", "🔄",
                 lambda _, oid=org_id: self._on_toggle(oid)),
            ])

        total = len(self._orgs)
        self._count_lbl.setText(f"{total} organization{'s' if total != 1 else ''}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_search(self, query: str) -> None:
        self._load(query)

    def _on_create(self) -> None:
        dlg = OrgFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit(
                "Success", "Organization created successfully.", "success"
            )
            app_signals.refresh_dashboard.emit()

    def _on_edit(self, org_id: int) -> None:
        org = next((o for o in self._orgs if o.id == org_id), None)
        if not org:
            return
        dlg = OrgFormDialog(org=org, parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit(
                "Success", "Organization updated.", "success"
            )

    def _on_toggle(self, org_id: int) -> None:
        org = next((o for o in self._orgs if o.id == org_id), None)
        if not org:
            return
        action = "deactivate" if org.is_active else "activate"
        dlg = ConfirmDialog(
            title=f"{'Deactivate' if org.is_active else 'Activate'} Organization",
            message=f"Are you sure you want to {action} '{org.name}'?",
            confirm_label=action.capitalize(),
            danger=org.is_active,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._service.update(org_id, {"is_active": not org.is_active})
                app_signals.org_updated.emit(org_id)
                app_signals.show_notification.emit(
                    "Done", f"Organization {action}d.", "info"
                )
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._orgs):
            self._on_edit(self._orgs[row].id)
