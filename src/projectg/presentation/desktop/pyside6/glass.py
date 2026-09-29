"""Background canvas: design.ms §26 dark blue-gray + radial glows + subtle starfield.

§26 rules:
  • Not flat #000 — use dark blue-gray
  • Subtle radial light (low-frequency)
  • Faint astrolabe motif as compositional anchor (not competing with UI)
  • Noise must be near-invisible

Glass panel widget (SmokedGlassFrame) follows §5:
  • background rgba(20,27,39,0.68)  [Qt opaque approximation: linear gradient]
  • border 1px rgba(255,255,255,0.08)
  • radius 15px (radius-md 14px, rounded to 15 for hero card)
  • decorative corner marks — thin fantasy ornament, §2.3 detail/modal
"""
from math import sin

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget, QFrame


class GlassCanvas(QWidget):
    """Main window background — §26 dark canvas with subtle radial atmosphere."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0
        self._twinkle = QTimer(self)
        self._twinkle.timeout.connect(self._advance_stars)
        self._twinkle.start(90)

    def _advance_stars(self):
        if self.isVisible():
            self._phase = (self._phase + 1) % 1000000
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()

        # §26 — dark blue-gray base, NOT flat black
        # bg-canvas #0C1018 → bg-elevated #121824 diagonal gradient
        base = QLinearGradient(0, 0, width, height)
        base.setColorAt(0.0, QColor('#0F1520'))   # slightly lighter corner
        base.setColorAt(0.5, QColor('#0C1018'))   # bg-canvas
        base.setColorAt(1.0, QColor('#101620'))   # warm dark edge
        painter.fillRect(self.rect(), base)

        # §26 — subtle radial lights (low-frequency, near-invisible)
        # Three glows: warm gold top-right, teal bottom-left, muted blue bottom
        for x, y, radius, color, alpha in (
            (0.88, -0.15, 0.72, '#D9C28B', 22),   # gold-soft top-right
            (-0.12, 0.82, 0.70, '#65D5C5', 16),   # Anemo teal bottom-left
            (0.55, 1.15, 0.58, '#2A4060', 28),    # deep blue bottom center
        ):
            glow = QRadialGradient(QPointF(width * x, height * y),
                                   max(width, height) * radius)
            tint = QColor(color)
            tint.setAlpha(alpha)
            glow.setColorAt(0, tint)
            tint.setAlpha(0)
            glow.setColorAt(1, tint)
            painter.fillRect(self.rect(), glow)

        # §2.3 / §27 — faint astrolabe motif as compositional anchor
        # Appears top-right quadrant; low opacity so it never competes with UI
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(217, 194, 139, 18), 1))   # gold-soft α18
        orbit = QRectF(width * 0.73, height * -0.22, width * 0.44, width * 0.44)
        painter.drawEllipse(orbit)
        painter.drawEllipse(orbit.adjusted(22, 22, -22, -22))
        painter.setPen(QPen(QColor(217, 194, 139, 26), 1))
        painter.drawLine(QPointF(width * 0.75, height * 0.12),
                         QPointF(width * 0.96, height * 0.30))
        painter.drawLine(QPointF(width * 0.89, height * 0.02),
                         QPointF(width * 0.96, height * 0.30))

        # §26 — near-invisible subtle noise via dim twinkling dots
        # Fixed positions keep composition calm; only intensity animates
        for index in range(34):
            x = width * (0.025 + ((index * 37 + 11) % 95) / 100)
            y = height * (0.035 + ((index * 53 + 7) % 90) / 100)
            glow = max(0, sin(getattr(self, '_phase', 0) * 0.038 + index * 1.73))
            alpha = int(20 + 55 * glow)   # kept dim: max ~75 vs old ~125
            color = QColor(217, 194, 139, alpha)   # gold-soft
            if index % 5 == 0:
                painter.setPen(QPen(color, 0.7))
                reach = 1.8 + 1.4 * glow
                painter.drawLine(QPointF(x - reach, y), QPointF(x + reach, y))
                painter.drawLine(QPointF(x, y - reach), QPointF(x, y + reach))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(x, y), 0.55 + glow * 0.55, 0.55 + glow * 0.55)
        painter.end()


class SmokedGlassFrame(QFrame):
    """Hero card glass surface — §5 standard glass panel, §2.3 thin ornament.

    Spec values:
      background  rgba(20, 27, 39, 0.68)
      border      1 px rgba(255,255,255,0.08)
      shadow      0 16px 48px rgba(0,0,0,0.20)  [Qt: outer rim glow]
      radius      15 px  (radius-md 14 px, +1 for hero emphasis)

    Decorative corner marks follow §2.3 "detail / modal" rule:
    thin gold lines, ≤125 alpha — they slow the eye at card edges
    without competing with content.
    """

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # §5 glass fill — dark blue-navy, low opacity equivalent via opaque dark
        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, QColor(28, 40, 60, 215))    # slightly lighter top-left
        fill.setColorAt(0.5, QColor(18, 26, 42, 228))    # bg-panel-strong center
        fill.setColorAt(1.0, QColor(22, 32, 50, 212))    # warm edge

        # §5 border — 1px rgba(255,255,255,0.08) low-contrast
        rim = QLinearGradient(rect.topLeft(), rect.bottomRight())
        rim.setColorAt(0.0, QColor(255, 255, 255, 28))   # stroke-soft top
        rim.setColorAt(0.5, QColor(217, 194, 139, 45))   # gold-soft mid (accent rim)
        rim.setColorAt(1.0, QColor(255, 255, 255, 18))   # stroke-soft bottom

        painter.setBrush(fill)
        painter.setPen(QPen(rim, 1.2))
        painter.drawRoundedRect(rect, 15, 15)

        # Inner highlight line — §25 glow only at edges, low opacity
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
        painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 13, 13)

        # §2.3 — thin fantasy corner marks (detail view ornament)
        # Only at top corners; gold-soft α=90 (restrained)
        painter.setPen(QPen(QColor(217, 194, 139, 90), 1))
        for left in (True, False):
            x = rect.left() + 16 if left else rect.right() - 16
            direction = 1 if left else -1
            painter.drawLine(QPointF(x, 8), QPointF(x + direction * 14, 8))
            painter.drawLine(QPointF(x, 8), QPointF(x, 16))
        painter.end()
