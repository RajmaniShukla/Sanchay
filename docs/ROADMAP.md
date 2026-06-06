# Development Roadmap — Sanchay

## Phase 0 — Foundation (Week 1)
- [x] Project structure created
- [x] SRS document
- [x] Database schema design
- [ ] Core layer: config, database engine, exceptions, security, signals
- [ ] SQLAlchemy models (all tables)
- [ ] Database initialization + seeding
- [ ] requirements.txt finalized

## Phase 1 — Auth & Shell (Week 1-2)
- [ ] Login screen (PySide6)
- [ ] First-run wizard (create admin account)
- [ ] Main window with sidebar navigation
- [ ] Dashboard with stat cards
- [ ] Session management
- [ ] Role-based menu visibility

## Phase 2 — Organization & People (Week 2-3)
- [ ] Organization CRUD (list, create, edit, deactivate)
- [ ] Department CRUD (with hierarchy)
- [ ] Person management (Employee/Student/Contractor/Candidate)
- [ ] Person search and filter
- [ ] Photo upload for persons

## Phase 3 — Asset Management (Week 3-4)
- [ ] Asset category CRUD (hierarchical)
- [ ] Asset registration form
- [ ] Asset list with search/filter
- [ ] Asset detail view
- [ ] Asset status tracking
- [ ] Photo upload for assets

## Phase 4 — Transactions (Week 4-5)
- [ ] Issue asset dialog
- [ ] Return asset dialog
- [ ] Availability check
- [ ] Issue history list
- [ ] Overdue flagging
- [ ] Transaction search

## Phase 5 — Reports (Week 5-6)
- [ ] Report selection screen
- [ ] Asset inventory report (PDF/Excel/CSV)
- [ ] Department asset report
- [ ] Issue/return history report
- [ ] Overdue assets report
- [ ] Person holding report
- [ ] Print preview

## Phase 6 — Settings & Admin (Week 6)
- [ ] User management (Admin only)
- [ ] Role assignment
- [ ] App settings panel
- [ ] Backup & restore
- [ ] Audit log viewer

## Phase 7 — Polish & Testing (Week 7)
- [ ] Unit tests (models, services)
- [ ] Integration tests (workflows)
- [ ] UI/UX review
- [ ] Keyboard navigation
- [ ] Error handling & user messages
- [ ] Performance testing

## Phase 8 — Packaging (Week 8)
- [ ] PyInstaller build (Windows .exe)
- [ ] Linux AppImage
- [ ] macOS .app bundle
- [ ] Installer / setup wizard
- [ ] User manual (PDF)

---

## Future Roadmap

### v1.1 — QR & Barcode
- QR code generation per asset
- Barcode scanner input support
- Print asset labels

### v1.2 — Maintenance
- Maintenance scheduling
- Maintenance history
- Service provider management
- AMC tracking

### v1.3 — Multi-user Network
- PostgreSQL backend
- Multi-user server mode
- Real-time sync

### v1.4 — Cloud
- Cloud backup (S3, Google Drive)
- Cross-branch sync
- Web dashboard companion

### v2.0 — Enterprise
- API endpoints (REST)
- Mobile app (Android/iOS)
- Email notifications
- Advanced analytics
- Custom report builder
