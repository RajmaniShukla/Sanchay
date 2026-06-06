# Database Schema — Sanchay v1.0.0

## Entity Relationship Overview

```
organizations ──< departments ──< persons
     │                │                │
     │                └────────────────┤
     │                                 │
     └──────< assets >────────────────>│
                  │                   │
                  └──< asset_issues >──┘
                           │
                           └──< asset_returns

users ──> roles
users ──> organizations
```

---

## Tables

### `roles`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| name | VARCHAR(50) | UNIQUE, NOT NULL | admin / manager / operator / viewer |
| description | TEXT | | Role description |
| permissions | JSON | NOT NULL | Permission map |
| created_at | DATETIME | NOT NULL | Record creation |
| updated_at | DATETIME | NOT NULL | Last update |

### `users`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Login username |
| email | VARCHAR(150) | UNIQUE | Email address |
| full_name | VARCHAR(150) | NOT NULL | Display name |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash |
| role_id | INTEGER | FK→roles.id | User role |
| org_id | INTEGER | FK→organizations.id | Associated org |
| dept_id | INTEGER | FK→departments.id | Associated dept |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| last_login | DATETIME | | Last login timestamp |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | Soft delete |

### `organizations`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| name | VARCHAR(200) | NOT NULL | Organization name |
| code | VARCHAR(20) | UNIQUE, NOT NULL | Short code (e.g. NRV) |
| org_type | VARCHAR(50) | NOT NULL | college/industry/factory/ngo/office/other |
| address | TEXT | | Full address |
| city | VARCHAR(100) | | City |
| state | VARCHAR(100) | | State |
| pincode | VARCHAR(10) | | PIN/ZIP |
| country | VARCHAR(100) | DEFAULT 'India' | Country |
| phone | VARCHAR(20) | | Contact phone |
| email | VARCHAR(150) | | Contact email |
| website | VARCHAR(255) | | Website URL |
| logo_path | VARCHAR(500) | | Logo file path |
| description | TEXT | | About the org |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | |

### `departments`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id, NOT NULL | Parent org |
| parent_dept_id | INTEGER | FK→departments.id | Parent dept (for hierarchy) |
| name | VARCHAR(200) | NOT NULL | Department name |
| code | VARCHAR(20) | NOT NULL | Short code |
| description | TEXT | | Description |
| head_person_id | INTEGER | FK→persons.id | Dept head |
| is_active | BOOLEAN | DEFAULT TRUE | |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | |

### `persons`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id, NOT NULL | |
| dept_id | INTEGER | FK→departments.id | |
| person_type | VARCHAR(20) | NOT NULL | employee/student/contractor/candidate |
| person_id_code | VARCHAR(50) | UNIQUE | EMP-001 / STU-001 etc. |
| first_name | VARCHAR(100) | NOT NULL | |
| last_name | VARCHAR(100) | | |
| email | VARCHAR(150) | | |
| phone | VARCHAR(20) | | |
| designation | VARCHAR(150) | | Job title / course |
| address | TEXT | | |
| city | VARCHAR(100) | | |
| state | VARCHAR(100) | | |
| date_of_joining | DATE | | |
| date_of_leaving | DATE | | |
| id_proof_type | VARCHAR(50) | | Aadhar/PAN/Passport etc. |
| id_proof_number | VARCHAR(50) | | |
| photo_path | VARCHAR(500) | | |
| notes | TEXT | | |
| status | VARCHAR(20) | DEFAULT 'active' | active/inactive |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | |

### `asset_categories`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id | |
| parent_category_id | INTEGER | FK→asset_categories.id | Hierarchical |
| name | VARCHAR(150) | NOT NULL | e.g. Electronics |
| code | VARCHAR(20) | NOT NULL | e.g. ELEC |
| description | TEXT | | |
| depreciation_rate | DECIMAL(5,2) | | Annual % |
| useful_life_years | INTEGER | | Expected life |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | |

