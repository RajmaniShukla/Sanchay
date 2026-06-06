"""
Sanchay — Person Form Dialog
===============================
Create / Edit dialog for any person type.
Organized into 3 tabs: Basic, Contact & Address, Details.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QTextEdit,
    QFormLayout, QWidget, QTabWidget, QDateEdit, QLabel,
)
from PySide6.QtCore import Qt, QDate

from app.views.widgets.form_dialog import FormDialog
from app.services.person_service import PersonService
from app.services.organization_service import DepartmentService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.person import Person
from app.constants import PersonType, ID_PROOF_TYPES


class PersonFormDialog(FormDialog):
    """Create or edit a Person (any type)."""

    def __init__(
        self,
        person: Optional[Person] = None,
        initial_type: str = "employee",
        parent=None,
    ):
        self._person       = person
        self._initial_type = person.person_type if person else initial_type
        self._svc          = PersonService()
        self._dept_svc     = DepartmentService()

        mode     = "Edit Person" if person else "Add New Person"
        subtitle = f"Editing: {person.full_name}" if person else "Fill in the details below"
        super().__init__(mode, subtitle, "Save Person", parent,
                         min_width=580, min_height=520)
        if person:
            self._populate(person)

    def _build_form(self, layout: QVBoxLayout) -> None:
        # Tab widget holds all sections
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0; border-radius: 8px; background: white;
            }
            QTabBar::tab {
                padding: 8px 20px; border: none; border-bottom: 2px solid transparent;
                color: #64748B; font-weight: 500; background: transparent;
            }
            QTabBar::tab:selected {
                color: #2563EB; border-bottom: 2px solid #2563EB; font-weight: 600;
            }
            QTabBar::tab:hover:!selected { color: #374151; }
        """)
        self._tabs.addTab(self._build_tab_basic(),   "👤  Basic Info")
        self._tabs.addTab(self._build_tab_contact(), "📞  Contact & Address")
        self._tabs.addTab(self._build_tab_details(), "📋  Details")
        layout.addWidget(self._tabs)

    # ── Tab 1: Basic Info ─────────────────────────────────────────────────────

    def _build_tab_basic(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Person type
        self.f_type = QComboBox()
        self.f_type.setFixedHeight(38)
        self._style_combo(self.f_type)
        for pt in PersonType:
            self.f_type.addItem(pt.label(), pt.value)
        # Select initial type
        for i in range(self.f_type.count()):
            if self.f_type.itemData(i) == self._initial_type:
                self.f_type.setCurrentIndex(i)
                break

        # First / Last name row
        name_row = QHBoxLayout()
        name_row.setSpacing(10)
        self.f_first = QLineEdit()
        self.f_first.setPlaceholderText("First name *")
        self.f_first.setFixedHeight(38)
        self._style_input(self.f_first)
        self.f_last = QLineEdit()
        self.f_last.setPlaceholderText("Last name")
        self.f_last.setFixedHeight(38)
        self._style_input(self.f_last)
        name_row.addWidget(self.f_first)
        name_row.addWidget(self.f_last)
        name_w = QWidget(); name_w.setLayout(name_row); name_w.setStyleSheet("background:white;")

        # Department
        self.f_dept = QComboBox()
        self.f_dept.setFixedHeight(38)
        self._style_combo(self.f_dept)
        self.f_dept.addItem("— Select Department —", None)
        try:
            org_id = current_session.org_id
            if org_id:
                depts = self._dept_svc.get_by_org(org_id)
                for d in depts:
                    self.f_dept.addItem(f"{d.name} ({d.code})", d.id)
        except Exception:
            pass

        # Designation
        self.f_designation = QLineEdit()
        self.f_designation.setPlaceholderText("e.g. Software Engineer, B.Tech CSE, Plumber")
        self.f_designation.setFixedHeight(38)
        self._style_input(self.f_designation)

        form.addRow(self.make_label("Person Type", required=True),  self.f_type)
        form.addRow(self.make_label("Full Name", required=True),    name_w)
        form.addRow(self.make_label("Department"),                  self.f_dept)
        form.addRow(self.make_label("Designation / Role"),          self.f_designation)
        return w

    # ── Tab 2: Contact & Address ──────────────────────────────────────────────

    def _build_tab_contact(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Email / Phone row
        ep_row = QHBoxLayout()
        ep_row.setSpacing(10)
        self.f_email = QLineEdit()
        self.f_email.setPlaceholderText("email@example.com")
        self.f_email.setFixedHeight(38)
        self._style_input(self.f_email)
        self.f_phone = QLineEdit()
        self.f_phone.setPlaceholderText("+91 98765 43210")
        self.f_phone.setFixedHeight(38)
        self._style_input(self.f_phone)
        ep_row.addWidget(self.f_email)
        ep_row.addWidget(self.f_phone)
        ep_w = QWidget(); ep_w.setLayout(ep_row); ep_w.setStyleSheet("background:white;")

        self.f_address = QTextEdit()
        self.f_address.setFixedHeight(70)
        self.f_address.setPlaceholderText("House / flat / street…")
        self.f_address.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 8px; font-size: 13px;
            }
            QTextEdit:focus { border: 2px solid #2563EB; padding: 7px; }
        """)

        # City / State
        cs_row = QHBoxLayout()
        cs_row.setSpacing(10)
        self.f_city = QLineEdit()
        self.f_city.setPlaceholderText("City")
        self.f_city.setFixedHeight(38)
        self._style_input(self.f_city)
        self.f_state = QLineEdit()
        self.f_state.setPlaceholderText("State")
        self.f_state.setFixedHeight(38)
        self._style_input(self.f_state)
        cs_row.addWidget(self.f_city)
        cs_row.addWidget(self.f_state)
        cs_w = QWidget(); cs_w.setLayout(cs_row); cs_w.setStyleSheet("background:white;")

        form.addRow(self.make_label("Email / Phone"),     ep_w)
        form.addRow(self.make_label("Address"),           self.f_address)
        form.addRow(self.make_label("City / State"),      cs_w)
        return w

    # ── Tab 3: Details ────────────────────────────────────────────────────────

    def _build_tab_details(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: white;")
        form = QFormLayout(w)
        form.setContentsMargins(20, 16, 20, 16)
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_joining = QDateEdit()
        self.f_joining.setFixedHeight(38)
        self.f_joining.setCalendarPopup(True)
        self.f_joining.setDate(QDate.currentDate())
        self.f_joining.setDisplayFormat("dd/MM/yyyy")
        self.f_joining.setSpecialValueText("Not set")
        self.f_joining.setStyleSheet("""
            QDateEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 13px; background: white;
            }
            QDateEdit:focus { border: 2px solid #2563EB; }
        """)

        # ID Proof type + number
        id_row = QHBoxLayout()
        id_row.setSpacing(10)
        self.f_id_type = QComboBox()
        self.f_id_type.setFixedHeight(38)
        self.f_id_type.setMinimumWidth(160)
        self._style_combo(self.f_id_type)
        self.f_id_type.addItem("— Select ID Type —", None)
        for proof in ID_PROOF_TYPES:
            self.f_id_type.addItem(proof, proof)
        self.f_id_number = QLineEdit()
        self.f_id_number.setPlaceholderText("ID number")
        self.f_id_number.setFixedHeight(38)
        self._style_input(self.f_id_number)
        id_row.addWidget(self.f_id_type)
        id_row.addWidget(self.f_id_number)
        id_w = QWidget(); id_w.setLayout(id_row); id_w.setStyleSheet("background:white;")

        self.f_notes = QTextEdit()
        self.f_notes.setFixedHeight(80)
        self.f_notes.setPlaceholderText("Any additional notes about this person…")
        self.f_notes.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 8px; font-size: 13px;
            }
            QTextEdit:focus { border: 2px solid #2563EB; padding: 7px; }
        """)

        form.addRow(self.make_label("Date of Joining"),  self.f_joining)
        form.addRow(self.make_label("ID Proof"),         id_w)
        form.addRow(self.make_label("Notes"),            self.f_notes)
        return w

    # ── Populate (Edit mode) ──────────────────────────────────────────────────

    def _populate(self, p: Person) -> None:
        # Basic
        for i in range(self.f_type.count()):
            if self.f_type.itemData(i) == p.person_type:
                self.f_type.setCurrentIndex(i)
                break
        self.f_first.setText(p.first_name or "")
        self.f_last.setText(p.last_name or "")
        for i in range(self.f_dept.count()):
            if self.f_dept.itemData(i) == p.dept_id:
                self.f_dept.setCurrentIndex(i)
                break
        self.f_designation.setText(p.designation or "")

        # Contact
        self.f_email.setText(p.email or "")
        self.f_phone.setText(p.phone or "")
        self.f_address.setPlainText(p.address or "")
        self.f_city.setText(p.city or "")
        self.f_state.setText(p.state or "")

        # Details
        if p.date_of_joining:
            self.f_joining.setDate(
                QDate(p.date_of_joining.year,
                      p.date_of_joining.month,
                      p.date_of_joining.day)
            )
        if p.id_proof_type:
            for i in range(self.f_id_type.count()):
                if self.f_id_type.itemData(i) == p.id_proof_type:
                    self.f_id_type.setCurrentIndex(i)
                    break
        self.f_id_number.setText(p.id_proof_number or "")
        self.f_notes.setPlainText(p.notes or "")

    # ── Collect & Save ────────────────────────────────────────────────────────

    def _collect_data(self):
        first = self.f_first.text().strip()
        if not first:
            self.set_error("First name is required.")
            self._tabs.setCurrentIndex(0)
            self.f_first.setFocus()
            return None

        ptype = self.f_type.currentData()
        if not ptype:
            self.set_error("Please select a person type.")
            self._tabs.setCurrentIndex(0)
            return None

        # Date of joining
        doj = None
        date_val = self.f_joining.date()
        if not self.f_joining.text() == "Not set":
            from datetime import date
            doj = date(date_val.year(), date_val.month(), date_val.day())

        return {
            "org_id":         current_session.org_id,
            "person_type":    ptype,
            "first_name":     first,
            "last_name":      self.f_last.text().strip() or None,
            "dept_id":        self.f_dept.currentData(),
            "designation":    self.f_designation.text().strip() or None,
            "email":          self.f_email.text().strip() or None,
            "phone":          self.f_phone.text().strip() or None,
            "address":        self.f_address.toPlainText().strip() or None,
            "city":           self.f_city.text().strip() or None,
            "state":          self.f_state.text().strip() or None,
            "date_of_joining": doj,
            "id_proof_type":  self.f_id_type.currentData(),
            "id_proof_number":self.f_id_number.text().strip() or None,
            "notes":          self.f_notes.toPlainText().strip() or None,
        }

    def _on_save(self, data: dict) -> None:
        if self._person:
            self._svc.update(self._person.id, data)
            app_signals.person_updated.emit(self._person.id)
        else:
            p = self._svc.create(**data)
            app_signals.person_created.emit(p.id)
        self.accept()

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _style_input(w) -> None:
        w.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 13px; color: #0F172A; background: white;
            }
            QLineEdit:focus { border: 2px solid #2563EB; padding: 0 9px; }
        """)

    @staticmethod
    def _style_combo(w) -> None:
        w.setStyleSheet("""
            QComboBox {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 0 10px; font-size: 13px; color: #0F172A; background: white;
            }
            QComboBox:focus { border: 2px solid #2563EB; }
            QComboBox::drop-down { border: none; width: 20px; }
        """)
