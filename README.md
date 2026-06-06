# 📦 Sanchay — Inventory & Asset Management System

> **Sanchay** (सञ्चय) — *collection, accumulation* — a professional, offline-first desktop application for managing organizational assets and inventory.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-green?logo=qt)
![SQLite](https://img.shields.io/badge/SQLite-3-orange?logo=sqlite)
![Architecture](https://img.shields.io/badge/Architecture-MVC-purple)

---

## ✨ Features

| Feature | Status |
|---------|--------|
| Multi-organization & department management | ✅ |
| Asset registration with categories & serial numbers | ✅ |
| Asset issue / return with full history | ✅ |
| Employee / Student / Contractor / Candidate management | ✅ |
| Role-based access (Admin / Manager / Operator / Viewer) | ✅ |
| Reports: PDF, Excel, CSV | 🔄 |
| Backup & Restore | ✅ |
| Audit trail for all changes | ✅ |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
cd D:\Projects\Sanchay

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m app.main
```

### First Run
On first launch, the **Setup Wizard** will guide you to:
1. Create the administrator account
2. Set up your first organization

---

## 🏗️ Architecture

```
Sanchay/
├── app/
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration
│   ├── constants.py         # Enums & constants
│   │
│   ├── core/                # Infrastructure
│   │   ├── database.py      # SQLAlchemy engine & sessions
│   │   ├── security.py      # Auth & session management
│   │   ├── signals.py       # Qt signal bus
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logger.py        # Logging setup
│   │
│   ├── models/              # SQLAlchemy ORM models
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic layer
│   ├── controllers/         # MVC controllers
│   └── views/               # PySide6 UI
│
├── docs/                    # SRS, Schema, Roadmap
├── backups/                 # Database backups
├── exports/                 # PDF/Excel/CSV exports
├── logs/                    # Application logs
└── tests/                   # Unit & integration tests
```

### Layer Responsibilities

| Layer | Role |
|-------|------|
| **Models** | SQLAlchemy ORM, pure data classes |
| **Repositories** | Database queries, no business logic |
| **Services** | Business rules, validation, orchestration |
| **Controllers** | Connect Views ↔ Services, handle events |
| **Views** | PySide6 UI, user interaction only |

---

## 📐 Database

SQLite database stored at `data/sanchay.db`. Key tables:

- `organizations` — Multi-org support
- `departments` — Hierarchical departments
- `persons` — Employees, Students, Contractors, Candidates
- `asset_categories` — Hierarchical asset categories
- `assets` — Full asset catalog with serial numbers
- `asset_issues` — Issue records (asset → person)
- `asset_returns` — Return records linked to issues
- `users` / `roles` — Authentication & RBAC
- `audit_logs` — Immutable audit trail

See [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) for full schema.

---

## 🎭 User Roles

| Role | Access |
|------|--------|
| **Admin** | Full access to everything |
| **Manager** | Dept assets + persons + reports |
| **Operator** | Issue/return assets, view records |
| **Viewer** | Read-only: view assets, persons, reports |

---

## 🗺️ Development Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for detailed phase breakdown.

| Phase | Status |
|-------|--------|
| 0 — Foundation (Core + Models + Services) | ✅ Complete |
| 1 — Auth & Shell (Login + Main Window + Dashboard) | ✅ Complete |
| 2 — Organization & People | 🔄 In Progress |
| 3 — Asset Management | 📅 Planned |
| 4 — Transactions | 📅 Planned |
| 5 — Reports | 📅 Planned |
| 6 — Settings & Admin | 📅 Planned |
| 7 — Testing | 📅 Planned |
| 8 — Packaging | 📅 Planned |

---

## 🔮 Future

- QR code per asset (scan to view/issue)
- Barcode scanner integration
- PostgreSQL backend for multi-user
- Cloud backup (S3, Google Drive)
- Maintenance scheduling
- Mobile companion app

---

## 📄 Documentation

| Doc | Path |
|-----|------|
| Software Requirements Specification | `docs/SRS.md` |
| Database Schema | `docs/DATABASE_SCHEMA.md` |
| Development Roadmap | `docs/ROADMAP.md` |

---

## 📃 License

Proprietary — All rights reserved.

---

*Built with ❤️ using Python, PySide6, and SQLAlchemy*
