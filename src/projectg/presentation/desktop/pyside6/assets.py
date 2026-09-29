"""Native desktop presentation: assets."""
import re
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QBrush, QPen
from projectg.presentation.desktop.pyside6.theme import COLORS


def _find_asset_dir() -> Path | None:
    # 1. Check relative to this source file (workspace_root/assets/genshin-impact)
    base = Path(__file__).resolve().parents[5] / "assets" / "genshin-impact"
    if base.is_dir():
        return base
    # 2. Check current working directory
    base = Path.cwd() / "assets" / "genshin-impact"
    if base.is_dir():
        return base
    # 3. Check PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "assets" / "genshin-impact"
        if base.is_dir():
            return base
    return None


ASSET_DIR = _find_asset_dir()


def _slugify_key(key: str) -> str:
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', str(key or ''))
    s = re.sub(r'[\s_]+', '-', s)
    return s.strip('-').lower()


def get_character_pixmap(character_key: str, size: int = 64, *, device_pixel_ratio: float = 1.0) -> QPixmap:
    size = max(1, round(size * device_pixel_ratio))
    if ASSET_DIR and character_key:
        chars_dir = ASSET_DIR / "characters"
        slug = _slugify_key(character_key)
        candidates = [
            chars_dir / f"{slug}.webp",
            chars_dir / f"{character_key.lower()}.webp",
            chars_dir / f"{slug.replace('-', '')}.webp",
        ]
        for p in candidates:
            if p.is_file():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    pix = pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    pix.setDevicePixelRatio(device_pixel_ratio)
                    return pix

    # Fallback monogram with celestial styling
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(COLORS["elevated"])))
    painter.setPen(QPen(QColor(COLORS["accent"]), 1.5))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 8, 8)
    initials = (character_key[:2] if len(character_key) >= 2 else (character_key or "?")).upper()
    font = QFont("Segoe UI", max(8, int(size * 0.35)), QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(COLORS["accent_hover"]))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    pix.setDevicePixelRatio(device_pixel_ratio)
    return pix


def get_weapon_pixmap(weapon_key: str, size: int = 48) -> QPixmap:
    if ASSET_DIR and weapon_key:
        weapons_dir = ASSET_DIR / "weapons"
        slug = _slugify_key(weapon_key)
        candidates = [
            weapons_dir / f"{slug}.webp",
            weapons_dir / f"{weapon_key.lower()}.webp",
            weapons_dir / f"{slug.replace('-', '')}.webp",
        ]
        for p in candidates:
            if p.is_file():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(COLORS["surface"])))
    painter.setPen(QPen(QColor(COLORS["secondary"]), 1))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)
    painter.setPen(QColor(COLORS["secondary"]))
    font = QFont("Segoe UI", max(8, int(size * 0.35)), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return pix


