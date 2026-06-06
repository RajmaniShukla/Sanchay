"""
Sanchay — Empty State Widget
==============================
A reusable widget that shows an icon, title, optional subtitle,
and an optional action button when a list or table has no data.

Usage:
    empty = EmptyStateWidget(
        icon="📭",
        title="No assets found",
        subtitle="Register your first asset to get started.",
        action_label="+ Register Asset",
    )
    empty.action_clicked.connect(self._on_create)
    layout.addWidget(empty)
    empty.setVisible(row_count == 0)
"""

from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal


class EmptyStateWidget(QWidget):
    """
    Shows icon + message + optional action button when a list is empty.

    Signals:
        action_clicked: Emitted when the optional action button is clicked.
    """

    action_clicked = Signal()

    def __init__(
        self,
        icon: str = "📭",
        title: str = "No records found",
        subtitle: str = "",
        action_label: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._build_ui(icon, title, subtitle, action_label)

    def _build_ui(
        self,
        icon: str,
        title: str,
        subtitle: str,
        action_label: str,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(40, 60, 40, 60)
        layout.setSpacing(10)

        # Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "font-size: 56px; background: transparent; border: none;"
        )
        layout.addWidget(icon_lbl)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #374151; "
            "background: transparent; border: none;"
        )
        layout.addWidget(title_lbl)

        # Subtitle
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setAlignment(Qt.AlignCenter)
            sub_lbl.setWordWrap(True)
            sub_lbl.setStyleSheet(
                "font-size: 13px; color: #64748B; "
                "background: transparent; border: none;"
            )
            layout.addWidget(sub_lbl)

        # Action button
        if action_label:
            layout.addSpacing(8)
            btn = QPushButton(action_label)
            btn.setFixedHeight(40)
            btn.setMinimumWidth(160)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #2563EB; color: white;
                    border-radius: 8px; font-weight: 600;
                    font-size: 13px; padding: 0 20px;
                    border: none;
                }
                QPushButton:hover { background: #1D4ED8; }
                QPushButton:pressed { background: #1E40AF; }
            """)
            btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(btn, 0, Qt.AlignCenter)

    def update_content(
        self,
        icon: str = "",
        title: str = "",
        subtitle: str = "",
    ) -> None:
        """Dynamically update the icon/title/subtitle labels."""
        labels = self.findChildren(QLabel)
        for i, lbl in enumerate(labels):
            if i == 0 and icon:
                lbl.setText(icon)
            elif i == 1 and title:
                lbl.setText(title)
            elif i == 2 and subtitle:
                lbl.setText(subtitle)
