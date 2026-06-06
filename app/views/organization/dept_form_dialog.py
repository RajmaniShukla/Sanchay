"""
Sanchay — Department Form Dialog
===================================
Create / Edit department with parent-dept hierarchy support.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QLineEdit, QComboBox, QTextEdit, QFormLayout,
)
from PySide6.QtCore import Qt

from app.views.widgets.form_dialog import FormDialog
from app.services.organization_service import DepartmentService
from app.core.signals import app_signals
from app.models.organization import Department


class DeptFormDialog(FormDialog):
    """Create or edit a Department."""

    def __init__(
        self,
        org_id: int,
        dept: Optional[Department] = None,
        parent=None,
    ):
        self._org_id = org_id
        self._dept   = dept
        self._service = DepartmentService()

        mode     = "Edit Department" if dept else "New Department"
        subtitle = f"Editing: {dept.name}" if dept else "Add a department to this organization"
        super().__init__(mode, subtitle, "Save Department", parent,
                         min_width=480, min_height=420)
        if dept:
            self._populate(dept)

    def _build_form(self, layout: QVBoxLayout) -> None:
        layout.addWidget(self.make_section("Department Details"))

        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Name
        self.f_name = QLineEdit()
        self.f_name.setPlaceholderText("e.g. Computer Science, HR, Production")
        self.f_name.setFixedHeight(38)
        self._style_input(self.f_name)

        # Code
        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText("e.g. CS, HR (unique within org)")
        self.f_code.setMaxLength(20)
        self.f_code.setFixedHeight(38)
        self._style_input(self.f_code)

        # Parent department
        self.f_parent = QComboBox()
        self.f_parent.setFixedHeight(38)
        self._style_combo(self.f_parent)
        self.f_parent.addItem("— None (Top-level) —", None)
        try:
            depts = self._service.get_by_org(self._org_id)
            for d in depts:
                # Exclude self from parent list
                if self._dept and d.id == self._dept.id:
                    continue
                self.f_parent.addItem(f"{d.name} ({d.code})", d.id)
        except Exception:
            pass

        # Description
        self.f_desc = QTextEdit()
        self.f_desc.setFixedHeight(80)
        self.f_desc.setPlaceholderText("Optional description for this department…")
        self.f_desc.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D1D5DB; border-radius: 6px;
                padding: 8px; font-size: 13px; color: #0F172A;
            }
            QTextEdit:focus { border: 2px solid #2563EB; padding: 7px; }
        """)

        form.addRow(self.make_label("Name", required=True),        self.f_name)
        form.addRow(self.make_label("Code", required=True),        self.f_code)
        form.addRow(self.make_label("Parent Department"),          self.f_parent)
        form.addRow(self.make_label("Description"),                self.f_desc)
        layout.addLayout(form)
        layout.addStretch()

    def _populate(self, dept: Department) -> None:
        self.f_name.setText(dept.name or "")
        self.f_code.setText(dept.code or "")
        self.f_desc.setPlainText(dept.description or "")
        if dept.parent_dept_id:
            for i in range(self.f_parent.count()):
                if self.f_parent.itemData(i) == dept.parent_dept_id:
                    self.f_parent.setCurrentIndex(i)
                    break

    def _collect_data(self):
        name = self.f_name.text().strip()
        code = self.f_code.text().strip().upper()

        if not name:
            self.set_error("Department name is required.")
            self.f_name.setFocus()
            return None
        if not code or len(code) < 2:
            self.set_error("Department code must be at least 2 characters.")
            self.f_code.setFocus()
            return None

        return {
            "name":           name,
            "code":           code,
            "parent_dept_id": self.f_parent.currentData(),
            "description":    self.f_desc.toPlainText().strip() or None,
        }

    def _on_save(self, data: dict) -> None:
        if self._dept:
            self._service.update(self._dept.id, data)
            app_signals.dept_updated.emit(self._dept.id)
        else:
            dept = self._service.create(org_id=self._org_id, **data)
            app_signals.dept_created.emit(dept.id)
        self.accept()

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
