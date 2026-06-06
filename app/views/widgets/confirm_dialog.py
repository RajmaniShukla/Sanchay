"""
Sanchay — Confirmation Dialog
================================
Reusable confirmation popup for destructive actions.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt


class ConfirmDialog(QDialog):
    """
    Clean confirmation dialog.

    Usage:
        dlg = ConfirmDialog(
            title="Delete Asset",
            message="Are you sure you want to delete 'Laptop Dell XPS'?\nThis action cannot be undone.",
            confirm_label="Delete",
            danger=True,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            # proceed
    """

    def __init__(
        self,
        title: str,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        danger: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setFixedWidth(420)
        self.setWindowTitle(title)
        self.setStyleSheet("QDialog { background: white; }")
        self._danger = danger
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._message = message
        self._title = title
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 20)
        layout.setSpacing(16)

        # Icon + title row
        title_row = QHBoxLayout()
        icon = "🗑️" if self._danger else "❓"
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 28px;")
        icon_lbl.setFixedWidth(40)

        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #0F172A;")
        title_lbl.setWordWrap(True)

        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl, 1)
        layout.addLayout(title_row)

        # Message
        msg_lbl = QLabel(self._message)
        msg_lbl.setStyleSheet("font-size: 13px; color: #4B5563; line-height: 1.5;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton(self._cancel_label)
        cancel_btn.setFixedHeight(38)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 1px solid #D1D5DB;
                border-radius: 6px; color: #374151; font-weight: 500;
            }
            QPushButton:hover { background: #F9FAFB; }
        """)
        cancel_btn.clicked.connect(self.reject)

        confirm_color = "#DC2626" if self._danger else "#2563EB"
        confirm_hover = "#B91C1C" if self._danger else "#1D4ED8"
        confirm_btn = QPushButton(self._confirm_label)
        confirm_btn.setFixedHeight(38)
        confirm_btn.setMinimumWidth(110)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {confirm_color}; border: none;
                border-radius: 6px; color: white; font-weight: 600;
            }}
            QPushButton:hover {{ background: {confirm_hover}; }}
        """)
        confirm_btn.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)
