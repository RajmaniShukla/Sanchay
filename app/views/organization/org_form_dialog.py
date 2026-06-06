"""
Sanchay — Organization Form Dialog
=====================================
Create / Edit organization dialog.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTextEdit, QFormLayout, QWidget,
)
from PySide6.QtCore import Qt

from app.views.widgets.form_dialog import FormDialog
from app.services.organization_service import OrganizationService
from app.core.signals import app_signals
from app.models.organization import Organization
from app.constants import OrgType


class OrgFormDialog(FormDialog):
    """Create or edit an Organization."""

    def __init__(self, org: Optional[Organization] = None, parent=None):
        self._org = org
        self._service = OrganizationService()
        mode = "Edit Organization" if org else "New Organization"
        subtitle = f"Editing: {org.name}" if org else "Fill in the details below"
        super().__init__(mode, subtitle, "Save Organization", parent,
                         min_width=580, min_height=560)
        if org:
            self._populate(org)

    def _build_form(self, layout: QVBoxLayout) -> None:
        # ── Section: Basic Info ────────────────────────────────────────────────
        layout.addWidget(self.make_section("Basic Information"))

        basic_form = QFormLayout()
        basic_form.setSpacing(12)
        basic_form.setLabelAlignment(Qt.AlignLeft)
        basic_form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        basic_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("e.g. Acme Technologies Pvt. Ltd.")
        self.f_name.setFixedHeight(38)
        self._style_input(self.f_name)

        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText("e.g. ACME")
        self.f_code.setMaxLength(10)
        self.f_code.setFixedHeight(38)
        self._style_input(self.f_code)

        self.f_type = QComboBox()
        self.f_type.setFixedHeight(38)
        self._style_combo(self.f_type)
        for ot in OrgType:
            self.f_type.addItem(ot.label(), ot.value)

        basic_form.addRow(self.make_label("Organization Name", required=True), self.f_name)
        basic_form.addRow(self.make_label("Short Code", required=True), self.f_code)
        basic_form.addRow(self.make_label("Type", required=True), self.f_type)
        layout.addLayout(basic_form)

        layout.addWidget(self.make_divider())

        # ── Section: Address ──────────────────────────────────────────────────
        layout.addWidget(self.make_section("Address & Contact"))

        contact_form = QFormLayout()
        contact_form.setSpacing(12)
        contact_form.setLabelAlignment(Qt.AlignLeft)
        contact_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_address = QTextEdit()
        self.f_address.setFixedHeight(68)
        self.f_address.setPlaceholderText("Street address, building, area…")
        self.f_address.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 8px; font-size: 13px; color: #0F172A;
            }
            QTextEdit:focus { border: 2px solid #2563EB; padding: 7px; }
        """)

        # Two-column row: City | State
        city_state = QHBoxLayout()
        city_state.setSpacing(10)
        self.f_city = QLineEdit()
        self.f_city.setPlaceholderText("City")
        self.f_city.setFixedHeight(38)
        self._style_input(self.f_city)
        self.f_state = QLineEdit()
        self.f_state.setPlaceholderText("State")
        self.f_state.setFixedHeight(38)
        self._style_input(self.f_state)
        city_state.addWidget(self.f_city)
        city_state.addWidget(self.f_state)

        # Pincode | Country
        pin_country = QHBoxLayout()
        pin_country.setSpacing(10)
        self.f_pincode = QLineEdit()
        self.f_pincode.setPlaceholderText("PIN / ZIP")
        self.f_pincode.setMaxLength(10)
        self.f_pincode.setFixedHeight(38)
        self._style_input(self.f_pincode)
        self.f_country = QLineEdit()
        self.f_country.setPlaceholderText("Country")
        self.f_country.setText("India")
        self.f_country.setFixedHeight(38)
        self._style_input(self.f_country)
        pin_country.addWidget(self.f_pincode)
        pin_country.addWidget(self.f_country)

        # Phone | Email
        phone_email = QHBoxLayout()
        phone_email.setSpacing(10)
        self.f_phone = QLineEdit()
        self.f_phone.setPlaceholderText("+91 98765 43210")
        self.f_phone.setFixedHeight(38)
        self._style_input(self.f_phone)
        self.f_email = QLineEdit()
        self.f_email.setPlaceholderText("contact@example.com")
        self.f_email.setFixedHeight(38)
        self._style_input(self.f_email)
        phone_email.addWidget(self.f_phone)
        phone_email.addWidget(self.f_email)

        self.f_website = QLineEdit()
        self.f_website.setPlaceholderText("https://www.example.com")
        self.f_website.setFixedHeight(38)
        self._style_input(self.f_website)

        city_w = QWidget(); city_w.setLayout(city_state); city_w.setStyleSheet("background:white;")
        pin_w  = QWidget(); pin_w.setLayout(pin_country); pin_w.setStyleSheet("background:white;")
        ph_w   = QWidget(); ph_w.setLayout(phone_email);  ph_w.setStyleSheet("background:white;")

        contact_form.addRow(self.make_label("Address"), self.f_address)
        contact_form.addRow(self.make_label("City / State"), city_w)
        contact_form.addRow(self.make_label("PIN / Country"), pin_w)
        contact_form.addRow(self.make_label("Phone / Email"), ph_w)
        contact_form.addRow(self.make_label("Website"), self.f_website)
        layout.addLayout(contact_form)

        layout.addWidget(self.make_divider())

        # ── Description ────────────────────────────────────────────────────────
        layout.addWidget(self.make_label("Description / Notes"))
        self.f_desc = QTextEdit()
        self.f_desc.setFixedHeight(72)
        self.f_desc.setPlaceholderText("Optional description about this organization…")
        self.f_desc.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 8px; font-size: 13px; color: #0F172A;
            }
            QTextEdit:focus { border: 2px solid #2563EB; padding: 7px; }
        """)
        layout.addWidget(self.f_desc)
        layout.addStretch()

    def _populate(self, org: Organization) -> None:
        self.f_name.setText(org.name or "")
        self.f_code.setText(org.code or "")
        # Set type combo
        for i in range(self.f_type.count()):
            if self.f_type.itemData(i) == org.org_type:
                self.f_type.setCurrentIndex(i)
                break
        self.f_address.setPlainText(org.address or "")
        self.f_city.setText(org.city or "")
        self.f_state.setText(org.state or "")
        self.f_pincode.setText(org.pincode or "")
        self.f_country.setText(org.country or "India")
        self.f_phone.setText(org.phone or "")
        self.f_email.setText(org.email or "")
        self.f_website.setText(org.website or "")
        self.f_desc.setPlainText(org.description or "")

    def _collect_data(self):
        name = self.f_name.text().strip()
        code = self.f_code.text().strip().upper()

        if not name:
            self.set_error("Organization name is required.")
            self.f_name.setFocus()
            return None
        if not code or len(code) < 2:
            self.set_error("Short code must be at least 2 characters.")
            self.f_code.setFocus()
            return None

        return {
            "name":        name,
            "code":        code,
            "org_type":    self.f_type.currentData(),
            "address":     self.f_address.toPlainText().strip() or None,
            "city":        self.f_city.text().strip() or None,
            "state":       self.f_state.text().strip() or None,
            "pincode":     self.f_pincode.text().strip() or None,
            "country":     self.f_country.text().strip() or "India",
            "phone":       self.f_phone.text().strip() or None,
            "email":       self.f_email.text().strip() or None,
            "website":     self.f_website.text().strip() or None,
            "description": self.f_desc.toPlainText().strip() or None,
        }

    def _on_save(self, data: dict) -> None:
        if self._org:
            self._service.update(self._org.id, data)
            app_signals.org_updated.emit(self._org.id)
        else:
            org = self._service.create(**data)
            app_signals.org_created.emit(org.id)
        self.accept()

    @staticmethod
    def _style_input(widget) -> None:
        widget.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 13px; color: #0F172A;
                background: white;
            }
            QLineEdit:focus { border: 2px solid #2563EB; padding: 0 9px; }
        """)

    @staticmethod
    def _style_combo(widget) -> None:
        widget.setStyleSheet("""
            QComboBox {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 13px; color: #0F172A;
                background: white;
            }
            QComboBox:focus { border: 2px solid #2563EB; }
            QComboBox::drop-down { border: none; width: 20px; }
        """)
