# Software Requirements Specification (SRS)
## Sanchay — Inventory & Asset Management System
**Version:** 1.0.0  
**Date:** 2026-06-06  
**Author:** Architecture Team  
**Status:** Approved

---

## 1. Introduction

### 1.1 Purpose
Sanchay is a standalone, offline-first desktop application designed to manage organizational assets and inventory. It targets colleges, industries, factories, NGOs, training institutes, and corporate offices that need a reliable, professional, and intuitive system without internet dependency.

### 1.2 Scope
The system handles:
- Multi-organization and multi-department asset tracking
- Employee/student/contractor/candidate management
- Asset lifecycle: registration → issue → return → disposal
- Role-based access control (RBAC)
- Reporting (PDF, Excel, CSV)
- Database backup and restore

### 1.3 Definitions
| Term | Meaning |
|------|---------|
| Asset | Any physical or digital item tracked by the organization |
| Issue | The act of assigning an asset to a person |
| Return | The act of receiving an asset back |
| Person | Collective term for employees, students, contractors, candidates |
| Org | Organization |

### 1.4 Technology Stack
| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| UI Framework | PySide6 (Qt 6.x) |
| Database | SQLite 3 (via SQLAlchemy 2.x) |
| ORM | SQLAlchemy 2.x |
| PDF Export | ReportLab |
| Excel Export | openpyxl |
| Password Hashing | bcrypt |
| Logging | loguru |
| Migrations | Alembic |

---

## 2. Overall Description

### 2.1 Product Perspective
Sanchay is a self-contained desktop application. All data is stored in a local SQLite file. Future versions will support PostgreSQL/MySQL and cloud sync.

### 2.2 Product Functions (High-Level)
1. Multi-organization management
2. Department hierarchy management
3. Person management (4 types)
4. Asset catalog with categories and serial number tracking
5. Asset issue and return workflow with full history
6. Role-based access (Admin / Manager / Operator / Viewer)
7. Reports (PDF, Excel, CSV)
8. Backup and restore

### 2.3 User Classes
| Role | Description | Access |
|------|-------------|--------|
| Admin | Full system access | Everything |
| Manager | Department-level management | Own dept assets + persons |
| Operator | Day-to-day operations | Issue/return, view records |
| Viewer | Read-only access | View reports and listings |

### 2.4 Operating Environment
- OS: Windows 10/11, Ubuntu 20.04+, macOS 12+
- Memory: 4 GB RAM minimum
- Storage: 500 MB minimum (for app + DB)
- Display: 1280×720 minimum

---

## 3. Functional Requirements

### 3.1 Authentication Module
| ID | Requirement |
|----|-------------|
| FR-AUTH-01 | System shall authenticate users with username + password |
| FR-AUTH-02 | Passwords shall be hashed with bcrypt |
| FR-AUTH-03 | Session shall persist for the application lifetime |
| FR-AUTH-04 | Failed login attempts shall be logged |
| FR-AUTH-05 | Admin can reset any user's password |
| FR-AUTH-06 | First-run wizard shall create the initial admin account |

### 3.2 Organization Management
| ID | Requirement |
|----|-------------|
| FR-ORG-01 | System shall support multiple organizations |
| FR-ORG-02 | Each organization has: name, code, type, address, contact info, logo |
| FR-ORG-03 | Organization types: College, Industry, Factory, NGO, Office, Other |
| FR-ORG-04 | Admin can create/edit/deactivate organizations |

### 3.3 Department Management
| ID | Requirement |
|----|-------------|
| FR-DEPT-01 | Departments belong to an organization |
| FR-DEPT-02 | Each department has: name, code, head person, parent department |
| FR-DEPT-03 | Departments can be nested (parent–child hierarchy) |
| FR-DEPT-04 | Deactivating a dept does not delete its records |

