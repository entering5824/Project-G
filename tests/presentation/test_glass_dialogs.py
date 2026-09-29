"""Check reparenting and persistent actions in the new desktop dialog shell."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QDialogButtonBox
from projectg.presentation.desktop.pyside6.dialogs import CharacterConfigDialog, SettingsDialog, TargetContractDialog, TargetEditorDialog


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def settings():
    return {
        'account': {'serverRegion': 'ASIA', 'gameLanguage': 'vi', 'worldLevel': 9,
                    'resin': None, 'weeklyClaimed': [], 'unavailableSources': []},
        'planner': {'reorderThreshold': 10, 'manualOrder': [], 'manualOrderEnabled': False},
        'artifact': {'adapterType': 'rv', 'thresholds': {}},
    }


def test_settings_tabs_retain_values_and_shell_only_prepares_once(app):
    view = SettingsDialog(settings())
    expected = view.payload()
    view.resize(800, 560)
    view.show()
    app.processEvents()
    first_scroll = view.dialog_scroll
    for index in range(3):
        view.sections.setCurrentIndex(index)
        app.processEvents()
        assert view.payload() == expected
    view.manual_order.setText('Amber, Fischl')
    view.manual_order_enabled.setChecked(True)
    view.resin.setValue(0)
    view.close()
    view.show()
    app.processEvents()
    assert view.dialog_scroll is first_scroll
    assert view.payload()['planner']['manualOrder'] == ['Amber', 'Fischl']
    assert view.payload()['account']['resin'] == 0
    view.close()


@pytest.mark.parametrize('factory', [
    lambda: SettingsDialog(settings()),
    TargetContractDialog,
    lambda: TargetEditorDialog([{'key': 'Amber', 'target': None}], 'Amber'),
])
def test_dialog_content_is_below_heading_and_submit_stays_in_bounds(app, factory):
    view = factory()
    view.resize(800, 560)
    view.show()
    for _ in range(3):
        app.processEvents()
    assert view.height() <= 560
    assert view.dialog_heading.geometry().bottom() < view.dialog_scroll.geometry().top()
    assert view.dialog_scroll.horizontalScrollBar().maximum() == 0
    for button in view.findChild(QDialogButtonBox).buttons():
        assert view.rect().contains(button.mapTo(view, button.rect().topLeft()))
        assert view.rect().contains(button.mapTo(view, button.rect().bottomRight()))
    view.dialog_scroll.verticalScrollBar().setValue(view.dialog_scroll.verticalScrollBar().maximum())
    app.processEvents()
    for button in view.findChild(QDialogButtonBox).buttons():
        assert button.isVisible()
    view.close()


def test_dialog_shell_localizes_default_save_without_replacing_specific_action(app):
    generic = CharacterConfigDialog({'characterKey': 'Amber', 'tiers': []})
    generic.show()
    app.processEvents()
    save = generic.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save)
    assert save.text() == 'Lưu'
    generic.close()

    specific = SettingsDialog(settings())
    specific.show()
    app.processEvents()
    save = specific.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Save)
    assert save.text() == 'Lưu cài đặt'
    specific.close()
