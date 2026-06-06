"""
Sanchay — Settings View
=========================
3-tab settings panel:
  General    — app settings (asset prefix, auto-backup, theme)
  Audit Log  — immutable audit trail viewer
  About      — version, database path, library info
"""

import sys
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QTableWidgetItem, QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QDate

from app.config import config
from app.services.settings_service import SettingsService
from app.core.signals import app_signals
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from loguru import logger


class SettingsView(QWidget):
    """Tabbed settings page: General | Audit Log | About."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc = SettingsService()
        self._build_ui()
        self._load_general()
        self._load_audit()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        hdr = QFrame()
        hdr.setStyleSheet("background:#1E293B;")
        hdr.setFixedHeight(52)
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(24, 0, 24, 0)
        t = QLabel("⚙️  Settings"); t.setStyleSheet("color:white; font-size:16px; font-weight:700;")
        s = QLabel("Manage application preferences and view the audit trail")
        s.setStyleSheet("color:#94A3B8; font-size:12px;")
        h_lay.addWidget(t); h_lay.addSpacing(20); h_lay.addWidget(s); h_lay.addStretch()
        root.addWidget(hdr)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#F8FAFC; }
            QTabBar { background:white; border-bottom:2px solid #E2E8F0; }
            QTabBar::tab {
                padding:10px 24px; border:none;
                border-bottom:3px solid transparent;
                color:#64748B; font-weight:500; background:white;
            }
            QTabBar::tab:selected {
                color:#2563EB; border-bottom:3px solid #2563EB; font-weight:700;
            }
            QTabBar::tab:hover:!selected { color:#374151; }
        """)
        self._tabs.addTab(self._build_general_tab(), "⚙️  General")
        self._tabs.addTab(self._build_audit_tab(),   "📋  Audit Log")
        self._tabs.addTab(self._build_about_tab(),   "ℹ️  About")
        self._tabs.currentChanged.connect(self._on_tab_change)
        root.addWidget(self._tabs, 1)

    # ── Tab 1: General ────────────────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:#F8FAFC;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(32, 24, 32, 24)
        outer.setSpacing(24)

        # ── Section: Asset defaults ────────────────────────────────────────────
        card = self._card()
        cl   = QVBoxLayout(card); cl.setContentsMargins(20,16,20,20); cl.setSpacing(14)
        cl.addWidget(self._section_label("📦  Asset Defaults"))

        f1 = QFormLayout(); f1.setSpacing(12); f1.setLabelAlignment(Qt.AlignLeft)
        f1.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_prefix = QLineEdit()
        self.f_prefix.setPlaceholderText("e.g. AST")
        self.f_prefix.setMaxLength(10)
        self.f_prefix.setFixedHeight(36)
        self._si(self.f_prefix)

        hint = QLabel("Auto-generated asset codes will be: PREFIX-0001, PREFIX-0002, …")
        hint.setStyleSheet("color:#64748B; font-size:11px;")

        f1.addRow(self._lbl("Asset Code Prefix"), self.f_prefix)
        cl.addLayout(f1)
        cl.addWidget(hint)
        outer.addWidget(card)

        # ── Section: Backup settings ───────────────────────────────────────────
        card2 = self._card()
        cl2   = QVBoxLayout(card2); cl2.setContentsMargins(20,16,20,20); cl2.setSpacing(14)
        cl2.addWidget(self._section_label("💾  Backup Settings"))

        self.f_auto_backup = QCheckBox("Enable automatic daily backup")
        self.f_auto_backup.setStyleSheet("font-size:13px; color:#374151;")

        f2 = QFormLayout(); f2.setSpacing(12); f2.setLabelAlignment(Qt.AlignLeft)
        f2.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_backup_loc = QLineEdit()
        self.f_backup_loc.setFixedHeight(36)
        self.f_backup_loc.setReadOnly(True)
        self.f_backup_loc.setStyleSheet("""
            QLineEdit {
                border:1px solid #E2E8F0; border-radius:6px;
                padding:0 10px; font-size:12px; background:#F8FAFC; color:#374151;
            }
        """)
        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedHeight(36)
        browse_btn.setStyleSheet("""
            QPushButton {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 14px; font-size:12px; background:white; color:#374151;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        browse_btn.clicked.connect(self._on_browse_backup_loc)

        loc_row = QHBoxLayout(); loc_row.setSpacing(8)
        loc_row.addWidget(self.f_backup_loc, 1)
        loc_row.addWidget(browse_btn)
        loc_w = QWidget(); loc_w.setLayout(loc_row); loc_w.setStyleSheet("background:transparent;")

        f2.addRow(self._lbl("Backup Location"), loc_w)

        cl2.addWidget(self.f_auto_backup)
        cl2.addLayout(f2)
        outer.addWidget(card2)

        # ── Save button ────────────────────────────────────────────────────────
        save_btn = QPushButton("💾  Save Settings")
        save_btn.setFixedHeight(42)
        save_btn.setFixedWidth(200)
        save_btn.setStyleSheet("""
            QPushButton {
                background:#2563EB; color:white; border-radius:8px;
                font-size:14px; font-weight:700;
            }
            QPushButton:hover { background:#1D4ED8; }
        """)
        save_btn.clicked.connect(self._on_save_general)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        outer.addLayout(btn_row)
        outer.addStretch()
        return w

    def _load_general(self) -> None:
        self.f_prefix.setText(self._svc.get("asset_code_prefix", "AST"))
        self.f_auto_backup.setChecked(self._svc.get_bool("auto_backup", False))
        loc = self._svc.backup_location
        self.f_backup_loc.setText(loc)

    def _on_browse_backup_loc(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Backup Folder",
            self.f_backup_loc.text() or str(config.BACKUPS_DIR),
        )
        if folder:
            self.f_backup_loc.setText(folder)

    def _on_save_general(self) -> None:
        prefix = self.f_prefix.text().strip().upper()
        if not prefix or len(prefix) < 2:
            app_signals.show_notification.emit(
                "Validation Error", "Asset prefix must be at least 2 characters.", "warning"
            )
            return
        self._svc.set_many({
            "asset_code_prefix": prefix,
            "auto_backup":       "true" if self.f_auto_backup.isChecked() else "false",
            "backup_location":   self.f_backup_loc.text().strip(),
        })
        app_signals.show_notification.emit("Saved", "Settings saved successfully.", "success")

    # ── Tab 2: Audit Log ──────────────────────────────────────────────────────

    def _build_audit_tab(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:#F8FAFC;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(12)

        # Filter row
        flt = QHBoxLayout(); flt.setSpacing(10)
        self._audit_search = SearchBar("Search action, user, description…")
        self._audit_search.set_min_width(280)
        self._audit_search.search_changed.connect(self._load_audit)

        self._audit_module = QComboBox()
        self._audit_module.setFixedHeight(34)
        self._audit_module.setMinimumWidth(140)
        self._audit_module.setStyleSheet("""
            QComboBox { border:1px solid #D1D5DB; border-radius:6px;
                        padding:0 8px; font-size:12px; background:white; }
            QComboBox::drop-down { border:none; width:16px; }
        """)
        self._audit_module.addItem("All Modules", None)
        for mod in ["assets","persons","users","organizations",
                    "departments","asset_issues","asset_returns","system"]:
            self._audit_module.addItem(mod.replace("_"," ").title(), mod)
        self._audit_module.currentIndexChanged.connect(lambda _: self._load_audit())

        self._audit_count = QLabel("")
        self._audit_count.setStyleSheet("color:#64748B; font-size:12px;")

        flt.addWidget(self._audit_search)
        flt.addWidget(self._audit_module)
        flt.addWidget(self._audit_count)
        flt.addStretch()
        lay.addLayout(flt)

        # Table
        cols = ["#", "Timestamp", "User", "Action", "Module", "Description"]
        self._audit_tbl = DataTable(cols)
        self._audit_tbl.set_column_widths({0: 44, 1: 160, 2: 100, 3: 90, 4: 110})
        lay.addWidget(self._audit_tbl, 1)
        return w

    def _load_audit(self, query: str = "") -> None:
        try:
            from app.core.database import get_db
            from app.models.audit import AuditLog
            from sqlalchemy import or_

            module_filter = self._audit_module.currentData() if hasattr(self, "_audit_module") else None
            q_text = query or (self._audit_search.text() if hasattr(self, "_audit_search") else "")

            with get_db() as db:
                q = db.query(AuditLog)
                if module_filter:
                    q = q.filter(AuditLog.module == module_filter)
                if q_text:
                    pat = f"%{q_text}%"
                    q = q.filter(or_(
                        AuditLog.action.ilike(pat),
                        AuditLog.description.ilike(pat),
                    ))
                logs = q.order_by(AuditLog.timestamp.desc()).limit(200).all()

            action_colors = {
                "CREATE": ("#DCFCE7","#15803D"), "UPDATE": ("#DBEAFE","#1D4ED8"),
                "DELETE": ("#FEE2E2","#B91C1C"), "LOGIN":  ("#F3E8FF","#7C3AED"),
                "ISSUE":  ("#FEF3C7","#B45309"), "RETURN": ("#DCFCE7","#15803D"),
                "BACKUP": ("#F0FDF4","#15803D"),
            }

            self._audit_tbl.setRowCount(0)
            for i, log in enumerate(logs):
                self._audit_tbl.insertRow(i)
                def _it(v):
                    it = QTableWidgetItem(str(v) if v else "—")
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    return it

                ab, af = action_colors.get(log.action, ("#F1F5F9","#374151"))
                self._audit_tbl.setItem(i, 0, _it(i+1))
                self._audit_tbl.setItem(i, 1, _it(
                    log.timestamp.strftime("%d %b %Y  %H:%M:%S")))
                self._audit_tbl.setItem(i, 2, _it(
                    log.user.username if log.user else "system"))
                self._audit_tbl.add_badge_cell(i, 3, log.action, ab, af)
                self._audit_tbl.setItem(i, 4, _it(log.module or "—"))
                self._audit_tbl.setItem(i, 5, _it(log.description or "—"))

            self._audit_count.setText(
                f"{len(logs)} log{'s' if len(logs)!=1 else ''} "
                f"{'(limited to 200)' if len(logs)==200 else ''}"
            )
        except Exception as e:
            logger.error(f"Audit log load error: {e}")

    # ── Tab 3: About ──────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        w = QWidget(); w.setStyleSheet("background:#F8FAFC;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(32, 24, 32, 24)
        lay.setSpacing(20)

        # App identity card
        app_card = self._card()
        ac_lay = QVBoxLayout(app_card)
        ac_lay.setContentsMargins(24, 20, 24, 20)
        ac_lay.setSpacing(8)

        logo = QLabel("📦")
        logo.setStyleSheet("font-size:48px;")
        logo.setAlignment(Qt.AlignCenter)

        name_lbl = QLabel(f"{config.APP_NAME}  v{config.APP_VERSION}")
        name_lbl.setStyleSheet(
            "font-size:22px; font-weight:700; color:#0F172A;"
        )
        name_lbl.setAlignment(Qt.AlignCenter)

        tag_lbl = QLabel(config.APP_TAGLINE)
        tag_lbl.setStyleSheet("font-size:14px; color:#64748B;")
        tag_lbl.setAlignment(Qt.AlignCenter)

        ac_lay.addWidget(logo)
        ac_lay.addWidget(name_lbl)
        ac_lay.addWidget(tag_lbl)
        lay.addWidget(app_card)

        # Tech info card
        tech_card = self._card()
        tc_lay = QFormLayout(tech_card)
        tc_lay.setContentsMargins(20, 16, 20, 16)
        tc_lay.setSpacing(10)
        tc_lay.setLabelAlignment(Qt.AlignLeft)

        import PySide6
        import sqlalchemy

        rows = [
            ("Python",       sys.version.split()[0]),
            ("PySide6 / Qt", PySide6.__version__),
            ("SQLAlchemy",   sqlalchemy.__version__),
            ("Database",     str(config.DB_PATH)),
            ("Exports",      str(config.EXPORTS_DIR)),
            ("Backups",      str(config.BACKUPS_DIR)),
            ("Logs",         str(config.LOG_FILE)),
        ]
        try:
            db_size = config.DB_PATH.stat().st_size / 1024
            rows.append(("DB Size", f"{db_size:.1f} KB"))
        except Exception:
            pass

        for label, value in rows:
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("font-size:12px; font-weight:600; color:#64748B;")
            val = QLabel(value)
            val.setStyleSheet("font-size:12px; color:#0F172A;")
            val.setWordWrap(True)
            tc_lay.addRow(lbl, val)

        lay.addWidget(tech_card)
        lay.addStretch()
        return w

    # ── Tab switch ────────────────────────────────────────────────────────────

    def _on_tab_change(self, idx: int) -> None:
        if idx == 1:
            self._load_audit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _card() -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:10px; }"
        )
        return f

    @staticmethod
    def _section_label(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(
            "font-size:13px; font-weight:700; color:#0F172A; "
            "border-bottom:2px solid #E2E8F0; padding-bottom:6px;"
        )
        return l

    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(f"{text}:")
        l.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        return l

    @staticmethod
    def _si(w) -> None:
        w.setStyleSheet("""
            QLineEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; color:#0F172A; background:white;
            }
            QLineEdit:focus { border:2px solid #2563EB; padding:0 9px; }
        """)
