"""Translate the overview query response for the desktop view."""

from projectg.application.use_cases.overview.get_overview import GetOverview


class OverviewController:
    def __init__(self, get_overview: GetOverview):
        self._get_overview = get_overview

    def load(self) -> dict:
        return self._get_overview.execute().values
