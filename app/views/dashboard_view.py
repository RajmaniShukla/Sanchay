"""
Sanchay — Dashboard View
==========================
Shows at-a-glance statistics and quick navigation cards.
The landing page after login.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QPushButton, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.core.security import current_session
from app.core.signals import app_signals
from app.services.asset_service import AssetService
from app.services.transaction_service import TransactionService
from app.services.person_service import PersonService
from app.constants import AssetStatus
from loguru import logger


class StatCard(QFrame):
    """A colorful statistics card for the dashboard."""

    def __init__(
        self,
        label: str,
        value: str,
        icon: str,
        bg_color: str = "#FFFFFF",
        accent: str = "#2563EB",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid #E2E8F0;
                border-left: 4px solid {accent};
            }}
        """)
        self.setFixedHeight(120)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 32px; color: {accent}; background: transparent; border: none;"
        )
        icon_lbl.setFixedWidth(48)
        icon_lbl.setAlignment(Qt.AlignCenter)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"font-size: 30px; font-weight: 700; color: #0F172A; "
            f"background: transparent; border: none;"
        )

        self.label_lbl = QLabel(label)
        self.label_lbl.setStyleSheet(
            "font-size: 12px; color: #64748B; font-weight: 500; "
            "background: transparent; border: none;"
        )

        text_col.addWidget(self.value_lbl)
        text_col.addWidget(self.label_lbl)
        text_col.addStretch()

        layout.addWidget(icon_lbl)
        layout.addLayout(text_col)
        layout.addStretch()

    def update_value(self, value: str) -> None:
        self.value_lbl.setText(value)


class QuickActionCard(QFrame):
    """A clickable card for quick navigation."""

    def __init__(self, icon: str, title: str, subtitle: str, nav_key: str, parent=None):
        super().__init__(parent)
        self.nav_key = nav_key
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: #2563EB;
                background-color: #EFF6FF;
            }
        """)
        self.setFixedHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            "font-size: 28px; background: transparent; border: none;"
        )
        icon_lbl.setFixedWidth(40)
        icon_lbl.setAlignment(Qt.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-weight: 600; font-size: 13px; color: #0F172A; "
            "background: transparent; border: none;"
        )
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(
            "font-size: 11px; color: #64748B; background: transparent; border: none;"
        )

        text_col.addWidget(title_lbl)
        text_col.addWidget(sub_lbl)

        arrow = QLabel("→")
        arrow.setStyleSheet("color: #94A3B8; font-size: 16px; background: transparent; border: none;")

        layout.addWidget(icon_lbl)
        layout.addLayout(text_col)
        layout.addStretch()
        layout.addWidget(arrow)

    def mousePressEvent(self, event):
        app_signals.navigate_to.emit(self.nav_key)


class DashboardView(QScrollArea):
    """
    Dashboard landing page.
    Shows stats and quick actions. Refreshes on signal.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asset_service = AssetService()
        self.txn_service = TransactionService()
        self.person_service = PersonService()

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)

        # Content widget
        content = QWidget()
        self.setWidget(content)
        self._root_layout = QVBoxLayout(content)
        self._root_layout.setContentsMargins(24, 24, 24, 24)
        self._root_layout.setSpacing(24)

        self._build_ui()
        self._load_stats()

        # Connect refresh signal
        app_signals.refresh_dashboard.connect(self._load_stats)
        app_signals.asset_created.connect(lambda _: self._load_stats())
        app_signals.asset_issued.connect(lambda *_: self._load_stats())
        app_signals.asset_returned.connect(lambda *_: self._load_stats())
        app_signals.person_created.connect(lambda _: self._load_stats())

    def _build_ui(self) -> None:
        layout = self._root_layout

        # ── Welcome header ─────────────────────────────────────────────────────
        welcome_row = QHBoxLayout()
        self.welcome_lbl = QLabel(
            f"Good day, {current_session.full_name or current_session.username}! 👋"
        )
        self.welcome_lbl.setStyleSheet(
            "font-size: 22px; font-weight: 700; color: #0F172A;"
        )
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("font-size: 13px; color: #64748B;")
        self.date_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._update_clock()
        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(60000)

        welcome_row.addWidget(self.welcome_lbl)
        welcome_row.addStretch()
        welcome_row.addWidget(self.date_lbl)
        layout.addLayout(welcome_row)

        # ── Stats cards ────────────────────────────────────────────────────────
        stats_lbl = QLabel("Overview")
        stats_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        layout.addWidget(stats_lbl)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.card_total      = StatCard("Total Assets",     "—", "📦", accent="#2563EB")
        self.card_available  = StatCard("Available",        "—", "✅", accent="#16A34A")
        self.card_issued     = StatCard("Currently Issued", "—", "📤", accent="#0891B2")
        self.card_overdue    = StatCard("Overdue",          "—", "⚠️", accent="#DC2626")
        self.card_persons    = StatCard("Active Persons",   "—", "👥", accent="#7C3AED")
        self.card_cats       = StatCard("Categories",       "—", "🗂️", accent="#D97706")

        stats_grid.addWidget(self.card_total,     0, 0)
        stats_grid.addWidget(self.card_available, 0, 1)
        stats_grid.addWidget(self.card_issued,    0, 2)
        stats_grid.addWidget(self.card_overdue,   1, 0)
        stats_grid.addWidget(self.card_persons,   1, 1)
        stats_grid.addWidget(self.card_cats,      1, 2)

        layout.addLayout(stats_grid)

        # ── Quick actions ──────────────────────────────────────────────────────
        qa_lbl = QLabel("Quick Actions")
        qa_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        layout.addWidget(qa_lbl)

        qa_grid = QGridLayout()
        qa_grid.setSpacing(12)

        actions = [
            ("📦", "Add New Asset",       "Register a new asset",          "assets.new"),
            ("📤", "Issue Asset",          "Assign asset to a person",      "transactions.issue"),
            ("📥", "Return Asset",         "Record an asset return",        "transactions.return"),
            ("👤", "Add Person",           "Register employee/student",     "persons.new"),
            ("📊", "View Reports",         "Generate and export reports",   "reports"),
            ("🔄", "Backup Database",      "Create a database backup",      "settings.backup"),
        ]

        for i, (icon, title, sub, key) in enumerate(actions):
            card = QuickActionCard(icon, title, sub, key)
            qa_grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(qa_grid)
        layout.addStretch()

    def _load_stats(self) -> None:
        """Load statistics from services and update cards."""
        try:
            org_id = current_session.org_id

            # Asset counts
            counts = self.asset_service.count_by_status(org_id)
            total = sum(counts.values())
            available = counts.get("available", 0)
            issued = counts.get("issued", 0)

            self.card_total.update_value(str(total))
            self.card_available.update_value(str(available))
            self.card_issued.update_value(str(issued))

            # Overdue
            txn_stats = self.txn_service.get_stats(org_id)
            self.card_overdue.update_value(str(txn_stats.get("overdue", 0)))

            # Persons
            p_counts = self.person_service.count_by_type(org_id)
            total_persons = sum(p_counts.values())
            self.card_persons.update_value(str(total_persons))

            # Categories
            from app.services.asset_service import AssetCategoryService
            cats = AssetCategoryService().get_all(org_id)
            self.card_cats.update_value(str(len(cats)))

        except Exception as e:
            logger.error(f"Dashboard stats load error: {e}")

    def _update_clock(self) -> None:
        from datetime import datetime
        now = datetime.now()
        self.date_lbl.setText(now.strftime("%A, %d %B %Y  •  %I:%M %p"))
