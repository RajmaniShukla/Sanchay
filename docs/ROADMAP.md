# Development Roadmap — Sanchay

## Phase 0 — Foundation ✅ Complete (2026-06-06)
- [x] Project structure (55 files across all layers)
- [x] SRS, Database Schema, Roadmap documentation
- [x] Core layer: config, database engine, exceptions, security, signals
- [x] SQLAlchemy models (11 tables)
- [x] Database initialisation + seeding (4 roles, default admin)
- [x] requirements.txt, .gitignore, README

## Phase 1 — Auth & Shell ✅ Complete (2026-06-06)
- [x] Login screen (PySide6) with bcrypt auth
- [x] First-run wizard (create admin + first organisation)
- [x] Main window with sidebar navigation + lazy page loading
- [x] Dashboard with live stat cards + recent activity
- [x] Session management + role-based menu visibility
- [x] Toast notification system

## Phase 2 — Organisation & People ✅ Complete (2026-06-06)
- [x] Organisation CRUD (list, create, edit, deactivate)
- [x] Department CRUD (with parent-child hierarchy)
- [x] Person management (Employee / Student / Contractor / Candidate)
- [x] Person tabs, search, department + status filter
- [x] Shared widgets: FormDialog, ConfirmDialog, SearchBar
- [x] 19 integration tests passing

## Phase 3 — Asset Management ✅ Complete (2026-06-06)
- [x] Asset category CRUD (hierarchical, parent indent)
- [x] Asset registration form (3-tab: Identity / Specs / Financial)
- [x] Asset list with search + 3 filter dropdowns + stat pills
- [x] Asset detail dialog (full metadata + colour-coded warranty + issue history)
- [x] 22 integration tests passing

## Phase 4 — Transactions ✅ Complete (2026-06-06)
- [x] Issue Asset page (2-panel: asset picker + person picker)
- [x] Return Asset page (active issue picker + return form)
- [x] Transaction History (4 tabs: Active / Overdue / All / Returns)
- [x] Quick Return inline action, overdue sync on startup
- [x] 14 integration tests passing

## Phase 5 — Reports ✅ Complete (2026-06-06)
- [x] 6 report types (inventory, dept, issues, returns, overdue, holdings)
- [x] PDF export (ReportLab, A4/landscape, professional layout)
- [x] Excel export (openpyxl, styled, freeze panes, auto-width)
- [x] CSV export (UTF-8-BOM, metadata header, summary footer)
- [x] Report preview + export-to-folder shortcut
- [x] 16 integration tests passing

## Phase 6 — Settings & Admin ✅ Complete (2026-06-06)
- [x] Settings panel (General / Audit Log / About tabs)
- [x] User management (Admin only): create, edit, deactivate, change password
- [x] Backup & Restore (threaded backup, double-confirm restore, WAL cleanup)
- [x] Settings persistence in DB (key-value store)
- [x] 24 integration tests passing

## Phase 7 — Deep Testing + Polish ✅ Complete (2026-06-06)
- [x] 3 parallel subagents: test-writer, hardener, polisher
- [x] 110 unit service tests (every method, happy + error path)
- [x] 68 edge case tests (None, empty, unicode, boundary values)
- [x] 56 security tests (password, session, SQL injection, roles)
- [x] Service hardening: validation, user-friendly errors, new methods
- [x] View polish: EmptyStateWidget, keyboard shortcuts (Ctrl+N/F5/Ctrl+F),
      tooltips, loading feedback, clickable dashboard cards, Recent Activity
- [x] Bugs fixed: bcrypt 72-byte cap, backup mkdir, WAL sidecar cleanup,
      org code regex, user_form_dialog corruption, setup_wizard corruption

## Phase 7.5 — Security Audit + Idiot-Proof ✅ Complete (2026-06-06)
- [x] `require_authenticated()` + `require_role()` + `require_permission()` helpers
- [x] Permission enforcement on all 5 write-service methods
- [x] 7 new validators: org_code, dept_code, asset_code, name, date, decimal, search
- [x] Defensive repository patterns: null guards, all-keys defaults, uniqueness loops
- [x] Backup/restore fully idiot-proof: size check, SQLite header check, WAL cleanup
- [x] 51 lifecycle tests (full org→dept→person→asset→issue→return→backup cycle)
- [x] 52 permission matrix tests (4 roles × all operations)
- [x] 54 exception path tests (every custom exception triggered + message verified)
- [x] **GRAND TOTAL: 643 tests, 0 failures across 11 suites**

## Phase 8 — Packaging 🔄 In Progress
- [x] Pre-phase 8 audit (2026-06-07)
  - [x] Fixed config.py: BUNDLE_ROOT split for onedir/onefile/source modes
  - [x] Fixed main_window.py: _load_icon_file() uses config.ICONS_DIR (frozen-safe)
  - [x] Fixed main.py: sys.path.insert guarded for frozen builds
  - [x] Installed PyInstaller 6.20.0 (supports Python 3.14)
- [x] sanchay.spec — onedir spec file written
- [x] Windows onedir build: dist\Sanchay\ (135.8 MB, Sanchay.exe launches ✅)
- [x] build_exe.bat — convenience build script
- [x] Phase 8 audit (2026-06-07) — reportlab + openpyxl lazy-import fix, logger sys.stderr guard
- [x] NSIS installer script (installer\sanchay_installer.nsi)
  - Start Menu + Desktop shortcuts
  - Add/Remove Programs registration
  - Uninstaller with optional user-data keep/delete prompt
  - installer\build_installer.bat convenience script
- [ ] Build final SanchaySetup-1.0.0.exe (needs NSIS installed)
- [x] User manual PDF (docs/Sanchay_User_Manual.pdf) — 17 sections, generated via generate_manual.py
- [ ] Auto-update check (GitHub releases)
- [ ] Linux AppImage build
- [ ] macOS .app bundle
- [ ] Release checklist

---

## Future Roadmap

### v1.1 — QR & Barcode
- QR code generation per asset
- Barcode scanner input (USB / Bluetooth)
- Print asset labels (A4 / label sheets)

### v1.2 — Maintenance
- Maintenance scheduling calendar
- AMC (Annual Maintenance Contract) tracking
- Service provider management
- Maintenance history per asset

### v1.3 — Multi-user Network
- PostgreSQL / MySQL backend migration
- Multi-user server mode (FastAPI REST)
- Real-time sync between clients

### v1.4 — Cloud & Mobile
- Cloud backup (S3, Google Drive, Dropbox)
- Cross-branch sync
- Android companion app
- Web dashboard (React)

### v2.0 — Enterprise
- REST API (OpenAPI spec)
- Email / SMS notifications
- Custom report builder
- Advanced analytics & charts
- White-label / branding support
