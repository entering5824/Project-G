"""Shared glass dialog layout with persistent actions and scrollable content."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QLabel, QScrollArea, QVBoxLayout, QWidget
from .glass import GlassCanvas
from .theme import DESKTOP_STYLE


class GlassDialog(QDialog):
    """Apply the presentation shell without changing a dialog's input contract."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(DESKTOP_STYLE)
        self._shell_ready = False

    def paintEvent(self, event):
        GlassCanvas.paintEvent(self, event)

    def setVisible(self, visible):
        if visible and not self._shell_ready and isinstance(self.layout(), QVBoxLayout):
            requested_size = self.size()
            self._prepare_shell()
            self.setMinimumSize(0, 0)
            self.layout().activate()
            self.resize(requested_size)
        super().setVisible(visible)

    def _prepare_shell(self):
        layout = self.layout()
        items = []
        while layout.count():
            items.append(layout.takeAt(0))
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(16)
        self.dialog_heading = QLabel(self.windowTitle())
        self.dialog_heading.setTextFormat(Qt.TextFormat.PlainText)
        self.dialog_heading.setObjectName('section')
        self.dialog_heading.setWordWrap(True)
        layout.addWidget(self.dialog_heading)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(2, 2, 8, 2)
        content_layout.setSpacing(14)
        footer = []
        for item in items:
            widget = item.widget()
            if isinstance(widget, QDialogButtonBox):
                footer.append(widget)
                for button in widget.buttons():
                    standard = widget.standardButton(button)
                    if widget.buttonRole(button) in (
                        QDialogButtonBox.ButtonRole.AcceptRole,
                        QDialogButtonBox.ButtonRole.YesRole,
                    ):
                        button.setObjectName('primaryButton')
                        if standard == QDialogButtonBox.StandardButton.Save and button.text().replace('&', '') == 'Save':
                            button.setText('Lưu')
                        elif standard == QDialogButtonBox.StandardButton.Ok and button.text().replace('&', '') == 'OK':
                            button.setText('Xác nhận')
                    elif standard == QDialogButtonBox.StandardButton.Cancel:
                        button.setText('Hủy')
                    elif standard == QDialogButtonBox.StandardButton.Close:
                        button.setText('Đóng')
            else:
                if widget is not None:
                    if isinstance(widget, QLabel):
                        widget.setWordWrap(True)
                    content_layout.addWidget(widget)
                elif item.layout() is not None:
                    content_layout.addLayout(item.layout())
                else:
                    content_layout.addItem(item)
        self.dialog_scroll = QScrollArea()
        self.dialog_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.dialog_scroll.setWidgetResizable(True)
        self.dialog_scroll.setWidget(content)
        layout.addWidget(self.dialog_scroll, 1)
        for widget in footer:
            layout.addWidget(widget)
        self._shell_ready = True
