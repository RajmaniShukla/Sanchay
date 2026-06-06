"""
Sanchay — Asset List View
============================
Full asset management page with search, multi-filter, status badges,
and inline action buttons for View / Edit / Delete.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QTableWidgetItem, QComboBox,
)
from PySide6.QtCore import Qt

from app.services.asset_service import AssetService, AssetCategoryService
from app.services.organization_service import DepartmentService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.asset import Asset
from app.constants import AssetStatus, AssetCondition
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.assets.asset_form_dialog import AssetFormDialog
from app.views.assets.asset_detail_dialog import AssetDetailDialog
from loguru import logger


class AssetListView(QWidget):
    """
    Asset inventory page.
    Filters: search · status · category · department
    Actions:  View Detail · Edit · Delete
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service   = AssetService()
        self._cat_svc   = AssetCategoryService()
        self._dept_svc  = DepartmentService()
        self._assets: list[Asset] = []
        self._build_ui()
        self._populate_filters()
        self._load()

        app_signals.asset_created.connect(lambda _: self._load())
        app_signals.asset_updated.connect(lambda _: self._load())
        app_signals.asset_deleted.connect(lambda _: self._load())
        app_signals.asset_issued.connect(lambda *_: self._load())
        app_signals.asset_returned.connect(lambda *_: self._load())

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar row 1: search + add ────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet("background:white; border-bottom:1px solid #E2E8F0;")
        toolbar.setFixedHeight(64)
        t_lay = QHBoxLayout(toolbar)
        t_lay.setContentsMargins(24, 12, 24, 12)
        t_lay.setSpacing(10)

        self._search = SearchBar("Search by name, code, serial, manufacturer…")
        self._search.set_min_width(300)
        self._search.search_changed.connect(lambda _: self._load())

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        add_btn = QPushButton("+ Register Asset")
        add_btn.setFixedHeight(38)
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

        # ── Toolbar row 2: filters ────────────────────────────────────────────
        filter_bar = QFrame()
        filter_bar.setStyleSheet("background:white; border-bottom:1px solid #E2E8F0;")
        filter_bar.setFixedHeight(52)
        f_lay = QHBoxLayout(filter_bar)
        f_lay.setContentsMargins(24, 8, 24, 8)
        f_lay.setSpacing(10)

        combo_style = """
            QComboBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:12px; color:#374151; background:white;
            }
            QComboBox:focus { border-color:#2563EB; }
            QComboBox::drop-down { border:none; width:16px; }
        """

        self._status_filter = QComboBox()
        self._status_filter.setFixedHeight(34)
        self._status_filter.setMinimumWidth(150)
        self._status_filter.setStyleSheet(combo_style)
        self._status_filter.addItem("All Status", None)
        for s in AssetStatus:
            self._status_filter.addItem(s.label(), s.value)
        self._status_filter.currentIndexChanged.connect(lambda _: self._load())

        self._cat_filter = QComboBox()
        self._cat_filter.setFixedHeight(34)
        self._cat_filter.setMinimumWidth(170)
        self._cat_filter.setStyleSheet(combo_style)
        self._cat_filter.addItem("All Categories", None)
        self._cat_filter.currentIndexChanged.connect(lambda _: self._load())

        self._dept_filter = QComboBox()
        self._dept_filter.setFixedHeight(34)
        self._dept_filter.setMinimumWidth(160)
        self._dept_filter.setStyleSheet(combo_style)
        self._dept_filter.addItem("All Departments", None)
        self._dept_filter.currentIndexChanged.connect(lambda _: self._load())

        reset_btn = QPushButton("✕ Clear Filters")
        reset_btn.setFixedHeight(34)
        reset_btn.setStyleSheet("""
            QPushButton {
                background:transparent; border:1px solid #D1D5DB;
                border-radius:6px; color:#64748B; font-size:12px; padding:0 12px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        reset_btn.clicked.connect(self._clear_filters)

        filter_lbl = QLabel("Filter:")
        filter_lbl.setStyleSheet("color:#374151; font-weight:600; font-size:12px;")
        f_lay.addWidget(filter_lbl)
        f_lay.addWidget(self._status_filter)
        f_lay.addWidget(self._cat_filter)
        f_lay.addWidget(self._dept_filter)
        f_lay.addWidget(reset_btn)
        f_lay.addStretch()
        layout.addWidget(filter_bar)

        # ── Asset stat pills ───────────────────────────────────────────────────
        self._stat_bar = QFrame()
        self._stat_bar.setStyleSheet("background:#F8FAFC; border-bottom:1px solid #E2E8F0;")
        self._stat_bar.setFixedHeight(44)
        sb_lay = QHBoxLayout(self._stat_bar)
        sb_lay.setContentsMargins(24, 8, 24, 8)
        sb_lay.setSpacing(16)

        self._stat_pills: dict[str, QLabel] = {}
        pill_defs = [
            ("available",   "Available",   "#DCFCE7", "#15803D"),
            ("issued",      "Issued",      "#DBEAFE", "#1D4ED8"),
            ("maintenance", "Maintenance", "#FEF3C7", "#B45309"),
            ("disposed",    "Disposed",    "#F1F5F9", "#64748B"),
            ("lost",        "Lost",        "#FEE2E2", "#B91C1C"),
        ]
        for key, label, bg, fg in pill_defs:
            pill = QLabel(f"{label}: —")
            pill.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:10px; "
                f"padding:2px 10px; font-size:11px; font-weight:600;"
            )
            self._stat_pills[key] = pill
            sb_lay.addWidget(pill)
        sb_lay.addStretch()
        layout.addWidget(self._stat_bar)

        # ── Table ──────────────────────────────────────────────────────────────
        cols = ["#", "Code", "Asset Name", "Category", "Department",
                "Serial Number", "Status", "Condition", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths(
            {0: 44, 1: 110, 3: 130, 4: 140, 5: 140, 6: 110, 7: 90, 8: 190}
        )
        self._table.row_double_clicked.connect(self._on_row_double_click)

        content = QWidget()
        content.setStyleSheet("background:#F8FAFC;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.addWidget(self._table)
        layout.addWidget(content, 1)

    def _populate_filters(self) -> None:
        org_id = current_session.org_id
        try:
            cats = self._cat_svc.get_all(org_id)
            for c in cats:
                self._cat_filter.addItem(c.name, c.id)
        except Exception:
            pass
        try:
            depts = self._dept_svc.get_by_org(org_id) if org_id else []
            for d in depts:
                self._dept_filter.addItem(d.name, d.id)
        except Exception:
            pass

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            org_id  = current_session.org_id
            query   = self._search.text()
            status  = self._status_filter.currentData()
            cat_id  = self._cat_filter.currentData()
            dept_id = self._dept_filter.currentData()

            assets, total = self._service.search(
                query=query, org_id=org_id, status=status,
                category_id=cat_id, dept_id=dept_id, limit=300,
            )
            self._assets = assets
            self._render(total)
            self._update_stat_pills()
        except Exception as e:
            logger.error(f"Asset list load error: {e}")

    def _render(self, total: int) -> None:
        self._table.setRowCount(0)

        status_map = {
            "available":   ("#DCFCE7", "#15803D"),
            "issued":      ("#DBEAFE", "#1D4ED8"),
            "maintenance": ("#FEF3C7", "#B45309"),
            "disposed":    ("#F1F5F9", "#64748B"),
            "lost":        ("#FEE2E2", "#B91C1C"),
        }
        cond_map = {
            "new":  "#15803D", "good": "#2563EB",
            "fair": "#B45309", "poor": "#DC2626",
        }

        for i, a in enumerate(self._assets):
            self._table.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            bg, fg = status_map.get(a.status, ("#F1F5F9", "#374151"))
            cond_color = cond_map.get(a.condition or "", "#374151")

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(a.asset_code))
            self._table.setItem(i, 2, _item(a.name))
            self._table.setItem(i, 3, _item(a.category_name))
            self._table.setItem(i, 4, _item(a.dept_name))
            self._table.setItem(i, 5, _item(a.serial_number))
            self._table.add_badge_cell(i, 6, a.status.capitalize(), bg, fg)

            # Condition with color
            cond_item = QTableWidgetItem((a.condition or "—").capitalize())
            cond_item.setFlags(cond_item.flags() & ~Qt.ItemIsEditable)
            from PySide6.QtGui import QColor
            cond_item.setForeground(QColor(cond_color))
            self._table.setItem(i, 7, cond_item)

            aid = a.id
            actions = [
                ("View",  "🔍", lambda _, x=aid: self._on_view(x)),
                ("Edit",  "✏️", lambda _, x=aid: self._on_edit(x)),
                ("Delete","🗑️", lambda _, x=aid: self._on_delete(x)),
            ]
            self._table.add_action_cell(i, 8, actions)

        shown = len(self._assets)
        extra = f" of {total}" if total > shown else ""
        self._count_lbl.setText(f"{shown}{extra} asset{'s' if shown != 1 else ''}")

    def _update_stat_pills(self) -> None:
        try:
            counts = self._service.count_by_status(current_session.org_id)
            labels = {
                "available": "Available", "issued": "Issued",
                "maintenance": "Maintenance", "disposed": "Disposed", "lost": "Lost",
            }
            for key, pill in self._stat_pills.items():
                cnt = counts.get(key, 0)
                pill.setText(f"{labels[key]}: {cnt}")
        except Exception:
            pass

    # ── Actions ───────────────────────────────────────────────────────────────

    def _clear_filters(self) -> None:
        self._status_filter.setCurrentIndex(0)
        self._cat_filter.setCurrentIndex(0)
        self._dept_filter.setCurrentIndex(0)
        self._search.clear()

    def _on_create(self) -> None:
        dlg = AssetFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit(
                "Success", "Asset registered successfully.", "success"
            )
            app_signals.refresh_dashboard.emit()

    def _on_view(self, asset_id: int) -> None:
        asset = next((a for a in self._assets if a.id == asset_id), None)
        if asset:
            dlg = AssetDetailDialog(asset, parent=self)
            dlg.exec()

    def _on_edit(self, asset_id: int) -> None:
        asset = next((a for a in self._assets if a.id == asset_id), None)
        if not asset:
            return
        dlg = AssetFormDialog(asset=asset, parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit("Success", "Asset updated.", "success")

    def _on_delete(self, asset_id: int) -> None:
        asset = next((a for a in self._assets if a.id == asset_id), None)
        if not asset:
            return
        dlg = ConfirmDialog(
            title="Delete Asset",
            message=f"Permanently delete asset '{asset.name}' ({asset.asset_code})?\n\n"
                    "This action cannot be undone. "
                    "Issued assets cannot be deleted.",
            confirm_label="Delete", danger=True, parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._service.delete(asset_id)
                app_signals.asset_deleted.emit(asset_id)
                app_signals.show_notification.emit(
                    "Deleted", f"'{asset.name}' removed.", "info"
                )
                app_signals.refresh_dashboard.emit()
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._assets):
            self._on_view(self._assets[row].id)
