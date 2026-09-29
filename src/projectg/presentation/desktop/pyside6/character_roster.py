"""Compact, action-first character rows for the native roster."""
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle


class CharacterRosterDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(250, 76)

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = option.rect.adjusted(2, 2, -2, -2)
        painter.setBrush(QColor(255, 255, 255, 235 if selected else 150 if hovered else 102))
        painter.setPen(QPen(QColor(214, 185, 121, 190) if selected
                            else QColor(255, 255, 255, 90), 1))
        painter.drawRoundedRect(rect, 12, 12)
        if selected:
            painter.fillRect(QRect(rect.left() + 2, rect.top() + 10, 3, rect.height() - 20),
                             QColor('#D8B775'))

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if icon:
            painter.drawPixmap(rect.left() + 10, rect.top() + 8, icon.pixmap(52, 52))
        content = index.data(Qt.ItemDataRole.UserRole) or {}
        state = content.get('state', 'none')
        label = {'ready': 'Có thể làm', 'wait': 'Cần chuẩn bị'}.get(state, 'Đang theo dõi')
        tag_width = 74 if state == 'ready' else 87 if state == 'wait' else 82
        tag = QRect(rect.right() - tag_width - 9, rect.center().y() - 11, tag_width, 22)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#E2EEE8') if state == 'ready' else
                         QColor('#F4EDDD') if state == 'wait' else QColor('#E7EDF0'))
        painter.drawRoundedRect(tag, 7, 7)
        painter.setPen(QColor('#427C60') if state == 'ready' else
                       QColor('#967542') if state == 'wait' else QColor('#62798A'))
        tag_font = QFont(option.font)
        tag_font.setPixelSize(10)
        painter.setFont(tag_font)
        painter.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)

        text_left = rect.left() + 72
        text_width = max(20, tag.left() - text_left - 5)
        name_font = QFont(option.font)
        name_font.setPixelSize(14)
        name_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(name_font)
        painter.setPen(QColor('#294257'))
        name = QFontMetrics(name_font).elidedText(str(index.data()),
                                                  Qt.TextElideMode.ElideRight, text_width)
        painter.drawText(QRect(text_left, rect.top() + 13, text_width, 23),
                         Qt.AlignmentFlag.AlignVCenter, name)
        meta_font = QFont(option.font)
        meta_font.setPixelSize(11)
        painter.setFont(meta_font)
        painter.setPen(QColor('#758A98'))
        painter.drawText(QRect(text_left, rect.top() + 38, text_width, 19),
                         Qt.AlignmentFlag.AlignVCenter,
                         f"Cấp {content.get('level', 0)}")
        painter.restore()
