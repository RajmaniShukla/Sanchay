"""
Sanchay — Asset Category List View
=====================================
Hierarchical asset category management with CRUD.
Shows parent → child indentation in the table for clarity.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QDialog, QTableWidgetItem,
)
from PySide6.QtCore import Qt

from app.services.asset_service import AssetCategoryService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.asset import AssetCategory
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from app.views.widgets.confirm_dialog import ConfirmDialog
from app.views.assets.category_form_dialog import CategoryFormDialog
from loguru import logger


class CategoryListView(QWidget):
    """Asset category management — hierarchical display, full CRUD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = AssetCategoryService()
        self._cats: list[AssetCategory] = []
        self._build_ui()
        self._load()

        app_signals.category_created.connect(lambda _: self._load())
        app_signals.category_updated.connect(lambda _: self._load())

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

        self._search = SearchBar("Search categories…")
        self._search.set_min_width(260)
        self._search.search_changed.connect(self._on_search)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        add_btn = QPushButton("+ New Category")
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

        # ── Info strip ─────────────────────────────────────────────────────────
        info = QFrame()
        info.setStyleSheet("background:#EFF6FF; border-bottom:1px solid #BFDBFE;")
        info.setFixedHeight(36)
        i_lay = QHBoxLayout(info)
        i_lay.setContentsMargins(24, 0, 24, 0)
        tip = QLabel("💡  Categories can be nested. Child categories inherit the parent's settings. "
                     "Sub-categories are indented with '↳' in the table.")
        tip.setStyleSheet("color:#1D4ED8; font-size:12px;")
        i_lay.addWidget(tip)
        layout.addWidget(info)

        # ── Table ──────────────────────────────────────────────────────────────
        cols = ["#", "Category Name", "Code", "Parent", "Depreciation %", "Life (yrs)", "Assets", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths({0: 44, 2: 90, 3: 160, 4: 120, 5: 90, 6: 80, 7: 160})
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
            org_id = current_session.org_id
            all_cats = self._service.get_all(org_id)
            if query:
                q = query.lower()
                all_cats = [c for c in all_cats
                            if q in c.name.lower() or q in c.code.lower()]
            # Sort: parents first, then children (simple flat sort for now)
            self._cats = sorted(all_cats, key=lambda c: (
                c.parent_category_id or 0, c.name
            ))
            self._render()
        except Exception as e:
            logger.error(f"Category load error: {e}")

    def _render(self) -> None:
        self._table.setRowCount(0)

        for i, cat in enumerate(self._cats):
            self._table.insertRow(i)

            def _item(val, bold=False):
                it = QTableWidgetItem(str(val) if val is not None else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if bold:
                    from PySide6.QtGui import QFont
                    f = it.font(); f.setBold(True); it.setFont(f)
                return it

            is_child  = cat.parent_category_id is not None
            name_str  = f"  ↳ {cat.name}" if is_child else cat.name
            parent_str = cat.parent.name if cat.parent else "—"
            depr_str  = f"{cat.depreciation_rate:.1f}%" if cat.depreciation_rate else "—"
            life_str  = str(cat.useful_life_years) if cat.useful_life_years else "—"
            asset_cnt = len(cat.assets) if hasattr(cat, "assets") else "—"

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(name_str, bold=not is_child))
            self._table.setItem(i, 2, _item(cat.code))
            self._table.setItem(i, 3, _item(parent_str))
            self._table.setItem(i, 4, _item(depr_str))
            self._table.setItem(i, 5, _item(life_str))
            self._table.setItem(i, 6, _item(asset_cnt))

            cid = cat.id
            self._table.add_action_cell(i, 7, [
                ("Edit",   "✏️", lambda _, x=cid: self._on_edit(x)),
                ("Delete", "🗑️", lambda _, x=cid: self._on_delete(x)),
            ])

        self._count_lbl.setText(
            f"{len(self._cats)} categor{'ies' if len(self._cats) != 1 else 'y'}"
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_search(self, query: str) -> None:
        self._load(query)

    def _on_create(self) -> None:
        dlg = CategoryFormDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit("Success", "Category created.", "success")

    def _on_edit(self, cat_id: int) -> None:
        cat = next((c for c in self._cats if c.id == cat_id), None)
        if not cat:
            return
        dlg = CategoryFormDialog(cat=cat, parent=self)
        if dlg.exec() == QDialog.Accepted:
            app_signals.show_notification.emit("Success", "Category updated.", "success")

    def _on_delete(self, cat_id: int) -> None:
        cat = next((c for c in self._cats if c.id == cat_id), None)
        if not cat:
            return
        dlg = ConfirmDialog(
            title="Delete Category",
            message=f"Delete category '{cat.name}'?\n\n"
                    "This will fail if any assets are assigned to it.",
            confirm_label="Delete", danger=True, parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._service.delete(cat_id)
                app_signals.category_updated.emit(cat_id)
                app_signals.show_notification.emit("Deleted", f"'{cat.name}' removed.", "info")
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")

    def _on_row_double_click(self, row: int) -> None:
        if row < len(self._cats):
            self._on_edit(self._cats[row].id)
