"""Reflow presentation cards without changing their data or interactions."""
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QGridLayout, QWidget


class ResponsiveCardGrid(QWidget):
    def __init__(self, minimum_card_width: int, maximum_columns: int, parent=None):
        super().__init__(parent)
        self._minimum_card_width = minimum_card_width
        self._maximum_columns = maximum_columns
        self._cards = []
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(10)

    def add_card(self, card):
        self._cards.append(card)
        self._reflow()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QSize(self._minimum_card_width, hint.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self):
        spacing = self._grid.spacing()
        columns = max(1, min(self._maximum_columns,
            (self.width() + spacing) // (self._minimum_card_width + spacing)))
        if columns == self._columns and self._grid.count() == len(self._cards):
            return
        while self._grid.count():
            self._grid.takeAt(0)
        for index, card in enumerate(self._cards):
            self._grid.addWidget(card, index // columns, index % columns)
        for column in range(self._maximum_columns):
            self._grid.setColumnStretch(column, 1 if column < columns else 0)
        self._columns = columns
