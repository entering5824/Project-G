"""Run the native desktop application through the ProjectG entry point."""

import sys


def main() -> int:
    import logging
    from PySide6.QtWidgets import QApplication, QMessageBox
    from projectg.bootstrap.desktop_environment import prepare_desktop_environment, migrate_desktop_database

    application = QApplication(sys.argv)
    application.setApplicationName("Genshin Planner")
    application.setOrganizationName("Genshin Planner")
    application.setApplicationVersion("0.1.0")
    try:
        prepare_desktop_environment()
        from projectg.bootstrap.settings import settings
        from projectg.infrastructure.logging.local_file import configure_local_file_logging
        configure_local_file_logging(settings)
        logging.getLogger(__name__).info("Desktop startup database=%s", settings.database_url)
        migrate_desktop_database()
        from projectg.infrastructure.game_data.json.loader import load_game_data
        load_game_data(settings.game_data_path, strict=True)
    except Exception as exc:
        logging.getLogger(__name__).exception("Desktop startup failed")
        QMessageBox.critical(None, "Genshin Planner", f"Không thể mở dữ liệu local:\n{exc}")
        return 1
    from projectg.bootstrap.dependencies import (
        build_account_import_controller,
        build_artifact_exchange_controller,
        build_character_configuration_controller,
        build_build_intent_controller,
        build_game_data_controller,
        build_planner_state_controller,
        build_target_controller,
        build_tier_pack_controller,
        build_support_controller,
        build_overview_controller,
        build_settings_controller,
        build_teams_controller,
    )
    from projectg.presentation.desktop.pyside6.main_window import MainWindow
    window = MainWindow(build_account_import_controller(), build_settings_controller(),
                        build_teams_controller(), build_character_configuration_controller(),
                        build_game_data_controller(), build_artifact_exchange_controller(),
                        build_planner_state_controller(), build_target_controller(),
                        build_tier_pack_controller(), build_support_controller(),
                        build_overview_controller(), build_build_intent_controller())
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
