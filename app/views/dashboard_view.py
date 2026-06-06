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
        nav_key: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.nav_key = nav_key
        self.setObjectName("statCard")
        base_style = f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid #E2E8F0;
                border-left: 4px solid {accent};
            }}
        """
        hover_style = f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: 1px solid #93C5FD;
                border-left: 4px solid {accent};
            }}
        """
        self.setStyleSheet(base_style)
        self._base_style  = base_style
        self._hover_style = hover_style
        if nav_key:
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip(f"Click to open {label} page")
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

    def mousePressEvent(self, event) -> None:
        if self.nav_key:
            app_signals.navigate_to.emit(self.nav_key)

    def enterEvent(self, event) -> None:
        if self.nav_key:
            self.setStyleSheet(self._hover_style)

    def leaveEvent(self, event) -> None:
        if self.nav_key:
            self.setStyleSheet(self._base_style)


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

        # Refresh button
        refresh_btn = QPushButton("🔄  Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setToolTip("Refresh dashboard statistics")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; border: 1px solid #E2E8F0;
                border-radius: 8px; color: #374151;
                font-size: 12px; font-weight: 500; padding: 0 14px;
            }
            QPushButton:hover { background: #E2E8F0; border-color: #CBD5E1; }
        """)
        refresh_btn.clicked.connect(self._load_stats)

        welcome_row.addWidget(self.welcome_lbl)
        welcome_row.addStretch()
        welcome_row.addWidget(self.date_lbl)
        welcome_row.addSpacing(12)
        welcome_row.addWidget(refresh_btn)
        layout.addLayout(welcome_row)

        # ── Stats cards ────────────────────────────────────────────────────────
        stats_lbl = QLabel("Overview")
        stats_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        layout.addWidget(stats_lbl)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        self.card_total      = StatCard("Total Assets",     "—", "📦", accent="#2563EB", nav_key="assets")
        self.card_available  = StatCard("Available",        "—", "✅", accent="#16A34A", nav_key="assets")
        self.card_issued     = StatCard("Currently Issued", "—", "📤", accent="#0891B2", nav_key="transactions")
        self.card_overdue    = StatCard("Overdue",          "—", "⚠️", accent="#DC2626", nav_key="transactions")
        self.card_persons    = StatCard("Active Persons",   "—", "👥", accent="#7C3AED", nav_key="persons")
        self.card_cats       = StatCard("Categories",       "—", "🗂️", accent="#D97706", nav_key="categories")

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

        # ── Recent Activity ────────────────────────────────────────────────────
        activity_lbl = QLabel("Recent Activity")
        activity_lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #374151;")
        layout.addWidget(activity_lbl)

        self._activity_frame = QFrame()
        self._activity_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
            }
        """)
        self._activity_layout = QVBoxLayout(self._activity_frame)
        self._activity_layout.setContentsMargins(16, 12, 16, 12)
        self._activity_layout.setSpacing(0)
        layout.addWidget(self._activity_frame)

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

        # Always try to load recent activity
        self._load_recent_activity()

    def _load_recent_activity(self) -> None:
        """Fetch last 5 audit log entries and display them."""
        # Clear existing activity rows
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            from app.core.database import get_db
            from app.models.audit import AuditLog
            from app.models.user import User
            from sqlalchemy import desc
            from sqlalchemy.orm import joinedload

            with get_db() as db:
                logs = (
                    db.query(AuditLog)
                    .options(joinedload(AuditLog.user))   # eager-load user
                    .order_by(desc(AuditLog.timestamp))
                    .limit(5)
                    .all()
                )

            if not logs:
                empty_lbl = QLabel("—  No recent activity")
                empty_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 8px 0;")
                self._activity_layout.addWidget(empty_lbl)
                return

            action_icons = {
                "CREATE": "➕",  "UPDATE": "✏️",  "DELETE": "🗑️",
                "LOGIN":  "🔑",  "LOGOUT": "🚪",   "ISSUE":  "📤",
                "RETURN": "📥",
            }

            for i, log in enumerate(logs):
                row = QFrame()
                row.setStyleSheet(
                    "QFrame { border: none; "
                    + ("border-bottom: 1px solid #F1F5F9; " if i < len(logs) - 1 else "")
                    + "}"
                )
                row_lay = QHBoxLayout(row)
                row_lay.setContentsMargins(0, 8, 0, 8)
                row_lay.setSpacing(10)

                action = log.action or "ACTION"
                icon   = action_icons.get(action.upper(), "📝")

                icon_lbl = QLabel(icon)
                icon_lbl.setFixedWidth(24)
                icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")

                desc_text = log.description or f"{action} on {log.table_name or 'record'}"
                if len(desc_text) > 80:
                    desc_text = desc_text[:77] + "…"

                user_part = f" — {log.user.username}" if log.user else ""
                detail_lbl = QLabel(f"{desc_text}{user_part}")
                detail_lbl.setStyleSheet(
                    "font-size: 12px; color: #374151; background: transparent; border: none;"
                )

                ts_str = log.timestamp.strftime("%d %b  %H:%M") if log.timestamp else ""
                ts_lbl = QLabel(ts_str)
                ts_lbl.setStyleSheet(
                    "font-size: 11px; color: #94A3B8; background: transparent; border: none;"
                )
                ts_lbl.setAlignment(Qt.AlignRight)

                row_lay.addWidget(icon_lbl)
                row_lay.addWidget(detail_lbl, 1)
                row_lay.addWidget(ts_lbl)
                self._activity_layout.addWidget(row)

        except Exception as e:
            logger.warning(f"Could not load recent activity: {e}")
            err_lbl = QLabel("—  Activity log unavailable")
            err_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 8px 0;")
            self._activity_layout.addWidget(err_lbl)

    def _update_clock(self) -> None:
        from datetime import datetime
        now = datetime.now()
        self.date_lbl.setText(now.strftime("%A, %d %B %Y  •  %I:%M %p"))
