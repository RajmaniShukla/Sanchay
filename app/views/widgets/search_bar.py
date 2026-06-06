"""
Sanchay — Search Bar Widget
==============================
Debounced search input with clear button and optional filter combos.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QComboBox,
)
from PySide6.QtCore import Qt, Signal, QTimer


class SearchBar(QWidget):
    """
    Search input with 350 ms debounce.
    Emits `search_changed(query: str)` after the user stops typing.
    """

    search_changed = Signal(str)

    def __init__(self, placeholder: str = "Search…", parent=None):
        super().__init__(parent)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._emit)
        self._build_ui(placeholder)

    def _build_ui(self, placeholder: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Search icon
        icon = QLabel("🔍")
        icon.setStyleSheet(
            "font-size: 14px; padding: 0 6px 0 12px; "
            "background: #F1F5F9; border: 1px solid #D1D5DB; "
            "border-right: none; border-radius: 20px 0 0 20px;"
        )
        icon.setFixedHeight(36)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.setFixedHeight(36)
        self._input.setStyleSheet("""
            QLineEdit {
                background: #F1F5F9; border: 1px solid #D1D5DB;
                border-left: none; border-right: none;
                font-size: 13px; color: #0F172A; padding: 0 8px;
            }
            QLineEdit:focus {
                background: white; border: 1px solid #2563EB;
                border-left: none; border-right: none;
                outline: none;
            }
        """)
        self._input.textChanged.connect(self._on_text_changed)

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(36, 36)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setVisible(False)
        self._clear_btn.setStyleSheet("""
            QPushButton {
                background: #F1F5F9; border: 1px solid #D1D5DB;
                border-left: none; border-radius: 0 20px 20px 0;
                color: #64748B; font-size: 11px;
            }
            QPushButton:hover { background: #E2E8F0; color: #DC2626; }
        """)
        self._clear_btn.clicked.connect(self.clear)

        layout.addWidget(icon)
        layout.addWidget(self._input, 1)
        layout.addWidget(self._clear_btn)

    def _on_text_changed(self, text: str) -> None:
        self._clear_btn.setVisible(bool(text))
        self._timer.start()

    def _emit(self) -> None:
        self.search_changed.emit(self._input.text().strip())

    def clear(self) -> None:
        self._input.clear()
        self._clear_btn.setVisible(False)
        self.search_changed.emit("")

    def text(self) -> str:
        return self._input.text().strip()

    def set_min_width(self, w: int) -> None:
        self._input.setMinimumWidth(w)


class FilterBar(QWidget):
    """
    Horizontal bar combining a SearchBar with optional filter ComboBoxes.
    Emits `filters_changed(query, {key: value})` when any input changes.
    """

    filters_changed = Signal(str, dict)

    def __init__(self, placeholder: str = "Search…", parent=None):
        super().__init__(parent)
        self._filters: dict[str, QComboBox] = {}
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        self._search = SearchBar(placeholder)
        self._search.set_min_width(280)
        self._search.search_changed.connect(self._on_change)
        self._layout.addWidget(self._search)

    def add_filter(self, key: str, items: list[tuple], placeholder: str = "") -> QComboBox:
        """
        Add a filter dropdown.
        items: list of (display_text, value) tuples.
        Returns the QComboBox for further customization.
        """
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setMinimumWidth(150)
        combo.setStyleSheet("""
            QComboBox {
                background: white; border: 1px solid #D1D5DB;
                border-radius: 6px; padding: 0 10px;
                font-size: 13px; color: #0F172A;
            }
            QComboBox:focus { border-color: #2563EB; }
            QComboBox::drop-down { border: none; width: 20px; }
        """)
        if placeholder:
            combo.addItem(placeholder, None)
        for text, value in items:
            combo.addItem(text, value)
        combo.currentIndexChanged.connect(self._on_change)
        self._filters[key] = combo
        self._layout.addWidget(combo)
        return combo

    def add_stretch(self) -> None:
        self._layout.addStretch()

    def _on_change(self) -> None:
        query = self._search.text()
        values = {k: combo.currentData() for k, combo in self._filters.items()}
        self.filters_changed.emit(query, values)

    def get_query(self) -> str:
        return self._search.text()

    def get_filter(self, key: str):
        combo = self._filters.get(key)
        return combo.currentData() if combo else None
