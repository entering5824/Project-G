"""Exercise native navigation and layouts without accessing account persistence."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QScrollArea
from projectg.presentation.desktop.pyside6.main_window import MainWindow


class PreviewWindow(MainWindow):
    def refresh(self):
        self.refresh_count = getattr(self, "refresh_count", 0) + 1

    def import_snapshot(self):
        self.snapshot_import_count = getattr(self, "snapshot_import_count", 0) + 1

    def import_good(self):
        self.good_import_count = getattr(self, "good_import_count", 0) + 1

    def import_account_file(self):
        self.account_file_count = getattr(self, "account_file_count", 0) + 1


@pytest.fixture
def window():
    app = QApplication.instance() or QApplication([])
    # Qt's offscreen plugin on Windows does not enumerate installed system fonts.
    if not QFontDatabase.families() and os.name == "nt":
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
    view = PreviewWindow(*([None] * 11))
    view.show()
    view.activateWindow()
    app.processEvents()
    yield view
    view._tier_dirty = False
    view.close()
    app.processEvents()


def test_keyboard_navigation_updates_page_context_and_search(window):
    for index, title in enumerate(("Hôm nay", "Kế hoạch", "Nhân vật", "Dữ liệu",
                                   "Điều chỉnh ưu tiên")):
        QTest.keyClick(window, getattr(Qt.Key, f"Key_{index + 1}"), Qt.KeyboardModifier.ControlModifier)
        QApplication.processEvents()
        assert window.pages.currentIndex() == index
        assert window.page_title.text() == title
        assert window.page_description.text()
        if index in (1, 2, 4):
            search = {1: window.roadmap_search, 2: window.character_search,
                      4: window.tier_search}[index]
            search.setText("Amber")
            QTest.keyClick(window, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
            assert search.hasFocus()
            assert search.selectedText() == "Amber"
            assert search.isClearButtonEnabled()


def test_navigation_uses_rail_on_wide_windows_and_top_bar_when_compact(window):
    window.nav.setCurrentRow(2)
    window.resize(1260, 780)
    QApplication.processEvents()
    assert window.nav.flow() == window.nav.Flow.TopToBottom
    assert window.nav.item(3).text() == "Dữ liệu"
    assert not window.nav.item(3).isHidden()
    assert window.nav.item(4).isHidden()
    assert window.sidebar.mapTo(window, window.sidebar.rect().topRight()).x() < (
        window.pages.mapTo(window, window.pages.rect().topLeft()).x())

    window.resize(800, 560)
    QApplication.processEvents()
    assert window.nav.flow() == window.nav.Flow.LeftToRight
    assert window.sidebar.mapTo(window, window.sidebar.rect().bottomLeft()).y() < (
        window.pages.mapTo(window, window.pages.rect().topLeft()).y())
    assert window.pages.currentIndex() == 2


def test_data_page_explains_empty_and_imported_account_states(window):
    window.nav.setCurrentRow(3)
    window._render_data({})
    assert window.data_status.text() == "Chưa có dữ liệu tài khoản"
    assert not window.data_health_button.isEnabled()
    assert not window.data_backup_button.isEnabled()
    before = window.account_file_count if hasattr(window, "account_file_count") else 0
    window.data_import_button.click()
    assert window.account_file_count == before + 1

    window._render_data({"snapshotId": 7, "snapshotImportedAt": "2026-09-29T10:30:00",
                         "characters": [{"key": "Amber"}, {"key": "YaeMiko"}]})
    assert window.data_status.text() == "Dữ liệu đã sẵn sàng"
    assert "2 nhân vật" in window.data_summary.text()
    assert "29/09/2026 10:30" in window.data_imported_at.text()
    QApplication.processEvents()
    assert (window.data_imported_at.width() >=
            window.data_imported_at.fontMetrics().horizontalAdvance(window.data_imported_at.text()))
    assert window.data_health_button.isEnabled()
    assert window.data_backup_button.isEnabled()
    window._render_data({"snapshotId": 7, "characters": []})
    assert window.data_status.text() == "Chưa có nhân vật trong dữ liệu"
    assert window.data_import_button.text() == "Nhập lại dữ liệu"
    window._loading = True
    window._render_data({"snapshotId": 7})
    assert not window.data_import_button.isEnabled()
    assert not window.data_restore_button.isEnabled()
    window._loading = False


def test_refresh_shortcut_respects_disabled_action(window):
    previous = window.refresh_count
    QTest.keyClick(window, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    assert window.refresh_count == previous + 1
    window.refresh_button.setEnabled(False)
    QTest.keyClick(window, Qt.Key.Key_R, Qt.KeyboardModifier.ControlModifier)
    assert window.refresh_count == previous + 1


def test_result_export_button_writes_loaded_result_without_refresh(window, monkeypatch, tmp_path):
    import json
    from zipfile import ZipFile
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    assert not window.export_results_button.isEnabled()
    window._data = {"snapshotId": 9, "today": {"noActionReason": "NO_STRATEGIC_GOAL"}}
    window.export_results_button.setEnabled(True)
    path = tmp_path / "evaluation.zip"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), ""))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    before = window.refresh_count
    window.export_results_button.click()
    with ZipFile(path) as archive:
        assert json.loads(archive.read("results.json"))["result"] == window._data
    assert window.refresh_count == before


def test_cancel_result_export_does_not_write(window, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog
    window._data = {"snapshotId": 9}
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    window.export_planner_results()
    assert not list(tmp_path.iterdir())


def test_global_actions_fit_small_window_on_all_pages(window):
    window.resize(800, 560)
    for index in range(5):
        window.nav.setCurrentRow(index)
        QApplication.processEvents()
        assert window.minimumSizeHint().width() <= 800
        for button in (window.snapshot_button, window.tools_button):
            position = button.mapTo(window, button.rect().topLeft())
            assert position.x() >= 0
            assert position.x() + button.width() <= window.width()
    assert window.refresh_action in window.tools_button.menu().actions()
    assert window.export_action in window.tools_button.menu().actions()


def test_compact_tier_list_keeps_controls_and_rows_visible(window):
    from types import SimpleNamespace
    row = {"characterKey": "Amber", "owned": True, "score": 84,
           "tier": "S+", "notes": "", "control": "NORMAL",
           "setOptions": [], "selectedSet": None}
    window.tier_pack_controller = SimpleNamespace(load=lambda: {
        "pack": {"minimumTierForRoadmap": "S+"}, "rows": [row]})
    window._render_tier_list()
    window.resize(800, 560)
    window.nav.setCurrentRow(4)
    QApplication.processEvents()
    assert window.tier_table.viewport().height() >= 110
    assert window.tier_options_panel.isHidden()
    for button in (window.tier_save_button, window.tier_options_button):
        position = button.mapTo(window, button.rect().topLeft())
        assert position.x() >= 0
        assert position.x() + button.width() <= window.width()
    assert window.page_title.toolTip() == window.page_description.text()


def test_today_card_fits_without_horizontal_scroll(window):
    window._render_today({"today": None})
    window.resize(800, 560)
    QApplication.processEvents()
    scroll = window.pages.widget(0).findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0


def test_character_cards_reflow_without_losing_artifact_content(window):
    window.nav.setCurrentRow(2)
    assert window.character_artifacts_card.isHidden()
    assert window.character_tabs.tabBar().isHidden()
    window.character_context_toggle.click()
    assert not window.character_artifacts_card.isHidden()
    assert not window.character_tabs.tabBar().isHidden()
    for index, label in enumerate(window.char_art_set):
        label.setText(f"Emblem of Severed Fate {index}")
    window.char_name.setText("Raiden Shogun")
    window.resize(1260, 780)
    for _ in range(3):
        QApplication.processEvents()
    assert window.char_avatar.width() == 104
    grid = window.char_art_slots_layout.layout()
    wide_positions = [grid.getItemPosition(i)[:2] for i in range(grid.count())]
    window.resize(800, 560)
    for _ in range(3):
        QApplication.processEvents()
    narrow_positions = [grid.getItemPosition(i)[:2] for i in range(grid.count())]
    assert grid.count() == 5
    assert window.character_picker.isVisible()
    assert window.character_left_panel.isHidden()
    assert [label.text() for label in window.char_art_set] == [
        f"Emblem of Severed Fate {index}" for index in range(5)]
    scroll = window.pages.widget(2).findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0


def test_character_search_reports_no_matches_and_recovers_when_cleared(window):
    window.character_list.blockSignals(True)
    window.character_list.addItems(["Amber", "Fischl"])
    window.character_list.blockSignals(False)
    window.character_search.setText("missing")
    assert all(window.character_list.item(i).isHidden() for i in range(2))
    assert "Không tìm thấy" in window.character_search_feedback.text()
    window.character_search.clear()
    assert all(not window.character_list.item(i).isHidden() for i in range(2))
    assert "2 / 2" in window.character_search_feedback.text()


def test_compact_character_search_shortcut_focuses_visible_picker(window):
    window.resize(800, 560)
    window.nav.setCurrentRow(2)
    QApplication.processEvents()
    assert window.character_picker.isVisible()
    assert not window.character_search.isVisible()
    QTest.keyClick(window, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert window.character_picker.lineEdit().hasFocus()


def test_character_next_step_shows_availability_and_primary_action(window):
    goal = {"rank": 1, "goalKey": "amber-skill", "character": {"key": "Amber"},
            "type": "TALENT_SKILL", "current": {"value": 6},
            "target": {"value": 8}, "status": "ACTIONABLE"}
    task = {"primaryGoal": {"goalKey": "amber-skill"}, "availability": "AVAILABLE"}
    window._render_roadmap({"roadmap": {"global": [goal]},
                            "today": {"farming": [task]}})
    window._data = {"characters": [{"key": "Amber", "target": None, "talents": {},
                                     "level": 80, "ascension": 6, "weapon": None,
                                     "artifacts": [], "teams": []}],
                    "roadmap": {"global": [goal]}, "today": {"todayState": {}}}
    window._render_characters(window._data)
    window.nav.setCurrentRow(2)
    assert window.char_next_status.text() == "Làm được ngay"
    assert window.char_next_button.objectName() == "primaryButton"
    assert window.char_next_button.isVisible()


def test_roadmap_filter_feedback_respects_search_and_status(window):
    from PySide6.QtWidgets import QTreeWidgetItem
    row = QTreeWidgetItem(["1", "Amber", "80", "90", "90", "Ready", "10"])
    row.setData(5, Qt.ItemDataRole.UserRole, "READY")
    window.roadmap_tree.addTopLevelItem(row)
    window.roadmap_filter.setCurrentIndex(1)
    assert row.isHidden()
    assert "Không có kết quả" in window.roadmap_search_feedback.text()
    window.roadmap_filter.setCurrentIndex(0)
    assert not row.isHidden()
    assert "1 / 1" in window.roadmap_search_feedback.text()


def test_today_keeps_the_first_view_free_of_material_tables(window):
    window._render_today({"today": None})
    assert not hasattr(window, "today_material_table")
    assert all(label.text() != "Chuẩn bị nguyên liệu"
               for label in window.pages.widget(0).findChildren(QLabel))


def test_secondary_information_is_available_on_demand(window):
    assert window.today_details_panel.isHidden()
    window.today_details_button.click()
    assert not window.today_details_panel.isHidden()
    window.today_details_button.click()
    assert window.today_details_panel.isHidden()
    window.char_art_subs[0].setText("CRIT Rate +10%")
    window.character_context_toggle.click()
    assert window.char_art_subs[0].isHidden()
    window.char_substats_toggle.click()
    assert not window.char_art_subs[0].isHidden()
    assert window.char_art_subs[0].text() == "CRIT Rate +10%"
    window.char_substats_toggle.click()
    assert window.char_art_subs[0].isHidden()
    assert window.character_more_button.menu().actions()[0].text().startswith("Điều chỉnh mức ưu tiên")


def test_account_split_button_keeps_both_import_paths(window):
    window.snapshot_button.click()
    assert window.account_file_count == 1
    window.good_import_action.trigger()
    assert window.good_import_count == 1
    assert window.good_import_action in window.snapshot_button.menu().actions()


def test_account_action_becomes_secondary_after_import(window):
    window._sync_account_action(True)
    assert window.snapshot_button.text() == "Cập nhật dữ liệu"
    assert window.snapshot_button.objectName() == "ghostButton"
    window._sync_account_action(False)
    assert window.snapshot_button.text() == "Dữ liệu tài khoản"
    assert window.snapshot_button.objectName() == "ghostButton"


def test_compact_tier_columns_preserve_hidden_values_in_payload(window):
    from types import SimpleNamespace
    pack = {"minimumTierForRoadmap": "B"}
    row = {"characterKey": "Amber", "owned": True, "score": 90, "tier": "S+",
           "notes": "Keep this note", "control": "FORCE_INCLUDE",
           "setOptions": ["SetA"], "selectedSet": "SetA"}
    window.tier_pack_controller = SimpleNamespace(load=lambda: {"pack": pack, "rows": [row]})
    window._render_tier_list()
    window.nav.setCurrentRow(4)
    window.resize(800, 560)
    QApplication.processEvents()
    assert window.tier_bands_scroll.isVisible()
    assert window.tier_table.isHidden()
    assert all(window.tier_table.isColumnHidden(i) for i in (1, 2, 4, 5, 6))
    assert window.tier_table.horizontalScrollBar().maximum() == 0
    before = window._tier_payload_from_table()
    window.tier_options_button.click()
    assert not window.tier_options_panel.isHidden()
    window.tier_details_toggle.setChecked(True)
    assert all(not window.tier_table.isColumnHidden(i) for i in (1, 2, 4, 5, 6))
    assert window._tier_payload_from_table() == before
    window.tier_details_toggle.setChecked(False)
    assert window._tier_payload_from_table() == before
    assert before["ratings"]["Amber"]["notes"] == "Keep this note"
    assert before["selectedSets"] == {"Amber": "SetA"}
    assert before["controls"] == {"Amber": "FORCE_INCLUDE"}
    assert window.tier_table.cellWidget(0, 5).currentText() == "Luôn chọn"
    assert "Nhấp đúp" in window.tier_table.item(0, 2).toolTip()


def test_tier_progress_updates_as_score_changes(window):
    from types import SimpleNamespace
    row = {"characterKey": "Amber", "owned": True, "score": None,
           "tier": "Unranked", "notes": "", "control": "NORMAL",
           "setOptions": [], "selectedSet": None}
    window.tier_pack_controller = SimpleNamespace(load=lambda: {
        "pack": {"minimumTierForRoadmap": "S+"}, "rows": [row]})
    window._render_tier_list()
    assert "0 / 1" in window.tier_progress.text()
    assert window.tier_table.item(0, 3).text() == "Chưa xếp"
    assert window.tier_table.cellWidget(0, 3).currentText() == "Chưa xếp"
    assert not window.tier_save_status.isVisible()
    window.tier_table.cellWidget(0, 3).setCurrentText("S+")
    assert window.tier_table.item(0, 2).text() == "84"
    assert "1 / 1" in window.tier_progress.text()
    assert "thay đổi chưa lưu" in window.tier_save_status.text()
    assert window.tier_save_button.text() == "Lưu thay đổi"
    window.tier_table.item(0, 2).setText("101")
    assert "0 / 1" in window.tier_progress.text()
    assert "1 điểm không hợp lệ" in window.tier_progress.text()
    assert window.tier_table.item(0, 2).toolTip() == "Nhập điểm từ 0 đến 100"
    assert window.tier_save_status.text().startswith("Điểm phải từ 0 đến 100")
    window.tier_table.item(0, 2).setText("")
    assert not window.tier_save_status.isVisible()
    window.tier_table.cellWidget(0, 5).setCurrentIndex(2)
    assert window.tier_save_status.text().startswith("1 thay đổi chưa lưu")
    assert window._tier_payload_from_table()["controls"] == {"Amber": "IGNORE"}


def test_recompute_keeps_unsaved_tier_edits(window, monkeypatch):
    from types import SimpleNamespace

    row = {"characterKey": "Amber", "owned": True, "score": None,
           "tier": "Unranked", "notes": "", "control": "NORMAL",
           "setOptions": [], "selectedSet": None}
    window.tier_pack_controller = SimpleNamespace(load=lambda: {
        "pack": {"minimumTierForRoadmap": "S+"}, "rows": [row]})
    window._render_tier_list()
    window.tier_table.item(0, 2).setText("84")
    assert window._tier_dirty
    rendered = []
    monkeypatch.setattr(window, "_render_tier_list", lambda: rendered.append(True) or True)
    for name in ("_render_today", "_render_roadmap", "_render_characters"):
        monkeypatch.setattr(window, name, lambda _data: None)
    window._loaded(window._generation, {"snapshotId": None})
    assert not rendered
    assert window.tier_table.item(0, 2).text() == "84"
    assert "Lưu để cập nhật kế hoạch" in window.tier_save_status.text()
    window._tier_dirty = False
    window._loaded(window._generation, {"snapshotId": None})
    assert len(rendered) == 1


def test_tier_import_and_close_require_discard_confirmation(window, monkeypatch):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    window._tier_dirty = True
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args: ("tier.json", ""))
    monkeypatch.setattr(QMessageBox, "exec", lambda prompt:
                        next(button for button in prompt.buttons() if button.text() == "Quay lại").click() or 0)
    window._import_tier_list()
    assert window.isVisible()
    window.close()
    assert window.isVisible()


def test_tier_load_failure_has_retry_and_preserves_previous_rows(window):
    from types import SimpleNamespace

    row = {"characterKey": "Amber", "owned": True, "score": 84,
           "tier": "S+", "notes": "", "control": "NORMAL",
           "setOptions": [], "selectedSet": None}
    failing = [True]
    def load():
        if failing[0]:
            raise OSError("tier file unavailable")
        return {"pack": {"minimumTierForRoadmap": "S+"}, "rows": [row]}
    window.tier_pack_controller = SimpleNamespace(load=load)
    window._render_tier_list()
    assert window.tier_empty.title.text() == "Không thể tải Tier List"
    assert window.tier_empty.action.text() == "Thử lại"
    assert not window.tier_save_button.isEnabled()
    failing[0] = False
    window.tier_empty.action.click()
    assert window.tier_table.rowCount() == 1
    assert window.tier_save_button.isEnabled()
    assert window.tier_empty.title.text() == "Chưa có nhân vật để xếp hạng"
    failing[0] = True
    window._render_tier_list()
    assert not window.tier_error_banner.isHidden()
    assert window.tier_table.item(0, 0).text() == "Amber"
    assert not window.tier_table.isEnabled()
    failing[0] = False
    window.tier_error_retry.click()
    assert window.tier_error_banner.isHidden()
    assert window.tier_table.isEnabled()


def test_compact_roadmap_keeps_rows_and_values_when_details_toggle(window):
    from PySide6.QtWidgets import QTreeWidgetItem
    item = QTreeWidgetItem(["1", "Amber", "80", "90", "90", "READY", "10"])
    item.setData(5, Qt.ItemDataRole.UserRole, "READY")
    window.roadmap_tree.addTopLevelItem(item)
    window.nav.setCurrentRow(1)
    window.resize(800, 560)
    QApplication.processEvents()
    assert window.roadmap_tree.horizontalScrollBar().maximum() == 0
    assert window.roadmap_tree.isColumnHidden(4)
    assert window.roadmap_tree.isColumnHidden(6)
    window.roadmap_details_toggle.setChecked(True)
    assert not window.roadmap_tree.isColumnHidden(4)
    assert not window.roadmap_tree.isColumnHidden(6)
    assert item.text(4) == "90"
    assert window.roadmap_tree.topLevelItemCount() == 1


def test_roadmap_empty_refresh_resets_previous_match_count(window):
    from PySide6.QtWidgets import QTreeWidgetItem
    window.roadmap_tree.addTopLevelItem(QTreeWidgetItem(["1", "Amber"]))
    window._filter_roadmap()
    assert "1 / 1" in window.roadmap_search_feedback.text()
    window._render_roadmap({"roadmap": {"global": []}, "today": None})
    assert window.roadmap_tree.topLevelItemCount() == 0
    assert "0 / 0" in window.roadmap_search_feedback.text()


def test_alternating_table_rows_use_readable_light_palette(window):
    from PySide6.QtGui import QPalette
    for table in (window.roadmap_tree, window.tier_table):
        table.ensurePolished()
        color = table.palette().color(QPalette.ColorRole.AlternateBase)
        assert color.lightness() > 210
        assert table.palette().color(QPalette.ColorRole.Text).lightness() < 130


def test_mondstadt_backdrop_and_hywenhei_are_available_in_native_ui(window):
    from PySide6.QtGui import QFontDatabase
    assert window.project_font_family == "HYWenHei"
    assert "HYWenHei" in QFontDatabase.families()
    canvas = window.centralWidget()
    assert not canvas._mondstadt.isNull()
    assert not canvas._mondstadt_blurred.isNull()


def test_character_status_filter_selects_a_visible_character(window):
    characters = [{"key": key, "target": None, "talents": {}, "level": 80,
                   "ascension": 6, "weapon": None, "artifacts": [], "teams": []}
                  for key in ("Amber", "Fischl")]
    goals = [{"goalKey": "amber", "character": {"key": "Amber"},
              "type": "CHARACTER_LEVEL", "status": "ACTIONABLE", "rank": 1},
             {"goalKey": "fischl", "character": {"key": "Fischl"},
              "type": "CHARACTER_LEVEL", "status": "BLOCKED", "rank": 2}]
    data = {"characters": characters, "roadmap": {"global": goals},
            "today": {"farming": [], "todayState": {}}}
    window._data = data
    window._render_roadmap(data)
    window._render_characters(data)
    window.character_list.setCurrentRow(1)
    window._set_character_filter("ready")
    assert window.character_list.currentItem().text() == "Amber"
    assert not window.character_list.item(0).isHidden()
    assert window.character_list.item(1).isHidden()


def test_roadmap_details_include_hidden_values_and_disable_for_filtered_row(window):
    from PySide6.QtWidgets import QTreeWidgetItem
    item = QTreeWidgetItem(["1", "Amber <b>literal</b>", "80", "90", "90", "READY", "10"])
    item.setToolTip(1, "Long beneficiary explanation")
    window.roadmap_tree.addTopLevelItem(item)
    window.roadmap_tree.setCurrentItem(item)
    assert window.roadmap_open_details_button.isEnabled()
    dialog = window._roadmap_details_dialog()
    text = dialog.content.toPlainText()
    assert "Mục tiêu cuối: 90" in text
    assert "Điểm ưu tiên: 10" in text
    assert "Long beneficiary explanation" in text
    assert "<b>literal</b>" in text
    assert dialog.content.isReadOnly()
    dialog.close()
    window.roadmap_search.setText("missing")
    assert not window.roadmap_open_details_button.isEnabled()
    assert window._roadmap_details_dialog() is None
    window.roadmap_search.clear()
    assert window.roadmap_open_details_button.isEnabled()


def test_enter_opens_selected_action_detail_in_place(window):
    window.nav.setCurrentRow(1)
    window._render_roadmap({"roadmap": {"global": [{"rank": 1, "character": {"key": "Amber"},
        "title": "Nâng cấp", "status": "ACTIONABLE", "current": {"value": 80},
        "nextMilestone": {"value": 90}}]}})
    window.action_queue.setFocus()
    QApplication.processEvents()
    QTest.keyClick(window.action_queue, Qt.Key.Key_Return)
    assert "Amber" in window.action_detail_title.text()
    assert "80 → 90" in window.action_detail_body.text()


def test_plan_detail_explains_reason_and_required_materials_before_source(window):
    goal = {"rank": 1, "goalKey": "amber-skill", "character": {"key": "Amber"},
            "type": "TALENT_SKILL", "status": "ACTIONABLE",
            "current": {"value": 6}, "nextMilestone": {"value": 8}}
    task = {"primaryGoal": {"goalKey": "amber-skill"},
            "whySummary": "Ưu tiên nhân vật đang xây dựng.",
            "requiredCost": {"Sách thiên phú": None, "Mora": 45000},
            "source": {"name": "Bí cảnh thử nghiệm", "resinCost": 20}}
    window._render_roadmap({"roadmap": {"global": [goal]},
                            "today": {"primaryTask": task}})
    window._show_action_detail(window.action_queue_filter.index(0, 0))
    body = window.action_detail_body.text()
    assert "Sách thiên phú: chưa rõ số lượng" in body
    assert "Mora: 45000" in body
    assert body.index("Vì sao bước này?") < body.index("Tổng vật phẩm ước tính") < body.index("Nguồn:")
    assert "chưa trừ vật phẩm đang có" in body
    assert window.action_detail_progress.text() == "6 → 8"
    assert "Ưu tiên nhân vật đang xây dựng." in window.action_detail_reason.text()
    assert [(row.widget().layout().itemAt(0).widget().text(),
             row.widget().layout().itemAt(1).widget().text())
            for row in (window.action_material_rows.itemAt(i)
                        for i in range(window.action_material_rows.count()))] == [
                ("Sách thiên phú", "Chưa rõ"), ("Mora", "45000")]
    assert "Bí cảnh thử nghiệm" in window.action_detail_source.text()

    window.action_queue_model.set_goals([{**goal, "goalKey": "other"}], [])
    window._show_action_detail(window.action_queue_filter.index(0, 0))
    assert window.action_materials_group.isHidden()
    assert window.action_source_group.isHidden()


def test_populated_today_preserves_unknown_and_zero_amounts_without_overflow(window):
    from copy import deepcopy
    task = {
        "title": "Farm Momiji-Dyed Court", "actionText": "Farm Momiji-Dyed Court",
        "character": {}, "score": 90, "availability": "UNAVAILABLE_TODAY",
        "source": {"name": "Momiji-Dyed Court · Nguồn farm thánh di vật cho toàn tài khoản",
                   "resinCost": 20, "resinAvailable": 160},
        "requiredCost": {"Book": None, "Mora": 45000, "Drop": 0},
    }
    data = {"today": {"primaryTask": task, "quickActions": [], "farming": [task],
                      "unavailable": [], "blocked": [], "sourceRoadmapEnabled": True}}
    original = deepcopy(data)
    window._render_today(data)
    window.resize(800, 560)
    for _ in range(3):
        QApplication.processEvents()
    assert data == original
    assert not hasattr(window, "today_material_table")
    assert "'Book': None" in window.today_context.toPlainText()
    assert window.today_title.text() == task["title"]
    assert window.today_action.text() == ""
    assert window.today_action.isHidden()
    assert window.today_avatar.isHidden()


def test_goal_title_and_nested_milestones_are_visible_without_resource_rows(window):
    task = {"title": "YaeMiko — Weapon 80 → 90", "actionText": "Farm/obtain Weapon EXP",
            "character": {"key": "YaeMiko"}, "score": 80, "availability": "AVAILABLE",
            "requiredCost": {"WeaponEXP": 10000}, "farmMethods": []}
    window._render_today({"today": {"primaryTask": task, "quickActions": [], "farming": [task],
                                    "unavailable": [], "blocked": []}})
    assert window.today_title.text() == "YaeMiko · Weapon 80 → 90"
    assert window.today_action.text() == "Thu thập Weapon EXP"
    window._render_roadmap({"roadmap": {"global": [{"rank": 1, "character": {"key": "YaeMiko"},
        "type": "WEAPON_LEVEL", "current": {"value": 1}, "nextMilestone": {"value": 20},
        "target": {"value": 90}, "score": 80, "status": "ACTIONABLE",
        "milestoneChain": [{"from": 1, "to": 20}, {"from": 20, "to": 40}, {"from": 40, "to": 90}]}]}})
    assert window.roadmap_tree.topLevelItemCount() == 1
    assert "1 → 20 → 40 → 90" in window.roadmap_tree.topLevelItem(0).toolTip(3)
    scroll = window.pages.widget(0).findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0


def test_today_removes_duplicate_character_name_and_unknown_resin_hint(window):
    task = {"title": "Zhongli — Weapon 20 → 90", "character": {"key": "Zhongli"},
            "actionText": "Farm Chaos Device; Farm Mora", "requiredCost": {"Mora": 100},
            "availability": "AVAILABLE", "source": {}, "score": 80}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    assert window.today_title.text() == "Zhongli · Weapon 20 → 90"
    assert window.today_action.text() == "Thu thập vật phẩm cần cho bước nâng này."
    assert window.today_resin_badge.isHidden()
    assert "Chaos Device" in window.today_action_detail.text()


def test_roadmap_summary_counts_goals_and_statuses(window):
    goals = [
        {"rank": 1, "character": {"key": "Amber"}, "status": "ACTIONABLE"},
        {"rank": 2, "character": {"key": "Amber"}, "status": "BLOCKED"},
        {"rank": 3, "character": {"key": "Fischl"}, "status": "READY"},
    ]
    window._render_roadmap({"roadmap": {"global": goals}})
    assert [window.roadmap_metric_values[key].text() for key in
            ("goals", "characters", "actionable", "blocked")] == ["3", "2", "1", "1"]
    assert window.roadmap_metrics.isHidden()
    assert "3 bước nâng cấp cho 2 nhân vật" in window.roadmap_summary.text()
    window._render_roadmap({"roadmap": {"global": []}, "today": None})
    assert window.roadmap_metrics.isHidden()


def test_roadmap_uses_localized_goal_and_status_labels(window):
    goal = {"rank": 1, "goalKey": "weapon-amber", "character": {"key": "Amber"},
            "type": "WEAPON_LEVEL", "current": {"value": 80},
            "target": {"value": 90}, "status": "ACTIONABLE"}
    window._render_roadmap({"roadmap": {"global": [goal]}})
    item = window.roadmap_tree.topLevelItem(0)
    assert item.text(1) == "Amber · Cấp vũ khí 80 → 90"
    assert item.data(1, Qt.ItemDataRole.UserRole) == "weapon-amber"
    assert item.text(5) == "Có thể làm"
    assert window.roadmap_filter.itemText(1) == "Có thể làm"
    window.roadmap_filter.setCurrentIndex(1)
    assert not item.isHidden()
    window.roadmap_filter.setCurrentIndex(2)
    assert item.isHidden()


def test_roadmap_restores_selected_goal_after_recompute(window):
    goals = [
        {"rank": 1, "goalKey": "amber-level", "character": {"key": "Amber"},
         "type": "CHARACTER_LEVEL", "current": {"value": 70},
         "target": {"value": 80}, "status": "ACTIONABLE"},
        {"rank": 2, "goalKey": "amber-weapon", "character": {"key": "Amber"},
         "type": "WEAPON_LEVEL", "current": {"value": 70},
         "target": {"value": 80}, "status": "BLOCKED"},
    ]
    window._render_roadmap({"roadmap": {"global": goals}})
    assert window.roadmap_tree.currentItem().data(1, Qt.ItemDataRole.UserRole) == "amber-level"
    assert window.roadmap_open_details_button.isEnabled()
    window.roadmap_tree.setCurrentItem(window.roadmap_tree.topLevelItem(1))
    window._render_roadmap({"roadmap": {"global": [dict(goals[1], rank=1),
                                                 dict(goals[0], rank=2)]}})
    assert window.roadmap_tree.currentItem().data(1, Qt.ItemDataRole.UserRole) == "amber-weapon"
    window.roadmap_filter.setCurrentIndex(1)
    window._render_roadmap({"roadmap": {"global": goals}})
    assert window.roadmap_tree.currentItem().data(1, Qt.ItemDataRole.UserRole) == "amber-level"
    window.roadmap_search.setText("không-có")
    window._render_roadmap({"roadmap": {"global": goals}})
    assert not window.roadmap_open_details_button.isEnabled()


def test_today_translates_known_goal_and_action_without_changing_task(window):
    from copy import deepcopy

    task = {"title": "YaeMiko — Weapon 80 → 90", "goalType": "WEAPON_LEVEL",
            "character": {"key": "YaeMiko"}, "current": {"value": 80},
            "target": {"value": 90}, "actionText": "Farm/obtain Weapon EXP; Obtain Mora",
            "availability": "AVAILABLE", "requiredCost": {}, "score": 90}
    before = deepcopy(task)
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    assert window.today_title.text() == "YaeMiko · Cấp vũ khí 80 → 90"
    assert window.today_action.text() == "Thu thập vật phẩm để nâng vũ khí."
    assert window.today_action_detail.text() == "Thu thập Weapon EXP; Nhận Mora"
    assert task == before


def test_empty_destinations_offer_a_working_next_step(window):
    from types import SimpleNamespace

    window._render_roadmap({"roadmap": {"global": []}, "today": None, "snapshotId": None})
    window._render_characters({"characters": []})
    window.tier_pack_controller = SimpleNamespace(load=lambda: {
        "pack": {"minimumTierForRoadmap": "S+"}, "rows": []})
    window._render_tier_list()

    for page, empty in ((1, window.roadmap_empty), (2, window.character_empty),
                        (4, window.tier_empty)):
        window.nav.setCurrentRow(page)
        QApplication.processEvents()
        assert empty.isVisible()
        assert empty.action.isEnabled()
        before = getattr(window, "account_file_count", 0)
        empty.action.click()
        assert window.account_file_count == before + 1

    window._render_roadmap({"roadmap": {"global": []}, "today": None, "snapshotId": 1})
    assert window.roadmap_empty.action.text() == "Tính lại kế hoạch"
    before = window.refresh_count
    window.roadmap_empty.action.click()
    assert window.refresh_count == before + 1


def test_today_journey_buttons_open_their_destinations(window):
    task = {"title": "Amber · Cấp độ", "character": {"key": "Amber"},
            "availability": "AVAILABLE", "requiredCost": {}, "score": 70}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    window.today_roadmap_button.click()
    assert window.pages.currentIndex() == 0
    assert window.today_inspector.isVisible()
    window._close_today_inspector()
    window.today_characters_button.click()
    assert window.pages.currentIndex() == 2


def test_today_links_select_character_and_goal_across_active_filters(window):
    characters = [{"key": key, "target": None, "talents": {}, "level": 80,
                   "ascension": 6, "weapon": None, "artifacts": [], "teams": []}
                  for key in ("Amber", "YaeMiko")]
    window._data = {"characters": characters, "today": None}
    window._render_characters(window._data)
    task = {"title": "YaeMiko — Weapon 80 → 90", "character": {"key": "YaeMiko"},
            "primaryGoal": {"goalKey": "goal-weapon"}, "availability": "AVAILABLE",
            "requiredCost": {}, "score": 90}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    window._render_roadmap({"roadmap": {"global": [
        {"rank": 1, "goalKey": "goal-level", "character": {"key": "YaeMiko"},
         "title": "Cấp độ", "status": "ACTIONABLE"},
        {"rank": 2, "goalKey": "goal-weapon", "character": {"key": "YaeMiko"},
         "title": "Vũ khí", "status": "BLOCKED"}]}})
    window.character_search.setText("Amber")
    window.roadmap_filter.setCurrentIndex(1)
    window.nav.setCurrentRow(0)
    window.today_characters_button.click()
    assert window.character_search.text() == ""
    assert window.character_list.currentItem().text() == "YaeMiko"
    window.nav.setCurrentRow(0)
    window.today_roadmap_button.click()
    assert window.pages.currentIndex() == 0
    window.today_inspector_plan.click()
    assert window.roadmap_filter.currentIndex() == 0
    assert window.roadmap_tree.currentItem().data(1, Qt.ItemDataRole.UserRole) == "goal-weapon"


def test_today_shows_decision_facts_and_opens_matching_roadmap_goal(window):
    task = {"title": "YaeMiko · Vũ khí", "character": {"key": "YaeMiko"},
            "score": 80, "availability": "AVAILABLE", "source": {"resinCost": 20},
            "requiredCost": {}}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    window._render_roadmap({"roadmap": {"global": [{"rank": 1,
        "character": {"key": "YaeMiko"}, "title": "Vũ khí", "status": "ACTIONABLE"}]}})
    window.nav.setCurrentRow(0)
    assert not window.today_facts.isHidden()
    assert window.today_resin_badge.isHidden()
    assert window.today_avail_badge.text() == "Làm được ngay"
    window.today_roadmap_button.click()
    assert window.pages.currentIndex() == 0
    assert "20 Nhựa/lượt" in window.today_inspector_body.text()
    window.today_inspector_plan.click()
    assert window.pages.currentIndex() == 1
    assert window.roadmap_tree.currentItem() is window.roadmap_tree.topLevelItem(0)
    window._render_today({"today": None})
    assert window.today_facts.isHidden()


def test_waiting_today_surfaces_actionable_alternative(window):
    primary = {"id": "wait", "title": "Amber · Thiên phú", "character": {"key": "Amber"},
               "availability": "UNAVAILABLE_TODAY", "nextAvailableDate": "2026-09-30",
               "requiredCost": {}, "score": 90}
    alternative = {"id": "ready", "title": "YaeMiko · Vũ khí", "character": {"key": "YaeMiko"},
                   "availability": "AVAILABLE", "actionText": "Thu thập nguyên liệu nâng vũ khí",
                   "requiredCost": {}, "score": 80}
    plan = {"primaryTask": primary, "quickActions": [], "farming": [alternative],
            "unavailable": [primary], "blocked": [], "alternativeTasks": [alternative]}
    window._render_today({"today": plan})
    window._render_roadmap({"roadmap": {"global": [
        {"rank": 1, "character": {"key": "YaeMiko"}, "title": "Vũ khí",
         "status": "ACTIONABLE"}]}})
    assert window.today_eyebrow.text() == "NÊN LÀM TIẾP"
    assert window.today_badge.text() == "CHƯA MỞ HÔM NAY"
    assert "30/09" in window.today_avail_badge.text()
    assert not window.today_waiting_alt.isHidden()
    today_layout = window.today_waiting_alt.parentWidget().layout()
    assert today_layout.indexOf(window.today_waiting_alt) < today_layout.indexOf(window.today_materials)
    assert window.today_waiting_alt_title.text() == alternative["title"]
    assert window.page_description.text() == "Có việc khác làm được trong lúc ưu tiên chính đang chờ."
    window.today_waiting_alt_button.click()
    assert window.pages.currentIndex() == 0
    assert window.today_inspector.isVisible()
    window.today_inspector_plan.click()
    assert window.pages.currentIndex() == 1
    assert window.roadmap_tree.currentItem() is window.roadmap_tree.topLevelItem(0)
    window._render_today({"today": {**plan, "primaryTask": alternative,
                                     "alternativeTasks": [primary]}})
    assert window.today_waiting_alt.isHidden()
    assert window.today_eyebrow.text() == "NÊN LÀM TIẾP"
    window.nav.setCurrentRow(0)
    assert window.page_description.text() == "Một việc nên làm tiếp theo cho tài khoản của bạn."


def test_character_actions_fit_their_panel_at_minimum_size(window):
    window.nav.setCurrentRow(2)
    window.resize(800, 560)
    for _ in range(3):
        QApplication.processEvents()
    assert window.char_avatar.width() == 72
    assert window.character_tabs.tabText(1) == "Chi tiết kỹ thuật"
    for button in (window.wants_build_button, window.pin_button, window.character_more_button):
        panel = button.parentWidget()
        assert panel.rect().contains(button.geometry())
        assert window.rect().contains(button.mapTo(window, button.rect().topLeft()))
        assert window.rect().contains(button.mapTo(window, button.rect().bottomRight()))
    assert window.character_config_button.isHidden()
    assert window.edit_rv_button.isHidden()
    window.character_config_button.setEnabled(False)
    window.edit_rv_button.setEnabled(False)
    window._sync_character_actions()
    assert not window.character_config_action.isEnabled()
    assert not window.character_rv_action.isEnabled()


def test_empty_account_import_uses_existing_snapshot_workflow(window):
    window._render_today({"today": None})
    assert window.today_import_button.isVisible()
    assert window.today_onboarding.isHidden()
    assert window.today_roadmap_button.isHidden()
    assert window.today_characters_button.isHidden()
    before = getattr(window, "account_file_count", 0)
    window.today_import_button.click()
    assert window.account_file_count == before + 1


def test_unranked_account_does_not_require_priority_setup(window):
    plan = {"primaryTask": None, "quickActions": [], "farming": [],
            "unavailable": [], "blocked": [], "coverage": {}}
    window._render_today({"today": plan, "characters": [{"key": "Amber", "tierScore": None}]})
    assert window.today_rank_button.isHidden()
    assert not window.today_onboarding.isVisible()
    assert "chọn hạng" not in window.today_action.text().casefold()
    assert window.today_avail_badge.property("state") == ""


def test_overview_failure_keeps_result_and_retry_does_not_block_navigation(window):
    previous = {"snapshotId": 12}
    window._data = previous
    window._loading = True
    window.refresh_button.setEnabled(False)
    window._failed(window._generation, "fixture load failure")
    assert window._data is previous
    assert window.feedback_banner.isVisible()
    assert window.retry_button.isVisible()
    assert "kết quả trước đó" in window.feedback_text.text()
    window.nav.setCurrentRow(1)
    assert window.pages.currentIndex() == 1
    before = window.refresh_count
    window.retry_button.click()
    assert window.refresh_count == before + 1


def test_stale_overview_failure_does_not_replace_current_feedback(window):
    window._show_feedback("Đang tính…")
    window._failed(window._generation - 1, "stale")
    assert window.feedback_text.text() == "Đang tính…"
    assert not window.retry_button.isVisible()


def test_tool_menu_groups_and_busy_state_follow_actual_actions(window):
    menu = window.tools_button.menu()
    assert [action.text() for action in menu.actions() if not action.isSeparator()] == [
        "Cài đặt…", "Phím tắt…", "Tính lại kế hoạch", "Xuất kết quả…",
        "Lập kế hoạch", "Dữ liệu", "Hỗ trợ", "Công cụ nâng cao"]
    before = window.refresh_count
    window.refresh_action.trigger()
    assert window.refresh_count == before + 1
    window._sync_tool_actions()
    assert not window.export_action.isEnabled()
    action = next(action for action, button in window._tool_actions if button is window.backup_button)
    window.backup_button.setEnabled(False)
    window._sync_tool_actions()
    assert not action.isEnabled()
    window.backup_button.setEnabled(True)
    window._sync_tool_actions()
    assert action.isEnabled()


def test_availability_and_rv_do_not_keep_stale_success_colors(window):
    task = {"title": "Farm", "character": {}, "availability": "AVAILABLE", "requiredCost": {}}
    plan = {"primaryTask": task, "quickActions": [], "farming": [], "unavailable": [], "blocked": []}
    window._render_today({"today": plan})
    assert window.today_avail_badge.property("state") == "success"
    task["availability"] = "UNKNOWN"
    window._render_today({"today": plan})
    assert window.today_avail_badge.property("state") == ""
    assert window.today_avail_badge.text() == "Chưa xác định điều kiện"
    assert window.today_badge.text() == "CẦN KIỂM TRA"
    assert window.today_roadmap_button.objectName() == "ghostButton"
    window._render_today({"today": None})
    assert window.today_avail_badge.property("state") == ""


def test_today_distinguishes_blocked_and_weekly_limited_tasks(window):
    task = {"title": "Farm", "character": {}, "availability": "PREREQUISITE_BLOCKED",
            "requiredCost": {}}
    plan = {"primaryTask": task, "quickActions": [], "farming": [], "unavailable": [], "blocked": []}
    window._render_today({"today": plan})
    assert window.today_badge.text() == "CẦN BƯỚC TRƯỚC"
    assert window.today_avail_badge.property("state") == "warning"
    task["availability"] = "WEEKLY_LIMITED"
    window._render_today({"today": plan})
    assert window.today_badge.text() == "GIỚI HẠN TUẦN"
    assert window.today_roadmap_button.objectName() == "ghostButton"
    window.today_roadmap_button.click()
    assert window.today_inspector_status.text() == "Giới hạn tuần"


def test_action_queue_switches_to_detail_and_restores_list_at_800(window):
    goals = [{"rank": rank, "goalKey": f"goal-{rank}", "character": {"key": "Amber"},
              "title": f"Bước {rank}", "status": "ACTIONABLE"} for rank in range(1, 31)]
    window._render_roadmap({"roadmap": {"global": goals}})
    window.nav.setCurrentRow(1)
    window.resize(800, 560)
    QApplication.processEvents()
    scroll = window.action_queue.verticalScrollBar()
    scroll.setValue(200)
    previous = scroll.value()
    index = window.action_queue_filter.index(12, 0)
    window._show_action_detail(index)
    assert window.action_list_panel.isHidden()
    assert window.action_detail_panel.isVisible()
    assert window.roadmap_summary.isHidden()
    assert "Bước 13" in window.action_detail_title.text()
    window.action_back.click()
    assert window.action_list_panel.isVisible()
    assert window.action_detail_panel.isHidden()
    assert not window.roadmap_summary.isHidden()
    assert scroll.value() == previous


def test_account_file_detects_good_and_snapshot_before_preview(window, monkeypatch, tmp_path):
    import json
    from PySide6.QtWidgets import QFileDialog
    from projectg.presentation.desktop.pyside6.actions.data_io import DataActions

    good = tmp_path / "good.json"
    good.write_text(json.dumps({"format": "GOOD", "characters": []}), encoding="utf-8")
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps({"characters": []}), encoding="utf-8")
    selected = [str(good), str(snapshot)]
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args: (selected.pop(0), ""))
    calls = []
    monkeypatch.setattr(window, "_run_good", lambda path, *, commit: calls.append(("good", path, commit)))
    monkeypatch.setattr(window, "_run_snapshot", lambda payload, *, commit: calls.append(("snapshot", payload, commit)))
    DataActions.import_account_file(window)
    DataActions.import_account_file(window)
    assert calls == [("good", str(good), False), ("snapshot", {"characters": []}, False)]


def test_materials_are_not_presented_as_inventory(window):
    assert not hasattr(window, "today_material_table")


def test_today_keeps_step_details_available_without_character_key(window):
    task = {"title": "Nguồn nâng cấp", "character": {}, "availability": "AVAILABLE",
            "requiredCost": {}}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    assert not window.today_roadmap_button.isHidden()
    window.today_roadmap_button.click()
    assert window.today_inspector.isVisible()
    assert window.today_inspector_plan.isHidden()


def test_today_surfaces_required_materials_without_inventing_inventory(window):
    task = {"title": "Amber · Thiên phú", "character": {"key": "Amber"},
            "availability": "AVAILABLE", "requiredCost": {"Sách thiên phú": None,
                                                        "Mora": 45000, "Vật phẩm đã đủ": 0}}
    window._render_today({"today": {"primaryTask": task, "quickActions": [],
                                    "farming": [task], "unavailable": [], "blocked": []}})
    assert not window.today_materials.isHidden()
    assert [(name.text(), amount.text()) for _, name, amount in window.today_material_rows[:3]] == [
        ("Sách thiên phú", "Chưa rõ"), ("Mora", "45000"), ("Vật phẩm đã đủ", "0")]
    assert "chưa trừ vật phẩm" in window.today_materials_note.text()
    assert window.today_roadmap_button.objectName() == "primaryButton"
    window._render_today({"today": None})
    assert window.today_materials.isHidden()


def test_empty_character_snapshot_hides_old_equipment_and_disables_actions(window):
    window.nav.setCurrentRow(2)
    window.char_name.setText("Previous character")
    window._render_characters({"characters": []})
    assert window.character_tabs.isHidden()
    assert window.character_empty.isVisible()
    assert not window.pin_button.isEnabled()
    assert not window.character_config_button.isEnabled()
