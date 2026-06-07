"""
Sanchay — Application Configuration
====================================
Central configuration management using environment variables
and a local settings file. All paths are resolved relative
to the application root directory.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Resolve application roots
# Supports normal execution and both PyInstaller build modes:
#   onedir  -> exe + resources sit in the same folder  (sys.executable.parent)
#   onefile -> resources are extracted to sys._MEIPASS; user-data lives
#              next to the exe so backups/exports/logs survive across runs.
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # User-mutable data (DB, logs, backups, exports) -> always next to the exe
    APP_ROOT = Path(sys.executable).parent
    # Read-only bundled resources (icons, styles):
    #   onefile: extracted to sys._MEIPASS temp dir
    #   onedir : same folder as the exe (no _MEIPASS)
    BUNDLE_ROOT = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else APP_ROOT
else:
    APP_ROOT = Path(__file__).parent.parent
    BUNDLE_ROOT = APP_ROOT

load_dotenv(APP_ROOT / ".env")


class AppConfig:
    """
    Central application configuration.
    All paths are absolute and created if they don't exist.
    """

    # -- Application Identity ------------------------------------------------
    APP_NAME: str = "Sanchay"
    APP_VERSION: str = "1.0.0"
    APP_TAGLINE: str = "Inventory & Asset Management System"
    ORGANIZATION: str = "Sanchay Systems"

    # -- Paths ----------------------------------------------------------------
    # User-mutable dirs — always next to the exe (survive app updates)
    ROOT_DIR: Path = APP_ROOT
    DATA_DIR: Path = ROOT_DIR / "data"
    LOGS_DIR: Path = ROOT_DIR / "logs"
    BACKUPS_DIR: Path = ROOT_DIR / "backups"
    EXPORTS_DIR: Path = ROOT_DIR / "exports"

    # Read-only bundled resources — BUNDLE_ROOT handles onefile _MEIPASS
    RESOURCES_DIR: Path = BUNDLE_ROOT / "app" / "resources"
    STYLES_DIR: Path = RESOURCES_DIR / "styles"
    ICONS_DIR: Path = RESOURCES_DIR / "icons"

    # Uploads are user-generated content; store next to exe, not in bundle
    APP_DIR: Path = ROOT_DIR / "app"
    UPLOADS_DIR: Path = APP_DIR / "resources" / "uploads"

    # -- Database ------------------------------------------------------------
    DB_FILENAME: str = os.getenv("DB_FILENAME", "sanchay.db")
    DB_PATH: Path = DATA_DIR / DB_FILENAME
    DB_URL: str = f"sqlite:///{DB_PATH}"

    # For future PostgreSQL support:
    # DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    # -- Security ------------------------------------------------------------
    BCRYPT_ROUNDS: int = 12
    SESSION_TIMEOUT_MINUTES: int = 480  # 8 hours

    # -- Logging -------------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = LOGS_DIR / "sanchay.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"

    # -- UI / Theme ----------------------------------------------------------
    DEFAULT_THEME: str = "light"
    WINDOW_MIN_WIDTH: int = 1280
    WINDOW_MIN_HEIGHT: int = 768
    SIDEBAR_WIDTH: int = 220

    # -- Reports -------------------------------------------------------------
    REPORT_PAGE_SIZE: str = "A4"
    PDF_AUTHOR: str = APP_NAME

    # -- Pagination ----------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = 50

    # -- Auto-backup ---------------------------------------------------------
    AUTO_BACKUP_ENABLED: bool = False
    AUTO_BACKUP_INTERVAL_DAYS: int = 1

    @classmethod
    def init_directories(cls) -> None:
        """Create all required directories if they don't exist."""
        dirs = [
            cls.DATA_DIR,
            cls.LOGS_DIR,
            cls.BACKUPS_DIR,
            cls.EXPORTS_DIR,
            cls.UPLOADS_DIR,
        ]
        for directory in dirs:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_first_run(cls) -> bool:
        """Returns True if the database file doesn't exist yet."""
        return not cls.DB_PATH.exists()


# Singleton instance
config = AppConfig()
