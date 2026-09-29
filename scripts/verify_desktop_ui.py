"""Render isolated native UI fixtures; never open the user's account database.

Run with QT_SCALE_FACTOR=1, 1.25 or 1.5 in separate processes for DPI checks.
"""
import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QScrollArea, QTabWidget
from projectg.presentation.desktop.pyside6.main_window import MainWindow
from projectg.presentation.desktop.pyside6.dialogs import (
    SettingsDialog, SnapshotEditorDialog, TargetContractDialog, TargetSelectionDialog,
    ArtifactSelectionDialog, TeamsDialog, PlanRunDialog, HistoryDialog,
    CharacterConfigDialog, TargetEditorDialog,
)
from projectg.presentation.desktop.pyside6.row_details_dialog import RowDetailsDialog


class FixtureWindow(MainWindow):
    def refresh(self):
        pass


def fixture():
    task = {
        "id": "waiting-weapon", "title": "YaeMiko · Vũ khí 80 → 90", "actionText": "Thu thập nguyên liệu nâng vũ khí",
        "character": {"key": "YaeMiko"}, "score": 90, "availability": "UNAVAILABLE_TODAY",
        "goalType": "WEAPON_LEVEL", "current": {"value": 80}, "target": {"value": 90},
        "primaryGoal": {"goalKey": "weapon-yaemiko"},
        "nextAvailableDate": "2026-09-30",
        "whySummary": "Dữ liệu minh họa để kiểm tra giao diện, không phải kế hoạch tài khoản thật.",
        "source": {"name": "Nguồn farm minh họa có tên dài để kiểm tra khả năng xuống dòng",
                   "resinCost": 20, "resinAvailable": 0},
        "requiredCost": {"Nguyên liệu chưa biết số lượng": None, "Mora": 45000, "Nguyên liệu đã đủ": 0},
    }
    alternative = {"id": "ready-talent", "title": "Amber · Thiên phú 6 → 8",
                   "actionText": "Thu thập nguyên liệu nâng thiên phú",
                   "character": {"key": "Amber"}, "score": 75,
                   "goalType": "TALENT_SKILL", "current": {"value": 6}, "target": {"value": 8},
                   "primaryGoal": {"goalKey": "skill-amber"},
                   "availability": "AVAILABLE", "requiredCost": {}}
    character = {
        "key": "YaeMiko", "level": 80, "ascension": 6,
        "talents": {"normal": 6, "skill": 9, "burst": 9},
        "weapon": {"key": "KagurasVerity", "level": 80, "ascension": 6, "refinement": 1},
        "target": None, "teams": [], "tierScore": 90,
        "buildProfiles": [{"archetype": "Dữ liệu minh họa", "depth": "BASIC", "status": "VERIFIED"}],
        "artifacts": [{"slot": slot, "set": "Emblem of Severed Fate", "level": 20,
                       "mainStat": "ATK%", "rv": 450 if index % 2 else None,
                       "substats": [{"key": "critRate_", "value": 10.5}]}
                      for index, slot in enumerate(("flower", "plume", "sands", "goblet", "circlet"))],
    }
    return {
        "snapshotId": "illustration", "characters": [character],
        "today": {"primaryTask": task, "quickActions": [], "farming": [alternative],
                  "unavailable": [task], "blocked": [], "todayState": {},
                  "alternativeTasks": [alternative]},
        "roadmap": {"global": [{"rank": 1, "goalKey": "weapon-yaemiko", "character": {"key": "YaeMiko"},
                     "type": "WEAPON_LEVEL", "current": {"value": 80},
                     "nextMilestone": {"value": 90}, "target": {"value": 90},
                     "score": 90, "status": "BLOCKED", "milestoneChain": []},
                    {"rank": 2, "goalKey": "skill-amber", "character": {"key": "Amber"},
                     "title": "Thiên phú 6 → 8", "type": "TALENT_SKILL", "current": {"value": 6},
                     "nextMilestone": {"value": 8}, "target": {"value": 8},
                     "score": 75, "status": "ACTIONABLE", "milestoneChain": []}]},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("docs/ui-preview/v3"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    if os.name == "nt" and not QFontDatabase.families():
        for font in ("segoeui.ttf", "segoeuib.ttf", "seguisb.ttf", "seguisym.ttf"):
            QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{font}")
    window = FixtureWindow(*([None] * 11))
    window.show()
    app.processEvents()
    data = fixture()
    window._data = data
    window._sync_account_action(True)
    window.export_results_button.setEnabled(True)
    window._render_today(data)
    window._render_roadmap(data)
    window._render_characters(data)
    # Render the real Tier List presentation with isolated illustrative data.
    window.tier_pack_controller = SimpleNamespace(load=lambda: {
        "pack": {"minimumTierForRoadmap": "S+"},
        "rows": [{"characterKey": "YaeMiko", "owned": True, "score": 90,
                  "tier": "S+", "notes": "Dữ liệu minh họa", "control": "NORMAL",
                  "setOptions": [], "selectedSet": None}],
    })
    window._render_tier_list()
    window.statusBar().showMessage("Dữ liệu minh họa kiểm tra giao diện, không phải tài khoản thật")
    checks = []
    for width, height in ((800, 560), (1260, 780), (1600, 1000)):
        window.resize(width, height)
        for page in range(4):
            window.nav.setCurrentRow(page)
            for _ in range(3):
                app.processEvents()
            assert window.width() == width, ("Window expanded", page, window.width(), width)
            for button in (window.snapshot_button, window.tools_button):
                point = button.mapTo(window, button.rect().topLeft())
                assert 0 <= point.x() and point.x() + button.width() <= width
            if page in (0, 2):
                scroll = window.pages.widget(page).findChild(QScrollArea)
                assert scroll.horizontalScrollBar().maximum() == 0, (page, width)
            if page == 2:
                for button in (window.character_config_button, window.wants_build_button,
                               window.edit_rv_button, window.pin_button, window.character_more_button):
                    assert button.parentWidget().rect().contains(button.geometry()), (width, button.text())
                    assert window.rect().contains(button.mapTo(window, button.rect().bottomRight()))
            name = f"page-{page}-{width}x{height}.png"
            assert window.grab().save(str(args.output / name))
            checks.append({"page": page, "size": [width, height], "image": name})
    window.resize(800, 560)
    window.nav.setCurrentRow(0)
    window._open_today_inspector(data["today"]["primaryTask"])
    for _ in range(3):
        app.processEvents()
    assert window.today_scroll.isHidden()
    assert window.today_inspector.isVisible()
    assert window.grab().save(str(args.output / "today-detail-800x560.png"))
    window._close_today_inspector()
    window.nav.setCurrentRow(1)
    window._show_action_detail(window.action_queue_filter.index(0, 0))
    for _ in range(3):
        app.processEvents()
    assert window.action_list_panel.isHidden()
    assert window.action_detail_panel.isVisible()
    assert window.grab().save(str(args.output / "plan-detail-800x560.png"))
    window._back_to_action_queue()
    window.nav.setCurrentRow(0)
    window.resize(1260, 780)
    window._data = {"snapshotId": None, "characters": []}
    window._render_characters(window._data)
    window._sync_account_action(False)
    window.export_results_button.setEnabled(False)
    window._apply_window_layout()
    window._render_today({"today": None})
    for _ in range(3):
        app.processEvents()
    window.grab().save(str(args.output / "empty-account.png"))
    window._show_feedback("Không thể cập nhật. Kết quả trước đó được giữ lại.", error=True)
    for _ in range(3):
        app.processEvents()
    window.grab().save(str(args.output / "error-retry.png"))
    settings = {
        "account": {"serverRegion": "ASIA", "gameLanguage": "vi", "worldLevel": 9,
                    "resin": None, "weeklyClaimed": [], "unavailableSources": []},
        "planner": {"reorderThreshold": 10, "manualOrder": [], "manualOrderEnabled": False},
        "artifact": {"adapterType": "rv", "thresholds": {}},
    }
    dialogs = [("settings", SettingsDialog(settings, window)),
               ("snapshot", SnapshotEditorDialog(window)),
               ("target-import", TargetContractDialog(window)),
               ("target-preview", TargetSelectionDialog({"validTargets": {}, "invalidTargets": [], "unknownCharacters": []}, window)),
               ("artifact-preview", ArtifactSelectionDialog({"validCount": 0, "evaluations": []}, window)),
               ("teams", TeamsDialog({"importedTeams": [], "configuredTeams": []}, window)),
               ("plan-runs", PlanRunDialog([], window)),
               ("history", HistoryDialog({}, window)),
               ("character-config", CharacterConfigDialog({"characterKey": "YaeMiko", "tiers": []}, window)),
               ("target-editor", TargetEditorDialog(data["characters"], "YaeMiko", window)),
               ("row-details", RowDetailsDialog("YaeMiko", (("Mốc", "80 → 90"),), parent=window))]
    for name, dialog in dialogs:
        dialog.resize(800, 560)
        if name == "snapshot":
            dialog.findChild(QTabWidget).setCurrentIndex(1)
        dialog.show()
        for _ in range(3):
            app.processEvents()
        assert dialog.height() <= 560, (name, "dialog expanded", dialog.height())
        buttons = dialog.findChild(QDialogButtonBox)
        for button in buttons.buttons():
            point = button.mapTo(dialog, button.rect().topLeft())
            assert point.y() + button.height() <= dialog.height(), name
            assert dialog.rect().contains(point), name
            assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight())), name
        assert dialog.findChild(QScrollArea) is not None
        heading = dialog.dialog_heading
        assert heading.geometry().bottom() < dialog.dialog_scroll.geometry().top(), name
        assert dialog.dialog_scroll.horizontalScrollBar().maximum() == 0, name
        assert dialog.grab().save(str(args.output / f"dialog-{name}.png"))
        dialog.close()
    args.output.joinpath("verification.json").write_text(json.dumps({
        "scaleFactor": os.environ.get("QT_SCALE_FACTOR", "1"),
        "devicePixelRatio": window.devicePixelRatioF(), "illustrativeData": True,
        "checks": checks,
        "dialogs": [name for name, _ in dialogs],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    window.close()
    print(f"Verified 4 screens at 3 sizes and {len(dialogs)} dialogs, scale={os.environ.get('QT_SCALE_FACTOR', '1')}")


if __name__ == "__main__":
    main()
