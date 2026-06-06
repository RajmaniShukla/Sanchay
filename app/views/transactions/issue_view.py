"""
Sanchay — Issue Asset View
============================
Full-page two-panel workflow for issuing an asset to a person.

Left  panel : search + select from available assets
Right panel : search + select from active persons
Bottom strip: expected-return date, purpose, notes → Issue button
"""

from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QDateEdit, QTextEdit, QSplitter, QTableWidgetItem,
    QScrollArea,
)
from PySide6.QtCore import Qt, QDate, QTimer

from app.services.asset_service import AssetService
from app.services.person_service import PersonService
from app.services.transaction_service import TransactionService
from app.core.security import current_session
from app.core.signals import app_signals
from app.models.asset import Asset
from app.models.person import Person
from app.views.widgets.data_table import DataTable
from loguru import logger


# ── Reusable picker panel ─────────────────────────────────────────────────────

class _PickerPanel(QFrame):
    """
    Generic search-and-select panel.
    Caller sets up the table columns, then calls load_data() with rows.
    """

    def __init__(self, title: str, placeholder: str, columns: list[str], parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        self._selected_id: int | None = None
        self._selected_label: str = ""
        self._items: list = []          # raw model objects
        self._build(title, placeholder, columns)

    def _build(self, title: str, placeholder: str, columns: list[str]) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # Header
        hdr = QLabel(title)
        hdr.setStyleSheet("font-size:13px; font-weight:700; color:#0F172A;")
        lay.addWidget(hdr)

        # Search box
        self._search = QLineEdit()
        self._search.setPlaceholderText(placeholder)
        self._search.setFixedHeight(36)
        self._search.setStyleSheet("""
            QLineEdit {
                background:#F1F5F9; border:1px solid #E2E8F0; border-radius:20px;
                padding:0 14px; font-size:13px;
            }
            QLineEdit:focus { background:white; border:2px solid #2563EB; }
        """)
        self._timer = QTimer(); self._timer.setSingleShot(True); self._timer.setInterval(300)
        self._timer.timeout.connect(self._on_debounced)
        self._search.textChanged.connect(lambda _: self._timer.start())
        lay.addWidget(self._search)

        # Table
        self._table = DataTable(columns)
        self._table.setMinimumHeight(180)
        self._table.row_selected.connect(self._on_select)
        lay.addWidget(self._table, 1)

        # Selection indicator
        self._sel_lbl = QLabel("Nothing selected")
        self._sel_lbl.setStyleSheet(
            "color:#64748B; font-size:12px; padding:6px 10px; "
            "background:#F8FAFC; border-radius:6px;"
        )
        self._sel_lbl.setWordWrap(True)
        lay.addWidget(self._sel_lbl)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_items(self, items: list, row_builder) -> None:
        """Populate table. row_builder(item) -> list of cell strings."""
        self._items = items
        self._table.set_data([row_builder(it) for it in items])
        # Restore selection highlight if previously selected
        for i, it in enumerate(items):
            if hasattr(it, "id") and it.id == self._selected_id:
                self._table.selectRow(i)
                break
        else:
            if self._selected_id not in [getattr(i, "id", None) for i in items]:
                self._clear_selection()

    def selected_id(self) -> int | None:
        return self._selected_id

    def selected_label(self) -> str:
        return self._selected_label

    def set_on_search(self, fn) -> None:
        self._on_search_fn = fn

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_debounced(self) -> None:
        if hasattr(self, "_on_search_fn"):
            self._on_search_fn(self._search.text().strip())

    def _on_select(self, row: int) -> None:
        if row < len(self._items):
            it = self._items[row]
            self._selected_id = it.id
            self._selected_label = self._item_label(it)
            self._sel_lbl.setText(f"✅  Selected: {self._selected_label}")
            self._sel_lbl.setStyleSheet(
                "color:#15803D; font-size:12px; font-weight:600; padding:6px 10px; "
                "background:#DCFCE7; border-radius:6px;"
            )
            if hasattr(self, "_on_selected_fn"):
                self._on_selected_fn()

    def _clear_selection(self) -> None:
        self._selected_id = None
        self._selected_label = ""
        self._sel_lbl.setText("Nothing selected")
        self._sel_lbl.setStyleSheet(
            "color:#64748B; font-size:12px; padding:6px 10px; "
            "background:#F8FAFC; border-radius:6px;"
        )

    def _item_label(self, it) -> str:
        if isinstance(it, Asset):
            return f"{it.name} ({it.asset_code})"
        if isinstance(it, Person):
            return f"{it.full_name} ({it.display_code})"
        return str(it)

    def set_on_selected(self, fn) -> None:
        self._on_selected_fn = fn

    def get_query(self) -> str:
        return self._search.text().strip()


# ── Main Issue View ───────────────────────────────────────────────────────────

class IssueView(QWidget):
    """
    Full-page workflow for issuing an available asset to an active person.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._asset_svc  = AssetService()
        self._person_svc = PersonService()
        self._txn_svc    = TransactionService()
        self._build_ui()
        self._load_assets()
        self._load_persons()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top info bar ───────────────────────────────────────────────────────
        info = QFrame()
        info.setStyleSheet("background:#EFF6FF; border-bottom:1px solid #BFDBFE;")
        info.setFixedHeight(40)
        i_lay = QHBoxLayout(info)
        i_lay.setContentsMargins(24, 0, 24, 0)
        tip = QLabel("ℹ️  Select an available asset (left) and an active person (right), "
                     "then fill in the details below and click Issue.")
        tip.setStyleSheet("color:#1D4ED8; font-size:12px;")
        i_lay.addWidget(tip)
        root.addWidget(info)

        # ── Main content area ──────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background:#F8FAFC;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(24, 20, 24, 0)
        c_lay.setSpacing(16)

        # ── Two-panel picker (splitter) ────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background:#E2E8F0; width:2px; }")

        # Asset picker
        self._asset_panel = _PickerPanel(
            "📦  Available Assets",
            "Search by name, code, serial, manufacturer…",
            ["Code", "Asset Name", "Category", "Location", "Condition"],
        )
        self._asset_panel.set_on_search(self._on_asset_search)
        self._asset_panel.set_on_selected(self._refresh_issue_btn)
        self._asset_panel.setMinimumWidth(400)

        # Person picker
        self._person_panel = _PickerPanel(
            "👤  Active Persons",
            "Search by name, ID, email, phone…",
            ["ID Code", "Name", "Type", "Department", "Designation"],
        )
        self._person_panel.set_on_search(self._on_person_search)
        self._person_panel.set_on_selected(self._refresh_issue_btn)
        self._person_panel.setMinimumWidth(380)

        splitter.addWidget(self._asset_panel)
        splitter.addWidget(self._person_panel)
        splitter.setSizes([500, 440])
        c_lay.addWidget(splitter, 1)

        # ── Issue details form ────────────────────────────────────────────────
        details = QFrame()
        details.setStyleSheet(
            "QFrame { background:white; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        d_lay = QHBoxLayout(details)
        d_lay.setContentsMargins(20, 14, 20, 14)
        d_lay.setSpacing(20)

        # Expected return date
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        dt_lbl = QLabel("Expected Return Date")
        dt_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        self._return_date = QDateEdit()
        self._return_date.setCalendarPopup(True)
        self._return_date.setDisplayFormat("dd/MM/yyyy")
        self._return_date.setDate(QDate.currentDate().addDays(7))
        self._return_date.setFixedHeight(36)
        self._return_date.setStyleSheet("""
            QDateEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white; min-width:150px;
            }
            QDateEdit:focus { border:2px solid #2563EB; }
        """)
        date_col.addWidget(dt_lbl)
        date_col.addWidget(self._return_date)
        d_lay.addLayout(date_col)

        # Purpose
        pur_col = QVBoxLayout()
        pur_col.setSpacing(4)
        pur_lbl = QLabel("Purpose")
        pur_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        self._purpose = QLineEdit()
        self._purpose.setPlaceholderText("e.g. Project work, Training, Field visit…")
        self._purpose.setFixedHeight(36)
        self._purpose.setStyleSheet("""
            QLineEdit {
                border:1px solid #D1D5DB; border-radius:6px;
                padding:0 10px; font-size:13px; background:white;
            }
            QLineEdit:focus { border:2px solid #2563EB; }
        """)
        pur_col.addWidget(pur_lbl)
        pur_col.addWidget(self._purpose)
        d_lay.addLayout(pur_col, 2)

        # Notes
        notes_col = QVBoxLayout()
        notes_col.setSpacing(4)
        n_lbl = QLabel("Notes")
        n_lbl.setStyleSheet("font-size:12px; font-weight:600; color:#374151;")
        self._notes = QLineEdit()
        self._notes.setPlaceholderText("Optional remarks…")
        self._notes.setFixedHeight(36)
        self._notes.setStyleSheet(self._purpose.styleSheet())
        notes_col.addWidget(n_lbl)
        notes_col.addWidget(self._notes)
        d_lay.addLayout(notes_col, 1)

        c_lay.addWidget(details)
        root.addWidget(content, 1)

        # ── Footer with action button ──────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet(
            "background:white; border-top:1px solid #E2E8F0;"
        )
        footer.setFixedHeight(60)
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 10, 24, 10)
        f_lay.setSpacing(12)

        self._status_lbl = QLabel("Select an asset and a person to continue.")
        self._status_lbl.setStyleSheet("color:#64748B; font-size:12px;")

        self._issue_btn = QPushButton("📤  Issue Asset")
        self._issue_btn.setFixedHeight(40)
        self._issue_btn.setMinimumWidth(160)
        self._issue_btn.setEnabled(False)
        self._issue_btn.setStyleSheet("""
            QPushButton {
                background:#16A34A; color:white; border-radius:8px;
                font-weight:700; font-size:14px; padding:0 24px;
            }
            QPushButton:hover  { background:#15803D; }
            QPushButton:disabled { background:#D1D5DB; color:#9CA3AF; }
        """)
        self._issue_btn.clicked.connect(self._on_issue)

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedHeight(40)
        reset_btn.setStyleSheet("""
            QPushButton {
                background:white; border:1px solid #D1D5DB;
                border-radius:8px; color:#374151; font-weight:500; padding:0 18px;
            }
            QPushButton:hover { background:#F1F5F9; }
        """)
        reset_btn.clicked.connect(self._reset)

        f_lay.addWidget(self._status_lbl, 1)
        f_lay.addWidget(reset_btn)
        f_lay.addWidget(self._issue_btn)
        root.addWidget(footer)

    # ── Data loaders ──────────────────────────────────────────────────────────

    def _load_assets(self, query: str = "") -> None:
        try:
            org_id = current_session.org_id
            assets, _ = self._asset_svc.search(
                query=query, org_id=org_id, status="available", limit=100
            )

            def row(a: Asset):
                return [
                    a.asset_code,
                    a.name,
                    a.category_name,
                    a.location or "—",
                    (a.condition or "—").capitalize(),
                ]

            self._asset_panel.set_items(assets, row)

            # Show empty-state hint if no assets are available
            if not assets:
                self._asset_panel._sel_lbl.setText(
                    "✅  All assets are currently issued or no assets registered yet."
                )
                self._asset_panel._sel_lbl.setStyleSheet(
                    "color:#B45309; font-size:12px; padding:6px 10px; "
                    "background:#FEF3C7; border-radius:6px;"
                )
        except Exception as e:
            logger.error(f"Asset load error: {e}")

    def _load_persons(self, query: str = "") -> None:
        try:
            org_id = current_session.org_id
            persons, _ = self._person_svc.search(
                query=query, org_id=org_id, status="active", limit=100
            )

            def row(p: Person):
                return [
                    p.display_code,
                    p.full_name,
                    p.person_type.capitalize(),
                    p.department.name if p.department else "—",
                    p.designation or "—",
                ]

            self._person_panel.set_items(persons, row)
        except Exception as e:
            logger.error(f"Person load error: {e}")

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_asset_search(self, q: str) -> None:
        self._load_assets(q)

    def _on_person_search(self, q: str) -> None:
        self._load_persons(q)

    def _refresh_issue_btn(self) -> None:
        a_id = self._asset_panel.selected_id()
        p_id = self._person_panel.selected_id()
        ready = bool(a_id and p_id)
        self._issue_btn.setEnabled(ready)
        if ready:
            self._status_lbl.setText(
                f"Ready to issue  '{self._asset_panel.selected_label()}'  →  "
                f"'{self._person_panel.selected_label()}'"
            )
            self._status_lbl.setStyleSheet("color:#15803D; font-size:12px; font-weight:600;")
        else:
            self._status_lbl.setText("Select an asset and a person to continue.")
            self._status_lbl.setStyleSheet("color:#64748B; font-size:12px;")

    def _on_issue(self) -> None:
        asset_id  = self._asset_panel.selected_id()
        person_id = self._person_panel.selected_id()
        if not asset_id or not person_id:
            return

        qd = self._return_date.date()
        from datetime import date as dt
        expected = dt(qd.year(), qd.month(), qd.day())

        self._issue_btn.setEnabled(False)
        self._issue_btn.setText("Issuing…")

        try:
            issue = self._txn_svc.issue_asset(
                asset_id=asset_id,
                person_id=person_id,
                expected_return_date=expected,
                purpose=self._purpose.text().strip() or None,
                notes=self._notes.text().strip() or None,
                org_id=current_session.org_id,
            )
            app_signals.asset_issued.emit(issue.id, asset_id)
            app_signals.show_notification.emit(
                "Asset Issued",
                f"'{self._asset_panel.selected_label()}' issued to "
                f"'{self._person_panel.selected_label()}'.",
                "success",
            )
            app_signals.refresh_dashboard.emit()
            self._reset()
            self._load_assets()   # Refresh — issued asset disappears from list
        except Exception as e:
            app_signals.show_notification.emit("Issue Failed", str(e), "error")
        finally:
            self._issue_btn.setEnabled(True)
            self._issue_btn.setText("📤  Issue Asset")

    def _reset(self) -> None:
        self._load_assets()
        self._load_persons()
        self._purpose.clear()
        self._notes.clear()
        self._return_date.setDate(QDate.currentDate().addDays(7))
        self._refresh_issue_btn()
