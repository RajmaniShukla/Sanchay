"""
Sanchay — Application Constants
=================================
All application-wide enumerations, choices, and static values.
Use these instead of raw strings throughout the codebase.
"""

from enum import Enum


# ── User Roles ───────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN    = "admin"
    MANAGER  = "manager"
    OPERATOR = "operator"
    VIEWER   = "viewer"

    @classmethod
    def choices(cls) -> list[str]:
        return [r.value for r in cls]

    def label(self) -> str:
        return self.value.capitalize()


# ── Person Types ─────────────────────────────────────────────────────────────

class PersonType(str, Enum):
    EMPLOYEE   = "employee"
    STUDENT    = "student"
    CONTRACTOR = "contractor"
    CANDIDATE  = "candidate"

    @classmethod
    def choices(cls) -> list[str]:
        return [t.value for t in cls]

    def label(self) -> str:
        return self.value.capitalize()

    def id_prefix(self) -> str:
        prefixes = {
            "employee":   "EMP",
            "student":    "STU",
            "contractor": "CON",
            "candidate":  "CAN",
        }
        return prefixes[self.value]


# ── Person Status ─────────────────────────────────────────────────────────────

class PersonStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"

    @classmethod
    def choices(cls) -> list[str]:
        return [s.value for s in cls]


# ── Organization Types ────────────────────────────────────────────────────────

class OrgType(str, Enum):
    COLLEGE   = "college"
    INDUSTRY  = "industry"
    FACTORY   = "factory"
    NGO       = "ngo"
    OFFICE    = "office"
    INSTITUTE = "institute"
    OTHER     = "other"

    @classmethod
    def choices(cls) -> list[str]:
        return [o.value for o in cls]

    def label(self) -> str:
        labels = {
            "college":   "College / University",
            "industry":  "Industry",
            "factory":   "Factory / Manufacturing",
            "ngo":       "NGO / Non-Profit",
            "office":    "Corporate Office",
            "institute": "Training Institute",
            "other":     "Other",
        }
        return labels[self.value]


# ── Asset Status ──────────────────────────────────────────────────────────────

class AssetStatus(str, Enum):
    AVAILABLE   = "available"
    ISSUED      = "issued"
    MAINTENANCE = "maintenance"
    DISPOSED    = "disposed"
    LOST        = "lost"

    @classmethod
    def choices(cls) -> list[str]:
        return [s.value for s in cls]

    def label(self) -> str:
        labels = {
            "available":   "Available",
            "issued":      "Issued",
            "maintenance": "Under Maintenance",
            "disposed":    "Disposed",
            "lost":        "Lost / Missing",
        }
        return labels[self.value]

    def badge_color(self) -> str:
        """Returns a color string for UI badges."""
        colors = {
            "available":   "#16a34a",   # green
            "issued":      "#2563eb",   # blue
            "maintenance": "#d97706",   # amber
            "disposed":    "#6b7280",   # gray
            "lost":        "#dc2626",   # red
        }
        return colors[self.value]


# ── Asset Condition ───────────────────────────────────────────────────────────

class AssetCondition(str, Enum):
    NEW  = "new"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

    @classmethod
    def choices(cls) -> list[str]:
        return [c.value for c in cls]

    def label(self) -> str:
        return self.value.capitalize()


# ── Issue Status ──────────────────────────────────────────────────────────────

class IssueStatus(str, Enum):
    ACTIVE   = "active"
    RETURNED = "returned"
    OVERDUE  = "overdue"

    @classmethod
    def choices(cls) -> list[str]:
        return [s.value for s in cls]

    def badge_color(self) -> str:
        colors = {
            "active":   "#2563eb",
            "returned": "#16a34a",
            "overdue":  "#dc2626",
        }
        return colors[self.value]


# ── Audit Actions ─────────────────────────────────────────────────────────────

class AuditAction(str, Enum):
    CREATE  = "CREATE"
    UPDATE  = "UPDATE"
    DELETE  = "DELETE"
    LOGIN   = "LOGIN"
    LOGOUT  = "LOGOUT"
    BACKUP  = "BACKUP"
    RESTORE = "RESTORE"
    EXPORT  = "EXPORT"
    ISSUE   = "ISSUE"
    RETURN  = "RETURN"


# ── ID Proof Types ────────────────────────────────────────────────────────────

ID_PROOF_TYPES = [
    "Aadhar Card",
    "PAN Card",
    "Passport",
    "Voter ID",
    "Driving License",
    "Employee ID",
    "Student ID",
    "Other",
]


# ── Report Types ──────────────────────────────────────────────────────────────

class ReportType(str, Enum):
    ASSET_INVENTORY  = "asset_inventory"
    DEPT_ASSETS      = "dept_assets"
    ISSUE_HISTORY    = "issue_history"
    RETURN_HISTORY   = "return_history"
    OVERDUE_ASSETS   = "overdue_assets"
    PERSON_HOLDINGS  = "person_holdings"

    def label(self) -> str:
        labels = {
            "asset_inventory": "Asset Inventory Report",
            "dept_assets":     "Department-wise Asset Report",
            "issue_history":   "Issue History Report",
            "return_history":  "Return History Report",
            "overdue_assets":  "Overdue Assets Report",
            "person_holdings": "Person Asset Holding Report",
        }
        return labels[self.value]


# ── Export Formats ────────────────────────────────────────────────────────────

class ExportFormat(str, Enum):
    PDF  = "pdf"
    XLSX = "xlsx"
    CSV  = "csv"

    def extension(self) -> str:
        return self.value

    def mime_type(self) -> str:
        types = {
            "pdf":  "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv":  "text/csv",
        }
        return types[self.value]


# ── UI Dimensions ─────────────────────────────────────────────────────────────

class UISize:
    SIDEBAR_W    = 220
    TOPBAR_H     = 56
    CONTENT_PAD  = 24
    CARD_RADIUS  = 8
    BTN_RADIUS   = 6
    INPUT_H      = 36
    TABLE_ROW_H  = 40


# ── Color Palette ─────────────────────────────────────────────────────────────

class Colors:
    # Primary
    PRIMARY       = "#2563EB"
    PRIMARY_DARK  = "#1D4ED8"
    PRIMARY_LIGHT = "#DBEAFE"

    # Status
    SUCCESS = "#16a34a"
    WARNING = "#d97706"
    DANGER  = "#dc2626"
    INFO    = "#0891b2"

    # Neutrals
    BG_PAGE    = "#F8FAFC"
    BG_CARD    = "#FFFFFF"
    BG_SIDEBAR = "#1E293B"
    BORDER     = "#E2E8F0"
    TEXT_MAIN  = "#0F172A"
    TEXT_MUTED = "#64748B"
    TEXT_WHITE = "#FFFFFF"
