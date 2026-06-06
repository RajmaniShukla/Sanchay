"""
Sanchay — Report View
=======================
Full-page report builder:
  Left  — report type selector (card buttons)
  Right — filter panel + live preview table
  Footer— record count + PDF / Excel / CSV export buttons
"""

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QDateEdit, QFileDialog, QTableWidgetItem,
    QScrollArea, QButtonGroup, QSizePolicy,
)
from PySide6.QtCore import Qt, QDate, QThread, Signal, QObject
from PySide6.QtGui import QColor

from app.config import config
from app.services.report_service import ReportService, ReportData, REPORT_TYPES
from app.services.organization_service import DepartmentService
from app.services.asset_service import AssetCategoryService
from app.core.security import current_session
from app.core.signals import app_signals
from app.views.widgets.data_table import DataTable
from loguru import logger


# ── Worker thread for generation / export ─────────────────────────────────────

class _Worker(QObject):
    """Run long operations off the UI thread."""
    finished = Signal(object)          # ReportData or Path
    error    = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn   = fn
        self._args = args
        self._kw   = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kw)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ── Report type button ────────────────────────────────────────────────────────

class _TypeBtn(QPushButton):
    """Styled checkable card for the report type selector."""

    ICONS = {
        "asset_inventory": "📦",
        "dept_assets":     "🏗️",
        "issue_history":   "📤",
        "return_history":  "📥",
        "overdue":         "⚠️",
        "person_holdings": "👥",
    }

    def __init__(self, key: str, label: str, parent=None):
        super().__init__(parent)
        self.key = key
        icon = self.ICONS.get(key, "📋")
        self.setText(f"{icon}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, checked: bool) -> None:
        if checked:
            self.setStyleSheet("""
                QPushButton {
                    background:#EFF6FF; border:2px solid #2563EB;
                    border-radius:8px; color:#1D4ED8; font-weight:700;
                    font-size:13px; text-align:left; padding:0 16px;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background:white; border:1px solid #E2E8F0;
                    border-radius:8px; color:#374151; font-weight:500;
                    font-size:13px; text-align:left; padding:0 16px;
                }
                QPushButton:hover { background:#F8FAFC; border-color:#CBD5E1; }
            """)

    def setChecked(self, checked: bool) -> None:
        super().setChecked(checked)
        self._apply_style(checked)


# ── Main Report View ──────────────────────────────────────────────────────────

class ReportView(QWidget):
    """Report builder / exporter page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc         = ReportService()
        self._report_data: ReportData | None = None
        self._active_type = "asset_inventory"
        self._build_ui()
        self._populate_filters()
        # Select first report type
        if self._type_btns:
            self._type_btns[0].setChecked(True)

    # ── UI Build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────────────────────
        hdr = QFrame()
        hdr.setStyleSheet("background:#1E293B;")
        hdr.setFixedHeight(52)
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(24, 0, 24, 0)
        title = QLabel("📊  Reports & Exports")
        title.setStyleSheet("color:white; font-size:16px; font-weight:700;")
        sub   = QLabel("Generate, preview, and export data in PDF · Excel · CSV")
        sub.setStyleSheet("color:#94A3B8; font-size:12px;")
        h_lay.addWidget(title)
        h_lay.addSpacing(20)
        h_lay.addWidget(sub)
        h_lay.addStretch()
        root.addWidget(hdr)

        # ── Body (left panel + right panel) ────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background:#F8FAFC;")
        b_lay = QHBoxLayout(body)
        b_lay.setContentsMargins(20, 16, 20, 0)
        b_lay.setSpacing(16)

        b_lay.addWidget(self._build_left_panel(), 0)
        b_lay.addWidget(self._build_right_panel(), 1)
        root.addWidget(body, 1)

        # ── Footer ─────────────────────────────────────────────────────────────
        root.addWidget(self._build_footer())

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setFixedWidth(228)
        panel.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:10px; }"
        )
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(6)

        lbl = QLabel("Report Type")
        lbl.setStyleSheet(
            "font-size:11px; font-weight:700; color:#64748B; "
            "letter-spacing:1px; text-transform:uppercase;"
        )
        lay.addWidget(lbl)
        lay.addSpacing(4)

        self._type_btns: list[_TypeBtn] = []
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        for key, label in REPORT_TYPES.items():
            btn = _TypeBtn(key, label)
            btn.clicked.connect(lambda _, k=key: self._on_type_select(k))
            self._btn_group.addButton(btn)
            self._type_btns.append(btn)
            lay.addWidget(btn)

        lay.addStretch()
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # ── Filter card ────────────────────────────────────────────────────────
        flt = QFrame()
        flt.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        flt.setFixedHeight(64)
        f_lay = QHBoxLayout(flt)
        f_lay.setContentsMargins(16, 8, 16, 8)
        f_lay.setSpacing(12)

        combo_css = """
            QComboBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 8px; font-size:12px; background:white; min-height:32px;
            }
            QComboBox:focus { border-color:#2563EB; }
            QComboBox::drop-down { border:none; width:16px; }
        """
        date_css = """
            QDateEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 8px; font-size:12px; background:white; min-height:32px;
            }
            QDateEdit:focus { border-color:#2563EB; }
        """
        lbl_css = "font-size:11px; font-weight:600; color:#374151;"

        # Dept filter
        self._dept_lbl = QLabel("Dept:")
        self._dept_lbl.setStyleSheet(lbl_css)
        self._dept_cb = QComboBox()
        self._dept_cb.setMinimumWidth(150)
        self._dept_cb.setStyleSheet(combo_css)

        # Status filter
        self._status_lbl = QLabel("Status:")
        self._status_lbl.setStyleSheet(lbl_css)
        self._status_cb = QComboBox()
        self._status_cb.setMinimumWidth(130)
        self._status_cb.setStyleSheet(combo_css)
        for s in [("All Status", None), ("Available", "available"),
                  ("Issued", "issued"), ("Maintenance", "maintenance"),
                  ("Disposed", "disposed")]:
            self._status_cb.addItem(s[0], s[1])

        # Date range
        self._from_lbl = QLabel("From:")
        self._from_lbl.setStyleSheet(lbl_css)
        self._from_dt = QDateEdit()
        self._from_dt.setCalendarPopup(True)
        self._from_dt.setDisplayFormat("dd/MM/yy")
        self._from_dt.setDate(QDate.currentDate().addDays(-90))
        self._from_dt.setFixedHeight(32)
        self._from_dt.setStyleSheet(date_css)

        self._to_lbl = QLabel("To:")
        self._to_lbl.setStyleSheet(lbl_css)
        self._to_dt = QDateEdit()
        self._to_dt.setCalendarPopup(True)
        self._to_dt.setDisplayFormat("dd/MM/yy")
        self._to_dt.setDate(QDate.currentDate())
        self._to_dt.setFixedHeight(32)
        self._to_dt.setStyleSheet(date_css)

        # Person type
        self._ptype_lbl = QLabel("Person:")
        self._ptype_lbl.setStyleSheet(lbl_css)
        self._ptype_cb = QComboBox()
        self._ptype_cb.setMinimumWidth(130)
        self._ptype_cb.setStyleSheet(combo_css)
        for pt in [("All Types", None), ("Employee", "employee"),
                   ("Student", "student"), ("Contractor", "contractor"),
                   ("Candidate", "candidate")]:
            self._ptype_cb.addItem(pt[0], pt[1])

        f_lay.addWidget(self._dept_lbl)
        f_lay.addWidget(self._dept_cb)
        f_lay.addWidget(self._status_lbl)
        f_lay.addWidget(self._status_cb)
        f_lay.addWidget(self._from_lbl)
        f_lay.addWidget(self._from_dt)
        f_lay.addWidget(self._to_lbl)
        f_lay.addWidget(self._to_dt)
        f_lay.addWidget(self._ptype_lbl)
        f_lay.addWidget(self._ptype_cb)
        f_lay.addStretch()

        gen_btn = QPushButton("▶  Generate Preview")
        gen_btn.setFixedHeight(36)
        gen_btn.setStyleSheet("""
            QPushButton {
                background:#2563EB; color:white; border-radius:6px;
                font-weight:600; padding:0 16px; font-size:12px;
            }
            QPushButton:hover { background:#1D4ED8; }
        """)
        gen_btn.clicked.connect(self._on_generate)
        f_lay.addWidget(gen_btn)

        lay.addWidget(flt)

        # ── Preview table ──────────────────────────────────────────────────────
        preview_lbl = QLabel("Preview  (first 100 rows)")
        preview_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        lay.addWidget(preview_lbl)

        self._table = DataTable(["Code", "Name", "Status"])   # rebuilt on generate
        lay.addWidget(self._table, 1)
        return panel

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setStyleSheet("background:white; border-top:1px solid #E2E8F0;")
        footer.setFixedHeight(58)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 9, 24, 9)
        f_lay.setSpacing(10)

        self._rec_lbl = QLabel("Generate a report to see the preview.")
        self._rec_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        btn_css = lambda bg, hov: f"""
            QPushButton {{
                background:{bg}; color:white; border-radius:6px;
                font-weight:600; font-size:12px; padding:0 18px;
            }}
            QPushButton:hover {{ background:{hov}; }}
            QPushButton:disabled {{ background:#D1D5DB; color:#9CA3AF; }}
        """
        self._pdf_btn = QPushButton("📄  Export PDF")
        self._pdf_btn.setFixedHeight(38)
        self._pdf_btn.setEnabled(False)
        self._pdf_btn.setStyleSheet(btn_css("#DC2626", "#B91C1C"))
        self._pdf_btn.clicked.connect(self._on_export_pdf)

        self._xls_btn = QPushButton("📊  Export Excel")
        self._xls_btn.setFixedHeight(38)
        self._xls_btn.setEnabled(False)
        self._xls_btn.setStyleSheet(btn_css("#16A34A", "#15803D"))
        self._xls_btn.clicked.connect(self._on_export_excel)

        self._csv_btn = QPushButton("📋  Export CSV")
        self._csv_btn.setFixedHeight(38)
        self._csv_btn.setEnabled(False)
        self._csv_btn.setStyleSheet(btn_css("#0891B2", "#0E7490"))
        self._csv_btn.clicked.connect(self._on_export_csv)

        f_lay.addWidget(self._rec_lbl, 1)
        f_lay.addWidget(self._pdf_btn)
        f_lay.addWidget(self._xls_btn)
        f_lay.addWidget(self._csv_btn)
        return footer

    # ── Filter population ─────────────────────────────────────────────────────

    def _populate_filters(self) -> None:
        try:
            org_id = current_session.org_id
            self._dept_cb.addItem("All Departments", None)
            if org_id:
                depts = DepartmentService().get_by_org(org_id)
                for d in depts:
                    self._dept_cb.addItem(f"{d.name} ({d.code})", d.id)
        except Exception as e:
            logger.warning(f"Filter population error: {e}")

    def _on_type_select(self, key: str) -> None:
        self._active_type = key
        for btn in self._type_btns:
            btn.setChecked(btn.key == key)
        # Show/hide relevant filters
        date_needed  = key in ("issue_history", "return_history")
        status_needed = key in ("asset_inventory",)
        ptype_needed  = key == "person_holdings"
        self._from_lbl.setVisible(date_needed)
        self._from_dt.setVisible(date_needed)
        self._to_lbl.setVisible(date_needed)
        self._to_dt.setVisible(date_needed)
        self._status_lbl.setVisible(status_needed)
        self._status_cb.setVisible(status_needed)
        self._ptype_lbl.setVisible(ptype_needed)
        self._ptype_cb.setVisible(ptype_needed)
        # Clear old preview
        self._table.clear_data()
        self._report_data = None
        self._enable_export_btns(False)
        self._rec_lbl.setText("Click  ▶ Generate Preview  to build the report.")

    # ── Generate ──────────────────────────────────────────────────────────────

    def _on_generate(self) -> None:
        self._rec_lbl.setText("Generating…")
        self._enable_export_btns(False)
        self._table.clear_data()

        fd  = self._from_dt.date()
        td  = self._to_dt.date()
        from datetime import date as _date
        from_d = _date(fd.year(), fd.month(), fd.day())
        to_d   = _date(td.year(), td.month(), td.day())

        org   = current_session.org_id
        org_n = ""
        try:
            from app.services.organization_service import OrganizationService
            if org:
                o = OrganizationService().get_by_id(org)
                org_n = o.name
        except Exception:
            pass

        try:
            data = self._svc.generate(
                report_type=self._active_type,
                org_id=org,
                org_name=org_n or config.APP_NAME,
                dept_id=self._dept_cb.currentData(),
                status=self._status_cb.currentData(),
                person_type=self._ptype_cb.currentData(),
                from_date=from_d,
                to_date=to_d,
            )
            self._on_generate_done(data)
        except Exception as e:
            self._rec_lbl.setText(f"Error: {e}")
            app_signals.show_notification.emit("Report Error", str(e), "error")

    def _on_generate_done(self, data: ReportData) -> None:
        self._report_data = data

        # Rebuild the preview table with correct columns
        # Recreate DataTable in the right panel
        old = self._table
        new_tbl = DataTable(data.columns)
        new_tbl.setAlternatingRowColors(True)
        layout = old.parent().layout()
        idx = layout.indexOf(old)
        layout.removeWidget(old)
        old.deleteLater()
        layout.insertWidget(idx, new_tbl, 1)
        self._table = new_tbl

        # Fill preview (first 100 rows)
        preview = data.rows[:100]
        self._table.set_data(preview)

        shown = len(preview)
        total = data.row_count
        extra = f" (showing first {shown})" if total > shown else ""
        self._rec_lbl.setText(
            f"✅  {total} record{'s' if total != 1 else ''} found{extra}."
            + "  |  " + "  |  ".join(f"{k}: {v}" for k, v in data.summary.items())
        )
        self._rec_lbl.setStyleSheet("color:#15803D; font-size:12px; font-weight:600;")
        self._enable_export_btns(True)
        app_signals.show_notification.emit(
            "Report Ready",
            f"{REPORT_TYPES.get(data.report_type, 'Report')} — {total} rows",
            "success",
        )

    # ── Export ────────────────────────────────────────────────────────────────

    def _on_export_pdf(self) -> None:
        self._export("pdf")

    def _on_export_excel(self) -> None:
        self._export("xlsx")

    def _on_export_csv(self) -> None:
        self._export("csv")

    def _export(self, fmt: str) -> None:
        if not self._report_data:
            return
        default_name = ReportService.default_filename(self._active_type, fmt)
        default_path = str(config.EXPORTS_DIR / default_name)

        filters = {
            "pdf":  "PDF Files (*.pdf)",
            "xlsx": "Excel Files (*.xlsx)",
            "csv":  "CSV Files (*.csv)",
        }
        filepath, _ = QFileDialog.getSaveFileName(
            self, f"Export {fmt.upper()}", default_path, filters[fmt]
        )
        if not filepath:
            return

        btn_map = {"pdf": self._pdf_btn, "xlsx": self._xls_btn, "csv": self._csv_btn}
        btn = btn_map.get(fmt)
        if btn:
            btn.setEnabled(False)
            btn.setText("Exporting…")

        try:
            fn_map = {
                "pdf":  self._svc.export_pdf,
                "xlsx": self._svc.export_excel,
                "csv":  self._svc.export_csv,
            }
            out = fn_map[fmt](self._report_data, Path(filepath))
            app_signals.show_notification.emit(
                "Export Complete",
                f"Saved to: {out.name}",
                "success",
            )
            # Open containing folder
            self._open_folder(out.parent)
        except Exception as e:
            app_signals.show_notification.emit("Export Failed", str(e), "error")
        finally:
            if btn:
                btn.setEnabled(True)
                labels = {"pdf": "📄  Export PDF",
                          "xlsx": "📊  Export Excel",
                          "csv": "📋  Export CSV"}
                btn.setText(labels[fmt])

    @staticmethod
    def _open_folder(path: Path) -> None:
        """Open the folder in the OS file explorer."""
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    def _enable_export_btns(self, enabled: bool) -> None:
        for btn in (self._pdf_btn, self._xls_btn, self._csv_btn):
            btn.setEnabled(enabled)
