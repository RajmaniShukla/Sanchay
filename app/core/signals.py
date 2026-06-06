"""
Sanchay — Application-wide Qt Signals
========================================
Centralised signal bus for cross-module communication.
Views emit signals here; other views/controllers connect to them.
This avoids tight coupling between UI components.

Usage:
    from app.core.signals import app_signals
    
    # Emit
    app_signals.asset_created.emit(asset_id)
    
    # Connect
    app_signals.asset_created.connect(self.on_asset_created)
"""

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """
    Singleton signal bus for the entire application.
    All cross-module Qt signals are defined here.
    """

    # ── Authentication ────────────────────────────────────────────────────────
    login_success   = Signal(int, str, str)   # user_id, username, role
    logout_request  = Signal()
    session_expired = Signal()

    # ── Navigation ────────────────────────────────────────────────────────────
    navigate_to     = Signal(str)             # page_key: str
    page_changed    = Signal(str)             # current page key

    # ── Organization ──────────────────────────────────────────────────────────
    org_created     = Signal(int)             # org_id
    org_updated     = Signal(int)
    org_deleted     = Signal(int)
    dept_created    = Signal(int)
    dept_updated    = Signal(int)
    dept_deleted    = Signal(int)

    # ── Persons ───────────────────────────────────────────────────────────────
    person_created  = Signal(int)             # person_id
    person_updated  = Signal(int)
    person_deleted  = Signal(int)

    # ── Assets ────────────────────────────────────────────────────────────────
    asset_created   = Signal(int)             # asset_id
    asset_updated   = Signal(int)
    asset_deleted   = Signal(int)
    category_created = Signal(int)
    category_updated = Signal(int)

    # ── Transactions ──────────────────────────────────────────────────────────
    asset_issued    = Signal(int, int)        # issue_id, asset_id
    asset_returned  = Signal(int, int)        # return_id, issue_id

    # ── Dashboard ─────────────────────────────────────────────────────────────
    refresh_dashboard = Signal()              # request dashboard stats refresh

    # ── Notifications ─────────────────────────────────────────────────────────
    show_notification = Signal(str, str, str) # title, message, type (info/success/warning/error)
    status_message    = Signal(str)           # short status bar message

    # ── Settings ─────────────────────────────────────────────────────────────
    theme_changed     = Signal(str)           # theme name
    settings_saved    = Signal()


# ── Singleton instance ────────────────────────────────────────────────────────
app_signals = AppSignals()
