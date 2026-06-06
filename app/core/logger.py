"""
Sanchay — Logging Configuration
=================================
Configures loguru for structured, rotating file + console logging.
Call setup_logging() once at application startup.
"""

import sys
from loguru import logger
from app.config import config


def setup_logging() -> None:
    """
    Configure application-wide logging with loguru.
    
    - Console: human-readable, INFO level
    - File: JSON-structured, DEBUG level, rotating
    """
    # Remove default handler
    logger.remove()

    # ── Console handler ───────────────────────────────────────────────────────
    logger.add(
        sys.stderr,
        level=config.LOG_LEVEL,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # ── File handler ──────────────────────────────────────────────────────────
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(config.LOG_FILE),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}",
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
        compression="zip",
        encoding="utf-8",
    )

    logger.info(f"Logging initialized — level={config.LOG_LEVEL}, file={config.LOG_FILE}")
