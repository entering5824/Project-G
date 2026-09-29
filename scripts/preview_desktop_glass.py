"""Render the desktop without touching account persistence."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from projectg.presentation.desktop.pyside6.main_window import MainWindow


class PreviewWindow(MainWindow):
    def refresh(self):
        pass


app = QApplication.instance() or QApplication([])
if not QFontDatabase.families() and os.name == 'nt':
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
window = PreviewWindow(*([None] * 11))
window._render_today({'today': None})
window._render_roadmap({'roadmap': {'global': []}, 'today': None, 'snapshotId': None})
window._render_characters({'characters': []})
window.tier_pack_controller = SimpleNamespace(load=lambda: {
    'pack': {'minimumTierForRoadmap': 'S+'}, 'rows': []})
window._render_tier_list()
window.resize(1260, 840)
window.show()
output = root / '.ui-preview'
output.mkdir(exist_ok=True)
for index, name in enumerate(('today', 'roadmap', 'characters', 'tier-list')):
    window.nav.setCurrentRow(index)
    for _ in range(3):
        app.processEvents()
    window.grab().save(str(output / f'{name}.png'))
window.resize(800, 560)
window.nav.setCurrentRow(0)
for _ in range(3):
    app.processEvents()
window.grab().save(str(output / 'compact.png'))

# Deterministic sample states expose hierarchy and density without user data.
sample_task = {
    'title': 'Yae Miko · Vũ khí 80 → 90',
    'actionText': 'Thu thập nguyên liệu nâng cấp vũ khí',
    'whySummary': 'Đây là mục tiêu có ưu tiên cao nhất của tài khoản',
    'character': {'key': 'YaeMiko'}, 'score': 86.5,
    'availability': 'AVAILABLE',
    'source': {'name': 'Bí cảnh nguyên liệu vũ khí', 'resinCost': 20},
    'requiredCost': {'Mora': 225000, 'WeaponEXP': 20000},
    'resourceInfo': {'Mora': {'name': 'Mora'}, 'WeaponEXP': {'name': 'Quặng tinh luyện'}},
}
window._render_today({'today': {'primaryTask': sample_task, 'quickActions': [],
                                'farming': [sample_task], 'unavailable': [], 'blocked': []}})
sample_goals = [
    {'rank': rank, 'character': {'key': key}, 'title': title,
     'current': {'value': current}, 'nextMilestone': {'value': target},
     'target': {'value': target}, 'status': status, 'score': score}
    for rank, key, title, current, target, status, score in (
        (1, 'YaeMiko', 'Vũ khí', 80, 90, 'ACTIONABLE', 86.5),
        (2, 'RaidenShogun', 'Thiên phú', 8, 9, 'BLOCKED', 79.0),
        (3, 'Fischl', 'Cấp độ', 70, 80, 'READY', 67.0),
    )
]
window._render_roadmap({'roadmap': {'global': sample_goals}, 'snapshotId': 1})
window.tier_pack_controller = SimpleNamespace(load=lambda: {
    'pack': {'minimumTierForRoadmap': 'B'},
    'rows': [
        {'characterKey': key, 'owned': True, 'score': score,
         'tier': tier, 'notes': '', 'control': 'NORMAL',
         'setOptions': [], 'selectedSet': None}
        for key, score, tier in (('YaeMiko', 88, 'S+'),
                                 ('RaidenShogun', 84, 'S+'),
                                 ('Fischl', None, 'Unranked'))
    ]})
window._render_tier_list()
window._sync_account_action(True)
window.resize(1260, 840)
for index, name in ((0, 'sample-today'), (1, 'sample-roadmap'), (3, 'sample-tier-list')):
    window.nav.setCurrentRow(index)
    for _ in range(3):
        app.processEvents()
    window.grab().save(str(output / f'{name}.png'))
window.resize(800, 560)
window.nav.setCurrentRow(0)
for _ in range(3):
    app.processEvents()
window.grab().save(str(output / 'sample-compact-today.png'))
window.close()
print(output)
