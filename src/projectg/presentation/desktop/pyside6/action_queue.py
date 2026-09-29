"""An ordered, virtualized presentation of planner goals."""
from datetime import date

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSortFilterProxyModel, Qt, QSize
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle

from .goal_copy import goal_display_title
from .theme import COLORS


def availability_text(goal, today=None):
    task = next((item for item in today or []
                 if (item.get("primaryGoal") or {}).get("goalKey") == goal.get("goalKey")), None)
    if task and task.get("availability") == "UNAVAILABLE_TODAY":
        next_day = task.get("nextAvailableDate")
        try:
            return "Mở lại " + date.fromisoformat(str(next_day)).strftime("%d/%m")
        except ValueError:
            return "Chưa mở hôm nay"
    return {"ACTIONABLE": "Làm được ngay", "BLOCKED": "Cần hoàn thành bước trước",
            "READY": "Đã đạt", "COMPLETE": "Hoàn tất"}.get(goal.get("status"), "Xem điều kiện")


class ActionQueueModel(QAbstractListModel):
    GoalRole = Qt.ItemDataRole.UserRole + 1
    SearchRole = Qt.ItemDataRole.UserRole + 2
    StatusRole = Qt.ItemDataRole.UserRole + 3
    AvailabilityRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.goals = []
        self.today_tasks = []

    def set_goals(self, goals, today_tasks=()):
        self.beginResetModel()
        self.goals = sorted(goals, key=lambda goal: int(goal.get("rank") or 0))
        self.today_tasks = list(today_tasks)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.goals)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.goals):
            return None
        goal = self.goals[index.row()]
        if role == self.GoalRole:
            return goal
        if role == self.StatusRole:
            return goal.get("status")
        if role == self.AvailabilityRole:
            return availability_text(goal, self.today_tasks)
        if role == self.SearchRole:
            return f"{(goal.get('character') or {}).get('key', '')} {goal_display_title(goal)}".casefold()
        if role == Qt.ItemDataRole.DisplayRole:
            return goal_display_title(goal)
        return None


class ActionQueueFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query = ""
        self.status = None

    def set_query(self, query):
        self.beginFilterChange()
        self.query = query.strip().casefold()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_status(self, status):
        self.beginFilterChange()
        self.status = status
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        index = model.index(row, 0, parent)
        return (not self.query or self.query in (model.data(index, model.SearchRole) or "")) and (
            not self.status or model.data(index, model.StatusRole) == self.status)


class ActionQueueDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 88)

    def paint(self, painter, option, index):
        goal = index.data(ActionQueueModel.GoalRole) or {}
        rect = option.rect.adjusted(3, 3, -3, -3)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.setBrush(QColor(COLORS["elevated"] if selected else
                                COLORS["hover"] if hovered else COLORS["surface"]))
        painter.drawRoundedRect(rect, 12, 12)
        if selected:
            painter.fillRect(rect.left(), rect.top() + 12, 3, rect.height() - 24,
                             QColor(COLORS["accent"]))
        rank = int(goal.get("rank") or index.row() + 1)
        character = (goal.get("character") or {}).get("name") or (goal.get("character") or {}).get("key") or "Nhân vật"
        painter.setPen(QColor(COLORS["secondary"]))
        painter.drawText(rect.adjusted(16, 15, 0, 0), f"{rank:02d}")
        left = rect.left() + 58
        font = QFont(option.font)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text"]))
        available_width = max(0, rect.right() - left - 12)
        painter.drawText(left, rect.top() + 28,
                         painter.fontMetrics().elidedText(character, Qt.TextElideMode.ElideRight, available_width))
        painter.drawText(left, rect.top() + 49,
                         painter.fontMetrics().elidedText(goal_display_title(goal), Qt.TextElideMode.ElideRight,
                                                           available_width))
        painter.setFont(option.font)
        status = goal.get("status")
        status_color = (COLORS["success"] if status == "ACTIONABLE" else
                        COLORS["warning"] if status == "BLOCKED" else COLORS["secondary"])
        painter.setPen(QColor(status_color))
        painter.drawText(left, rect.top() + 69,
                         painter.fontMetrics().elidedText(index.data(ActionQueueModel.AvailabilityRole) or "",
                                                           Qt.TextElideMode.ElideRight, available_width))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor(COLORS["accent"]), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)
        painter.restore()
