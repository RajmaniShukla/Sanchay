"""
Sanchay — Transaction History View
=====================================
Full transaction audit: 4 tabs — Active Issues | Overdue | All Issues | Returns
Includes date-range filter, search, and inline "Return" quick-action.
"""

from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QTableWidgetItem, QDialog, QDateEdit,
    QComboBox, QStackedWidget,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

from app.services.transaction_service import TransactionService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.transaction import AssetIssue, AssetReturn
from app.constants import IssueStatus
from app.views.widgets.data_table import DataTable
from app.views.widgets.search_bar import SearchBar
from loguru import logger


class TransactionListView(QWidget):
    """
    Transaction history page with 4 tabs:
      - Active Issues
      - Overdue Issues
      - All Issues
      - Returns
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._txn_svc = TransactionService()
        self._build_ui()
        self._load()

        app_signals.asset_issued.connect(lambda *_: self._load())
        app_signals.asset_returned.connect(lambda *_: self._load())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Filter toolbar ─────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setStyleSheet("background:white; border-bottom:1px solid #E2E8F0;")
        toolbar.setFixedHeight(58)
        t_lay = QHBoxLayout(toolbar)
        t_lay.setContentsMargins(24, 10, 24, 10)
        t_lay.setSpacing(12)

        self._search = SearchBar("Search asset, person, code…")
        self._search.set_min_width(280)
        self._search.search_changed.connect(lambda _: self._load())

        date_style = """
            QDateEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 8px; font-size:12px; background:white;
            }
            QDateEdit:focus { border-color:#2563EB; }
        """
        from_lbl = QLabel("From:")
        from_lbl.setStyleSheet("color:#374151; font-size:12px; font-weight:600;")
        self._from_date = QDateEdit()
        self._from_date.setCalendarPopup(True)
        self._from_date.setDisplayFormat("dd/MM/yyyy")
        self._from_date.setDate(QDate.currentDate().addDays(-30))
        self._from_date.setFixedHeight(34)
        self._from_date.setStyleSheet(date_style)
        self._from_date.dateChanged.connect(lambda _: self._load())

        to_lbl = QLabel("To:")
        to_lbl.setStyleSheet("color:#374151; font-size:12px; font-weight:600;")
        self._to_date = QDateEdit()
        self._to_date.setCalendarPopup(True)
        self._to_date.setDisplayFormat("dd/MM/yyyy")
        self._to_date.setDate(QDate.currentDate())
        self._to_date.setFixedHeight(34)
        self._to_date.setStyleSheet(date_style)
        self._to_date.dateChanged.connect(lambda _: self._load())

        reset_btn = QPushButton("✕ Reset")
        reset_btn.setFixedHeight(34)
        reset_btn.setStyleSheet("""
            QPushButton {
                background:transparent; border:1px solid #D1D5DB;
                border-radius:6px; color:#64748B; font-size:12px; padding:0 10px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        reset_btn.clicked.connect(self._reset_filters)

        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        t_lay.addWidget(self._search)
        t_lay.addWidget(from_lbl)
        t_lay.addWidget(self._from_date)
        t_lay.addWidget(to_lbl)
        t_lay.addWidget(self._to_date)
        t_lay.addWidget(reset_btn)
        t_lay.addWidget(self._count_lbl)
        t_lay.addStretch()
        root.addWidget(toolbar)

        # ── Stats strip ────────────────────────────────────────────────────────
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background:#F8FAFC; border-bottom:1px solid #E2E8F0;")
        stats_bar.setFixedHeight(42)
        sb_lay = QHBoxLayout(stats_bar)
        sb_lay.setContentsMargins(24, 6, 24, 6)
        sb_lay.setSpacing(16)

        self._stat_active  = self._make_pill("Active Issues: —",  "#DBEAFE", "#1D4ED8")
        self._stat_overdue = self._make_pill("Overdue: —",        "#FEE2E2", "#B91C1C")
        self._stat_returns = self._make_pill("Total Returns: —",  "#DCFCE7", "#15803D")

        sb_lay.addWidget(self._stat_active)
        sb_lay.addWidget(self._stat_overdue)
        sb_lay.addWidget(self._stat_returns)
        sb_lay.addStretch()
        root.addWidget(stats_bar)

        # ── Tab widget ─────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border:none; background:#F8FAFC; }
            QTabBar { background:white; border-bottom:2px solid #E2E8F0; }
            QTabBar::tab {
                padding:10px 22px; border:none;
                border-bottom:3px solid transparent;
                color:#64748B; font-weight:500; background:white;
            }
            QTabBar::tab:selected {
                color:#2563EB; border-bottom:3px solid #2563EB;
                font-weight:700; background:white;
            }
            QTabBar::tab:hover:!selected { color:#374151; }
        """)
        self._tabs.currentChanged.connect(self._load)

        # Tab 0: Active Issues
        self._active_tbl = self._make_issue_table(with_return_btn=True)
        # Tab 1: Overdue
        self._overdue_tbl = self._make_issue_table(with_return_btn=True, overdue=True)
        # Tab 2: All Issues
        self._all_tbl = self._make_issue_table(with_return_btn=False)
        # Tab 3: Returns
        self._returns_tbl = self._make_return_table()

        self._tabs.addTab(self._wrap(self._active_tbl),  "📤  Active Issues")
        self._tabs.addTab(self._wrap(self._overdue_tbl), "⚠️  Overdue")
        self._tabs.addTab(self._wrap(self._all_tbl),     "📋  All Issues")
        self._tabs.addTab(self._wrap(self._returns_tbl), "📥  Returns")
        root.addWidget(self._tabs, 1)

    # ── Table factory helpers ─────────────────────────────────────────────────

    def _make_issue_table(self, with_return_btn: bool, overdue: bool = False) -> DataTable:
        extra = ["Action"] if with_return_btn else []
        cols = ["#", "Issue #", "Asset Code", "Asset Name", "Issued To",
                "Type", "Issued Date", "Expected Return", "Status"] + extra
        tbl = DataTable(cols)
        tbl.set_column_widths({0: 44, 1: 70, 2: 100, 4: 150, 5: 90,
                               6: 140, 7: 130, 8: 90})
        return tbl

    def _make_return_table(self) -> DataTable:
        cols = ["#", "Return #", "Asset Code", "Asset Name",
                "Returned By", "Received By", "Return Date",
                "Condition", "Remarks"]
        tbl = DataTable(cols)
        tbl.set_column_widths({0: 44, 1: 72, 2: 100, 4: 150, 5: 120, 6: 140, 7: 90})
        return tbl

    @staticmethod
    def _wrap(table: DataTable) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:#F8FAFC;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(table)
        return w

    # ── Data ──────────────────────────────────────────────────────────────────

    def _get_dates(self):
        fd = self._from_date.date()
        td = self._to_date.date()
        from datetime import date as dt
        return (
            dt(fd.year(), fd.month(), fd.day()),
            dt(td.year(), td.month(), td.day()),
        )

    def _load(self, *_) -> None:
        tab = self._tabs.currentIndex()
        try:
            from_dt, to_dt = self._get_dates()
            org_id = current_session.org_id
            query  = self._search.text()

            if tab == 0:     # Active
                self._populate_issues(
                    self._active_tbl, org_id, "active",
                    from_dt, to_dt, query, with_return_btn=True
                )
            elif tab == 1:   # Overdue
                self._populate_overdue(self._overdue_tbl, org_id, query)
            elif tab == 2:   # All issues
                self._populate_issues(
                    self._all_tbl, org_id, None,
                    from_dt, to_dt, query, with_return_btn=False
                )
            elif tab == 3:   # Returns
                self._populate_returns(self._returns_tbl, org_id, from_dt, to_dt, query)

            self._update_stats(org_id)
        except Exception as e:
            logger.error(f"Transaction list load error: {e}")

    def _populate_issues(
        self, tbl: DataTable, org_id, status, from_dt, to_dt, query, with_return_btn
    ) -> None:
        issues, total = self._txn_svc.get_all_issues(
            org_id=org_id, status=status,
            from_date=from_dt, to_date=to_dt, limit=300,
        )
        if query:
            q = query.lower()
            issues = [i for i in issues
                      if q in (i.asset.name  if i.asset  else "").lower()
                      or q in (i.person.full_name if i.person else "").lower()
                      or q in (i.asset.asset_code if i.asset  else "").lower()]

        status_styles = {
            "active":   ("#DBEAFE", "#1D4ED8"),
            "returned": ("#DCFCE7", "#15803D"),
            "overdue":  ("#FEE2E2", "#B91C1C"),
        }
        tbl.setRowCount(0)

        for i, issue in enumerate(issues):
            tbl.insertRow(i)
            asset  = issue.asset
            person = issue.person
            s_bg, s_fg = status_styles.get(issue.status, ("#F1F5F9", "#374151"))

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            tbl.setItem(i, 0, _item(i + 1))
            tbl.setItem(i, 1, _item(f"#{issue.id}"))
            tbl.setItem(i, 2, _item(asset.asset_code if asset else "—"))
            tbl.setItem(i, 3, _item(asset.name if asset else "—"))
            tbl.setItem(i, 4, _item(person.full_name if person else "—"))
            tbl.setItem(i, 5, _item(
                person.person_type.capitalize() if person else "—"))
            tbl.setItem(i, 6, _item(issue.issue_date.strftime("%d %b %Y  %H:%M")))
            tbl.setItem(i, 7, _item(
                issue.expected_return_date.strftime("%d %b %Y")
                if issue.expected_return_date else "—"))
            tbl.add_badge_cell(i, 8, issue.status.capitalize(), s_bg, s_fg)

            if with_return_btn and issue.status == "active":
                issue_id = issue.id
                tbl.add_action_cell(i, 9, [
                    ("Return", "📥", lambda _, iid=issue_id: self._quick_return(iid)),
                ])
            elif with_return_btn:
                tbl.setItem(i, 9, _item("—"))

        self._count_lbl.setText(f"{len(issues)} record{'s' if len(issues) != 1 else ''}")

    def _populate_overdue(self, tbl: DataTable, org_id, query: str) -> None:
        issues = self._txn_svc.get_overdue_issues(org_id)
        if query:
            q = query.lower()
            issues = [i for i in issues
                      if q in (i.asset.name if i.asset else "").lower()
                      or q in (i.person.full_name if i.person else "").lower()]

        tbl.setRowCount(0)
        today = date.today()
        for i, issue in enumerate(issues):
            tbl.insertRow(i)
            asset  = issue.asset
            person = issue.person
            exp    = issue.expected_return_date
            days_late = (today - exp).days if exp else 0

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            tbl.setItem(i, 0, _item(i + 1))
            tbl.setItem(i, 1, _item(f"#{issue.id}"))
            tbl.setItem(i, 2, _item(asset.asset_code if asset else "—"))
            tbl.setItem(i, 3, _item(asset.name if asset else "—"))
            tbl.setItem(i, 4, _item(person.full_name if person else "—"))
            tbl.setItem(i, 5, _item(
                person.person_type.capitalize() if person else "—"))
            tbl.setItem(i, 6, _item(issue.issue_date.strftime("%d %b %Y  %H:%M")))
            tbl.setItem(i, 7, _item(
                exp.strftime("%d %b %Y") if exp else "—"))

            late_item = QTableWidgetItem(f"⚠  {days_late} day(s) late")
            late_item.setFlags(late_item.flags() & ~Qt.ItemIsEditable)
            late_item.setForeground(QColor("#B91C1C"))
            f = late_item.font(); f.setBold(True); late_item.setFont(f)
            tbl.setItem(i, 7, late_item)      # overwrite expected return col

            tbl.add_badge_cell(i, 8, "Overdue", "#FEE2E2", "#B91C1C")
            iid = issue.id
            tbl.add_action_cell(i, 9, [
                ("Return", "📥", lambda _, x=iid: self._quick_return(x)),
            ])

        self._count_lbl.setText(
            f"{len(issues)} overdue issue{'s' if len(issues) != 1 else ''}"
        )

    def _populate_returns(self, tbl: DataTable, org_id, from_dt, to_dt, query) -> None:
        returns, total = self._txn_svc.get_all_returns(
            org_id=org_id, from_date=from_dt, to_date=to_dt, limit=300
        )
        if query:
            q = query.lower()
            returns = [r for r in returns
                       if (r.asset  and q in r.asset.name.lower())
                       or (r.person and q in r.person.full_name.lower())]

        cond_colors = {
            "new": "#15803D", "good": "#2563EB",
            "fair": "#B45309", "poor": "#DC2626",
        }
        tbl.setRowCount(0)

        for i, ret in enumerate(returns):
            tbl.insertRow(i)

            def _item(val):
                it = QTableWidgetItem(str(val) if val else "—")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                return it

            asset  = ret.asset
            person = ret.person
            recvd  = ret.returned_to

            tbl.setItem(i, 0, _item(i + 1))
            tbl.setItem(i, 1, _item(f"#{ret.id}"))
            tbl.setItem(i, 2, _item(asset.asset_code if asset else "—"))
            tbl.setItem(i, 3, _item(asset.name if asset else "—"))
            tbl.setItem(i, 4, _item(person.full_name if person else "—"))
            tbl.setItem(i, 5, _item(recvd.username if recvd else "—"))
            tbl.setItem(i, 6, _item(ret.return_date.strftime("%d %b %Y  %H:%M")))

            cond = ret.condition_on_return or "—"
            cond_it = QTableWidgetItem(cond.capitalize())
            cond_it.setFlags(cond_it.flags() & ~Qt.ItemIsEditable)
            cond_it.setForeground(QColor(cond_colors.get(cond, "#374151")))
            tbl.setItem(i, 7, cond_it)

            rem_it = QTableWidgetItem(ret.remarks or "—")
            rem_it.setFlags(rem_it.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(i, 8, rem_it)

        self._count_lbl.setText(
            f"{len(returns)} return{'s' if len(returns) != 1 else ''}"
        )

    # ── Quick Return ──────────────────────────────────────────────────────────

    def _quick_return(self, issue_id: int) -> None:
        """Inline return action straight from the table."""
        from app.views.widgets.confirm_dialog import ConfirmDialog
        try:
            # Look up issue to show asset name in confirm dialog
            issues, _ = self._txn_svc.get_all_issues(limit=1)  # dummy to warm cache
            # Use a simple confirm dialog
            dlg = ConfirmDialog(
                title="Record Return",
                message=f"Mark issue #{issue_id} as returned?\n\n"
                        "The asset condition will be set to 'Good'. "
                        "You can change it from the Return Asset page.",
                confirm_label="Record Return",
                danger=False,
                parent=self,
            )
            if dlg.exec() == QDialog.Accepted:
                ret = self._txn_svc.return_asset(
                    issue_id=issue_id,
                    condition_on_return="good",
                    remarks="Quick return via transaction list.",
                )
                app_signals.asset_returned.emit(ret.id, issue_id)
                app_signals.show_notification.emit(
                    "Returned", f"Issue #{issue_id} marked as returned.", "success"
                )
                app_signals.refresh_dashboard.emit()
        except Exception as e:
            app_signals.show_notification.emit("Error", str(e), "error")

    # ── Stats pills ───────────────────────────────────────────────────────────

    def _update_stats(self, org_id) -> None:
        try:
            stats = self._txn_svc.get_stats(org_id)
            returns, _ = self._txn_svc.get_all_returns(org_id=org_id, limit=1)
            all_returns, total_ret = self._txn_svc.get_all_returns(org_id=org_id, limit=9999)
            self._stat_active.setText(f"Active Issues: {stats.get('active_issues', 0)}")
            self._stat_overdue.setText(f"Overdue: {stats.get('overdue', 0)}")
            self._stat_returns.setText(f"Total Returns: {total_ret}")
        except Exception:
            pass

    def _reset_filters(self) -> None:
        self._search.clear()
        self._from_date.setDate(QDate.currentDate().addDays(-30))
        self._to_date.setDate(QDate.currentDate())

    @staticmethod
    def _make_pill(text: str, bg: str, fg: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:10px; "
            f"padding:2px 12px; font-size:11px; font-weight:600;"
        )
        return lbl
