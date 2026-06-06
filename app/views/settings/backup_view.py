"""
Sanchay — Backup & Restore View
==================================
Full-page backup management:
  - DB stats card (size, record count, last backup)
  - One-click "Create Backup Now" button
  - Scrollable list of existing backup files (name · size · date · actions)
  - Restore with double-confirmation
  - Auto-cleanup of old backups
"""

import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QMessageBox, QTableWidgetItem,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject

from app.config import config
from app.services.backup_service import BackupService
from app.core.signals import app_signals
from app.views.widgets.data_table import DataTable
from app.views.widgets.confirm_dialog import ConfirmDialog
from loguru import logger


# ── Background backup worker ──────────────────────────────────────────────────

class _BackupWorker(QObject):
    done    = Signal(str)   # filepath str
    error   = Signal(str)

    def __init__(self, svc: BackupService, dest=None):
        super().__init__()
        self._svc  = svc
        self._dest = dest

    def run(self):
        try:
            path = self._svc.create_backup(self._dest)
            self.done.emit(str(path))
        except Exception as e:
            self.error.emit(str(e))


# ── Main View ─────────────────────────────────────────────────────────────────

class BackupView(QWidget):
    """Backup & Restore management page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc     = BackupService()
        self._backups: list[dict] = []
        self._thread: QThread | None = None
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet("background:#1E293B;")
        hdr.setFixedHeight(52)
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(24, 0, 24, 0)
        title = QLabel("💾  Backup & Restore")
        title.setStyleSheet("color:white; font-size:16px; font-weight:700;")
        sub   = QLabel("Protect your data — back up and restore the SQLite database")
        sub.setStyleSheet("color:#94A3B8; font-size:12px;")
        h_lay.addWidget(title)
        h_lay.addSpacing(20)
        h_lay.addWidget(sub)
        h_lay.addStretch()
        root.addWidget(hdr)

        # ── Content ────────────────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background:#F8FAFC;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 20)
        c_lay.setSpacing(20)

        # ── Stats + action row ─────────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # DB Stats card
        stats_card = QFrame()
        stats_card.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:10px; }"
        )
        stats_card.setFixedHeight(110)
        sc_lay = QHBoxLayout(stats_card)
        sc_lay.setContentsMargins(20, 14, 20, 14)
        sc_lay.setSpacing(32)

        self._stat_widgets: dict[str, QLabel] = {}
        for icon, label, key in [
            ("🗄️",  "Database File",  "db_size"),
            ("📦",  "Total Records",  "records"),
            ("🕐",  "Last Backup",    "last_backup"),
            ("📂",  "Backup Location","location"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            i_lbl = QLabel(f"{icon}  {label}")
            i_lbl.setStyleSheet("font-size:11px; font-weight:600; color:#64748B;")
            v_lbl = QLabel("—")
            v_lbl.setStyleSheet("font-size:13px; font-weight:700; color:#0F172A;")
            v_lbl.setWordWrap(True)
            self._stat_widgets[key] = v_lbl
            col.addWidget(i_lbl)
            col.addWidget(v_lbl)
            sc_lay.addLayout(col)

        top_row.addWidget(stats_card, 1)

        # Action card
        action_card = QFrame()
        action_card.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:10px; }"
        )
        action_card.setFixedHeight(110)
        ac_lay = QVBoxLayout(action_card)
        ac_lay.setContentsMargins(20, 12, 20, 12)
        ac_lay.setSpacing(8)

        self._backup_btn = QPushButton("💾  Create Backup Now")
        self._backup_btn.setFixedHeight(42)
        self._backup_btn.setStyleSheet("""
            QPushButton {
                background:#2563EB; color:white; border-radius:8px;
                font-size:14px; font-weight:700;
            }
            QPushButton:hover { background:#1D4ED8; }
            QPushButton:disabled { background:#93C5FD; }
        """)
        self._backup_btn.clicked.connect(self._on_create_backup)

        custom_btn = QPushButton("📁  Save to custom location…")
        custom_btn.setFixedHeight(32)
        custom_btn.setStyleSheet("""
            QPushButton {
                background:transparent; border:1px solid #D1D5DB;
                border-radius:6px; color:#374151; font-size:12px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        custom_btn.clicked.connect(self._on_backup_custom)

        ac_lay.addWidget(self._backup_btn)
        ac_lay.addWidget(custom_btn)
        top_row.addWidget(action_card)
        c_lay.addLayout(top_row)

        # ── Warning banner ─────────────────────────────────────────────────────
        warn = QFrame()
        warn.setStyleSheet(
            "QFrame { background:#FEF3C7; border:1px solid #FDE68A; border-radius:8px; }"
        )
        warn.setFixedHeight(40)
        w_lay = QHBoxLayout(warn)
        w_lay.setContentsMargins(16, 0, 16, 0)
        w_lbl = QLabel(
            "⚠️  Restoring a backup will REPLACE the current database. "
            "A safety copy will be created automatically before restore."
        )
        w_lbl.setStyleSheet("color:#B45309; font-size:12px;")
        w_lay.addWidget(w_lbl)
        c_lay.addWidget(warn)

        # ── Backups table ──────────────────────────────────────────────────────
        tbl_hdr = QHBoxLayout()
        tbl_lbl = QLabel("Available Backups")
        tbl_lbl.setStyleSheet("font-size:14px; font-weight:700; color:#0F172A;")
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setFixedHeight(30)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background:transparent; border:1px solid #D1D5DB;
                border-radius:5px; color:#374151; font-size:12px; padding:0 10px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        refresh_btn.clicked.connect(self._load)
        tbl_hdr.addWidget(tbl_lbl)
        tbl_hdr.addWidget(self._count_lbl)
        tbl_hdr.addStretch()
        tbl_hdr.addWidget(refresh_btn)
        c_lay.addLayout(tbl_hdr)

        cols = ["#", "Backup File", "Size", "Created At", "Actions"]
        self._table = DataTable(cols)
        self._table.set_column_widths({0: 44, 2: 100, 3: 180, 4: 200})
        c_lay.addWidget(self._table, 1)
        root.addWidget(content, 1)

        # ── Status bar ─────────────────────────────────────────────────────────
        status_bar = QFrame()
        status_bar.setStyleSheet("background:white; border-top:1px solid #E2E8F0;")
        status_bar.setFixedHeight(36)
        sb_lay = QHBoxLayout(status_bar)
        sb_lay.setContentsMargins(24, 0, 24, 0)
        self._status_lbl = QLabel("Ready.")
        self._status_lbl.setStyleSheet("color:#64748B; font-size:12px;")
        sb_lay.addWidget(self._status_lbl)
        root.addWidget(status_bar)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            self._backups = self._svc.list_backups()
            self._render()
            self._update_stats()
        except Exception as e:
            logger.error(f"Backup list load error: {e}")

    def _render(self) -> None:
        self._table.setRowCount(0)
        for i, bk in enumerate(self._backups):
            self._table.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val))
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            size_str = (
                f"{bk['size_kb']:.1f} KB" if bk['size_kb'] < 1024
                else f"{bk['size_kb']/1024:.2f} MB"
            )
            created  = bk['created_at'].strftime("%d %b %Y  %H:%M:%S")

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(bk["name"]))
            self._table.setItem(i, 2, _item(size_str))
            self._table.setItem(i, 3, _item(created))

            path = bk["path"]
            self._table.add_action_cell(i, 4, [
                ("Restore", "🔄", lambda _, p=path: self._on_restore(p)),
                ("Delete",  "🗑️", lambda _, p=path: self._on_delete_backup(p)),
            ])

        cnt = len(self._backups)
        self._count_lbl.setText(f"{cnt} backup{'s' if cnt != 1 else ''}")

    def _update_stats(self) -> None:
        try:
            db_path = config.DB_PATH
            if db_path.exists():
                size_kb = db_path.stat().st_size / 1024
                size_str = (f"{size_kb:.1f} KB" if size_kb < 1024
                            else f"{size_kb/1024:.2f} MB")
                self._stat_widgets["db_size"].setText(size_str)
            else:
                self._stat_widgets["db_size"].setText("Not found")

            # Record count
            try:
                from app.core.database import get_db
                from app.models.asset import Asset
                from app.models.person import Person
                with get_db() as db:
                    assets  = db.query(Asset).filter(Asset.is_deleted == False).count()
                    persons = db.query(Person).filter(Person.is_deleted == False).count()
                self._stat_widgets["records"].setText(
                    f"{assets} assets · {persons} persons"
                )
            except Exception:
                self._stat_widgets["records"].setText("—")

            # Last backup
            if self._backups:
                last = self._backups[0]["created_at"].strftime("%d %b %Y  %H:%M")
                self._stat_widgets["last_backup"].setText(last)
            else:
                self._stat_widgets["last_backup"].setText("No backups yet")

            # Location
            loc = str(config.BACKUPS_DIR)
            if len(loc) > 40:
                loc = "…" + loc[-38:]
            self._stat_widgets["location"].setText(loc)

        except Exception as e:
            logger.warning(f"Stats update error: {e}")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_create_backup(self) -> None:
        self._do_backup(None)

    def _on_backup_custom(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose Backup Location", str(config.BACKUPS_DIR)
        )
        if folder:
            self._do_backup(Path(folder))

    def _do_backup(self, dest) -> None:
        self._backup_btn.setEnabled(False)
        self._backup_btn.setText("Creating backup…")
        self._status_lbl.setText("⏳  Backup in progress…")
        self._status_lbl.setStyleSheet("color:#2563EB; font-size:12px;")

        # Run in a thread so the UI doesn't freeze
        self._thread  = QThread()
        self._worker  = _BackupWorker(self._svc, dest)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_backup_done)
        self._worker.error.connect(self._on_backup_error)
        self._worker.done.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.start()

    def _on_backup_done(self, filepath: str) -> None:
        self._backup_btn.setEnabled(True)
        self._backup_btn.setText("💾  Create Backup Now")
        self._status_lbl.setText(f"✅  Backup saved: {Path(filepath).name}")
        self._status_lbl.setStyleSheet("color:#15803D; font-size:12px; font-weight:600;")
        app_signals.show_notification.emit(
            "Backup Created",
            f"Saved: {Path(filepath).name}",
            "success",
        )
        self._load()

    def _on_backup_error(self, msg: str) -> None:
        self._backup_btn.setEnabled(True)
        self._backup_btn.setText("💾  Create Backup Now")
        self._status_lbl.setText(f"❌  Backup failed: {msg}")
        self._status_lbl.setStyleSheet("color:#DC2626; font-size:12px; font-weight:600;")
        app_signals.show_notification.emit("Backup Failed", msg, "error")

    def _on_restore(self, backup_path: Path) -> None:
        name = backup_path.name
        # Two-step confirmation for destructive restore
        dlg1 = ConfirmDialog(
            title="Restore Database",
            message=(
                f"You are about to restore from:\n'{name}'\n\n"
                "This will REPLACE your current database. "
                "All data added after this backup was created will be lost.\n\n"
                "A safety copy of the current database will be created first."
            ),
            confirm_label="Yes, Restore",
            danger=True,
            parent=self,
        )
        if dlg1.exec() != QDialog.Accepted:
            return

        dlg2 = ConfirmDialog(
            title="⚠️  Final Confirmation",
            message=(
                "This is your last chance.\n\n"
                "Restoring will restart the application.\n"
                "Click 'Restore Now' to proceed."
            ),
            confirm_label="Restore Now",
            danger=True,
            parent=self,
        )
        if dlg2.exec() != QDialog.Accepted:
            return

        try:
            self._svc.restore_backup(backup_path)
            self._status_lbl.setText("✅  Restore complete — please restart Sanchay.")
            self._status_lbl.setStyleSheet("color:#15803D; font-size:12px; font-weight:700;")
            app_signals.show_notification.emit(
                "Restore Complete",
                "Database restored. Please restart the application for changes to take effect.",
                "success",
            )
            QMessageBox.information(
                self,
                "Restore Complete",
                "The database has been restored successfully.\n\n"
                "Please close and restart Sanchay for the changes to take effect.",
            )
        except Exception as e:
            app_signals.show_notification.emit("Restore Failed", str(e), "error")
            self._status_lbl.setText(f"❌  Restore failed: {e}")

    def _on_delete_backup(self, backup_path: Path) -> None:
        dlg = ConfirmDialog(
            title="Delete Backup",
            message=f"Permanently delete backup file:\n'{backup_path.name}'?",
            confirm_label="Delete",
            danger=True,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted:
            try:
                self._svc.delete_backup(backup_path)
                self._load()
                app_signals.show_notification.emit(
                    "Deleted", f"'{backup_path.name}' removed.", "info"
                )
            except Exception as e:
                app_signals.show_notification.emit("Error", str(e), "error")
