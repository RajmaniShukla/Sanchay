"""
Sanchay — Asset Form Dialog
==============================
Create / Edit asset — 3 tabs: Identity · Specifications · Financial
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QTextEdit,
    QFormLayout, QWidget, QTabWidget, QDateEdit, QLabel,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt, QDate

from app.views.widgets.form_dialog import FormDialog
from app.services.asset_service import AssetService, AssetCategoryService
from app.services.organization_service import DepartmentService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.asset import Asset
from app.constants import AssetCondition


class AssetFormDialog(FormDialog):
    """Create or edit an Asset."""

    def __init__(self, asset: Optional[Asset] = None, parent=None):
        self._asset    = asset
        self._service  = AssetService()
        self._cat_svc  = AssetCategoryService()
        self._dept_svc = DepartmentService()

        mode     = "Edit Asset" if asset else "Register New Asset"
        subtitle = f"Editing: {asset.name} ({asset.asset_code})" if asset else \
                   "Fill in the details to register a new asset"
        super().__init__(mode, subtitle, "Save Asset", parent,
                         min_width=600, min_height=540)
        if asset:
            self._populate(asset)

    # ── Shell form ────────────────────────────────────────────────────────────

    def _build_form(self, layout: QVBoxLayout) -> None:
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border:1px solid #E2E8F0; border-radius:8px; background:white;
            }
            QTabBar::tab {
                padding:8px 20px; border:none;
                border-bottom:2px solid transparent;
                color:#64748B; font-weight:500; background:transparent;
            }
            QTabBar::tab:selected {
                color:#2563EB; border-bottom:2px solid #2563EB; font-weight:600;
            }
            QTabBar::tab:hover:!selected { color:#374151; }
        """)
        self._tabs.addTab(self._build_tab_identity(),  "📦  Identity")
        self._tabs.addTab(self._build_tab_specs(),     "🔧  Specifications")
        self._tabs.addTab(self._build_tab_financial(), "💰  Financial")
        layout.addWidget(self._tabs)

    # ── Tab 1: Identity ───────────────────────────────────────────────────────

    def _build_tab_identity(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("e.g. Dell Latitude 5520 Laptop")
        self.f_name.setFixedHeight(38)
        self._si(self.f_name)

        # Code with "Auto" hint
        code_row = QHBoxLayout()
        code_row.setSpacing(8)
        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText("Auto-generated if left blank")
        self.f_code.setFixedHeight(38)
        self._si(self.f_code)
        auto_lbl = QLabel("Leave blank to auto-generate")
        auto_lbl.setStyleSheet("color:#64748B; font-size:11px;")
        code_row.addWidget(self.f_code)
        code_w = QWidget(); code_w.setLayout(code_row); code_w.setStyleSheet("background:white;")

        self.f_category = QComboBox()
        self.f_category.setFixedHeight(38)
        self._sc(self.f_category)
        self.f_category.addItem("— Select Category —", None)
        try:
            cats = self._cat_svc.get_all(current_session.org_id)
            for c in cats:
                indent = "  ↳ " if c.parent_category_id else ""
                self.f_category.addItem(f"{indent}{c.name} ({c.code})", c.id)
        except Exception:
            pass

        self.f_dept = QComboBox()
        self.f_dept.setFixedHeight(38)
        self._sc(self.f_dept)
        self.f_dept.addItem("— Select Department —", None)
        try:
            depts = self._dept_svc.get_by_org(current_session.org_id)
            for d in depts:
                self.f_dept.addItem(f"{d.name} ({d.code})", d.id)
        except Exception:
            pass

        self.f_location = QLineEdit()
        self.f_location.setPlaceholderText("e.g. Server Room, Lab 3, Floor 2")
        self.f_location.setFixedHeight(38)
        self._si(self.f_location)

        self.f_condition = QComboBox()
        self.f_condition.setFixedHeight(38)
        self._sc(self.f_condition)
        for cond in AssetCondition:
            self.f_condition.addItem(cond.label(), cond.value)

        self.f_desc = QTextEdit()
        self.f_desc.setFixedHeight(72)
        self.f_desc.setPlaceholderText("Optional notes or description about this asset…")
        self._ste(self.f_desc)

        form.addRow(self.make_label("Asset Name",    required=True), self.f_name)
        form.addRow(self.make_label("Asset Code"),                   code_w)
        form.addRow(self.make_label("Category"),                     self.f_category)
        form.addRow(self.make_label("Department"),                   self.f_dept)
        form.addRow(self.make_label("Location"),                     self.f_location)
        form.addRow(self.make_label("Condition"),                    self.f_condition)
        form.addRow(self.make_label("Description"),                  self.f_desc)
        return w

    # ── Tab 2: Specifications ─────────────────────────────────────────────────

    def _build_tab_specs(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_serial = QLineEdit()
        self.f_serial.setPlaceholderText("Manufacturer serial number")
        self.f_serial.setFixedHeight(38)
        self._si(self.f_serial)

        self.f_model = QLineEdit()
        self.f_model.setPlaceholderText("e.g. Latitude 5520")
        self.f_model.setFixedHeight(38)
        self._si(self.f_model)

        self.f_manufacturer = QLineEdit()
        self.f_manufacturer.setPlaceholderText("e.g. Dell, HP, Lenovo, Samsung")
        self.f_manufacturer.setFixedHeight(38)
        self._si(self.f_manufacturer)

        self.f_supplier = QLineEdit()
        self.f_supplier.setPlaceholderText("Vendor / supplier name")
        self.f_supplier.setFixedHeight(38)
        self._si(self.f_supplier)

        form.addRow(self.make_label("Serial Number"),  self.f_serial)
        form.addRow(self.make_label("Model Number"),   self.f_model)
        form.addRow(self.make_label("Manufacturer"),   self.f_manufacturer)
        form.addRow(self.make_label("Supplier"),       self.f_supplier)
        return w

    # ── Tab 3: Financial ──────────────────────────────────────────────────────

    def _build_tab_financial(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        date_style = """
            QDateEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QDateEdit:focus { border:2px solid #2563EB; }
        """

        self.f_purchase_date = QDateEdit()
        self.f_purchase_date.setCalendarPopup(True)
        self.f_purchase_date.setDisplayFormat("dd/MM/yyyy")
        self.f_purchase_date.setDate(QDate.currentDate())
        self.f_purchase_date.setFixedHeight(38)
        self.f_purchase_date.setStyleSheet(date_style)

        self.f_purchase_price = QDoubleSpinBox()
        self.f_purchase_price.setRange(0, 99_999_999)
        self.f_purchase_price.setDecimals(2)
        self.f_purchase_price.setPrefix("₹ ")
        self.f_purchase_price.setGroupSeparatorShown(True)
        self.f_purchase_price.setFixedHeight(38)
        self.f_purchase_price.setStyleSheet(self._spin_css())
        self.f_purchase_price.setSpecialValueText("Not specified")

        self.f_current_value = QDoubleSpinBox()
        self.f_current_value.setRange(0, 99_999_999)
        self.f_current_value.setDecimals(2)
        self.f_current_value.setPrefix("₹ ")
        self.f_current_value.setGroupSeparatorShown(True)
        self.f_current_value.setFixedHeight(38)
        self.f_current_value.setStyleSheet(self._spin_css())
        self.f_current_value.setSpecialValueText("Not specified")

        self.f_warranty = QDateEdit()
        self.f_warranty.setCalendarPopup(True)
        self.f_warranty.setDisplayFormat("dd/MM/yyyy")
        self.f_warranty.setDate(QDate.currentDate().addYears(1))
        self.f_warranty.setFixedHeight(38)
        self.f_warranty.setStyleSheet(date_style)

        # Warranty status indicator
        self._warranty_status_lbl = QLabel("")
        self._warranty_status_lbl.setStyleSheet("font-size:11px; color:#64748B;")
        self.f_warranty.dateChanged.connect(self._update_warranty_status)
        self._update_warranty_status(self.f_warranty.date())

        form.addRow(self.make_label("Purchase Date"),    self.f_purchase_date)
        form.addRow(self.make_label("Purchase Price"),   self.f_purchase_price)
        form.addRow(self.make_label("Current Value"),    self.f_current_value)
        form.addRow(self.make_label("Warranty Expiry"),  self.f_warranty)
        form.addRow("", self._warranty_status_lbl)
        return w

    def _update_warranty_status(self, qdate) -> None:
        from datetime import date
        d = date(qdate.year(), qdate.month(), qdate.day())
        today = date.today()
        diff  = (d - today).days
        if diff > 0:
            self._warranty_status_lbl.setText(f"✅  Valid — expires in {diff} day(s)")
            self._warranty_status_lbl.setStyleSheet("font-size:11px; color:#15803D;")
        else:
            self._warranty_status_lbl.setText(f"❌  Expired {abs(diff)} day(s) ago")
            self._warranty_status_lbl.setStyleSheet("font-size:11px; color:#DC2626;")

    # ── Populate (Edit) ───────────────────────────────────────────────────────

    def _populate(self, a: Asset) -> None:
        self.f_name.setText(a.name or "")
        self.f_code.setText(a.asset_code or "")
        for i in range(self.f_category.count()):
            if self.f_category.itemData(i) == a.category_id:
                self.f_category.setCurrentIndex(i); break
        for i in range(self.f_dept.count()):
            if self.f_dept.itemData(i) == a.dept_id:
                self.f_dept.setCurrentIndex(i); break
        for i in range(self.f_condition.count()):
            if self.f_condition.itemData(i) == a.condition:
                self.f_condition.setCurrentIndex(i); break
        self.f_location.setText(a.location or "")
        self.f_desc.setPlainText(a.description or "")
        # Specs
        self.f_serial.setText(a.serial_number or "")
        self.f_model.setText(a.model_number or "")
        self.f_manufacturer.setText(a.manufacturer or "")
        self.f_supplier.setText(a.supplier or "")
        # Financial
        if a.purchase_date:
            self.f_purchase_date.setDate(
                QDate(a.purchase_date.year, a.purchase_date.month, a.purchase_date.day))
        if a.purchase_price:
            self.f_purchase_price.setValue(float(a.purchase_price))
        if a.current_value:
            self.f_current_value.setValue(float(a.current_value))
        if a.warranty_expiry_date:
            self.f_warranty.setDate(
                QDate(a.warranty_expiry_date.year,
                      a.warranty_expiry_date.month,
                      a.warranty_expiry_date.day))

    # ── Collect & Save ────────────────────────────────────────────────────────

    def _collect_data(self):
        name = self.f_name.text().strip()
        if not name:
            self.set_error("Asset name is required.")
            self._tabs.setCurrentIndex(0)
            self.f_name.setFocus()
            return None

        from datetime import date
        def _qdate(qd):
            return date(qd.year(), qd.month(), qd.day())

        price = self.f_purchase_price.value()
        cur_val = self.f_current_value.value()

        return {
            "name":                 name,
            "asset_code":           self.f_code.text().strip() or None,
            "category_id":          self.f_category.currentData(),
            "dept_id":              self.f_dept.currentData(),
            "org_id":               current_session.org_id,
            "location":             self.f_location.text().strip() or None,
            "condition":            self.f_condition.currentData(),
            "description":          self.f_desc.toPlainText().strip() or None,
            "serial_number":        self.f_serial.text().strip() or None,
            "model_number":         self.f_model.text().strip() or None,
            "manufacturer":         self.f_manufacturer.text().strip() or None,
            "supplier":             self.f_supplier.text().strip() or None,
            "purchase_date":        _qdate(self.f_purchase_date.date()),
            "purchase_price":       price if price > 0 else None,
            "current_value":        cur_val if cur_val > 0 else None,
            "warranty_expiry_date": _qdate(self.f_warranty.date()),
        }

    def _on_save(self, data: dict) -> None:
        if self._asset:
            self._service.update(self._asset.id, data)
            app_signals.asset_updated.emit(self._asset.id)
        else:
            a = self._service.create(**data)
            app_signals.asset_created.emit(a.id)
        self.accept()

    # ── Style helpers ─────────────────────────────────────────────────────────

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

    @staticmethod
    def _ste(w) -> None:
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
            QDoubleSpinBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QDoubleSpinBox:focus { border:2px solid #2563EB; }
        """
