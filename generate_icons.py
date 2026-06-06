"""
Sanchay Icon Generator
========================
Generates the full icon set for Windows (.ico) and Linux (.png files).
Option 1: Bold white "S" on Sanchay blue (#2563EB) rounded square.

Run once. Re-run anytime you want to change the icon.
Output: app/resources/icons/
"""

import sys, struct, io
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath
from PySide6.QtCore import Qt, QRect, QRectF

app = QApplication(sys.argv)

# ── Icon design ───────────────────────────────────────────────────────────────
BG_COLOR   = "#2563EB"   # Sanchay brand blue
TEXT_COLOR = "#FFFFFF"   # White S
FONT_FACE  = "Segoe UI"  # Falls back to system sans on Linux


def make_icon_pixmap(size: int) -> QPixmap:
    """
    Draw a blue rounded-square with a bold white 'S'.
    Scales cleanly from 16 px (taskbar) to 512 px (hi-DPI Linux).
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Background — rounded square
    radius = max(2, size // 7)
    p.setBrush(QColor(BG_COLOR))
    p.setPen(Qt.NoPen)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    p.fillPath(path, QColor(BG_COLOR))

    # Letter "S" — scales with icon size
    p.setPen(QColor(TEXT_COLOR))
    font_size = max(6, int(size * 0.60))
    font = QFont(FONT_FACE, font_size, QFont.Bold)
    p.setFont(font)
    p.drawText(QRect(0, 0, size, size), Qt.AlignCenter, "S")

    p.end()
    return pix


# ── Output directory ──────────────────────────────────────────────────────────
from pathlib import Path
OUT = Path("app/resources/icons")
OUT.mkdir(parents=True, exist_ok=True)


# ── Linux PNG set ─────────────────────────────────────────────────────────────
LINUX_SIZES = [16, 32, 48, 64, 128, 256, 512]

print("Generating Linux PNG set...")
for sz in LINUX_SIZES:
    pix = make_icon_pixmap(sz)
    path = OUT / f"sanchay_{sz}.png"
    pix.save(str(path))
    print(f"  [OK] {path.name}  ({sz}x{sz})")


# ── Windows ICO ───────────────────────────────────────────────────────────────
# ICO format: header + directory + image data (PNG compressed for sizes >= 16)
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]

print("\nGenerating Windows ICO...")

def pixmap_to_png_bytes(pix: QPixmap) -> bytes:
    """Export a QPixmap to raw PNG bytes via QBuffer."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    pix.save(buf, "PNG")
    buf.close()
    return bytes(buf.data())

# Collect all PNG chunks
chunks: list[bytes] = []
for sz in ICO_SIZES:
    pix = make_icon_pixmap(sz)
    chunks.append(pixmap_to_png_bytes(pix))

# Build ICO binary manually
# ICO header: 6 bytes
# ICONDIRENTRY per image: 16 bytes each
# Then raw image data

num = len(ICO_SIZES)
header = struct.pack("<HHH", 0, 1, num)   # reserved=0, type=1 (ICO), count

# Each ICONDIRENTRY (16 bytes):
#   BYTE  bWidth       (0 = 256)
#   BYTE  bHeight      (0 = 256)
#   BYTE  bColorCount
#   BYTE  bReserved
#   WORD  wPlanes
#   WORD  wBitCount
#   DWORD dwBytesInRes
#   DWORD dwImageOffset

HEADER_SIZE  = 6
DIR_SIZE     = 16 * num
data_offset  = HEADER_SIZE + DIR_SIZE

entries = b""
current_offset = data_offset
for sz, chunk in zip(ICO_SIZES, chunks):
    w = 0 if sz == 256 else sz
    h = 0 if sz == 256 else sz
    entries += struct.pack(
        "<BBBBHHII",
        w, h,          # width, height (0 = 256)
        0,             # color count (0 = no palette)
        0,             # reserved
        1,             # planes
        32,            # bit count
        len(chunk),    # size of image data
        current_offset,
    )
    current_offset += len(chunk)

ico_data = header + entries + b"".join(chunks)
ico_path = OUT / "sanchay.ico"
ico_path.write_bytes(ico_data)
print(f"  [OK] {ico_path.name}  ({len(ico_data)//1024} KB, {num} sizes)")


# ── Verify ICO ────────────────────────────────────────────────────────────────
try:
    from PIL import Image
    img = Image.open(str(ico_path))
    print(f"  [OK] ICO verified via Pillow — sizes: {img.info.get('sizes', 'n/a')}")
except ImportError:
    pass   # Pillow not installed; ICO still valid


# ── Linux .desktop file ───────────────────────────────────────────────────────
from app.config import config
desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={config.APP_NAME}
GenericName=Inventory & Asset Manager
Comment={config.APP_TAGLINE}
Exec=sanchay
Icon=sanchay
Terminal=false
Categories=Office;Finance;
Keywords=inventory;assets;management;tracking;
StartupWMClass=sanchay
"""

desktop_path = OUT / "sanchay.desktop"
desktop_path.write_text(desktop_content, encoding="utf-8")
print(f"\n  [OK] {desktop_path.name}  (Linux launcher)")


# ── Summary ───────────────────────────────────────────────────────────────────
print()
print("=" * 52)
print("  Icon set generated successfully!")
print()
print("  Windows")
print(f"    {ico_path}  ← use in PyInstaller --icon")
print()
print("  Linux (place each in hicolor theme dirs)")
for sz in LINUX_SIZES:
    p = OUT / f"sanchay_{sz}.png"
    print(f"    {p.name}  → hicolor/{sz}x{sz}/apps/sanchay.png")
print(f"    {desktop_path.name}  → /usr/share/applications/")
print("=" * 52)
