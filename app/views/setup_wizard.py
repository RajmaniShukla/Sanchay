"""
Sanchay — First-Run Setup Wizard
====================================
Shown when no database exists. Guides the user through:
  1. Creating the admin account
  2. Setting up the first organization
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QMessageBox, QStackedWidget,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService
from app.core.security import validate_password_strength
from app.constants import OrgType
from loguru import logger


class SetupWizard(QDialog):
    """
    Modal wizard for first-time setup.
    Emits `setup_complete` when done.
    """

    setup_complete = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to Sanchay — Initial Setup")
        self.setFixedSize(500, 560)
        self.setModal(True)
        self.auth_service = AuthService()
        self.org_service = OrganizationService()
        self._current_step = 0
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("QDialog { background-color: white; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background-color: #2563EB;")
        header.setFixedHeight(80)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(32, 16, 32, 16)

        title = QLabel("📦  Sanchay Setup Wizard")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")
        step_lbl = QLabel("Step 1 of 2 — Create Admin Account")
        step_lbl.setStyleSheet("color: #BFDBFE; font-size: 12px;")
        self.step_label = step_lbl

        h_layout.addWidget(title)
        h_layout.addWidget(step_lbl)
        layout.addWidget(header)

        # ── Steps ──────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_step1())
        self.stack.addWidget(self._build_step2())
        layout.addWidget(self.stack, 1)

        # ── Footer buttons ─────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet("border-top: 1px solid #E2E8F0;")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 16, 24, 16)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("secondaryButton")
        self.back_btn.setVisible(False)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("primaryButton")
        self.next_btn.setStyleSheet(
            "background-color: #2563EB; color: white; border-radius: 6px; "
            "padding: 10px 24px; font-weight: 600; font-size: 14px;"
        )

        f_layout.addWidget(self.back_btn)
        f_layout.addStretch()
        f_layout.addWidget(self.next_btn)
        layout.addWidget(footer)

        self.back_btn.clicked.connect(self._go_back)
        self.next_btn.clicked.connect(self._go_next)

    def _build_step1(self) -> QWidget:
        """Step 1: Admin account creation."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        desc = QLabel(
            "Create the administrator account. This account has full access "
            "to all features and settings."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #64748B; font-size: 13px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)

        self.admin_name = QLineEdit()
        self.admin_name.setPlaceholderText("e.g. System Administrator")
        self.admin_name.setFixedHeight(40)

        self.admin_user = QLineEdit()
        self.admin_user.setPlaceholderText("e.g. admin")
        self.admin_user.setFixedHeight(40)

        self.admin_email = QLineEdit()
        self.admin_email.setPlaceholderText("e.g. admin@example.com")
        self.admin_email.setFixedHeight(40)

        self.admin_pass = QLineEdit()
        self.admin_pass.setEchoMode(QLineEdit.Password)
        self.admin_pass.setPlaceholderText("At least 6 characters")
        self.admin_pass.setFixedHeight(40)

        self.admin_pass2 = QLineEdit()
        self.admin_pass2.setEchoMode(QLineEdit.Password)
        self.admin_pass2.setPlaceholderText("Re-enter password")
        self.admin_pass2.setFixedHeight(40)

        form.addRow("Full Name *", self.admin_name)
        form.addRow("Username *", self.admin_user)
        form.addRow("Email", self.admin_email)
        form.addRow("Password *", self.admin_pass)
        form.addRow("Confirm Password *", self.admin_pass2)

        self.step1_error = QLabel("")
        self.step1_error.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.step1_error.hide()

        layout.addLayout(form)
        layout.addWidget(self.step1_error)
        layout.addStretch()
        return widget

    def _build_step2(self) -> QWidget:
        """Step 2: First organization."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        desc = QLabel(
            "Set up your organization. You can add more organizations and "
            "departments later from the settings."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #64748B; font-size: 13px;")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft)

        self.org_name = QLineEdit()
        self.org_name.setPlaceholderText("e.g. Acme Corporation")
        self.org_name.setFixedHeight(40)

        self.org_code = QLineEdit()
        self.org_code.setPlaceholderText("e.g. ACM (3-5 chars)")
        self.org_code.setMaxLength(10)
        self.org_code.setFixedHeight(40)

        self.org_type = QComboBox()
        self.org_type.setFixedHeight(40)
        for ot in OrgType:
            self.org_type.addItem(ot.label(), ot.value)

        self.org_city = QLineEdit()
        self.org_city.setPlaceholderText("City")
        self.org_city.setFixedHeight(40)

        self.org_phone = QLineEdit()
        self.org_phone.setPlaceholderText("+91 98765 43210")
        self.org_phone.setFixedHeight(40)

        form.addRow("Organization Name *", self.org_name)
        form.addRow("Short Code *", self.org_code)
        form.addRow("Type *", self.org_type)
        form.addRow("City", self.org_city)
        form.addRow("Phone", self.org_phone)

        self.step2_error = QLabel("")
        self.step2_error.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.step2_error.hide()

        layout.addLayout(form)
        layout.addWidget(self.step2_error)
        layout.addStretch()
        return widget

    def _go_next(self) -> None:
        if self._current_step == 0:
            if self._validate_step1():
                self._current_step = 1
                self.stack.setCurrentIndex(1)
                self.step_label.setText("Step 2 of 2 — Set Up Organization")
                self.back_btn.setVisible(True)
                self.next_btn.setText("Finish Setup ✓")
        elif self._current_step == 1:
            if self._validate_step2():
                self._finish()

    def _go_back(self) -> None:
        self._current_step = 0
        self.stack.setCurrentIndex(0)
        self.step_label.setText("Step 1 of 2 — Create Admin Account")
        self.back_btn.setVisible(False)
        self.next_btn.setText("Next →")

    def _validate_step1(self) -> bool:
        self.step1_error.hide()
        name = self.admin_name.text().strip()
        user = self.admin_user.text().strip()
        pwd = self.admin_pass.text()
        pwd2 = self.admin_pass2.text()

        if not name:
            return self._err1("Full name is required.")
        if not user:
            return self._err1("Username is required.")
        if len(user) < 3:
            return self._err1("Username must be at least 3 characters.")
        valid, msg = validate_password_strength(pwd)
        if not valid:
            return self._err1(msg)
        if pwd != pwd2:
            return self._err1("Passwords do not match.")
        return True

    def _validate_step2(self) -> bool:
        self.step2_error.hide()
        name = self.org_name.text().strip()
        code = self.org_code.text().strip().upper()
        if not name:
            return self._err2("Organization name is required.")
        if not code or len(code) < 2:
            return self._err2("Organization code must be at least 2 characters.")
        return True

    def _finish(self) -> None:
        try:
            # Seed roles first
            self.auth_service.seed_default_roles()

            # Create admin user
            self.auth_service.create_user(
                username=self.admin_user.text().strip().lower(),
                full_name=self.admin_name.text().strip(),
                password=self.admin_pass.text(),
                role_name="admin",
                email=self.admin_email.text().strip() or None,
            )

            # Create first org
            self.org_service.create(
                name=self.org_name.text().strip(),
                code=self.org_code.text().strip().upper(),
                org_type=self.org_type.currentData(),
                city=self.org_city.text().strip() or None,
                phone=self.org_phone.text().strip() or None,
            )

            logger.info("Setup wizard completed successfully.")
            self.setup_complete.emit()
            self.accept()

        except Exception as e:
            logger.exception("Setup wizard error")
            QMessageBox.critical(self, "Setup Failed", str(e))

    def _err1(self, msg: str) -> bool:
        self.step1_error.setText(msg)
        self.step1_error.show()
        return False

    def _err2(self, msg: str) -> bool:
        self.step2_error.setText(msg)
        self.step2_error.show()
        return False
