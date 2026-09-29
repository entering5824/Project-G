"""The action queue must show the same availability as its detail view."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtCore")

from projectg.presentation.desktop.pyside6.action_queue import ActionQueueModel


def test_waiting_goal_shows_known_reopening_date():
    model = ActionQueueModel()
    model.set_goals(
        [{"goalKey": "weapon", "rank": 1, "status": "BLOCKED", "character": {"key": "YaeMiko"}}],
        [{"primaryGoal": {"goalKey": "weapon"}, "availability": "UNAVAILABLE_TODAY",
          "nextAvailableDate": "2026-09-30"}],
    )

    assert model.data(model.index(0, 0), model.AvailabilityRole) == "Mở lại 30/09"
