"""Reusable, actionable empty state for desktop destinations.

design.ms §20 — Empty States:
  • Use instruction copy, not technical "No data found" strings
  • Provide a clear primary action
  • May include a simple illustration (eyebrow serves as visual cue here)

§6 Typography in empty state:
  • eyebrow: 12px/700 gold (contextual category)
  • emptyTitle: 22-24px/600 (display hierarchy)
  • emptyDescription: 14px/400 secondary text — instructional
  • action: §19 primaryButton (one clear CTA)
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class EmptyState(QFrame):
    """Instructional empty state card with a primary CTA.

    Use instruction-style copy per §20:
      ✓ "Chưa có dữ liệu tài khoản — Nhập Account Snapshot để bắt đầu."
      ✗ "No account data found."

    Args:
        eyebrow:     Short category label (12px gold, e.g. "BẮT ĐẦU")
        title:       Instructional headline (22px/600)
        description: Friendly explanation of what to do next (14px secondary)
        action:      Primary button label (gold, §19)
        callback:    Function to call when the primary button is clicked
    """

    def __init__(self, eyebrow: str, title: str, description: str,
                 action: str, callback, parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setMinimumHeight(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        # Eyebrow — §6 Label 12px/600, gold per §4.1
        self.eyebrow = QLabel(eyebrow)
        self.eyebrow.setObjectName("eyebrow")
        layout.addWidget(self.eyebrow)

        # Title — §6 Display/page title 22-24px/600
        self.title = QLabel(title)
        self.title.setObjectName("emptyTitle")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        # Description — §6 Body 14px/400, §33 instructional copy
        self.description = QLabel(description)
        self.description.setObjectName("emptyDescription")
        self.description.setWordWrap(True)
        layout.addWidget(self.description)

        # §7 space-5=20px breathing room before CTA
        layout.addSpacing(8)

        # §19 — one primary action button per screen
        actions = QHBoxLayout()
        self.action = QPushButton(action)
        self.action.setObjectName("primaryButton")
        self.action.clicked.connect(callback)
        actions.addWidget(self.action)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()

    def update_copy(self, title: str, description: str, action: str, callback=None):
        """Update copy without rebuilding the widget.

        Prefer instructional titles and §33-style description text:
          "Nhập Account Snapshot hoặc file GOOD để Project G
           phân tích nhân vật và đề xuất bước nâng cấp tiếp theo."
        """
        self.title.setText(title)
        self.description.setText(description)
        self.action.setText(action)
        if callback is not None:
            try:
                self.action.clicked.disconnect()
            except RuntimeError:
                pass
            self.action.clicked.connect(callback)
