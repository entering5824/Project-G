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
        rect = option.rect.adjusted(3, 0, -3, 0)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        if selected or hovered:
            painter.setPen(QPen(QColor(255, 255, 255, 36), 1) if selected else Qt.PenStyle.NoPen)
            painter.setBrush(QColor(COLORS["elevated"] if selected else COLORS["hover"]))
            painter.drawRoundedRect(rect.adjusted(8, 4, -4, -4), 12, 12)

        # One continuous path gives the ordered goals a timeline shape.
        axis = rect.left() + 27
        painter.setPen(QPen(QColor(217, 194, 139, 55), 1))
        painter.drawLine(axis, rect.top(), axis, rect.bottom())
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1))
        painter.drawLine(rect.left() + 62, rect.bottom(), rect.right() - 12, rect.bottom())
        status = goal.get("status")
        status_color = (COLORS["success"] if status == "ACTIONABLE" else
                        COLORS["warning"] if status == "BLOCKED" else COLORS["secondary"])
        painter.setPen(QPen(QColor(COLORS["accent_hover"] if selected else status_color), 2))
        painter.setBrush(QColor(COLORS["elevated"]))
        painter.drawEllipse(axis - 6, rect.top() + 21, 12, 12)
        rank = int(goal.get("rank") or index.row() + 1)
        character = (goal.get("character") or {}).get("name") or (goal.get("character") or {}).get("key") or "Nhân vật"
        painter.setPen(QColor(COLORS["secondary"]))
        painter.drawText(rect.left() + 42, rect.top() + 29, f"{rank:02d}")
        left = rect.left() + 66
        font = QFont(option.font)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text"]))
        available_width = max(0, rect.right() - left - 12)
        painter.drawText(left, rect.top() + 27,
                         painter.fontMetrics().elidedText(character, Qt.TextElideMode.ElideRight, available_width))
        painter.drawText(left, rect.top() + 48,
                         painter.fontMetrics().elidedText(goal_display_title(goal), Qt.TextElideMode.ElideRight,
                                                           available_width))
        painter.setFont(option.font)
        painter.setPen(QColor(status_color))
        painter.drawText(left, rect.top() + 68,
                         painter.fontMetrics().elidedText(index.data(ActionQueueModel.AvailabilityRole) or "",
                                                           Qt.TextElideMode.ElideRight, available_width))
        if option.state & QStyle.StateFlag.State_HasFocus:
            painter.setPen(QPen(QColor(COLORS["accent"]), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(10, 6, -6, -6), 10, 10)
        painter.restore()
