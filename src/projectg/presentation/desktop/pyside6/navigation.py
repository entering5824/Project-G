"""Navigation pills — design.ms §17, §23 motion grammar.

§17 rules:
  • Few items (Tiếp theo / Nhân vật / Kế hoạch / Dữ liệu)
  • Current page: subtle glow + brighter label + small indicator
  • No large filled tab for every item
  • Settings stays outside primary nav

§23 hover motion:
  • translateY -1 or -2 px  → approximated by luminance increase only (Qt)
  • slight luminance increase on hover
  • border highlight on selected

§32 focus:
  • 2 px accent ring, offset 2 px
"""
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPen, QRadialGradient
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from .theme import COLORS


class NavigationDelegate(QStyledItemDelegate):
    """Custom pill renderer for the horizontal nav strip.

    Selected state:
      • subtle gold glow behind pill (§25 glow: large radius, low opacity)
      • gold bottom indicator line (§17 indicator nhỏ)
      • brighter label text (#F3F5F7)

    Default state:
      • transparent background
      • secondary text (#B9C0CB)

    Hover state:
      • faint fill to acknowledge interaction
    """

    def sizeHint(self, option, index):
        rail = bool(option.widget and option.widget.property("rail"))
        return QSize(170 if rail else 120, 48)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        # Inset the hit rect slightly for visual breathing room
        rect = option.rect.adjusted(4, 4, -4, -4)
        rail = bool(option.widget and option.widget.property("rail"))
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)

        # §25 — glow only for selected state, large radius, low opacity
        if selected:
            glow = QRadialGradient(
                rect.center().x(), rect.center().y() + 4,
                rect.width() * 0.7
            )
            glow.setColorAt(0, QColor(217, 194, 139, 18))   # gold-soft α18
            glow.setColorAt(1, QColor(217, 194, 139, 0))
            painter.setBrush(glow)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 8, 8)

        # Pill fill — very subtle on hover, transparent otherwise
        if hovered and not selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 10))
            painter.drawRoundedRect(rect, 8, 8)

        # §17 indicator — thin gold bottom line for selected (horizontal nav)
        # or left rail line for vertical nav
        if selected:
            painter.setPen(QPen(QColor(COLORS['accent']), 2))
            if rail:
                painter.drawLine(
                    rect.topLeft() + QPoint(2, 8),
                    rect.bottomLeft() + QPoint(2, -8)
                )
            else:
                # Bottom indicator, inset 20px each side
                painter.drawLine(
                    rect.bottomLeft() + QPoint(20, -2),
                    rect.bottomRight() + QPoint(-20, -2)
                )

        # Label text — §6 Label 12–13 px / 500, §17 brighter when selected
        font = QFont(option.font)
        font.setPixelSize(13)
        font.setWeight(QFont.Weight.DemiBold if selected else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(
            QColor(COLORS['text']) if selected else QColor(COLORS['secondary'])
        )
        painter.drawText(
            rect.adjusted(22 if rail else 0, 0, 0, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            if rail else Qt.AlignmentFlag.AlignCenter,
            index.data()
        )

        # §32 — focus ring: 2px accent, visible
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor(COLORS['accent']), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)

        painter.restore()
