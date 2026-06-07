# -*- mode: python ; coding: utf-8 -*-
# ===========================================================================
# Sanchay — PyInstaller spec file
# Build: onedir (recommended for desktop apps with persistent user data)
#
# Usage:
#   venv\Scripts\pyinstaller.exe sanchay.spec --clean -y
#
# Output:
#   dist\Sanchay\         <- distribute this entire folder
#   dist\Sanchay\Sanchay.exe
# ===========================================================================

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Project root (same directory as this spec file)
ROOT = Path(SPECPATH)

block_cipher = None

# ---------------------------------------------------------------------------
# collect_all for packages that use lazy / dynamic imports
# PyInstaller static analysis misses these without explicit collection
# ---------------------------------------------------------------------------
rl_datas,    rl_bins,    rl_hidden    = collect_all("reportlab")
xl_datas,    xl_bins,    xl_hidden    = collect_all("openpyxl")

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[] + rl_bins + xl_bins,
    datas=[
        # Bundle the entire resources folder (icons, styles, fonts)
        (str(ROOT / "app" / "resources"), "app/resources"),
    ] + rl_datas + xl_datas,
    hiddenimports=[
        # SQLAlchemy dialects
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.pool",
        # PySide6 plugins that may not be auto-detected
        "PySide6.QtSvg",
        "PySide6.QtXml",
        "PySide6.QtPrintSupport",
        # loguru sink internals
        "loguru._datetime",
        # bcrypt
        "bcrypt",
        # dotenv
        "dotenv",
        # reportlab (lazy imports in report_service.py)
        "reportlab.lib.colors",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
        "reportlab.lib.units",
        "reportlab.lib.enums",
        "reportlab.platypus",
        "reportlab.platypus.tables",
        "reportlab.platypus.paragraph",
        "reportlab.pdfgen",
        "reportlab.pdfbase",
        "reportlab.pdfbase.ttfonts",
        "reportlab.pdfbase.pdfmetrics",
        # openpyxl (lazy imports in report_service.py)
        "openpyxl",
        "openpyxl.styles",
        "openpyxl.styles.fills",
        "openpyxl.styles.fonts",
        "openpyxl.styles.borders",
        "openpyxl.styles.alignment",
        "openpyxl.utils",
        "openpyxl.utils.cell",
        "openpyxl.workbook",
        "openpyxl.worksheet",
        "openpyxl.worksheet.worksheet",
        "openpyxl.cell._writer",
        # csv (stdlib, but be explicit)
        "csv",
    ] + rl_hidden + xl_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed at runtime
        "pytest",
        "pytest_qt",
        "_pytest",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ---------------------------------------------------------------------------
# PYZ archive
# ---------------------------------------------------------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---------------------------------------------------------------------------
# EXE
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,         # onedir: binaries go in COLLECT
    name="Sanchay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                      # compress if UPX is available; harmless if not
    console=False,                 # windowed app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "app" / "resources" / "icons" / "sanchay.ico"),
    version_file=None,
)

# ---------------------------------------------------------------------------
# COLLECT (onedir bundle)
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Sanchay",                # dist\Sanchay\
)
