"""
Sanchay — Return Asset View
=============================
Full-page workflow for recording an asset return.

Top   : Search active issues (by asset name / person / code)
Middle: Table of matching active issues — click a row to select
Bottom: Return form — condition on return, remarks → Record Return
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QTextEdit, QTableWidgetItem,
)
from PySide6.QtCore import Qt, QTimer

from app.services.transaction_service import TransactionService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.transaction import AssetIssue
from app.constants import AssetCondition
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from loguru import logger


class ReturnView(QWidget):
    """Full-page workflow for recording an asset return."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._txn_svc = TransactionService()
        self._issues: list[AssetIssue] = []
        self._selected_issue: AssetIssue | None = None
        self._build_ui()
        self._load_issues()

        # Refresh when an issue is created or returned elsewhere
        app_signals.asset_issued.connect(lambda *_: self._load_issues())
        app_signals.asset_returned.connect(lambda *_: self._load_issues())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Info bar ───────────────────────────────────────────────────────────
        info = QFrame()
        info.setStyleSheet("background:#FFF7ED; border-bottom:1px solid #FED7AA;")
        info.setFixedHeight(40)
        i_lay = QHBoxLayout(info)
        i_lay.setContentsMargins(24, 0, 24, 0)
        tip = QLabel("ℹ️  Search for the active issue below, click the row to select it, "
                     "fill in the return details and click Record Return.")
        tip.setStyleSheet("color:#B45309; font-size:12px;")
        i_lay.addWidget(tip)
        root.addWidget(info)

        # ── Content ────────────────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background:#F8FAFC;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 16)
        c_lay.setSpacing(16)

        # ── Search bar ─────────────────────────────────────────────────────────
        search_row = QHBoxLayout()
        self._search = SearchBar("Search active issues by asset name, person name, code…")
        self._search.set_min_width(400)
        self._search.search_changed.connect(self._on_search)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        search_row.addWidget(self._search)
        search_row.addWidget(self._count_lbl)
        search_row.addStretch()
        c_lay.addLayout(search_row)

        # ── Active issues table ────────────────────────────────────────────────
        tbl_lbl = QLabel("Active Issues  —  click a row to select")
        tbl_lbl.setStyleSheet("font-size:13px; font-weight:700; color:#0F172A;")
        c_lay.addWidget(tbl_lbl)

        cols = ["#", "Asset Code", "Asset Name", "Issued To", "Type",
                "Issued Date", "Expected Return", "Days Remaining", "Status"]
        self._table = DataTable(cols)
        self._table.setFixedHeight(240)
        self._table.set_column_widths(
            {0: 44, 1: 100, 4: 100, 5: 140, 6: 130, 7: 110, 8: 90}
        )
        self._table.row_selected.connect(self._on_row_select)
        c_lay.addWidget(self._table)

        # ── Return details card ────────────────────────────────────────────────
        self._detail_card = QFrame()
        self._detail_card.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        self._detail_card.setVisible(False)
        dc_lay = QVBoxLayout(self._detail_card)
        dc_lay.setContentsMargins(20, 16, 20, 16)
        dc_lay.setSpacing(12)

        # Selected issue summary
        self._issue_summary = QLabel("")
        self._issue_summary.setStyleSheet(
            "font-size:13px; font-weight:600; color:#0F172A; "
            "background:#F8FAFC; border-radius:6px; padding:10px 14px;"
        )
        self._issue_summary.setWordWrap(True)
        dc_lay.addWidget(self._issue_summary)

        form_row = QHBoxLayout()
        form_row.setSpacing(16)

        # Condition
        cond_col = QVBoxLayout()
        cond_col.setSpacing(4)
        cond_lbl = QLabel("Condition on Return")
        cond_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        self._condition = QComboBox()
        self._condition.setFixedHeight(36)
        self._condition.setMinimumWidth(180)
        self._condition.setStyleSheet("""
            QComboBox {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QComboBox:focus { border:2px solid #2563EB; }
            QComboBox::drop-down { border:none; width:20px; }
        """)
        for cond in AssetCondition:
            self._condition.addItem(cond.label(), cond.value)
        # default "good"
        for i in range(self._condition.count()):
            if self._condition.itemData(i) == "good":
                self._condition.setCurrentIndex(i)
                break
        cond_col.addWidget(cond_lbl)
        cond_col.addWidget(self._condition)
        form_row.addLayout(cond_col)

        # Remarks
        rem_col = QVBoxLayout()
        rem_col.setSpacing(4)
        rem_lbl = QLabel("Remarks")
        rem_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        self._remarks = QTextEdit()
        self._remarks.setFixedHeight(64)
        self._remarks.setPlaceholderText("Any observations or notes about this return…")
        self._remarks.setStyleSheet("""
            QTextEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:8px; font-size:13px;
            }
            QTextEdit:focus { border:2px solid #2563EB; padding:7px; }
        """)
        rem_col.addWidget(rem_lbl)
        rem_col.addWidget(self._remarks)
        form_row.addLayout(rem_col, 2)
        dc_lay.addLayout(form_row)
        c_lay.addWidget(self._detail_card)
        c_lay.addStretch()
        root.addWidget(content, 1)

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet("background:white; border-top:1px solid #E2E8F0;")
        footer.setFixedHeight(60)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 10, 24, 10)
        f_lay.setSpacing(12)

        self._footer_lbl = QLabel("Select an active issue from the table above.")
        self._footer_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        self._return_btn = QPushButton("📥  Record Return")
        self._return_btn.setFixedHeight(40)
        self._return_btn.setMinimumWidth(170)
        self._return_btn.setEnabled(False)
        self._return_btn.setStyleSheet("""
            QPushButton {
                background:#D97706; color:white; border-radius:8px;
                font-weight:700; font-size:14px; padding:0 24px;
            }
            QPushButton:hover  { background:#B45309; }
            QPushButton:disabled { background:#D1D5DB; color:#9CA3AF; }
        """)
        self._return_btn.clicked.connect(self._on_return)

        f_lay.addWidget(self._footer_lbl, 1)
        f_lay.addWidget(self._return_btn)
        root.addWidget(footer)

    # ── Data ──────────────────────────────────────────────────────────────────

    def _load_issues(self, query: str = "") -> None:
        self._count_lbl.setText("Loading…")
        try:
            issues, _ = self._txn_svc.get_all_issues(
                org_id=current_session.org_id,
                status="active",
                limit=200,
            )
            if query:
                q = query.lower()
                issues = [
                    i for i in issues
                    if q in (i.asset.name if i.asset else "").lower()
                    or q in (i.person.full_name if i.person else "").lower()
                    or q in (i.asset.asset_code if i.asset else "").lower()
                ]
            self._issues = issues
            self._render()
        except Exception as e:
            logger.error(f"Return view load error: {e}")
            self._count_lbl.setText("Error loading data")

    def _render(self) -> None:
        from datetime import date as dt_date
        today = dt_date.today()
        self._table.setRowCount(0)

        for i, issue in enumerate(self._issues):
            self._table.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            asset = issue.asset
            person = issue.person
            exp = issue.expected_return_date

            if exp:
                diff = (exp - today).days
                remaining = f"{diff}d" if diff >= 0 else f"⚠ {abs(diff)}d overdue"
                rem_color = "#15803D" if diff >= 0 else "#DC2626"
            else:
                remaining = "—"
                rem_color = "#374151"

            self._table.setItem(i, 0, _item(i + 1))
            self._table.setItem(i, 1, _item(asset.asset_code if asset else "—"))
            self._table.setItem(i, 2, _item(asset.name if asset else "—"))
            self._table.setItem(i, 3, _item(person.full_name if person else "—"))
            self._table.setItem(i, 4, _item(
                person.person_type.capitalize() if person else "—"))
            self._table.setItem(i, 5, _item(
                issue.issue_date.strftime("%d %b %Y %H:%M")))
            self._table.setItem(i, 6, _item(
                exp.strftime("%d %b %Y") if exp else "—"))

            # Remaining days with color
            rem_it = QTableWidgetItem(remaining)
            rem_it.setFlags(rem_it.flags() & ~Qt.ItemIsEditable)
            from PySide6.QtGui import QColor
            rem_it.setForeground(QColor(rem_color))
            if "overdue" in remaining:
                from PySide6.QtGui import QFont
                f = rem_it.font(); f.setBold(True); rem_it.setFont(f)
            self._table.setItem(i, 7, rem_it)

            bg  = "#FEE2E2" if "overdue" in remaining else "#DBEAFE"
            fg  = "#B91C1C" if "overdue" in remaining else "#1D4ED8"
            lbl = "Overdue" if "overdue" in remaining else "Active"
            self._table.add_badge_cell(i, 8, lbl, bg, fg)

        cnt = len(self._issues)
        self._count_lbl.setText(f"{cnt} active issue{'s' if cnt != 1 else ''}")

        # Show an empty-state hint if no active issues exist
        if cnt == 0:
            self._footer_lbl.setText(
                "ℹ️  No active issues found. All assets have been returned."
            )
            self._footer_lbl.setStyleSheet("color:#15803D; font-size:12px; font-weight:500;")
        else:
            self._footer_lbl.setText("Select an active issue from the table above.")
            self._footer_lbl.setStyleSheet("color:#64748B; font-size:12px;")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_search(self, query: str) -> None:
        self._load_issues(query)

    def _on_row_select(self, row: int) -> None:
        if row >= len(self._issues):
            return
        self._selected_issue = self._issues[row]
        issue = self._selected_issue
        asset  = issue.asset
        person = issue.person

        summary = (
            f"Asset:   {asset.name if asset else '—'}  ({asset.asset_code if asset else '—'})\n"
            f"Person:  {person.full_name if person else '—'}  ({person.display_code if person else '—'})\n"
            f"Issued:  {issue.issue_date.strftime('%d %b %Y %H:%M')}  "
            f"by {issue.issued_by.username if issue.issued_by else 'system'}"
        )
        self._issue_summary.setText(summary)
        self._detail_card.setVisible(True)
        self._return_btn.setEnabled(True)
        self._footer_lbl.setText(
            f"Returning '{asset.name if asset else '—'}' from '{person.full_name if person else '—'}'"
        )
        self._footer_lbl.setStyleSheet("color:#B45309; font-size:12px; font-weight:600;")

    def _on_return(self) -> None:
        if not self._selected_issue:
            return

        issue = self._selected_issue
        self._return_btn.setEnabled(False)
        self._return_btn.setText("Recording…")

        try:
            asset_return = self._txn_svc.return_asset(
                issue_id=issue.id,
                condition_on_return=self._condition.currentData(),
                remarks=self._remarks.toPlainText().strip() or None,
            )
            asset_name = issue.asset.name if issue.asset else "Asset"
            person_name = issue.person.full_name if issue.person else "Person"

            app_signals.asset_returned.emit(asset_return.id, issue.id)
            app_signals.show_notification.emit(
                "Return Recorded",
                f"'{asset_name}' returned by '{person_name}'.",
                "success",
            )
            app_signals.refresh_dashboard.emit()
            self._reset()
        except Exception as e:
            app_signals.show_notification.emit("Return Failed", str(e), "error")
        finally:
            self._return_btn.setEnabled(True)
            self._return_btn.setText("📥  Record Return")

    def _reset(self) -> None:
        self._selected_issue = None
        self._detail_card.setVisible(False)
        self._return_btn.setEnabled(False)
        self._footer_lbl.setText("Select an active issue from the table above.")
        self._footer_lbl.setStyleSheet("color:#64748B; font-size:12px;")
        self._remarks.clear()
        self._load_issues()