### `assets`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id | |
| dept_id | INTEGER | FK→departments.id | Assigned dept |
| category_id | INTEGER | FK→asset_categories.id | |
| name | VARCHAR(200) | NOT NULL | Asset name |
| asset_code | VARCHAR(50) | UNIQUE, NOT NULL | Internal code |
| serial_number | VARCHAR(100) | | Manufacturer serial |
| model_number | VARCHAR(100) | | |
| manufacturer | VARCHAR(150) | | Brand |
| supplier | VARCHAR(150) | | Vendor |
| purchase_date | DATE | | |
| purchase_price | DECIMAL(12,2) | | Original cost |
| current_value | DECIMAL(12,2) | | After depreciation |
| warranty_expiry_date | DATE | | |
| location | VARCHAR(200) | | Physical location |
| description | TEXT | | Notes |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'available' | available/issued/maintenance/disposed/lost |
| condition | VARCHAR(20) | DEFAULT 'good' | new/good/fair/poor |
| photo_path | VARCHAR(500) | | |
| qr_code_path | VARCHAR(500) | | Future: QR code image |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |
| is_deleted | BOOLEAN | DEFAULT FALSE | |

### `asset_issues`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id | |
| asset_id | INTEGER | FK→assets.id, NOT NULL | |
| person_id | INTEGER | FK→persons.id, NOT NULL | Issued to |
| issued_by_user_id | INTEGER | FK→users.id | Issued by (operator) |
| issue_date | DATETIME | NOT NULL | Auto timestamp |
| expected_return_date | DATE | | Due date |
| purpose | TEXT | | Reason for issue |
| notes | TEXT | | |
| status | VARCHAR(20) | DEFAULT 'active' | active/returned/overdue |
| created_at | DATETIME | NOT NULL | |
| updated_at | DATETIME | NOT NULL | |

### `asset_returns`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| org_id | INTEGER | FK→organizations.id | |
| issue_id | INTEGER | FK→asset_issues.id, NOT NULL | |
| asset_id | INTEGER | FK→assets.id | |
| person_id | INTEGER | FK→persons.id | Returned by |
| returned_to_user_id | INTEGER | FK→users.id | Received by |
| return_date | DATETIME | NOT NULL | Auto timestamp |
| condition_on_return | VARCHAR(20) | | new/good/fair/poor |
| remarks | TEXT | | |
| created_at | DATETIME | NOT NULL | |

### `audit_logs`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | Primary key |
| user_id | INTEGER | FK→users.id | Who did it |
| action | VARCHAR(50) | NOT NULL | CREATE/UPDATE/DELETE/LOGIN etc. |
| module | VARCHAR(50) | | assets/persons/users etc. |
| table_name | VARCHAR(100) | | Affected table |
| record_id | INTEGER | | Affected record |
| old_values | JSON | | Before state |
| new_values | JSON | | After state |
| description | TEXT | | Human-readable log |
| timestamp | DATETIME | NOT NULL | When |

### `app_settings`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTO | |
| key | VARCHAR(100) | UNIQUE, NOT NULL | Setting key |
| value | TEXT | | Setting value |
| description | TEXT | | What it controls |
| updated_at | DATETIME | | Last updated |

---

## Indexes
```sql
CREATE INDEX idx_assets_status ON assets(status, is_deleted);
CREATE INDEX idx_assets_dept ON assets(dept_id);
CREATE INDEX idx_assets_category ON assets(category_id);
CREATE INDEX idx_persons_dept ON persons(dept_id, status);
CREATE INDEX idx_persons_type ON persons(person_type);
CREATE INDEX idx_issues_asset ON asset_issues(asset_id, status);
CREATE INDEX idx_issues_person ON asset_issues(person_id);
CREATE INDEX idx_returns_issue ON asset_returns(issue_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id, timestamp);
CREATE INDEX idx_departments_org ON departments(org_id);
```

---

## Default Data
```sql
-- Roles (seeded on first run)
INSERT INTO roles (name, description, permissions) VALUES
('admin',    'Full system access',        '{"all": true}'),
('manager',  'Dept-level management',     '{"assets": "rw", "persons": "rw", "reports": "r", "settings": "r"}'),
('operator', 'Day-to-day operations',     '{"assets": "r", "persons": "r", "transactions": "rw"}'),
('viewer',   'Read-only access',          '{"assets": "r", "persons": "r", "reports": "r"}');

-- Default settings
INSERT INTO app_settings (key, value, description) VALUES
('app_name',         'Sanchay',    'Application display name'),
('auto_backup',      'false',      'Enable daily auto-backup'),
('backup_location',  './backups',  'Backup folder path'),
('asset_code_prefix','AST',        'Asset code prefix'),
('theme',            'light',      'UI theme (light/dark)');
```
