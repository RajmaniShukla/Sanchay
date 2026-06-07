"""
Sanchay — PDF User Manual Generator
Produces: docs/Sanchay_User_Manual.pdf
Run: venv/Scripts/python.exe generate_manual.py
"""

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas as pdfcanvas

# ── Branding ────────────────────────────────────────────────────────────────
BLUE       = colors.HexColor("#2563EB")
BLUE_LIGHT = colors.HexColor("#EFF6FF")
BLUE_MID   = colors.HexColor("#BFDBFE")
DARK       = colors.HexColor("#1E293B")
GREY       = colors.HexColor("#64748B")
GREY_LIGHT = colors.HexColor("#F8FAFC")
GREEN      = colors.HexColor("#16A34A")
RED        = colors.HexColor("#DC2626")
AMBER      = colors.HexColor("#D97706")
WHITE      = colors.white

OUTPUT = Path("docs/Sanchay_User_Manual.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ── Page template with header/footer ────────────────────────────────────────
class SanchayDocTemplate(SimpleDocTemplate):
    def __init__(self, filename, **kw):
        super().__init__(filename, **kw)
        self.chapter = ""

    def handle_flowable(self, flowable):
        if hasattr(flowable, "_chapter_marker"):
            self.chapter = flowable._chapter_marker
        super().handle_flowable(flowable)

    def afterPage(self):
        self.canv.saveState()
        w, h = A4

        # Header bar
        self.canv.setFillColor(BLUE)
        self.canv.rect(0, h - 1.2*cm, w, 1.2*cm, fill=1, stroke=0)
        self.canv.setFillColor(WHITE)
        self.canv.setFont("Helvetica-Bold", 9)
        self.canv.drawString(1.5*cm, h - 0.8*cm, "SANCHAY — Inventory & Asset Management System")
        self.canv.setFont("Helvetica", 9)
        self.canv.drawRightString(w - 1.5*cm, h - 0.8*cm, "User Manual v1.0.0")

        # Footer line
        self.canv.setStrokeColor(BLUE_MID)
        self.canv.setLineWidth(0.5)
        self.canv.line(1.5*cm, 1.2*cm, w - 1.5*cm, 1.2*cm)
        self.canv.setFillColor(GREY)
        self.canv.setFont("Helvetica", 8)
        self.canv.drawString(1.5*cm, 0.7*cm, self.chapter)
        self.canv.drawRightString(w - 1.5*cm, 0.7*cm,
                                  f"Page {self.canv.getPageNumber()}")
        self.canv.restoreState()


# ── Styles ───────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    s = {}

    s["cover_title"] = ParagraphStyle("cover_title",
        fontSize=36, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=6)
    s["cover_sub"] = ParagraphStyle("cover_sub",
        fontSize=16, fontName="Helvetica",
        textColor=BLUE_MID, alignment=TA_CENTER, spaceAfter=4)
    s["cover_ver"] = ParagraphStyle("cover_ver",
        fontSize=12, fontName="Helvetica",
        textColor=BLUE_MID, alignment=TA_CENTER)

    s["h1"] = ParagraphStyle("h1",
        fontSize=20, fontName="Helvetica-Bold",
        textColor=BLUE, spaceBefore=18, spaceAfter=6,
        borderPad=0, leading=24)
    s["h2"] = ParagraphStyle("h2",
        fontSize=14, fontName="Helvetica-Bold",
        textColor=DARK, spaceBefore=12, spaceAfter=4, leading=18)
    s["h3"] = ParagraphStyle("h3",
        fontSize=11, fontName="Helvetica-Bold",
        textColor=DARK, spaceBefore=8, spaceAfter=3, leading=14)
    s["body"] = ParagraphStyle("body",
        fontSize=10, fontName="Helvetica",
        textColor=DARK, spaceAfter=5, leading=15, alignment=TA_JUSTIFY)
    s["note"] = ParagraphStyle("note",
        fontSize=9, fontName="Helvetica-Oblique",
        textColor=GREY, spaceAfter=4, leading=13)
    s["bullet"] = ParagraphStyle("bullet",
        fontSize=10, fontName="Helvetica",
        textColor=DARK, spaceAfter=3, leading=14,
        leftIndent=16, bulletIndent=6)
    s["code"] = ParagraphStyle("code",
        fontSize=9, fontName="Courier",
        textColor=DARK, backColor=GREY_LIGHT,
        spaceAfter=4, leading=13,
        leftIndent=12, rightIndent=12,
        borderPad=4)
    s["toc_h1"] = ParagraphStyle("toc_h1",
        fontSize=11, fontName="Helvetica-Bold",
        textColor=BLUE, spaceBefore=4, spaceAfter=2, leading=14)
    s["toc_h2"] = ParagraphStyle("toc_h2",
        fontSize=10, fontName="Helvetica",
        textColor=DARK, spaceBefore=1, spaceAfter=1, leading=13,
        leftIndent=14)
    return s


# ── Helpers ──────────────────────────────────────────────────────────────────
def h1(text, s, chapter=""):
    class _Marker(Paragraph):
        pass
    p = _Marker(text, s["h1"])
    p._chapter_marker = chapter or text
    return [
        PageBreak(),
        HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=4),
        p,
        Spacer(1, 3*mm),
    ]

