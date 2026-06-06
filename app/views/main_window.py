"""
Sanchay — Main Application Window
=====================================
The root window shown after login.
Contains the sidebar navigation, top bar, and content area (stacked pages).
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget,
    QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QAction

from app.config import config
from app.core.security import current_session
from app.core.signals import app_signals
from app.views.dashboard_view import DashboardView
from app.views.widgets.notification import show_toast
from loguru import logger


# ── Navigation Item Definition ────────────────────────────────────────────────

NAV_ITEMS = [
    # (section_label, items: [(icon, label, key, roles)])
    (None, [
        ("🏠", "Dashboard",    "dashboard",         ["admin", "manager", "operator", "viewer"]),
    ]),
    ("ASSETS", [
        ("📦", "Assets",           "assets",        ["admin", "manager", "operator", "viewer"]),
        ("🗂️", "Categories",       "categories",    ["admin", "manager"]),
        ("📤", "Issue Asset",      "issue",         ["admin", "manager", "operator"]),
        ("📥", "Return Asset",     "return",        ["admin", "manager", "operator"]),
        ("📋", "Transactions",     "transactions",  ["admin", "manager", "operator", "viewer"]),
    ]),
    ("PEOPLE", [
        ("👤", "Persons",          "persons",       ["admin", "manager", "operator", "viewer"]),
    ]),
    ("ORGANIZATION", [
        ("🏢", "Organizations",    "organizations", ["admin"]),
        ("🏗️",  "Departments",     "departments",   ["admin", "manager"]),
    ]),
    ("REPORTS", [
        ("📊", "Reports",          "reports",       ["admin", "manager", "viewer"]),
    ]),
    ("SYSTEM", [
        ("⚙️",  "Settings",        "settings",      ["admin"]),
        ("👥", "Users",            "users",         ["admin"]),
        ("💾", "Backup & Restore", "backup",        ["admin"]),
    ]),
]


class SidebarButton(QPushButton):
    """Navigation button in the sidebar."""

    def __init__(self, icon: str, label: str, key: str, parent=None):
        super().__init__(parent)
        self.nav_key = key
        self.setCheckable(True)
        self.setObjectName("navButton")
        self.setText(f"  {icon}  {label}")
        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton#navButton {
                background-color: transparent;
                color: #94A3B8;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding: 0px 12px;
                font-size: 13px;
                font-weight: 400;
            }
            QPushButton#navButton:hover {
                background-color: #334155;
                color: #E2E8F0;
            }
            QPushButton#navButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: 600;
            }
        """)


