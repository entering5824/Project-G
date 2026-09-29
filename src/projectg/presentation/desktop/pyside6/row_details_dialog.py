from projectg.presentation.desktop.pyside6.dialog_shell import GlassDialog
"""Keyboard-accessible, read-only details for a displayed table row."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QPushButton, QTextEdit, QVBoxLayout,
)


class RowDetailsDialog(GlassDialog):
    def __init__(self, title: str, fields: tuple[tuple[str, str], ...],
                 explanation: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi tiết lộ trình")
        self.resize(620, 460)
        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setTextFormat(Qt.TextFormat.PlainText)
        heading.setObjectName("section")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.content = QTextEdit()
        self.content.setReadOnly(True)
        text = "\n".join(f"{label}: {value}" for label, value in fields)
        if explanation:
            text += "\n\nThông tin bổ sung\n" + explanation
        self.content.setPlainText(text)
        self.content.setAccessibleName("Chi tiết đầy đủ của mục lộ trình")
        layout.addWidget(self.content, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Đóng")
        self.copy_button = QPushButton("Sao chép nội dung")
        self.copy_button.clicked.connect(self._copy)
        buttons.addButton(self.copy_button, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _copy(self):
        QApplication.clipboard().setText(self.content.toPlainText())
        self.copy_button.setText("Đã sao chép")
