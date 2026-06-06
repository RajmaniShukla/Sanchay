"""
Sanchay — Reusable Data Table Widget
=======================================
A professional table widget with sorting, column configuration,
and action button support built on top of QTableWidget.
"""

from typing import Callable, Optional
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QWidget, QHBoxLayout, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont


class DataTable(QTableWidget):
    """
    Styled data table widget.
    
    Features:
        - Alternating row colors
        - Fixed headers with sorting
        - Row selection
        - Built-in empty state message
    """

    row_selected = Signal(int)   # Emits row index on selection
    row_double_clicked = Signal(int)

    def __init__(self, columns: list[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._columns = columns
        self._setup_table()

    def _setup_table(self) -> None:
        self.setColumnCount(len(self._columns))
        self.setHorizontalHeaderLabels(self._columns)

        # Appearance
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.StrongFocus)

        # Header
        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSortIndicatorShown(True)
        header.setSectionResizeMode(QHeaderView.Interactive)
        if self._columns:
            header.setStretchLastSection(True)

        # Row height
        self.verticalHeader().setDefaultSectionSize(44)

        # Signals
        self.itemSelectionChanged.connect(self._on_selection_changed)
        self.cellDoubleClicked.connect(lambda r, c: self.row_double_clicked.emit(r))

    def set_data(self, rows: list[list]) -> None:
        """
        Populate the table with data rows.
        
        Args:
            rows: List of lists, each inner list is one row's cell values.
        """
        self.setRowCount(0)  # Clear
        for row_idx, row_data in enumerate(rows):
            self.insertRow(row_idx)
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "—")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.setItem(row_idx, col_idx, item)

    def set_row_data(self, row_idx: int, col_idx: int, value: str, color: Optional[str] = None) -> None:
        """Set a specific cell value and optionally style it."""
        item = QTableWidgetItem(value)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if color:
            item.setForeground(QColor(color))
        self.setItem(row_idx, col_idx, item)

    def add_badge_cell(self, row_idx: int, col_idx: int, text: str, bg_color: str, fg_color: str) -> None:
        """Insert a colored badge label into a cell."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        badge = QLabel(text)
        badge.setStyleSheet(
            f"background-color: {bg_color}; color: {fg_color}; "
            f"border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 600;"
        )
        badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(badge)
        layout.addStretch()
        self.setCellWidget(row_idx, col_idx, container)

    def add_action_cell(
        self, row_idx: int, col_idx: int,
        actions: list[tuple[str, str, Callable]]  # (label, icon, callback)
    ) -> None:
        """Insert action buttons into a cell."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        for label, icon_text, callback in actions:
            btn = QPushButton(f"{icon_text} {label}" if icon_text else label)
            btn.setObjectName("iconButton")
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 4px; "
                "padding: 2px 8px; font-size: 11px; }"
                "QPushButton:hover { background-color: #EFF6FF; border-color: #93C5FD; }"
            )
            btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()
        self.setCellWidget(row_idx, col_idx, container)

    def get_selected_row(self) -> Optional[int]:
        rows = self.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def set_column_widths(self, widths: dict[int, int]) -> None:
        """Set specific column widths. {col_index: width_px}"""
        for col, width in widths.items():
            self.setColumnWidth(col, width)

    def _on_selection_changed(self) -> None:
        row = self.get_selected_row()
        if row is not None:
            self.row_selected.emit(row)

    def clear_data(self) -> None:
        self.setRowCount(0)

    def row_count(self) -> int:
        return self.rowCount()
