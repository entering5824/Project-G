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
from pathlib import Path
import sys

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QWidget, QFrame


class GlassCanvas(QWidget):
    """Main window background — §26 dark canvas with subtle radial atmosphere."""

    def __init__(self, parent=None):
        super().__init__(parent)
        asset_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[5]))
        backdrop = asset_root / 'assets' / 'genshin-impact' / 'backgrounds'
        self._mondstadt = QPixmap(str(backdrop / 'mondstadt-glass.webp'))
        self._mondstadt_blurred = QPixmap(str(backdrop / 'mondstadt-glass-blurred.webp'))
        self._backdrop_size = None
        self._sharp_cache = QPixmap()
        self._blur_cache = QPixmap()
        self._phase = 0
        self._twinkle = QTimer(self)
        self._twinkle.timeout.connect(self._advance_stars)
        if self._mondstadt.isNull():
            self._twinkle.start(90)

    def _scaled_backdrop(self, blurred=False):
        size = self.size()
        if size != self._backdrop_size:
            self._backdrop_size = size
            for source, attribute in ((self._mondstadt, '_sharp_cache'),
                                      (self._mondstadt_blurred, '_blur_cache')):
                if source.isNull() or size.isEmpty():
                    setattr(self, attribute, QPixmap())
                    continue
                scaled = source.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                       Qt.TransformationMode.SmoothTransformation)
                left = max(0, (scaled.width() - size.width()) // 2)
                top = max(0, (scaled.height() - size.height()) // 2)
                setattr(self, attribute, scaled.copy(left, top, size.width(), size.height()))
        return self._blur_cache if blurred else self._sharp_cache

    def glass_sample(self, origin, size):
        backdrop = self._scaled_backdrop(blurred=True)
        if backdrop.isNull():
            return QPixmap()
        return backdrop.copy(origin.x(), origin.y(), size.width(), size.height())

    def _advance_stars(self):
        if self.isVisible():
            self._phase = (self._phase + 1) % 1000000
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()

        backdrop = self._scaled_backdrop()
        if not backdrop.isNull():
            painter.drawPixmap(0, 0, backdrop)
            veil = QLinearGradient(0, 0, width, height)
            veil.setColorAt(0.0, QColor(221, 238, 246, 55))
            veil.setColorAt(0.55, QColor(222, 237, 242, 28))
            veil.setColorAt(1.0, QColor(22, 48, 70, 55))
            painter.fillRect(self.rect(), veil)
            painter.end()
            return

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


class BackdropGlassFrame(QFrame):
    """A translucent panel that samples the blurred Mondstadt canvas behind it."""

    def __init__(self, parent=None, *, warm=False):
        super().__init__(parent)
        self._warm = warm
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        canvas = self.window().centralWidget()
        if isinstance(canvas, GlassCanvas):
            origin = self.mapTo(canvas, QPoint(0, 0))
            sample = canvas.glass_sample(origin, self.size())
            if not sample.isNull():
                painter.setClipPath(self._rounded_path(rect))
                painter.drawPixmap(0, 0, sample)
                painter.setClipping(False)
        tint = QColor(250, 247, 235, 211) if self._warm else QColor(248, 252, 252, 194)
        painter.setBrush(tint)
        painter.setPen(QPen(QColor(255, 255, 255, 225), 1.4))
        painter.drawRoundedRect(rect, 20, 20)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 110), 1))
        painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 17, 17)
        painter.end()

    @staticmethod
    def _rounded_path(rect):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRoundedRect(rect, 20, 20)
        return path


class SmokedGlassFrame(BackdropGlassFrame):
    """The primary action card shares the real blurred backdrop and gold detail."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(178, 139, 77, 130), 1))
        for left in (True, False):
            x = rect.left() + 16 if left else rect.right() - 16
            direction = 1 if left else -1
            painter.drawLine(QPointF(x, 8), QPointF(x + direction * 14, 8))
            painter.drawLine(QPointF(x, 8), QPointF(x, 16))
        painter.end()
