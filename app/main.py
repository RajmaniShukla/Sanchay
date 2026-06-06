"""
Sanchay — Application Entry Point
=====================================
Bootstraps the Qt application, initialises the database,
checks for first-run, and shows either the setup wizard
or the login screen.

Run with:
    python -m app.main
    # or
    python app/main.py
"""

import sys
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt, QTimer

from app.config import config
from app.core.logger import setup_logging
from app.core.database import init_db, check_connection
from app.core.signals import app_signals
from loguru import logger


def load_stylesheet(app: QApplication) -> None:
    """Load the main QSS stylesheet."""
    qss_path = config.STYLES_DIR / "main.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        logger.warning(f"Stylesheet not found at {qss_path}")


def show_login(app: QApplication) -> None:
    """Show the login window. On success, show the main window."""
    from app.views.login_view import LoginView
    from app.views.main_window import MainWindow

    login = LoginView()
    login.setWindowTitle(f"{config.APP_NAME} — Login")
    login.setMinimumSize(800, 600)
    login.showMaximized()

    main_window: MainWindow = None

    def on_login_success(user_id: int, username: str, role: str) -> None:
        nonlocal main_window
        login.hide()
        main_window = MainWindow()
        main_window.showMaximized()
        logger.info(f"Main window opened for user '{username}'.")

    def on_logout() -> None:
        nonlocal main_window
        if main_window:
            main_window.close()
            main_window = None
        login.password_input.clear()
        login.username_input.setFocus()
        login.show()

    login.login_success.connect(on_login_success)
    app_signals.logout_request.connect(on_logout)


def run_first_time_setup(app: QApplication) -> bool:
    """
    Run the setup wizard for first-time installations.
    Returns True if setup was completed, False if cancelled.
    """
    from app.views.setup_wizard import SetupWizard

    wizard = SetupWizard()
    result = wizard.exec()
    return result == SetupWizard.Accepted


def main() -> int:
    """Application entry point."""
    # ── Qt App ────────────────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)

    # Set app-wide icon so taskbar shows the Sanchay icon, not the Python logo
    from app.views.main_window import _make_app_icon
    app.setWindowIcon(_make_app_icon(64))
    app.setApplicationVersion(config.APP_VERSION)
    app.setOrganizationName(config.ORGANIZATION)

    # ── Logging ───────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")

    # ── Stylesheet ────────────────────────────────────────────────────────────
    load_stylesheet(app)

    # ── Directories ───────────────────────────────────────────────────────────
    config.init_directories()

    # ── Database ──────────────────────────────────────────────────────────────
    is_first_run = config.is_first_run()
    try:
        init_db()
        if not check_connection():
            QMessageBox.critical(None, "Database Error",
                "Could not connect to the database. Please check your installation.")
            return 1
    except Exception as e:
        logger.exception("Database initialization failed")
        QMessageBox.critical(None, "Database Error",
            f"Failed to initialize database:\n{e}\n\nThe application cannot start.")
        return 1

    logger.info(f"Database ready at: {config.DB_PATH}")

    # ── First Run ─────────────────────────────────────────────────────────────
    if is_first_run:
        logger.info("First run detected — showing setup wizard.")
        completed = run_first_time_setup(app)
        if not completed:
            logger.info("Setup wizard cancelled. Exiting.")
            return 0

    # ── Seed app settings defaults ─────────────────────────────────────────────
    try:
        from app.services.settings_service import SettingsService
        SettingsService().seed_defaults()
    except Exception as e:
        logger.warning(f"Could not seed settings: {e}")

    # ── Sync overdue issues on startup ────────────────────────────────────────
    try:
        from app.services.transaction_service import TransactionService
        TransactionService().sync_overdue_statuses()
    except Exception as e:
        logger.warning(f"Could not sync overdue statuses: {e}")

    # ── Show login screen ─────────────────────────────────────────────────────
    show_login(app)

    logger.info("Application event loop started.")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