### 3.4 Person Management
| ID | Requirement |
|----|-------------|
| FR-PER-01 | System manages 4 person types: Employee, Student, Contractor, Candidate |
| FR-PER-02 | Each person has: ID, name, email, phone, department, designation, join date |
| FR-PER-03 | Person status: Active / Inactive |
| FR-PER-04 | System prevents issuing assets to inactive persons |
| FR-PER-05 | Person photo upload (optional) |
| FR-PER-06 | Search persons by name, ID, email, department |

### 3.5 Asset Management
| ID | Requirement |
|----|-------------|
| FR-ASS-01 | Assets are organized into categories (hierarchical) |
| FR-ASS-02 | Each asset has: code, name, serial number, model, manufacturer, supplier |
| FR-ASS-03 | Financial fields: purchase date, purchase price, warranty expiry |
| FR-ASS-04 | Asset status: Available / Issued / Under Maintenance / Disposed / Lost |
| FR-ASS-05 | Asset condition: New / Good / Fair / Poor |
| FR-ASS-06 | Asset photo upload (optional) |
| FR-ASS-07 | Asset can be assigned to a department/location |
| FR-ASS-08 | System prevents issuing an unavailable asset |
| FR-ASS-09 | Bulk import assets from CSV |

### 3.6 Asset Issue/Return
| ID | Requirement |
|----|-------------|
| FR-TXN-01 | Asset issue records: asset, person, issued_by, issue_date, expected_return_date, purpose |
| FR-TXN-02 | Issue date/time is auto-populated |
| FR-TXN-03 | System checks asset availability before allowing issue |
| FR-TXN-04 | Return records: condition on return, remarks |
| FR-TXN-05 | Return date/time is auto-populated |
| FR-TXN-06 | Overdue issues are flagged |
| FR-TXN-07 | Full issue/return history is preserved |
| FR-TXN-08 | Asset status is updated automatically on issue/return |

### 3.7 Reporting
| ID | Requirement |
|----|-------------|
| FR-REP-01 | Asset inventory report (all assets with status) |
| FR-REP-02 | Department-wise asset report |
| FR-REP-03 | Issue history report (date range filter) |
| FR-REP-04 | Overdue assets report |
| FR-REP-05 | Person asset holding report |
| FR-REP-06 | Export to PDF, Excel (XLSX), CSV |
| FR-REP-07 | Report preview before export |

### 3.8 User Management
| ID | Requirement |
|----|-------------|
| FR-USR-01 | Admin creates/edits/deactivates users |
| FR-USR-02 | Each user has a role: Admin / Manager / Operator / Viewer |
| FR-USR-03 | Roles have predefined permission sets |
| FR-USR-04 | Admin can unlock locked accounts |

### 3.9 Backup & Restore
| ID | Requirement |
|----|-------------|
| FR-BAK-01 | One-click backup to timestamped `.db` file |
| FR-BAK-02 | Restore from a backup file with confirmation |
| FR-BAK-03 | Auto-backup option (daily) |
| FR-BAK-04 | Backup location is configurable |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Application shall start within 3 seconds on standard hardware |
| NFR-02 | All DB operations shall complete within 1 second for ≤100,000 records |
| NFR-03 | UI shall be responsive; no freezes during reports |
| NFR-04 | Passwords shall never be stored in plaintext |
| NFR-05 | All data mutations shall be audit-logged |
| NFR-06 | Application shall gracefully handle DB corruption |
| NFR-07 | Code shall follow PEP 8 and have ≥80% test coverage |
| NFR-08 | Application shall run offline (no internet required) |

---

## 5. Future Requirements (Phase 2+)

| Feature | Priority |
|---------|----------|
| QR Code generation for assets | High |
| Barcode scanner integration | High |
| Multi-user network mode | Medium |
| PostgreSQL / MySQL migration | Medium |
| Cloud synchronization | Low |
| Maintenance scheduling | Medium |
| Email notifications | Low |
| Mobile companion app | Low |

---

## 6. Constraints
- Must run on Windows 10, Ubuntu 20.04+, macOS 12+
- Must function fully offline
- Database must be portable (single file, easily backed up)
- UI must be keyboard-navigable for accessibility

---

*End of SRS v1.0.0*