def h2(text, s):
    return [Paragraph(text, s["h2"])]

def h3(text, s):
    return [Paragraph(text, s["h3"])]

def body(text, s):
    return Paragraph(text, s["body"])

def note(text, s):
    return Paragraph(f"<i>💡 {text}</i>", s["note"])

def bullet(items, s):
    return [Paragraph(f"• {i}", s["bullet"]) for i in items]

def tip_box(title, text, s, color=BLUE_LIGHT, border=BLUE):
    data = [[Paragraph(f"<b>{title}</b>", s["h3"]),
             Paragraph(text, s["body"])]]
    t = Table(data, colWidths=["25%", "75%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("BOX",        (0,0), (-1,-1), 1, border),
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    return [t, Spacer(1, 4*mm)]

def role_table(s):
    header = ["Role", "Assets", "Issue/Return", "Reports", "Users", "Backup"]
    rows = [
        ["Admin",    "✔", "✔", "✔", "✔", "✔"],
        ["Manager",  "✔", "✔", "✔", "✗", "✗"],
        ["Operator", "✗", "✔", "✗", "✗", "✗"],
        ["Viewer",   "✗", "✗", "✔", "✗", "✗"],
    ]
    all_rows = [header] + rows
    col_w = [3.5*cm, 2*cm, 2.8*cm, 2.5*cm, 2*cm, 2.5*cm]
    t = Table(all_rows, colWidths=col_w)
    style = [
        ("BACKGROUND",  (0,0), (-1,0),  BLUE),
        ("TEXTCOLOR",   (0,0), (-1,0),  WHITE),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("ALIGN",       (0,0), (0,-1),  "LEFT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, GREY_LIGHT]),
        ("BOX",         (0,0), (-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",   (0,0), (-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 7),
    ]
    for r in range(1, len(all_rows)):
        for c in range(1, len(header)):
            val = all_rows[r][c]
            clr = GREEN if val == "✔" else RED
            style.append(("TEXTCOLOR", (c,r), (c,r), clr))
            style.append(("FONTNAME",  (c,r), (c,r), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 4*mm)]

def shortcut_table(s):
    header = ["Shortcut", "Action"]
    rows = [
        ["Ctrl + N",   "New record (on any list page)"],
        ["F5",         "Refresh current list"],
        ["Ctrl + F",   "Focus the search bar"],
        ["Del",        "Delete selected row"],
        ["Escape",     "Cancel / close dialog"],
    ]
    t = Table([header]+rows, colWidths=[4*cm, 12*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
        ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_LIGHT]),
        ("BOX",          (0,0),(-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",    (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("FONTNAME",     (0,1),(0,-1),  "Courier-Bold"),
    ]))
    return [t, Spacer(1, 4*mm)]

def report_table(s):
    header = ["Report", "Description", "Export"]
    rows = [
        ["Asset Inventory",    "All assets with status, condition, price, warranty", "PDF · Excel · CSV"],
        ["Department Assets",  "Assets grouped by department with totals",           "PDF · Excel · CSV"],
        ["Issue History",      "All issue records with date-range filter",           "PDF · Excel · CSV"],
        ["Return History",     "All returns with condition on return",               "PDF · Excel · CSV"],
        ["Overdue Assets",     "Active issues past expected return date",            "PDF · Excel · CSV"],
        ["Person Holdings",    "Active asset holdings per person",                   "PDF · Excel · CSV"],
    ]
    t = Table([header]+rows, colWidths=[4*cm, 9.5*cm, 3*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",    (0,0),(-1,0), WHITE),
        ("FONTNAME",     (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_LIGHT]),
        ("BOX",          (0,0),(-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",    (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
    ]))
    return [t, Spacer(1, 4*mm)]


# ── Cover page ───────────────────────────────────────────────────────────────
def cover_page(s):
    w, h = A4
    story = []

    # Blue banner block built as a table
    cover_data = [[
        Paragraph("SANCHAY", s["cover_title"]),
    ],[
        Paragraph("सञ्चय  ·  Inventory &amp; Asset Management System", s["cover_sub"]),
    ],[
        Paragraph("User Manual  ·  Version 1.0.0", s["cover_ver"]),
    ]]
    cover_t = Table(cover_data, colWidths=[16*cm])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(Spacer(1, 3*cm))
    story.append(cover_t)
    story.append(Spacer(1, 1.5*cm))

    # Tagline
    story.append(Paragraph(
        "A professional, offline-first desktop application for managing<br/>"
        "organisational assets — from laptops to lab equipment.",
        ParagraphStyle("cov_body", fontSize=12, fontName="Helvetica",
                       textColor=GREY, alignment=TA_CENTER, leading=18)
    ))
    story.append(Spacer(1, 2*cm))

    # Feature pills as a 2-col table
    feats = [
        ("Multi-org & Department Support",  "Role-Based Access Control"),
        ("Asset Registration & Tracking",   "PDF · Excel · CSV Reports"),
        ("Issue / Return Workflow",         "Backup & Restore"),
        ("Audit Trail for Every Action",    "Keyboard Shortcuts & Search"),
    ]
    feat_rows = []
    for l, r in feats:
        feat_rows.append([
            Paragraph(f"✔  {l}", ParagraphStyle("fp", fontSize=10,
                fontName="Helvetica", textColor=DARK, leading=14)),
            Paragraph(f"✔  {r}", ParagraphStyle("fp2", fontSize=10,
                fontName="Helvetica", textColor=DARK, leading=14)),
        ])
    ft = Table(feat_rows, colWidths=[8*cm, 8*cm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE_LIGHT),
        ("BOX",           (0,0),(-1,-1), 1, BLUE_MID),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(ft)
    story.append(Spacer(1, 2*cm))

    # Publisher info
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE_MID))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "Published by <b>Sanchay Systems</b>  ·  2026  ·  Proprietary &amp; Confidential",
        ParagraphStyle("pub", fontSize=9, fontName="Helvetica",
                       textColor=GREY, alignment=TA_CENTER)
    ))
    story.append(PageBreak())
    return story


# ── Main build ───────────────────────────────────────────────────────────────
def build():
    s = make_styles()
    doc = SanchayDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm,  bottomMargin=1.8*cm,
        title="Sanchay User Manual",
        author="Sanchay Systems",
        subject="Inventory & Asset Management System",
    )
    story = []

    # ── Cover ────────────────────────────────────────────────────────────────
    story += cover_page(s)

    # ── 1. Introduction ──────────────────────────────────────────────────────
    story += h1("1. Introduction", s, "1. Introduction")
    story.append(body(
        "<b>Sanchay</b> (सञ्चय, meaning <i>collection</i> or <i>accumulation</i>) is a "
        "professional, offline-first desktop application for tracking and managing "
        "organisational assets. It runs entirely on your local machine — no internet "
        "connection or cloud account required.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("1.1  Key Features", s)
    story += bullet([
        "Multi-organisation and department management",
        "Asset registration with categories, serial numbers, warranty tracking",
        "Issue and return workflow with overdue detection",
        "Employee, Student, Contractor, and Candidate management",
        "Role-based access control (Admin / Manager / Operator / Viewer)",
        "PDF, Excel, and CSV reports (6 report types)",
        "Backup and Restore with WAL-safe SQLite copy",
        "Immutable audit trail for every action",
        "Full input validation and security hardening (bcrypt, SQL-injection prevention)",
    ], s)
    story.append(Spacer(1, 3*mm))
    story += h2("1.2  System Requirements", s)
    req = [
        ["Component", "Minimum"],
        ["Operating System", "Windows 10 / 11 (64-bit)"],
        ["Processor",        "Intel Core i3 or equivalent"],
        ["RAM",              "4 GB"],
        ["Disk Space",       "500 MB free (for application + data)"],
        ["Display",          "1280 × 768 or higher resolution"],
    ]
    rt = Table(req, colWidths=[5*cm, 11*cm])
    rt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_LIGHT]),
        ("BOX",           (0,0),(-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    story.append(rt)
    story.append(Spacer(1, 4*mm))

    # ── 2. Installation ──────────────────────────────────────────────────────
    story += h1("2. Installation", s, "2. Installation")
    story.append(body(
        "Sanchay is distributed as a single installer file: "
        "<b>SanchaySetup-1.0.0.exe</b>. No Python or additional runtime is required.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("2.1  Running the Installer", s)
    story += bullet([
        "Double-click <b>SanchaySetup-1.0.0.exe</b>.",
        "If Windows SmartScreen appears, click <b>More info → Run anyway</b>.",
        "Accept the license agreement and click <b>Next</b>.",
        "Choose the installation folder (default: <i>C:\\Program Files\\Sanchay</i>) and click <b>Install</b>.",
        "Once complete, tick <b>Launch Sanchay now</b> and click <b>Finish</b>.",
    ], s)
    story.append(Spacer(1, 3*mm))
    story += h2("2.2  What Gets Installed", s)
    story += bullet([
        "<b>C:\\Program Files\\Sanchay\\Sanchay.exe</b> — main application",
        "<b>C:\\Program Files\\Sanchay\\_internal\\</b> — bundled runtime and resources",
        "Start Menu shortcut: <i>Sanchay → Sanchay</i>",
        "Desktop shortcut: <i>Sanchay</i>",
        "Add/Remove Programs entry for clean uninstallation",
    ], s)
    story.append(Spacer(1, 3*mm))
    story += h2("2.3  Data Location", s)
    story.append(body(
        "All user data (database, logs, backups, exports) is stored in the "
        "<b>same folder as Sanchay.exe</b>. This means your data is portable — "
        "copy the entire Sanchay folder to another machine and all your records come with it.", s))
    story += bullet([
        "<i>data\\sanchay.db</i> — SQLite database (all your records)",
        "<i>logs\\sanchay.log</i> — rotating application log",
        "<i>backups\\</i> — database backup files",
        "<i>exports\\</i> — generated PDF / Excel / CSV reports",
    ], s)
    story += tip_box("💡 Tip", "Before uninstalling, always take a manual backup via "
        "Settings → Backup so you don't lose data.", s)

    # ── 3. First Run ─────────────────────────────────────────────────────────
    story += h1("3. First Run — Setup Wizard", s, "3. First Run — Setup Wizard")
    story.append(body(
        "On the very first launch, Sanchay runs a <b>Setup Wizard</b> to create the "
        "administrator account and your first organisation.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("3.1  Setup Steps", s)
    steps = [
        ["Step 1", "Welcome screen — click Start Setup."],
        ["Step 2", "Enter Admin credentials: username, full name, email, and a strong password."],
        ["Step 3", "Enter your first Organisation name and a short code (e.g. ACME / ACM)."],
        ["Step 4", "Review the summary and click Finish."],
    ]
    st = Table(steps, colWidths=[2.5*cm, 14*cm])
    st.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), BLUE),
        ("TEXTCOLOR",     (0,0),(0,-1), WHITE),
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(1,0),(-1,-1),[WHITE, GREY_LIGHT]),
        ("BOX",           (0,0),(-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN",         (0,0),(0,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(st)
    story.append(Spacer(1, 4*mm))
    story += tip_box("⚠ Note",
        "The Setup Wizard runs only once. After completion, you will always see "
        "the Login screen. If you forget your admin password, contact your system administrator.", s,
        color=colors.HexColor("#FFFBEB"), border=AMBER)

    # ── 4. Logging In ────────────────────────────────────────────────────────
    story += h1("4. Logging In", s, "4. Logging In")
    story.append(body(
        "After the first-run setup (or on every subsequent launch), Sanchay shows the "
        "<b>Login screen</b>.", s))
    story += bullet([
        "Enter your <b>Username</b> and <b>Password</b>.",
        "Click <b>Login</b> or press <b>Enter</b>.",
        "The application opens to the <b>Dashboard</b>.",
    ], s)
    story.append(Spacer(1, 3*mm))
    story += tip_box("🔒 Security",
        "Passwords are hashed with bcrypt (12 rounds). Sessions expire after 8 hours "
        "of inactivity. All failed logins are recorded in the audit log.", s)

    # ── 5. Dashboard ─────────────────────────────────────────────────────────
    story += h1("5. Dashboard", s, "5. Dashboard")
    story.append(body(
        "The Dashboard is the home screen, visible immediately after login. It gives a "
        "live snapshot of your asset inventory.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("5.1  Stat Cards", s)
    story += bullet([
        "<b>Total Assets</b> — count of all registered assets",
        "<b>Available</b> — assets not currently issued",
        "<b>Issued</b> — assets currently with a person",
        "<b>Overdue</b> — issued assets past their return date (highlighted in red)",
        "<b>Under Maintenance</b> — assets marked for service",
    ], s)
    story += tip_box("💡 Tip",
        "Click any stat card to jump directly to the filtered asset list for that status.", s)
    story += h2("5.2  Recent Activity", s)
    story.append(body(
        "The Recent Activity panel shows the last 10 events — new assets, issues, returns, "
        "and logins — with timestamps and the user who performed them.", s))

    # ── 6. Organisations ─────────────────────────────────────────────────────
    story += h1("6. Organisations & Departments", s, "6. Organisations & Departments")
    story.append(body(
        "Sanchay supports multiple organisations under one installation, each with its "
        "own departments. Navigate via <b>Sidebar → Organisation</b>.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("6.1  Managing Organisations", s)
    story += bullet([
        "Click <b>+ New Organisation</b> (or <b>Ctrl+N</b>) to add one.",
        "Fill in: Name, Code (unique short identifier, e.g. ACME), Type, and Address.",
        "Click the <b>edit icon</b> on any row to update details.",
        "Deactivate an organisation to hide it from dropdowns without deleting its data.",
    ], s)
    story += h2("6.2  Managing Departments", s)
    story += bullet([
        "Navigate to <b>Sidebar → Departments</b>.",
        "Each department belongs to an organisation and can have a parent department "
        "(for hierarchical structures like divisions → teams).",
        "Departments appear in asset and person forms for assignment.",
    ], s)

    # ── 7. People ────────────────────────────────────────────────────────────
    story += h1("7. Managing People", s, "7. Managing People")
    story.append(body(
        "The People module manages everyone who can be assigned an asset. "
        "Navigate via <b>Sidebar → People</b>.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("7.1  Person Types", s)
    story += bullet([
        "<b>Employee</b> — permanent or contractual staff",
        "<b>Student</b> — for educational institutions",
        "<b>Contractor</b> — third-party vendors or consultants",
        "<b>Candidate</b> — interview or temporary access",
    ], s)
    story += h2("7.2  Adding a Person", s)
    story += bullet([
        "Click <b>+ New Person</b> (or <b>Ctrl+N</b>).",
        "Fill in the three tabs: <b>Basic Info</b> (name, email, phone), "
        "<b>Assignment</b> (department, type, employee ID), and <b>Notes</b>.",
        "Click <b>Save</b>.",
    ], s)
    story += h2("7.3  Search & Filter", s)
    story += bullet([
        "Use the <b>Search bar</b> (Ctrl+F) to find by name, email, or ID.",
        "Use the <b>Type</b> tab (Employee / Student / Contractor / Candidate) to filter.",
        "Use the <b>Status</b> filter to show Active or Inactive persons.",
    ], s)

    # ── 8. Asset Categories ──────────────────────────────────────────────────
    story += h1("8. Asset Categories", s, "8. Asset Categories")
    story.append(body(
        "Categories organise your assets into a hierarchy (e.g. Electronics → Laptops). "
        "Navigate via <b>Sidebar → Categories</b>.", s))
    story += bullet([
        "Click <b>+ New Category</b> to create one.",
        "Optionally assign a <b>Parent Category</b> for nested hierarchies.",
        "Set a <b>Depreciation Rate</b> (%) for financial tracking.",
        "Categories appear in the Asset form and all reports.",
    ], s)

    # ── 9. Assets ────────────────────────────────────────────────────────────
    story += h1("9. Assets", s, "9. Assets")
    story.append(body(
        "The Assets module is the core of Sanchay. Every item you want to track — "
        "laptops, projectors, vehicles, tools — is an asset. Navigate via <b>Sidebar → Assets</b>.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("9.1  Registering an Asset", s)
    story.append(body("Click <b>+ New Asset</b> (or <b>Ctrl+N</b>). The form has three tabs:", s))
    story += bullet([
        "<b>Identity</b> — Name, Asset Code (auto-generated or manual), Category, "
        "Organisation, Department, Serial Number, Model, Manufacturer, Location.",
        "<b>Specs</b> — Description, condition (New / Good / Fair / Poor / Damaged), "
        "status (Available / Issued / Maintenance / Retired / Lost).",
        "<b>Financial</b> — Purchase date, Purchase price, Warranty expiry date, "
        "Depreciation rate.",
    ], s)
    story += h2("9.2  Asset List", s)
    story += bullet([
        "Use the <b>Search bar</b> to find assets by name, code, or serial number.",
        "Filter by <b>Status</b>, <b>Category</b>, or <b>Department</b> using the dropdowns.",
        "The <b>stat pills</b> at the top show counts per status at a glance.",
        "Click any row to open the <b>Asset Detail</b> dialog — full metadata, "
        "colour-coded warranty status, and complete issue history.",
    ], s)
    story += h2("9.3  Asset Statuses", s)
    stat_rows = [
        ["Available",    "Ready to be issued"],
        ["Issued",       "Currently with a person"],
        ["Maintenance",  "Undergoing repair or service"],
        ["Retired",      "Decommissioned, no longer in use"],
        ["Lost",         "Reported missing"],
    ]
    at = Table([["Status","Meaning"]]+stat_rows, colWidths=[4*cm, 12*cm])
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), BLUE),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_LIGHT]),
        ("BOX",           (0,0),(-1,-1), 0.5, BLUE_MID),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, BLUE_MID),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
    ]))
    story.append(at)
    story.append(Spacer(1, 4*mm))

    # ── 10. Transactions ─────────────────────────────────────────────────────
    story += h1("10. Issue & Return Assets", s, "10. Issue & Return Assets")
    story.append(body(
        "The transaction workflow records who has which asset and when it must be returned. "
        "Navigate via <b>Sidebar → Issue Asset</b> or <b>Return Asset</b>.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("10.1  Issuing an Asset", s)
    story += bullet([
        "Go to <b>Sidebar → Issue Asset</b>.",
        "Left panel: search and select the asset to issue (only Available assets appear).",
        "Right panel: search and select the person receiving it.",
        "Set the <b>Expected Return Date</b> (optional but recommended).",
        "Add any <b>Remarks</b> and click <b>Issue Asset</b>.",
        "The asset status changes to <b>Issued</b> automatically.",
    ], s)
    story += h2("10.2  Returning an Asset", s)
    story += bullet([
        "Go to <b>Sidebar → Return Asset</b>.",
        "Search and select the active issue record.",
        "Set the <b>Return Condition</b> (Good / Fair / Poor / Damaged).",
        "Add remarks and click <b>Return Asset</b>.",
        "The asset status reverts to <b>Available</b>.",
    ], s)
    story += h2("10.3  Transaction History", s)
    story.append(body(
        "Navigate to <b>Sidebar → Transactions</b> to see the full history with four tabs:", s))
    story += bullet([
        "<b>Active</b> — currently issued assets",
        "<b>Overdue</b> — issues past the expected return date",
        "<b>All Issues</b> — complete issue log with date filter",
        "<b>Returns</b> — complete return log",
    ], s)
    story += tip_box("⚡ Quick Return",
        "On the Active or Overdue tabs, click the <b>Return</b> button on any row "
        "to return an asset inline — without navigating to the Return page.", s)

    # ── 11. Reports ──────────────────────────────────────────────────────────
    story += h1("11. Reports", s, "11. Reports")
    story.append(body(
        "Navigate to <b>Sidebar → Reports</b>. Sanchay offers six built-in report types, "
        "all exportable to PDF, Excel, and CSV.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("11.1  Available Reports", s)
    story += report_table(s)
    story += h2("11.2  Generating a Report", s)
    story += bullet([
        "Select a <b>Report Type</b> from the card grid.",
        "Use the <b>filter bar</b> to narrow by date range, department, or status.",
        "The <b>preview table</b> updates live as you change filters.",
        "Click <b>Export PDF</b>, <b>Export Excel</b>, or <b>Export CSV</b>.",
        "The file saves to the <b>exports\\</b> folder and the folder opens automatically.",
    ], s)

    # ── 12. Settings ─────────────────────────────────────────────────────────
    story += h1("12. Settings", s, "12. Settings")
    story.append(body(
        "Navigate to <b>Sidebar → Settings</b>. The Settings panel has three tabs.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("12.1  General Settings", s)
    story += bullet([
        "<b>Asset Code Prefix</b> — prefix for auto-generated asset codes (e.g. AST-).",
        "<b>Organisation Name</b> — displayed in report headers.",
        "<b>Theme</b> — Light or Dark (planned for future release).",
        "<b>Auto-Backup</b> — enable and set interval (daily).",
    ], s)
    story += h2("12.2  Audit Log", s)
    story.append(body(
        "The Audit Log tab shows a searchable, read-only record of every action "
        "performed in the system — who did what, and when. Entries cannot be edited or deleted.", s))
    story += h2("12.3  About", s)
    story.append(body(
        "Displays application version, build info, and database statistics (table counts, DB size).", s))

    # ── 13. User Management ──────────────────────────────────────────────────
    story += h1("13. User Management", s, "13. User Management")
    story.append(body(
        "<b>Admin only.</b> Navigate to <b>Sidebar → Users</b>.", s))
    story += bullet([
        "Click <b>+ New User</b> to create an account.",
        "Set the <b>Role</b> (Admin / Manager / Operator / Viewer).",
        "Use the <b>toggle</b> to activate or deactivate a user.",
        "Click <b>Change Password</b> to reset a user's password.",
        "Your own account cannot be deactivated.",
    ], s)
    story.append(Spacer(1, 3*mm))
    story += h2("13.1  Roles & Permissions", s)
    story += role_table(s)

    # ── 14. Backup & Restore ─────────────────────────────────────────────────
    story += h1("14. Backup & Restore", s, "14. Backup & Restore")
    story.append(body(
        "<b>Admin only.</b> Navigate to <b>Sidebar → Backup</b>.", s))
    story.append(Spacer(1, 3*mm))
    story += h2("14.1  Creating a Backup", s)
    story += bullet([
        "Click <b>Create Backup Now</b>.",
        "A timestamped <i>.db</i> file is saved to the <b>backups\\</b> folder.",
        "The backup list below shows all available backups with size and date.",
    ], s)
    story += h2("14.2  Restoring a Backup", s)
    story += bullet([
        "Select a backup from the list.",
        "Click <b>Restore</b>. A confirmation dialog will appear.",
        "Type CONFIRM and click OK.",
        "The application restarts with the restored database.",
    ], s)
    story += tip_box("⚠ Warning",
        "Restoring overwrites your current database. Always create a fresh backup "
        "before restoring an older one.", s,
        color=colors.HexColor("#FFFBEB"), border=AMBER)
    story += h2("14.3  Deleting a Backup", s)
    story += bullet([
        "Select a backup from the list and click <b>Delete</b>.",
        "Deleted backups cannot be recovered.",
    ], s)

    # ── 15. Keyboard Shortcuts ────────────────────────────────────────────────
    story += h1("15. Keyboard Shortcuts", s, "15. Keyboard Shortcuts")
    story += shortcut_table(s)

    # ── 16. Troubleshooting ──────────────────────────────────────────────────
    story += h1("16. Troubleshooting", s, "16. Troubleshooting")
    story.append(Spacer(1, 2*mm))

    issues = [
        ("App does not launch",
         "Check the logs\\sanchay.log file next to Sanchay.exe for error details. "
         "Ensure you have write permission to the installation folder."),
        ("Setup Wizard does not appear",
         "The wizard runs only on first launch (when no database exists). "
         "If data\\sanchay.db exists, the login screen will show instead."),
        ("Login fails with correct credentials",
         "Passwords are case-sensitive. If you have forgotten the admin password, "
         "restore a backup or contact your administrator."),
        ("Reports show no data",
         "Ensure the filter date range covers the period you expect. "
         "Clear all filters (click Reset) and try again."),
        ("Export folder does not open",
         "The exports\\ folder is next to Sanchay.exe. Navigate there manually in File Explorer."),
        ("Database is corrupt after a crash",
         "Use Backup → Restore to load the most recent clean backup. "
         "Backups are stored in the backups\\ folder next to Sanchay.exe."),
        ("Overdue count seems wrong",
         "Overdue status is synced on startup. Restart the application to trigger a fresh sync."),
    ]
    for title, desc in issues:
        story += [KeepTogether([
            Paragraph(f"<b>Problem:</b> {title}", s["h3"]),
            Paragraph(f"<b>Solution:</b> {desc}", s["body"]),
            Spacer(1, 4*mm),
        ])]

    # ── 17. Uninstallation ────────────────────────────────────────────────────
    story += h1("17. Uninstalling Sanchay", s, "17. Uninstalling Sanchay")
    story += bullet([
        "Open <b>Windows Settings → Apps → Installed Apps</b>.",
        "Search for <b>Sanchay</b> and click <b>Uninstall</b>.",
        "The uninstaller asks: <i>Do you want to keep your data?</i>",
        "Click <b>Yes</b> to keep database, backups, and exports.",
        "Click <b>No</b> to remove everything.",
    ], s)
    story += tip_box("💡 Tip",
        "Always choose Yes to keep data and take a manual backup first. "
        "You can delete the leftover folder manually later if needed.", s)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc.build(story)
    print(f"\n✅  PDF generated: {OUTPUT.resolve()}")
    print(f"   Size: {OUTPUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
