"""
Sanchay — Base Form Dialog
============================
Reusable base class for all Create/Edit dialogs.
Provides a consistent layout: header, scrollable body, footer.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QSizePolicy,
)
from PySide6.QtCore import Qt


class FormDialog(QDialog):
    """
    Base dialog for Create / Edit forms.

    Subclass and implement:
        _build_form(layout: QVBoxLayout) — add your form widgets here
        _collect_data() -> dict          — return validated field values
        _on_save(data: dict)             — call your service, then self.accept()

    Call `set_error(msg)` to show inline errors.
    Call `set_loading(True/False)` to disable/enable the save button.
    """

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        save_label: str = "Save",
        parent=None,
        min_width: int = 520,
        min_height: int = 400,
    ):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle
        self._save_label = save_label

        self.setModal(True)
        self.setMinimumWidth(min_width)
        self.setMinimumHeight(min_height)
        self.setWindowTitle(title)
        self.setStyleSheet("QDialog { background-color: #FFFFFF; }")

        self._build_shell()
        self._build_form(self._form_layout)

    # ── Shell construction ────────────────────────────────────────────────────

    def _build_shell(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background-color: #F8FAFC; border-bottom: 1px solid #E2E8F0;")
        header.setFixedHeight(68)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(24, 12, 24, 12)
        h_layout.setSpacing(2)

        title_lbl = QLabel(self._title)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 700; color: #0F172A;")

        if self._subtitle:
            sub_lbl = QLabel(self._subtitle)
            sub_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
            h_layout.addWidget(title_lbl)
            h_layout.addWidget(sub_lbl)
        else:
            h_layout.addWidget(title_lbl)
            h_layout.addStretch()

        root.addWidget(header)

        # ── Scrollable form body ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: white; border: none; }")

        form_container = QWidget()
        form_container.setStyleSheet("background: white;")
        self._form_layout = QVBoxLayout(form_container)
        self._form_layout.setContentsMargins(24, 20, 24, 20)
        self._form_layout.setSpacing(16)

        scroll.setWidget(form_container)
        root.addWidget(scroll, 1)

        # ── Error label ─────────────────────────────────────────────────────────
        self._error_frame = QFrame()
        self._error_frame.setStyleSheet(
            "background: #FEF2F2; border-top: 1px solid #FECACA; "
            "border-bottom: 1px solid #FECACA;"
        )
        self._error_frame.setVisible(False)
        err_layout = QHBoxLayout(self._error_frame)
        err_layout.setContentsMargins(24, 8, 24, 8)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color: #B91C1C; font-size: 12px; font-weight: 500;")
        self._error_lbl.setWordWrap(True)
        err_layout.addWidget(QLabel("⚠"))
        err_layout.addWidget(self._error_lbl, 1)
        root.addWidget(self._error_frame)

        # ── Footer ──────────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setStyleSheet(
            "background: #F8FAFC; border-top: 1px solid #E2E8F0;"
        )
        footer.setFixedHeight(60)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 10, 24, 10)
        f_layout.setSpacing(10)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.setMinimumWidth(90)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: white; border: 1px solid #D1D5DB;
                border-radius: 6px; color: #374151; font-weight: 500;
            }
            QPushButton:hover { background: #F9FAFB; }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton(self._save_label)
        self.save_btn.setFixedHeight(38)
        self.save_btn.setMinimumWidth(110)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #2563EB; border: none;
                border-radius: 6px; color: white; font-weight: 600;
            }
            QPushButton:hover { background: #1D4ED8; }
            QPushButton:disabled { background: #93C5FD; }
        """)
        self.save_btn.clicked.connect(self._handle_save)

        f_layout.addStretch()
        f_layout.addWidget(self.cancel_btn)
        f_layout.addWidget(self.save_btn)
        root.addWidget(footer)

    # ── To override ──────────────────────────────────────────────────────────

    def _build_form(self, layout: QVBoxLayout) -> None:
        """Override: add form widgets to this layout."""
        pass

    def _collect_data(self) -> Optional[dict]:
        """
        Override: read field values, validate, return dict.
        Return None to abort save (show error via set_error first).
        """
        return {}

    def _on_save(self, data: dict) -> None:
        """Override: call service with data, then call self.accept()."""
        self.accept()

    # ── Helpers for subclasses ────────────────────────────────────────────────

    def set_error(self, message: str) -> None:
        """Show an error banner above the footer."""
        self._error_lbl.setText(message)
        self._error_frame.setVisible(bool(message))

    def clear_error(self) -> None:
        self._error_frame.setVisible(False)

    def set_loading(self, loading: bool) -> None:
        """Disable/enable save button during async operations."""
        self.save_btn.setEnabled(not loading)
        self.save_btn.setText("Saving…" if loading else self._save_label)
        self.cancel_btn.setEnabled(not loading)

    def _handle_save(self) -> None:
        self.clear_error()
        data = self._collect_data()
        if data is None:
            return
        self.set_loading(True)
        try:
            self._on_save(data)
        except Exception as e:
            self.set_error(str(e))
        finally:
            self.set_loading(False)

    # ── Layout helpers ────────────────────────────────────────────────────────

    @staticmethod
    def make_label(text: str, required: bool = False) -> QLabel:
        suffix = " <span style='color:#DC2626'>*</span>" if required else ""
        lbl = QLabel(f"{text}{suffix}")
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #374151;")
        return lbl

    @staticmethod
    def make_section(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #0F172A; "
            "border-bottom: 2px solid #E2E8F0; padding-bottom: 6px;"
        )
        return lbl

    @staticmethod
    def make_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("border: 1px solid #E2E8F0;")
        return line
