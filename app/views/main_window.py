"""
Sanchay - Main Application Window
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
from PySide6.QtGui import QIcon, QFont, QAction, QPixmap, QPainter, QColor

from app.config import config
from app.core.security import current_session
from app.core.signals import app_signals
from app.views.dashboard_view import DashboardView
from app.views.widgets.notification import show_toast
from loguru import logger


def _load_icon_file() -> QIcon:
    """
    Load the pre-generated icon file.
    Windows: sanchay.ico  (multi-size ICO)
    Linux  : sanchay_256.png  (largest PNG)
    Falls back to the programmatic icon if the file is missing.
    """
    import sys
    from pathlib import Path
    icons_dir = Path(__file__).parent.parent / "resources" / "icons"
    if sys.platform == "win32":
        ico = icons_dir / "sanchay.ico"
        if ico.exists():
            return QIcon(str(ico))
    else:
        png = icons_dir / "sanchay_256.png"
        if png.exists():
            return QIcon(str(png))
    # Fallback: draw programmatically
    return _make_app_icon(64)


def _make_app_icon(size: int = 64) -> QIcon:
    """
    Programmatic app icon - blue rounded square with a white package glyph.
    Used for both the taskbar and the window title bar.
    No external image files required.
    """
    from PySide6.QtGui import QPainterPath
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)

    # Background - deep blue rounded rect
    p.setBrush(QColor("#2563EB"))
    p.setPen(Qt.NoPen)
    radius = size // 6
    p.drawRoundedRect(0, 0, size, size, radius, radius)

    # Box lid (top rectangle)
    p.setBrush(QColor("#FFFFFF"))
    lid_h = size // 8
    lid_w = int(size * 0.55)
    lid_x = (size - lid_w) // 2
    lid_y = int(size * 0.22)
    p.drawRoundedRect(lid_x, lid_y, lid_w, lid_h, 2, 2)

    # Box body (larger rectangle below lid)
    body_w = int(size * 0.50)
    body_h = int(size * 0.35)
    body_x = (size - body_w) // 2
    body_y = lid_y + lid_h + 2
    p.drawRoundedRect(body_x, body_y, body_w, body_h, 2, 2)

    # Centre stripe on body
    p.setBrush(QColor("#2563EB"))
    stripe_w = int(size * 0.10)
    stripe_x = (size - stripe_w) // 2
    p.drawRect(stripe_x, body_y, stripe_w, body_h)

    p.end()
    return QIcon(pixmap)


def _make_emoji_icon(size: int = 32) -> QIcon:
    """Alias kept for compatibility - delegates to _make_app_icon."""
    return _make_app_icon(size)


def _make_logout_icon(size: int = 18) -> QIcon:
    """Draw a logout arrow icon using QPainter (no external image files)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#94A3B8"))          # default grey; CSS hover overrides button bg

    # Arrow shaft: horizontal rectangle
    shaft_h = max(3, size // 5)
    shaft_w = int(size * 0.55)
    shaft_y = (size - shaft_h) // 2
    p.drawRect(int(size * 0.28), shaft_y, shaft_w, shaft_h)

    # Arrowhead: right-pointing triangle
    from PySide6.QtGui import QPolygonF
    from PySide6.QtCore import QPointF
    tip_x   = size - 1
    mid_y   = size // 2
    head_h  = max(6, size // 2)
    poly = QPolygonF([
        QPointF(tip_x,              mid_y),
        QPointF(tip_x - head_h // 2, mid_y - head_h // 2),
        QPointF(tip_x - head_h // 2, mid_y + head_h // 2),
    ])
    p.drawPolygon(poly)

    # Bracket: vertical bar on the left + top + bottom stubs
    bar_w = max(2, size // 8)
    p.drawRect(0, 0,            bar_w, int(size * 0.38))   # top-left stub
    p.drawRect(0, int(size * 0.62), bar_w, int(size * 0.38))   # bottom-left stub
    p.drawRect(0, 0,            bar_w, size)                # full left bar (thin)
    p.end()
    return QIcon(pixmap)



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
        self.setWindowTitle(f"{config.APP_NAME} - {config.APP_TAGLINE}")
        icon = _load_icon_file()   # .ico on Windows, .png on Linux
        self.setWindowIcon(icon)
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self._nav_buttons: dict[str, SidebarButton] = {}
        self._pages: dict[str, QWidget] = {}
        self._current_page = "dashboard"

        self._setup_ui()
        self._connect_signals()
        self._navigate_to("dashboard")
        self._show_org_status()

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
        logo_frame.setFixedHeight(84)          # increased: was 72, clipped text
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(16, 14, 16, 10)
        logo_layout.setSpacing(4)

        # Icon + name on one row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(_make_app_icon(26).pixmap(26, 26))
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignCenter)

        app_name = QLabel(config.APP_NAME)
        app_name.setObjectName("appTitle")
        app_name.setStyleSheet(
            "color: #F1F5F9; font-size: 16px; font-weight: 700; "
            "letter-spacing: 0.5px;"
        )

        title_row.addWidget(icon_lbl)
        title_row.addWidget(app_name)
        title_row.addStretch()

        app_tag = QLabel(config.APP_TAGLINE)
        app_tag.setObjectName("appVersion")
        app_tag.setStyleSheet("color: #475569; font-size: 10px;")

        logo_layout.addLayout(title_row)
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

        # ── User profile strip + logout ───────────────────────────────────────
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background-color: #0F172A; border-top: 1px solid #334155;")
        bottom_frame.setFixedHeight(72)
        b_layout = QHBoxLayout(bottom_frame)
        b_layout.setContentsMargins(12, 8, 10, 8)
        b_layout.setSpacing(10)

        # Avatar circle showing user initials
        initials = (current_session.full_name or current_session.username or "?")[:2].upper()
        avatar = QLabel(initials)
        avatar.setFixedSize(38, 38)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background-color: #2563EB; color: white; border-radius: 19px; "
            "font-size: 13px; font-weight: 700;"
        )

        # Name + coloured role badge
        user_col = QVBoxLayout()
        user_col.setSpacing(1)
        user_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(current_session.full_name or current_session.username)
        name_lbl.setStyleSheet("color: #E2E8F0; font-weight: 600; font-size: 12px;")
        name_lbl.setMaximumWidth(120)

        _role_colors = {
            "admin": "#F87171", "manager": "#60A5FA",
            "operator": "#34D399", "viewer": "#94A3B8",
        }
        _rc = _role_colors.get(current_session.role or "viewer", "#94A3B8")
        role_lbl = QLabel((current_session.role or "viewer").capitalize())
        role_lbl.setStyleSheet(f"color: {_rc}; font-size: 10px; font-weight: 600;")

        user_col.addWidget(name_lbl)
        user_col.addWidget(role_lbl)

        # Logout button — painted arrow icon, turns red on hover
        logout_btn = QPushButton()
        logout_btn.setToolTip("Logout")
        logout_btn.setFixedSize(34, 34)
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setIcon(_make_logout_icon(16))
        logout_btn.setIconSize(QSize(16, 16))
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #DC2626;
                border-color: #DC2626;
            }
        """)
        logout_btn.clicked.connect(self._on_logout)

        b_layout.addWidget(avatar)
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

        # Other pages are loaded lazily - placeholder shown until first nav
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
        """
        Lazy-load real page views on first visit.
        Once loaded, the placeholder is replaced and never recreated.
        """
        loaders = {
            "organizations": self._load_org_view,
            "departments":   self._load_dept_view,
            "persons":       self._load_person_view,
            "assets":        self._load_asset_view,
            "categories":    self._load_category_view,
            "issue":         self._load_issue_view,
            "return":        self._load_return_view,
            "transactions":  self._load_transaction_view,
            "reports":       self._load_report_view,
            "settings":      self._load_settings_view,
            "users":         self._load_user_view,
            "backup":        self._load_backup_view,
        }
        loader = loaders.get(key)
        if loader:
            loader()

    def _replace_placeholder(self, key: str, real_widget) -> None:
        """Swap a placeholder page with the real widget."""
        old = self._pages.get(key)
        if old is real_widget:
            return  # Already loaded
        if old:
            self.stack.removeWidget(old)
            old.deleteLater()
        self._pages[key] = real_widget
        self.stack.addWidget(real_widget)

    def _load_org_view(self) -> None:
        existing = self._pages.get("organizations")
        from app.views.organization.org_list_view import OrgListView
        if not isinstance(existing, OrgListView):
            self._replace_placeholder("organizations", OrgListView())

    def _load_dept_view(self) -> None:
        existing = self._pages.get("departments")
        from app.views.organization.dept_list_view import DeptListView
        if not isinstance(existing, DeptListView):
            self._replace_placeholder("departments", DeptListView())

    def _load_person_view(self) -> None:
        existing = self._pages.get("persons")
        from app.views.employees.person_list_view import PersonListView
        if not isinstance(existing, PersonListView):
            self._replace_placeholder("persons", PersonListView())

    def _load_asset_view(self) -> None:
        existing = self._pages.get("assets")
        from app.views.assets.asset_list_view import AssetListView
        if not isinstance(existing, AssetListView):
            self._replace_placeholder("assets", AssetListView())

    def _load_category_view(self) -> None:
        existing = self._pages.get("categories")
        from app.views.assets.category_list_view import CategoryListView
        if not isinstance(existing, CategoryListView):
            self._replace_placeholder("categories", CategoryListView())

    def _load_issue_view(self) -> None:
        existing = self._pages.get("issue")
        from app.views.transactions.issue_view import IssueView
        if not isinstance(existing, IssueView):
            self._replace_placeholder("issue", IssueView())

    def _load_return_view(self) -> None:
        existing = self._pages.get("return")
        from app.views.transactions.return_view import ReturnView
        if not isinstance(existing, ReturnView):
            self._replace_placeholder("return", ReturnView())

    def _load_transaction_view(self) -> None:
        existing = self._pages.get("transactions")
        from app.views.transactions.transaction_list_view import TransactionListView
        if not isinstance(existing, TransactionListView):
            self._replace_placeholder("transactions", TransactionListView())

    def _load_report_view(self) -> None:
        existing = self._pages.get("reports")
        from app.views.reports.report_view import ReportView
        if not isinstance(existing, ReportView):
            self._replace_placeholder("reports", ReportView())

    def _load_settings_view(self) -> None:
        existing = self._pages.get("settings")
        from app.views.settings.settings_view import SettingsView
        if not isinstance(existing, SettingsView):
            self._replace_placeholder("settings", SettingsView())

    def _load_user_view(self) -> None:
        existing = self._pages.get("users")
        from app.views.settings.user_list_view import UserListView
        if not isinstance(existing, UserListView):
            self._replace_placeholder("users", UserListView())

    def _load_backup_view(self) -> None:
        existing = self._pages.get("backup")
        from app.views.settings.backup_view import BackupView
        if not isinstance(existing, BackupView):
            self._replace_placeholder("backup", BackupView())

    # ── Signals & Events ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        app_signals.navigate_to.connect(self._navigate_to)
        app_signals.show_notification.connect(self._on_notification)
        app_signals.status_message.connect(self._on_status_message)

    def _on_notification(self, title: str, message: str, kind: str) -> None:
        show_toast(self, f"{title}: {message}" if title else message, kind)

    def _on_status_message(self, message: str) -> None:
        self.statusBar().showMessage(message, 4000)

    def _show_org_status(self) -> None:
        """Show the current org name in the status bar after login."""
        try:
            org_id = current_session.org_id
            if org_id:
                from app.services.organization_service import OrganizationService
                orgs = OrganizationService().get_all()
                org = next((o for o in orgs if o.id == org_id), None)
                if org:
                    msg = f"🏢  {org.name}  |  Logged in as {current_session.full_name or current_session.username}  (@{current_session.role})"
                    self.statusBar().showMessage(msg)
                    return
            self.statusBar().showMessage(
                f"Logged in as {current_session.full_name or current_session.username} (@{current_session.role})"
            )
        except Exception:
            pass

    def _on_logout(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            f"Logout as '{current_session.username}'?\n\n"
            "All unsaved changes will be lost.",
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