class MainWindow(QMainWindow):
    """
    Root application window.
    
    Architecture:
        - Left sidebar: navigation
        - Top bar: page title + user info
        - Center: QStackedWidget for page content
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} — {config.APP_TAGLINE}")
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self._nav_buttons: dict[str, SidebarButton] = {}
        self._pages: dict[str, QWidget] = {}
        self._current_page = "dashboard"

        self._setup_ui()
        self._connect_signals()
        self._navigate_to("dashboard")

    # ── UI Construction ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        root.addWidget(sidebar)

        # Main panel (topbar + content)
        main_panel = QVBoxLayout()
        main_panel.setContentsMargins(0, 0, 0, 0)
        main_panel.setSpacing(0)

        self.top_bar = self._build_top_bar()
        main_panel.addWidget(self.top_bar)

        self.stack = QStackedWidget()
        main_panel.addWidget(self.stack, 1)

        root.addLayout(main_panel, 1)

        # Load pages lazily (placeholder + on-demand load)
        self._init_pages()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(config.SIDEBAR_WIDTH)
        sidebar.setStyleSheet("""
            QWidget#sidebar {
                background-color: #1E293B;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Logo area ──────────────────────────────────────────────────────────
        logo_frame = QFrame()
        logo_frame.setStyleSheet("background-color: #0F172A;")
        logo_frame.setFixedHeight(72)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 12, 16, 12)
        logo_layout.setSpacing(2)

        app_name = QLabel(f"📦 {config.APP_NAME}")
        app_name.setObjectName("appTitle")
        app_name.setStyleSheet("color: #F1F5F9; font-size: 17px; font-weight: 700;")

        app_tag = QLabel(config.APP_TAGLINE)
        app_tag.setObjectName("appVersion")
        app_tag.setStyleSheet("color: #475569; font-size: 10px;")

        logo_layout.addWidget(app_name)
        logo_layout.addWidget(app_tag)
        layout.addWidget(logo_frame)

        # ── Navigation items ───────────────────────────────────────────────────
        nav_widget = QWidget()
        nav_widget.setStyleSheet("background-color: transparent;")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(0)

        role = current_session.role or "viewer"

        for section_label, items in NAV_ITEMS:
            if section_label:
                lbl = QLabel(section_label)
                lbl.setObjectName("navSection")
                lbl.setStyleSheet(
                    "color: #475569; font-size: 10px; font-weight: 600; "
                    "letter-spacing: 1px; padding: 16px 8px 4px 8px;"
                )
                nav_layout.addWidget(lbl)

            for icon, label, key, allowed_roles in items:
                if role not in allowed_roles:
                    continue
                btn = SidebarButton(icon, label, key)
                btn.clicked.connect(lambda checked, k=key: self._navigate_to(k))
                self._nav_buttons[key] = btn
                nav_layout.addWidget(btn)

        nav_layout.addStretch()
        layout.addWidget(nav_widget, 1)

        # ── User info + logout ─────────────────────────────────────────────────
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #0F172A; border-top: 1px solid #334155;")
        bottom_frame.setFixedHeight(72)
        b_layout = QHBoxLayout(bottom_frame)
        b_layout.setContentsMargins(12, 10, 12, 10)

        user_col = QVBoxLayout()
        user_col.setSpacing(2)

        name_lbl = QLabel(current_session.full_name or current_session.username)
        name_lbl.setStyleSheet("color: #E2E8F0; font-weight: 600; font-size: 12px;")

        role_lbl = QLabel(f"@{current_session.role}")
        role_lbl.setStyleSheet("color: #475569; font-size: 11px;")

        user_col.addWidget(name_lbl)
        user_col.addWidget(role_lbl)

        logout_btn = QPushButton("⏻")
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(32, 32)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B; color: #94A3B8;
                border: 1px solid #334155; border-radius: 6px; font-size: 16px;
            }
            QPushButton:hover { background-color: #DC2626; color: white; border-color: #DC2626; }
        """)
        logout_btn.clicked.connect(self._on_logout)

        b_layout.addLayout(user_col)
        b_layout.addStretch()
        b_layout.addWidget(logout_btn)

        layout.addWidget(bottom_frame)
        return sidebar

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        bar.setStyleSheet("""
            QWidget#topBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E2E8F0;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        self.page_title_lbl = QLabel("Dashboard")
        self.page_title_lbl.setObjectName("pageTitle")
        self.page_title_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")

        self.breadcrumb_lbl = QLabel("")
        self.breadcrumb_lbl.setStyleSheet("color: #64748B; font-size: 12px;")

        layout.addWidget(self.page_title_lbl)
        layout.addWidget(self.breadcrumb_lbl)
        layout.addStretch()

        # Version badge
        ver_lbl = QLabel(f"v{config.APP_VERSION}")
        ver_lbl.setStyleSheet(
            "color: #94A3B8; font-size: 11px; background: #F1F5F9; "
            "border-radius: 10px; padding: 2px 8px;"
        )
        layout.addWidget(ver_lbl)
        return bar

    def _init_pages(self) -> None:
        """Add the dashboard and placeholder pages to the stack."""
        # Dashboard loads immediately
        dashboard = DashboardView()
        self._add_page("dashboard", dashboard, "Dashboard")

        # Other pages are loaded lazily — placeholder shown until first nav
        placeholders = [
            ("assets",        "📦 Assets"),
            ("categories",    "🗂️ Asset Categories"),
            ("issue",         "📤 Issue Asset"),
            ("return",        "📥 Return Asset"),
            ("transactions",  "📋 Transaction History"),
            ("persons",       "👤 Persons"),
            ("organizations", "🏢 Organizations"),
            ("departments",   "🏗️ Departments"),
            ("reports",       "📊 Reports"),
            ("settings",      "⚙️ Settings"),
            ("users",         "👥 User Management"),
            ("backup",        "💾 Backup & Restore"),
        ]
        for key, title in placeholders:
            self._add_placeholder(key, title)

    def _add_page(self, key: str, widget: QWidget, title: str) -> None:
        self._pages[key] = widget
        self.stack.addWidget(widget)

    def _add_placeholder(self, key: str, title: str) -> None:
        """Create a coming-soon placeholder for pages not yet implemented."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon_lbl = QLabel(title.split()[0])
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px;")

        name_lbl = QLabel(title[1:].strip() if title[0] in "📦🗂📤📥📋👤🏢🏗📊⚙👥💾" else title)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F172A;")

        sub_lbl = QLabel("This section will be available in the next phase.")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("color: #64748B; font-size: 14px;")

        layout.addWidget(icon_lbl)
        layout.addWidget(name_lbl)
        layout.addWidget(sub_lbl)

        self._add_page(key, widget, title)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate_to(self, key: str) -> None:
        """Switch to a page by key."""
        if key not in self._pages:
            logger.warning(f"Unknown nav key: '{key}'")
            return

        # Lazy load real pages
        self._lazy_load_page(key)

        # Highlight the nav button
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)

        # Switch stack
        page = self._pages[key]
        self.stack.setCurrentWidget(page)
        self._current_page = key

        # Update top bar title
        page_titles = {
            "dashboard":    "Dashboard",
            "assets":       "Asset Management",
            "categories":   "Asset Categories",
            "issue":        "Issue Asset",
            "return":       "Return Asset",
            "transactions": "Transaction History",
            "persons":      "Person Management",
            "organizations":"Organizations",
            "departments":  "Departments",
            "reports":      "Reports",
            "settings":     "Settings",
            "users":        "User Management",
            "backup":       "Backup & Restore",
        }
        self.page_title_lbl.setText(page_titles.get(key, key.capitalize()))

    def _lazy_load_page(self, key: str) -> None:
        """Load real page implementations on first visit."""
        # Pages are currently placeholders — replace with real views here
        # as each phase is implemented. Example:
        #
        # if key == "assets" and isinstance(self._pages.get(key), QWidget):
        #     from app.views.assets.asset_list_view import AssetListView
        #     real_page = AssetListView()
        #     old = self._pages[key]
        #     self.stack.removeWidget(old)
        #     self._add_page(key, real_page, "Assets")
        pass

    # ── Signals & Events ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        app_signals.navigate_to.connect(self._navigate_to)
        app_signals.show_notification.connect(self._on_notification)
        app_signals.status_message.connect(self._on_status_message)

    def _on_notification(self, title: str, message: str, kind: str) -> None:
        show_toast(self, f"{title}: {message}" if title else message, kind)

    def _on_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self, "Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from app.services.auth_service import AuthService
            AuthService().logout()
            app_signals.logout_request.emit()

    def closeEvent(self, event) -> None:
        logger.info("Application window closing.")
        event.accept()
