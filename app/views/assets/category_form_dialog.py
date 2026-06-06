"""
Sanchay — Asset Category Form Dialog
=======================================
Create / Edit an asset category (hierarchical).
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QLineEdit, QComboBox, QTextEdit,
    QFormLayout, QDoubleSpinBox, QSpinBox,
)
from PySide6.QtCore import Qt

from app.views.widgets.form_dialog import FormDialog
from app.services.asset_service import AssetCategoryService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.asset import AssetCategory


class CategoryFormDialog(FormDialog):
    """Create or edit an Asset Category."""

    def __init__(self, cat: Optional[AssetCategory] = None, parent=None):
        self._cat     = cat
        self._service = AssetCategoryService()
        mode     = "Edit Category" if cat else "New Asset Category"
        subtitle = f"Editing: {cat.name}" if cat else "Define a new asset category"
        super().__init__(mode, subtitle, "Save Category", parent,
                         min_width=480, min_height=440)
        if cat:
            self._populate(cat)

    def _build_form(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self.make_section("Category Details"))

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("e.g. Electronics, Furniture, Vehicles")
        self.f_name.setFixedHeight(38)
        self._style(self.f_name)

        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText("e.g. ELEC, FURN (unique code)")
        self.f_code.setMaxLength(20)
        self.f_code.setFixedHeight(38)
        self._style(self.f_code)

        self.f_parent = QComboBox()
        self.f_parent.setFixedHeight(38)
        self._style_combo(self.f_parent)
        self.f_parent.addItem("— None (Top-level) —", None)
        try:
            org_id = current_session.org_id
            cats   = self._service.get_all(org_id)
            for c in cats:
                if self._cat and c.id == self._cat.id:
                    continue
                self.f_parent.addItem(f"{c.name} ({c.code})", c.id)
        except Exception:
            pass

        self.f_desc = QTextEdit()
        self.f_desc.setFixedHeight(72)
        self.f_desc.setPlaceholderText("Optional description…")
        self._style_textedit(self.f_desc)

        form.addRow(self.make_label("Category Name", required=True), self.f_name)
        form.addRow(self.make_label("Code",          required=True), self.f_code)
        form.addRow(self.make_label("Parent Category"),              self.f_parent)
        form.addRow(self.make_label("Description"),                  self.f_desc)
        layout.addLayout(form)

        layout.addWidget(self.make_divider())
        layout.addWidget(self.make_section("Depreciation (Optional)"))

        dep_form = QFormLayout()
        dep_form.setSpacing(14)
        dep_form.setLabelAlignment(Qt.AlignLeft)
        dep_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_depr = QDoubleSpinBox()
        self.f_depr.setRange(0, 100)
        self.f_depr.setDecimals(2)
        self.f_depr.setSuffix(" % per year")
        self.f_depr.setFixedHeight(38)
        self.f_depr.setStyleSheet(self._spin_css())
        self.f_depr.setSpecialValueText("Not set")

        self.f_life = QSpinBox()
        self.f_life.setRange(0, 100)
        self.f_life.setSuffix(" years")
        self.f_life.setFixedHeight(38)
        self.f_life.setStyleSheet(self._spin_css())
        self.f_life.setSpecialValueText("Not set")

        dep_form.addRow(self.make_label("Annual Depreciation Rate"), self.f_depr)
        dep_form.addRow(self.make_label("Expected Useful Life"),      self.f_life)
        layout.addLayout(dep_form)
        layout.addStretch()

    def _populate(self, cat: AssetCategory) -> None:
        self.f_name.setText(cat.name or "")
        self.f_code.setText(cat.code or "")
        self.f_desc.setPlainText(cat.description or "")
        if cat.parent_category_id:
            for i in range(self.f_parent.count()):
                if self.f_parent.itemData(i) == cat.parent_category_id:
                    self.f_parent.setCurrentIndex(i)
                    break
        if cat.depreciation_rate:
            self.f_depr.setValue(float(cat.depreciation_rate))
        if cat.useful_life_years:
            self.f_life.setValue(cat.useful_life_years)

    def _collect_data(self):
        name = self.f_name.text().strip()
        code = self.f_code.text().strip().upper()
        if not name:
            self.set_error("Category name is required.")
            self.f_name.setFocus()
            return None
        if not code or len(code) < 2:
            self.set_error("Code must be at least 2 characters.")
            self.f_code.setFocus()
            return None
        return {
            "name":               name,
            "code":               code,
            "org_id":             current_session.org_id,
            "parent_category_id": self.f_parent.currentData(),
            "description":        self.f_desc.toPlainText().strip() or None,
            "depreciation_rate":  self.f_depr.value() or None,
            "useful_life_years":  self.f_life.value() or None,
        }

    def _on_save(self, data: dict) -> None:
        if self._cat:
            self._service.update(self._cat.id, data)
            app_signals.category_updated.emit(self._cat.id)
        else:
            c = self._service.create(**data)
            app_signals.category_created.emit(c.id)
        self.accept()

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _style(w) -> None:
        w.setStyleSheet("""
            QLineEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; color:#0F172A; background:white;
            }
            QLineEdit:focus { border:2px solid #2563EB; padding:0 9px; }
        """)

    @staticmethod
    def _style_combo(w) -> None:
        w.setStyleSheet("""
            QComboBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QComboBox:focus { border:2px solid #2563EB; }
            QComboBox::drop-down { border:none; width:20px; }
        """)

    @staticmethod
    def _style_textedit(w) -> None:
        w.setStyleSheet("""
            QTextEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:8px; font-size:13px;
            }
            QTextEdit:focus { border:2px solid #2563EB; padding:7px; }
        """)

    @staticmethod
    def _spin_css() -> str:
        return """
            QDoubleSpinBox, QSpinBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QDoubleSpinBox:focus, QSpinBox:focus { border:2px solid #2563EB; }
        """
