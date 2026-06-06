"""
Sanchay — Asset Detail Dialog
================================
Read-only view of a single asset with full metadata + issue history.
Quick action buttons: Issue / Return / Maintenance / Dispose.
"""

from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QTableWidgetItem,
)
from PySide6.QtCore import Qt

from app.models.asset import Asset
from app.services.transaction_service import TransactionService
from app.views.widgets.data_table import DataTable
from app.constants import AssetStatus
from loguru import logger


class AssetDetailDialog(QDialog):
    """
    Full-detail view for a single asset.
    Shows metadata, financial info, and complete issue/return history.
    """

    def __init__(self, asset: Asset, parent=None):
        super().__init__(parent)
        self._asset   = asset
        self._txn_svc = TransactionService()
        self.setWindowTitle(f"Asset — {asset.name}")
        self.setMinimumSize(720, 580)
        self.setModal(True)
        self.setStyleSheet("QDialog { background:white; }")
        self._build_ui()
        self._load_history()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header banner ──────────────────────────────────────────────────────
        a = self._asset
        status_colors = {
            "available":   ("#DCFCE7", "#15803D"),
            "issued":      ("#DBEAFE", "#1D4ED8"),
            "maintenance": ("#FEF3C7", "#B45309"),
            "disposed":    ("#F1F5F9", "#475569"),
            "lost":        ("#FEE2E2", "#B91C1C"),
        }
        s_bg, s_fg = status_colors.get(a.status, ("#F1F5F9", "#374151"))

        header = QFrame()
        header.setStyleSheet("background:#1E293B;")
        header.setFixedHeight(100)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(28, 16, 28, 16)
        h_lay.setSpacing(20)

        icon_lbl = QLabel("📦")
        icon_lbl.setStyleSheet("font-size:40px; color:white;")
        icon_lbl.setFixedWidth(52)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        name_lbl = QLabel(a.name)
        name_lbl.setStyleSheet("color:white; font-size:19px; font-weight:700;")

        code_lbl = QLabel(f"Code: {a.asset_code}  •  S/N: {a.serial_number or '—'}")
        code_lbl.setStyleSheet("color:#94A3B8; font-size:12px;")

        title_col.addWidget(name_lbl)
        title_col.addWidget(code_lbl)

        status_badge = QLabel(a.status.upper())
        status_badge.setStyleSheet(
            f"background:{s_bg}; color:{s_fg}; border-radius:10px; "
            f"padding:4px 14px; font-size:11px; font-weight:700;"
        )

        h_lay.addWidget(icon_lbl)
        h_lay.addLayout(title_col, 1)
        h_lay.addWidget(status_badge)
        root.addWidget(header)

        # ── Scrollable body ────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:white;")
        body = QWidget()
        body.setStyleSheet("background:white;")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(28, 20, 28, 20)
        b_lay.setSpacing(20)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # ── Two-column details ────────────────────────────────────────────────
        details_row = QHBoxLayout()
        details_row.setSpacing(24)

        # Left: Asset Info
        left = QFrame()
        left.setStyleSheet("background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0;")
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(16, 14, 16, 14)
        l_lay.setSpacing(10)
        l_lay.addWidget(self._section("📦 Asset Information"))
        l_lay.addWidget(self._row("Category",    a.category_name))
        l_lay.addWidget(self._row("Department",  a.dept_name))
        l_lay.addWidget(self._row("Location",    a.location or "—"))
        l_lay.addWidget(self._row("Manufacturer",a.manufacturer or "—"))
        l_lay.addWidget(self._row("Model",       a.model_number or "—"))
        l_lay.addWidget(self._row("Supplier",    a.supplier or "—"))
        l_lay.addWidget(self._row("Condition",   (a.condition or "—").capitalize()))
        if a.description:
            l_lay.addWidget(self._row("Notes",   a.description))

        # Right: Financial Info
        right = QFrame()
        right.setStyleSheet("background:#F8FAFC; border-radius:8px; border:1px solid #E2E8F0;")
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(16, 14, 16, 14)
        r_lay.setSpacing(10)
        r_lay.addWidget(self._section("💰 Financial Details"))
        r_lay.addWidget(self._row(
            "Purchase Date",
            a.purchase_date.strftime("%d %b %Y") if a.purchase_date else "—"
        ))
        r_lay.addWidget(self._row(
            "Purchase Price",
            f"₹ {float(a.purchase_price):,.2f}" if a.purchase_price else "—"
        ))
        r_lay.addWidget(self._row(
            "Current Value",
            f"₹ {float(a.current_value):,.2f}" if a.current_value else "—"
        ))

        # Warranty with color coding
        if a.warranty_expiry_date:
            today = date.today()
            diff  = (a.warranty_expiry_date - today).days
            color = "#15803D" if diff > 0 else "#DC2626"
            suffix = f"  ({diff}d left)" if diff > 0 else f"  (expired {abs(diff)}d ago)"
            r_lay.addWidget(self._row(
                "Warranty Expiry",
                a.warranty_expiry_date.strftime("%d %b %Y") + suffix,
                value_color=color,
            ))
        else:
            r_lay.addWidget(self._row("Warranty Expiry", "—"))

        r_lay.addWidget(self._row(
            "Warranty Status",
            {"valid": "✅  Valid", "expired": "❌  Expired", "none": "—"}.get(
                a.warranty_status, "—"
            )
        ))
        r_lay.addStretch()

        details_row.addWidget(left, 1)
        details_row.addWidget(right, 1)
        b_lay.addLayout(details_row)

        # ── Issue History ──────────────────────────────────────────────────────
        b_lay.addWidget(self._section("📋 Issue / Return History"))

        cols = ["#", "Issued To", "Issued By", "Issue Date", "Expected Return", "Return Date", "Status"]
        self._hist_table = DataTable(cols)
        self._hist_table.setFixedHeight(200)
        self._hist_table.set_column_widths({0: 40, 3: 140, 4: 130, 5: 140, 6: 90})
        b_lay.addWidget(self._hist_table)

        # ── Footer ─────────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet("border-top:1px solid #E2E8F0; background:#F8FAFC;")
        footer.setFixedHeight(56)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 10, 24, 10)
        f_lay.setSpacing(10)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton {
                background:white; border:1px solid #D1D5DB;
                border-radius:6px; color:#374151; font-weight:500; padding:0 20px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        close_btn.clicked.connect(self.accept)

        f_lay.addStretch()
        f_lay.addWidget(close_btn)
        root.addWidget(footer)

    def _load_history(self) -> None:
        try:
            issues = self._txn_svc.get_issue_history_for_asset(self._asset.id)
            self._hist_table.setRowCount(0)

            if not issues:
                self._hist_table.setRowCount(1)
                empty = QTableWidgetItem("No issue history found for this asset.")
                empty.setTextAlignment(Qt.AlignCenter)
                self._hist_table.setItem(0, 0, empty)
                self._hist_table.setSpan(0, 0, 1, 7)
                return

            status_colors = {
                "active":   ("#DBEAFE", "#1D4ED8"),
                "returned": ("#DCFCE7", "#15803D"),
                "overdue":  ("#FEE2E2", "#B91C1C"),
            }

            for i, issue in enumerate(issues):
                self._hist_table.insertRow(i)

                def _item(val):
                    it = QTableWidgetItem(str(val) if val else "—")
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    return it

                ret = issue.returns[0] if issue.returns else None
                ret_date_str = ret.return_date.strftime("%d %b %Y %H:%M") if ret else "—"
                bg, fg = status_colors.get(issue.status, ("#F1F5F9", "#374151"))

                self._hist_table.setItem(i, 0, _item(i + 1))
                self._hist_table.setItem(i, 1, _item(issue.person_name))
                self._hist_table.setItem(i, 2, _item(
                    issue.issued_by.username if issue.issued_by else "—"))
                self._hist_table.setItem(i, 3, _item(
                    issue.issue_date.strftime("%d %b %Y %H:%M")))
                self._hist_table.setItem(i, 4, _item(
                    issue.expected_return_date.strftime("%d %b %Y")
                    if issue.expected_return_date else "—"))
                self._hist_table.setItem(i, 5, _item(ret_date_str))
                self._hist_table.add_badge_cell(i, 6, issue.status.capitalize(), bg, fg)

        except Exception as e:
            logger.error(f"Asset history load error: {e}")

    # ── Small helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _section(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-size:13px; font-weight:700; color:#0F172A; "
            "padding-bottom:4px; border-bottom:2px solid #E2E8F0;"
        )
        return lbl

    @staticmethod
    def _row(label: str, value: str, value_color: str = "#374151") -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background:transparent; border:none;")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet("color:#64748B; font-size:12px; font-weight:600;")
        lbl.setFixedWidth(120)

        val = QLabel(value)
        val.setStyleSheet(f"color:{value_color}; font-size:12px;")
        val.setWordWrap(True)

        lay.addWidget(lbl)
        lay.addWidget(val, 1)
        return frame
