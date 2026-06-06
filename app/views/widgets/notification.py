"""
Sanchay — Toast Notification Widget
=======================================
Animated toast notification that appears at the top-right of the window
and auto-dismisses after a few seconds.
"""

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve
from PySide6.QtGui import QColor


class ToastNotification(QWidget):
    """
    A self-dismissing toast notification popup.
    
    Types: 'success' | 'error' | 'warning' | 'info'
    """

    COLORS = {
        "success": ("#DCFCE7", "#15803D", "#16A34A"),
        "error":   ("#FEE2E2", "#B91C1C", "#DC2626"),
        "warning": ("#FEF3C7", "#B45309", "#D97706"),
        "info":    ("#DBEAFE", "#1D4ED8", "#2563EB"),
    }

    ICONS = {
        "success": "✓",
        "error":   "✕",
        "warning": "⚠",
        "info":    "ℹ",
    }

    def __init__(self, parent: QWidget, message: str, kind: str = "info", duration: int = 3000):
        super().__init__(parent)
        self._build_ui(message, kind)
        self._animate_in()
        QTimer.singleShot(duration, self._dismiss)

    def _build_ui(self, message: str, kind: str) -> None:
        bg, fg, border = self.COLORS.get(kind, self.COLORS["info"])
        icon = self.ICONS.get(kind, "ℹ")

        self.setObjectName("toast")
        self.setStyleSheet(f"""
            QWidget#toast {{
                background-color: {bg};
                border: 1px solid {border};
                border-left: 4px solid {border};
                border-radius: 8px;
            }}
        """)
        self.setFixedHeight(52)
        self.setMinimumWidth(320)
        self.setMaximumWidth(480)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {border}; font-size: 16px; font-weight: bold;")
        icon_lbl.setFixedWidth(20)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet(f"color: {fg}; font-size: 13px; font-weight: 500;")
        msg_lbl.setWordWrap(True)

        layout.addWidget(icon_lbl)
        layout.addWidget(msg_lbl, 1)
        self.adjustSize()

    def _animate_in(self) -> None:
        parent = self.parent()
        if parent:
            x = parent.width() - self.width() - 20
            self.move(x, -self.height())
            self.show()
            self._anim = QPropertyAnimation(self, b"pos")
            self._anim.setDuration(300)
            self._anim.setStartValue(QPoint(x, -self.height()))
            self._anim.setEndValue(QPoint(x, 16))
            self._anim.setEasingCurve(QEasingCurve.OutCubic)
            self._anim.start()

    def _dismiss(self) -> None:
        parent = self.parent()
        if not parent:
            self.hide()
            return
        x = parent.width() - self.width() - 20
        self._anim_out = QPropertyAnimation(self, b"pos")
        self._anim_out.setDuration(250)
        self._anim_out.setStartValue(QPoint(x, 16))
        self._anim_out.setEndValue(QPoint(x, -self.height() - 20))
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.deleteLater)
        self._anim_out.start()


def show_toast(parent: QWidget, message: str, kind: str = "info", duration: int = 3000) -> None:
    """Convenience function to show a toast notification."""
    ToastNotification(parent, message, kind, duration)
