"""
Sanchay — Login View
======================
The first screen users see. Handles authentication and the
first-run setup wizard for initial admin account creation.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QFormLayout, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QColor, QPalette

from app.config import config
from app.services.auth_service import AuthService
from app.core.exceptions import AuthenticationError, AccountInactiveError
from loguru import logger


class LoginView(QWidget):
    """
    Login screen shown on application start.
    Emits `login_success` with (user_id, username, role) on success.
    """

    login_success = Signal(int, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_service = AuthService()
        self._setup_ui()

    def _setup_ui(self) -> None:
        # ── Full-screen blue background ────────────────────────────────────────
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#EFF6FF"))
        self.setPalette(palette)

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignCenter)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Login card ─────────────────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("loginContainer")
        card.setFixedWidth(420)
        card.setStyleSheet("""
            QFrame#loginContainer {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E2E8F0;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)

        # ── Logo + title ───────────────────────────────────────────────────────
        header = QVBoxLayout()
        header.setSpacing(4)

        logo_lbl = QLabel("📦")
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("font-size: 48px;")

        title_lbl = QLabel(config.APP_NAME)
        title_lbl.setObjectName("loginTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("font-size: 28px; font-weight: 700; color: #0F172A;")

        subtitle_lbl = QLabel(config.APP_TAGLINE)
        subtitle_lbl.setObjectName("loginSubtitle")
        subtitle_lbl.setAlignment(Qt.AlignCenter)
        subtitle_lbl.setStyleSheet("font-size: 13px; color: #64748B;")

        header.addWidget(logo_lbl)
        header.addWidget(title_lbl)
        header.addWidget(subtitle_lbl)
        card_layout.addLayout(header)

        # ── Divider ────────────────────────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("border: 1px solid #E2E8F0;")
        card_layout.addWidget(divider)

        # ── Form ───────────────────────────────────────────────────────────────
        form = QVBoxLayout()
        form.setSpacing(14)

        # Username
        user_lbl = QLabel("Username")
        user_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(42)
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB; border-radius: 8px;
                padding: 10px 14px; font-size: 14px; color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #2563EB; padding: 9px 13px; }
        """)

        # Password
        pass_lbl = QLabel("Password")
        pass_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D1D5DB; border-radius: 8px;
                padding: 10px 14px; font-size: 14px; color: #0F172A;
            }
            QLineEdit:focus { border: 2px solid #2563EB; padding: 9px 13px; }
        """)

        form.addWidget(user_lbl)
        form.addWidget(self.username_input)
        form.addWidget(pass_lbl)
        form.addWidget(self.password_input)
        card_layout.addLayout(form)

        # ── Error label ────────────────────────────────────────────────────────
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.error_lbl.setAlignment(Qt.AlignCenter)
        self.error_lbl.setWordWrap(True)
        self.error_lbl.hide()
        card_layout.addWidget(self.error_lbl)

        # ── Login button ───────────────────────────────────────────────────────
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; color: white;
                border-radius: 8px; font-size: 15px; font-weight: 600;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E40AF; }
            QPushButton:disabled { background-color: #93C5FD; }
        """)
        card_layout.addWidget(self.login_btn)

        # ── Footer ─────────────────────────────────────────────────────────────
        footer_lbl = QLabel(f"v{config.APP_VERSION}")
        footer_lbl.setAlignment(Qt.AlignCenter)
        footer_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        card_layout.addWidget(footer_lbl)

        root.addWidget(card)

        # ── Connect signals ────────────────────────────────────────────────────
        self.login_btn.clicked.connect(self._on_login)
        self.password_input.returnPressed.connect(self._on_login)
        self.username_input.returnPressed.connect(
            lambda: self.password_input.setFocus()
        )

        # Auto-focus username
        self.username_input.setFocus()

    def _on_login(self) -> None:
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            self._show_error("Please enter your username.")
            self.username_input.setFocus()
            return
        if not password:
            self._show_error("Please enter your password.")
            self.password_input.setFocus()
            return

        self._clear_error()
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")

        try:
            result = self.auth_service.login(username, password)
            self.login_success.emit(
                result["user_id"],
                result["username"],
                result["role"],
            )
        except AuthenticationError as e:
            self._show_error(str(e.message))
            self.password_input.clear()
            self.password_input.setFocus()
        except AccountInactiveError as e:
            self._show_error(str(e.message))
        except Exception as e:
            logger.exception("Unexpected login error")
            self._show_error("An unexpected error occurred. Please try again.")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")

    def _show_error(self, message: str) -> None:
        self.error_lbl.setText(message)
        self.error_lbl.show()

    def _clear_error(self) -> None:
        self.error_lbl.clear()
        self.error_lbl.hide()
