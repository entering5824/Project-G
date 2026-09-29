"""Guard the core dependency boundary as modules move into the source layout."""

import ast
import sys
from pathlib import Path


DOMAIN_ROOT = Path(__file__).parents[2] / "src" / "projectg" / "domain"
PROJECT_ROOT = DOMAIN_ROOT.parent


def _imports(tree: ast.AST, path: Path) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    relative_path = path.relative_to(DOMAIN_ROOT.parent)
    package = ["projectg", *relative_path.parts[:-1]]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                module = ".".join([*base, *(node.module.split(".") if node.module else [])])
                found.append((module, node.lineno))
            elif node.module:
                found.append((node.module, node.lineno))
    return found


def test_project_layers_follow_the_dependency_rule() -> None:
    allowed = {
        "domain": {"domain"},
        "application": {"domain", "application"},
        "interface_adapters": {"domain", "application", "interface_adapters"},
        "infrastructure": {"domain", "application", "infrastructure"},
        "presentation": {"application", "interface_adapters", "presentation"},
        "bootstrap": {"domain", "application", "interface_adapters", "infrastructure",
                       "presentation", "bootstrap"},
    }
    violations = []
    for path in sorted(PROJECT_ROOT.rglob("*.py")):
        relative = path.relative_to(PROJECT_ROOT)
        if not relative.parts or relative.parts[0] not in allowed:
            continue
        owner = relative.parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith("app."):
                violations.append(f"{relative}:{line} imports legacy module {module}")
                continue
            if not module.startswith("projectg."):
                continue
            target = module.split(".")[1]
            if target in allowed and target not in allowed[owner]:
                violations.append(f"{relative}:{line} ({owner}) imports {module}")

    assert not violations, "Project layers must point inward only:\n" + "\n".join(violations)


def test_domain_imports_only_python_standard_library_and_domain() -> None:
    violations = []
    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            root = module.split(".", 1)[0]
            in_domain = module == "projectg.domain" or module.startswith("projectg.domain.")
            if (root not in sys.stdlib_module_names and not in_domain) or root in {
                "json", "os", "pathlib", "sqlite3", "uuid", "logging", "requests",
            }:
                violations.append(f"{path.relative_to(DOMAIN_ROOT)}:{line} imports {module}")

    assert not violations, "Domain imports must stay standard-library-only:\n" + "\n".join(violations)


def test_domain_does_not_read_global_clock_or_generate_random_ids() -> None:
    violations = []
    for path in sorted(DOMAIN_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if isinstance(owner, ast.Name) and (
                (owner.id == "datetime" and node.func.attr == "now")
                or (owner.id == "uuid" and node.func.attr == "uuid4")
            ):
                violations.append(f"{path.relative_to(DOMAIN_ROOT)}:{node.lineno} calls {owner.id}.{node.func.attr}")

    assert not violations, "Domain must receive time and identifiers through ports:\n" + "\n".join(violations)


def test_application_does_not_read_global_clock_or_generate_random_ids() -> None:
    application_root = DOMAIN_ROOT.parent / "application"
    violations = []
    for path in sorted(application_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if not isinstance(function, ast.Attribute) or not isinstance(function.value, ast.Name):
                continue
            owner, method = function.value.id, function.attr
            if (owner == "datetime" and method in {"now", "utcnow"}) or (
                owner == "date" and method == "today"
            ) or (owner == "uuid" and method == "uuid4"):
                violations.append(
                    f"{path.relative_to(application_root)}:{node.lineno} calls {owner}.{method}"
                )

    assert not violations, "Application must receive time and identifiers through ports:\n" + "\n".join(violations)


def test_application_does_not_import_drivers_or_use_direct_io() -> None:
    application_root = PROJECT_ROOT / "application"
    forbidden_imports = {
        "json", "os", "pathlib", "sqlite3", "sqlalchemy", "pydantic", "PySide6",
        "alembic", "requests", "httpx", "fastapi", "flask",
    }
    violations = []
    for path in sorted(application_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            root = module.split(".", 1)[0]
            if root in forbidden_imports:
                violations.append(f"{path.relative_to(application_root)}:{line} imports {module}")
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
                owner, method = function.value.id, function.attr
                if ((owner == "datetime" and method in {"now", "utcnow"})
                        or (owner == "date" and method == "today")
                        or (owner == "uuid" and method == "uuid4")):
                    violations.append(
                        f"{path.relative_to(application_root)}:{node.lineno} calls {owner}.{method}"
                    )

    assert not violations, "Application must use ports for drivers, IO, time, and IDs:\n" + "\n".join(violations)


def test_sqlite_repository_adapters_do_not_depend_on_legacy_app_modules() -> None:
    repository_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "repositories"
    violations = []
    for path in sorted(repository_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith("app."):
                violations.append(f"{path.relative_to(repository_root)}:{line} imports {module}")

    assert not violations, "SQLite repository implementations must use canonical adapters:\n" + "\n".join(violations)


def test_sqlite_history_adapters_do_not_depend_on_legacy_app_modules() -> None:
    history_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "history"
    violations = []
    for path in sorted(history_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith("app."):
                violations.append(f"{path.relative_to(history_root)}:{line} imports {module}")

    assert not violations, "SQLite history adapters must use canonical adapters:\n" + "\n".join(violations)


def test_game_data_adapters_do_not_depend_on_legacy_or_interface_adapter_modules() -> None:
    game_data_root = DOMAIN_ROOT.parent / "infrastructure" / "game_data"
    violations = []
    for path in sorted(game_data_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith(("app.", "projectg.interface_adapters")):
                violations.append(f"{path.relative_to(game_data_root)}:{line} imports {module}")

    assert not violations, "Game data infrastructure must not depend on legacy or interface adapter modules:\n" + "\n".join(violations)


def test_application_does_not_import_outer_layers_or_frameworks() -> None:
    application_root = DOMAIN_ROOT.parent / "application"
    forbidden = ("app", "sqlalchemy", "PySide6", "pydantic", "alembic", "json", "os", "pathlib", "sqlite3", "uuid", "logging", "requests")
    violations = []
    for path in sorted(application_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            root = module.split(".", 1)[0]
            if root in forbidden or module.startswith(("projectg.infrastructure", "projectg.presentation", "projectg.interface_adapters")):
                violations.append(f"{path.relative_to(application_root)}:{line} imports {module}")

    assert not violations, "Application must depend inward through ports:\n" + "\n".join(violations)


def test_application_imports_only_python_standard_library_and_inner_modules() -> None:
    application_root = DOMAIN_ROOT.parent / "application"
    violations = []
    for path in sorted(application_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            root = module.split(".", 1)[0]
            in_core = module == "projectg.domain" or module.startswith((
                "projectg.domain.", "projectg.application",
            ))
            if root not in sys.stdlib_module_names and not in_core:
                violations.append(f"{path.relative_to(application_root)}:{line} imports {module}")

    assert not violations, (
        "Application imports must use Python's standard library or inner ProjectG modules:\n"
        + "\n".join(violations)
    )


def test_presentation_reaches_application_through_interface_adapters() -> None:
    presentation_root = DOMAIN_ROOT.parent / "presentation"
    violations = []
    for path in sorted(presentation_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            root = module.split(".", 1)[0]
            if root == "app" or module.startswith((
                "projectg.application", "projectg.domain", "projectg.infrastructure",
            )):
                violations.append(f"{path.relative_to(presentation_root)}:{line} imports {module}")

    assert not violations, "Presentation must call interface adapters, not inner details:\n" + "\n".join(violations)


def test_interface_adapters_do_not_import_drivers_or_presentation() -> None:
    adapters_root = DOMAIN_ROOT.parent / "interface_adapters"
    violations = []
    for path in sorted(adapters_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module.startswith(("projectg.infrastructure", "projectg.presentation", "PySide6", "app", "sqlalchemy")):
                violations.append(f"{path.relative_to(adapters_root)}:{line} imports {module}")

    assert not violations, "Interface adapters must not depend on drivers or UI widgets:\n" + "\n".join(violations)


def test_infrastructure_does_not_depend_on_composition_root_or_inbound_adapters() -> None:
    infrastructure_root = DOMAIN_ROOT.parent / "infrastructure"
    violations = []
    for path in sorted(infrastructure_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith((
                "app.", "projectg.bootstrap", "projectg.interface_adapters", "projectg.presentation",
            )):
                violations.append(f"{path.relative_to(infrastructure_root)}:{line} imports {module}")

    assert not violations, "Infrastructure must implement inward ports without importing outer layers:\n" + "\n".join(violations)


def test_projectg_source_does_not_import_legacy_app_package() -> None:
    source_root = DOMAIN_ROOT.parent
    violations = []
    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module, line in _imports(tree, path):
            if module == "app" or module.startswith("app."):
                violations.append(f"{path.relative_to(source_root)}:{line} imports {module}")

    assert not violations, "Canonical ProjectG source must not depend on legacy app modules:\n" + "\n".join(violations)


def test_today_planner_receives_runtime_state_through_constructor() -> None:
    planner_path = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "today_planner.py"
    tree = ast.parse(planner_path.read_text(encoding="utf-8"), filename=str(planner_path))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
            if (function.value.id == "datetime" and function.attr in {"now", "utcnow"}) or (
                function.value.id == "uuid" and function.attr == "uuid4"
            ):
                violations.append(f"{planner_path.name}:{node.lineno} calls {function.value.id}.{function.attr}")
    for module, line in _imports(tree, planner_path):
        if module == "projectg.bootstrap" or module.startswith((
            "projectg.bootstrap.", "projectg.infrastructure.game_data.json.repository",
        )):
            violations.append(f"{planner_path.name}:{line} imports runtime composition state {module}")

    assert not violations, "TodayPlanner must receive clock, IDs, and game data explicitly:\n" + "\n".join(violations)


def test_backup_gateway_is_composed_only_at_the_application_boundary() -> None:
    source_root = DOMAIN_ROOT.parent
    violations = []
    for path in sorted(source_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id == "LocalBackupGateway" and "bootstrap" not in path.relative_to(source_root).parts:
                violations.append(f"{path.relative_to(source_root)}:{node.lineno} constructs LocalBackupGateway")

    assert not violations, "Only the composition root may construct backup adapters:\n" + "\n".join(violations)


def test_backup_is_split_between_archive_sqlite_and_application_policy() -> None:
    source_root = DOMAIN_ROOT.parent
    legacy = source_root / "infrastructure" / "persistence" / "sqlite" / "backup_storage.py"
    assert not legacy.exists(), "backup_storage.py must not return as a backup god-module"

    archive = source_root / "infrastructure" / "archive" / "backup_archive.py"
    database = source_root / "infrastructure" / "persistence" / "sqlite" / "backup_database.py"
    support_port = source_root / "application" / "ports" / "outbound" / "support_gateway.py"
    backup_policy = source_root / "application" / "backups" / "policy.py"

    archive_text = archive.read_text(encoding="utf-8")
    database_text = database.read_text(encoding="utf-8")
    support_text = support_port.read_text(encoding="utf-8")
    policy_text = backup_policy.read_text(encoding="utf-8")

    assert "sqlalchemy" not in archive_text.lower()
    assert "sqlite3" not in archive_text
    assert "zipfile" not in database_text
    assert "manifest.json" not in database_text
    assert "def create_backup" not in support_text
    assert "def restore_backup" not in support_text
    assert "parse_backup_manifest" in policy_text
    assert "select_automatic_backups_to_keep" in policy_text


def test_history_adapters_do_not_generate_time_or_ids_globally() -> None:
    history_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "history"
    violations = []
    for path in sorted(history_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            owner = node.func.value
            if isinstance(owner, ast.Name) and (
                (owner.id in {"datetime", "date"} and node.func.attr in {"now", "utcnow", "today"})
                or (owner.id == "uuid" and node.func.attr == "uuid4")
            ):
                violations.append(
                    f"{path.relative_to(history_root)}:{node.lineno} calls {owner.id}.{node.func.attr}"
                )

    assert not violations, "History persistence must receive clock and ID ports:\n" + "\n".join(violations)


def test_planner_drivers_receive_catalog_and_configuration_dependencies() -> None:
    infrastructure_root = DOMAIN_ROOT.parent / "infrastructure"
    paths = (
        infrastructure_root / "persistence" / "sqlite" / "planner_gateway.py",
        infrastructure_root / "persistence" / "sqlite" / "planner_provenance.py",
        infrastructure_root / "persistence" / "sqlite" / "data_health_gateway.py",
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            imported = {alias.name for alias in node.names}
            if node.module == "projectg.infrastructure.configuration.settings" and "settings" in imported:
                violations.append(f"{path.relative_to(infrastructure_root)}:{node.lineno} imports settings singleton")
            if node.module == "projectg.infrastructure.game_data.json.repository" and "get_game_data" in imported:
                violations.append(f"{path.relative_to(infrastructure_root)}:{node.lineno} imports global game catalog")

    assert not violations, "Planner adapters must receive settings and game data through constructors:\n" + "\n".join(violations)


def test_artifact_persistence_receives_game_catalog_explicitly() -> None:
    path = (DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
            / "artifacts" / "service.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported = {alias.name for alias in node.names}
            if node.module == "projectg.infrastructure.game_data.json.repository" and "get_game_data" in imported:
                violations.append(f"{path.name}:{node.lineno} imports global game catalog")
            if node.module == "projectg.infrastructure.configuration.settings" and "settings" in imported:
                violations.append(f"{path.name}:{node.lineno} imports settings singleton")

    assert not violations, "Artifact persistence must receive external runtime state explicitly:\n" + "\n".join(violations)


def test_json_catalog_and_build_pack_adapters_require_configured_paths() -> None:
    infrastructure_root = DOMAIN_ROOT.parent / "infrastructure"
    loader = infrastructure_root / "game_data" / "json" / "loader.py"
    profiles = infrastructure_root / "game_data" / "json" / "build_profiles.py"
    review = infrastructure_root / "persistence" / "sqlite" / "planner_provenance.py"
    violations = []
    for path in (loader, profiles, review):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "projectg.infrastructure.configuration.settings":
                if any(alias.name == "settings" for alias in node.names):
                    violations.append(f"{path.name}:{node.lineno} imports settings singleton")
            if isinstance(node, ast.ImportFrom) and node.module == "projectg.infrastructure.game_data.json.build_profiles":
                if any(alias.name == "PACK_PATH" for alias in node.names):
                    violations.append(f"{path.name}:{node.lineno} imports default build path")
    assert not violations, "Catalog paths must enter through configuration:\n" + "\n".join(violations)
    for path, function_name in ((loader, "load_game_data"), (profiles, "load_build_pack")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name)
        first = function.args.args[0].arg
        assert first == "path", f"{path.name}.{function_name} must require an explicit path"


def test_legacy_python_package_is_removed_from_repository() -> None:
    repo_root = DOMAIN_ROOT.parents[2]
    assert not (repo_root / "backend").exists(), (
        "The legacy backend source tree must not return; all Python code belongs under src/projectg."
    )

    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pythonpath = ["src"]' in pyproject
    assert 'where = ["src"]' in pyproject
    assert 'include = ["projectg*"]' in pyproject
    assert 'pythonpath = ["backend"' not in pyproject
    assert 'include = ["app*"' not in pyproject


def test_source_tests_and_scripts_do_not_import_legacy_app_namespace() -> None:
    repo_root = DOMAIN_ROOT.parents[2]
    violations: list[str] = []
    for root_name in ("src", "tests", "scripts"):
        root = repo_root / root_name
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    if module == "app" or module.startswith("app."):
                        violations.append(
                            f"{path.relative_to(repo_root)}:{node.lineno} imports legacy module {module}"
                        )

    assert not violations, "Legacy app.* imports are forbidden:\n" + "\n".join(violations)


def test_cost_policy_is_not_implemented_inside_sqlite() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    assert not (sqlite_root / "cost_service.py").exists()
    engine = DOMAIN_ROOT / "costs" / "engine.py"
    assert engine.exists(), "Progression cost policy belongs to the domain layer."


def test_planner_service_facade_is_removed_and_application_owns_execution() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    assert not (sqlite_root / "planner_service.py").exists()

    gateway = sqlite_root / "planner_gateway.py"
    gateway_text = gateway.read_text(encoding="utf-8")
    gateway_imports = {module for module, _ in _imports(
        ast.parse(gateway_text, filename=str(gateway)), gateway)}
    assert "projectg.application.planning.generate" not in gateway_imports
    assert "projectg.domain.planning.engine" not in gateway_imports
    assert "PlannerInput(" not in gateway_text
    assert "profile_targets" not in gateway_text

    use_case = PROJECT_ROOT / "application" / "use_cases" / "planning" / "run_planner.py"
    use_case_text = use_case.read_text(encoding="utf-8")
    assert "prepare_planner_input" in use_case_text
    assert "GeneratePlan" in use_case_text
    assert "load_facts()" in use_case_text
    assert "load_config()" in use_case_text


def test_planner_input_policy_stays_in_application_not_sqlite_or_json_loader() -> None:
    assembler = (PROJECT_ROOT / "application" / "planning" / "input.py").read_text(encoding="utf-8")
    build_policy = (PROJECT_ROOT / "application" / "planning" / "build_knowledge.py").read_text(encoding="utf-8")
    sqlite_gateway = (PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "planner_gateway.py").read_text(encoding="utf-8")
    build_loader = (PROJECT_ROOT / "infrastructure" / "game_data" / "json" / "build_profiles.py").read_text(encoding="utf-8")

    assert "derive_profile_targets" in assembler
    assert "label_for" in assembler
    assert '"freshnessStatus"' in assembler
    assert "def derive_profile_targets" in build_policy
    assert "label_for" not in sqlite_gateway
    assert "freshnessStatus" not in sqlite_gateway
    assert "profile_targets" not in build_loader


def test_data_health_service_is_removed_and_sqlite_exposes_only_typed_facts() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    assert not (sqlite_root / "health_service.py").exists()

    path = sqlite_root / "data_health_gateway.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imports = {module for module, _ in _imports(tree, path)}
    assert "projectg.application.ports.outbound.data_health_gateway" in imports
    assert "projectg.application.health.report" not in imports
    assert "projectg.domain.costs.engine" not in imports
    assert "projectg.infrastructure.game_data.json.repository" not in imports
    assert "decisionImpact" not in text
    assert "MISSING_TARGET" not in text
    assert "SOURCE_MAPPING_MISSING" not in text

    use_case = PROJECT_ROOT / "application" / "use_cases" / "support" / "get_data_health.py"
    use_case_text = use_case.read_text(encoding="utf-8")
    assert "build_data_health_report" in use_case_text
    assert "CostEngine" in use_case_text
    assert "load_facts()" in use_case_text
    assert "self._game_data.load()" in use_case_text


def test_planner_review_module_is_removed_and_provenance_adapter_has_no_feedback_policy() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    assert not (sqlite_root / "planner_review.py").exists()
    path = sqlite_root / "planner_provenance.py"
    text = path.read_text(encoding="utf-8")
    assert "class PlannerProvenance" in text
    assert "PlannerFeedback" not in text
    assert "feedback_summary" not in text
    assert "serialize_feedback" not in text
    assert "Counter" not in text
    assert "defaultdict" not in text


def test_sqlite_history_adapter_delegates_snapshot_diff_policy_to_domain() -> None:
    history_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "history"
    assert not (history_root / "service.py").exists()
    assert not (history_root / "completion.py").exists()
    path = history_root / "snapshots.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imports = {module for module, _ in _imports(tree, path)}
    assert "projectg.domain.history.diff" in imports
    assert "collections" not in imports
    assert "ARTIFACT_PIECE_CHANGED" not in text
    assert "WEAPON_LEVEL_CHANGED" not in text
    assert (history_root / "events.py").exists()
    assert (history_root / "completion_reader.py").exists()


def test_artifact_persistence_delegates_quality_status_policy_to_domain() -> None:
    path = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite" / "artifacts" / "service.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imports = {module for module, _ in _imports(tree, path)}
    assert "projectg.domain.artifacts.status" in imports
    assert "projectg.domain.artifacts.quality" not in imports


def test_good_import_god_service_is_removed_and_sqlite_only_persists_validated_imports() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    legacy = sqlite_root / "good_import_service.py"
    assert not legacy.exists()
    path = sqlite_root / "account_import_gateway.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imports = {module for module, _ in _imports(tree, path)}
    assert "projectg.domain.account.regression" not in imports
    assert "detect_progression_regressions" not in text
    assert "hashlib" not in imports
    assert "json" not in imports
    assert "GoodImporter" not in text
    assert "commit_validated" in text

    for forbidden in (
        "select(",
        "SnapshotCharacter",
        "SnapshotWeapon",
        "SnapshotArtifact",
        "SnapshotTeam",
        "AccountRepository",
        "SnapshotRepository",
        "os.replace",
        "Path(",
        "def _persist(",
        "def _write_raw(",
    ):
        assert forbidden not in text
    assert "AccountImportContextReader" in text
    assert "AccountSnapshotWriter" in text
    assert "AccountImportHistoryEffects" in text
    assert "AccountImportRawDocumentStorage" in text


def test_account_import_persistence_is_decomposed_by_driver_responsibility() -> None:
    sqlite_root = DOMAIN_ROOT.parent / "infrastructure" / "persistence" / "sqlite"
    package = sqlite_root / "account_import"
    context = (package / "context_reader.py").read_text(encoding="utf-8")
    writer = (package / "snapshot_writer.py").read_text(encoding="utf-8")
    history = (package / "history_effects.py").read_text(encoding="utf-8")
    raw = (
        DOMAIN_ROOT.parent / "infrastructure" / "filesystem" / "account_import_raw_storage.py"
    ).read_text(encoding="utf-8")

    assert "AccountImportContext" in context
    assert "SnapshotCharacter" in context
    assert "SnapshotWeapon" in context
    assert "SnapshotArtifact(" not in context
    assert "SnapshotTeam(" not in context

    assert "class AccountSnapshotWriter" in writer
    assert "SnapshotCharacter(" in writer
    assert "SnapshotWeapon(" in writer
    assert "SnapshotArtifact(" in writer
    assert "SnapshotTeam(" in writer
    assert "persist_snapshot_diff" not in writer
    assert "reconcile_completion" not in writer

    assert "persist_snapshot_diff" in history
    assert "reconcile_completion" in history
    assert "SnapshotCharacter(" not in history
    assert "SnapshotWeapon(" not in history

    assert "os.replace" in raw
    assert "sqlalchemy" not in raw.lower()
    assert "projectg.infrastructure.persistence" not in raw


def test_account_import_application_owns_duplicate_regression_and_coverage_policy() -> None:
    policy = DOMAIN_ROOT.parent / "application" / "imports" / "policy.py"
    text = policy.read_text(encoding="utf-8")
    assert "detect_progression_regressions" in text
    assert "current_canonical_hash" in text
    assert "coverage" in text


def test_good_document_adapter_owns_external_good_merge_and_hashing() -> None:
    path = DOMAIN_ROOT.parent / "infrastructure" / "serialization" / "good_document.py"
    text = path.read_text(encoding="utf-8")
    assert "materials" in text
    assert "previous_effective_document" in text
    assert "canonical_state_hash" in text
    assert "sqlalchemy" not in text


def test_sqlite_today_adapter_does_not_own_compilation_or_selection_rules() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "today_planner.py"
    source = path.read_text(encoding="utf-8")
    forbidden_markers = (
        "resolve_requirements(",
        "resolve_cost(",
        "TaskCompiler(",
        "build_farm_roadmap(",
        "def _best_task(",
        "def _strategic_character_order(",
        "def _ordering_group(",
    )
    violations = [marker for marker in forbidden_markers if marker in source]
    assert not violations, (
        "SQLite Today adapter must delegate compile/selection policies inward: "
        + ", ".join(violations)
    )


def test_today_application_orchestration_has_no_persistence_dependency() -> None:
    path = PROJECT_ROOT / "application" / "planning" / "today.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations = []
    for module, line in _imports(tree, path):
        if module.startswith(("projectg.infrastructure", "sqlalchemy")):
            violations.append(f"{path.name}:{line} imports {module}")
    assert not violations, "Today application use case must not depend on persistence:\n" + "\n".join(violations)


def test_legacy_target_operations_module_is_removed() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "target_operations.py"
    assert not path.exists(), "Target workflow must not return to a SQLite operations god-module."


def test_sqlite_target_adapter_does_not_own_validation_preview_or_preset_key_policy() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "target_gateway.py"
    source = path.read_text(encoding="utf-8")
    forbidden_markers = (
        "def validate_target(",
        "def build_target_import_preview(",
        "def next_preset_key(",
        "unicodedata",
        "validate_target_rules",
        "_TargetShape",
    )
    violations = [marker for marker in forbidden_markers if marker in source]
    assert not violations, (
        "SQLite target adapter must persist normalized decisions, not own target policy: "
        + ", ".join(violations)
    )


def test_target_application_owns_import_preview_and_selection_workflow() -> None:
    preview_path = PROJECT_ROOT / "application" / "use_cases" / "targets" / "preview_target_payload.py"
    commit_path = PROJECT_ROOT / "application" / "use_cases" / "targets" / "commit_targets.py"
    preview_source = preview_path.read_text(encoding="utf-8")
    commit_source = commit_path.read_text(encoding="utf-8")
    assert "build_target_import_preview(" in preview_source
    assert "build_target_import_preview(" in commit_source
    assert "select_target_import(" in commit_source
    assert "commit_validated(" in commit_source


def test_target_preset_key_policy_is_owned_by_domain() -> None:
    domain_policy = PROJECT_ROOT / "domain" / "targets" / "presets.py"
    create_use_case = PROJECT_ROOT / "application" / "use_cases" / "targets" / "create_target_preset.py"
    assert domain_policy.exists()
    source = create_use_case.read_text(encoding="utf-8")
    assert "next_preset_key(" in source
    assert "preset_context(" in source


def test_legacy_artifact_operations_module_is_removed() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "artifact_operations.py"
    assert not path.exists(), "Artifact exchange workflow must not return to a SQLite god-module."


def test_sqlite_artifact_exchange_adapter_only_persists_validated_decisions() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "artifact_exchange_gateway.py"
    source = path.read_text(encoding="utf-8")
    forbidden_markers = (
        "parse_exchange(",
        "normalize_metrics(",
        "validate_metrics(",
        "ArtifactQualityAdapter(",
        "def preview(",
        "def confirm(",
    )
    violations = [marker for marker in forbidden_markers if marker in source]
    assert not violations, (
        "SQLite artifact exchange adapter must persist application decisions, not own exchange policy: "
        + ", ".join(violations)
    )
    assert "def load_context(" in source
    assert "def commit_validated(" in source


def test_artifact_application_owns_preview_validation_and_commit_preparation() -> None:
    policy = PROJECT_ROOT / "application" / "artifacts" / "policy.py"
    preview = PROJECT_ROOT / "application" / "use_cases" / "artifacts" / "preview_exchange.py"
    confirm = PROJECT_ROOT / "application" / "use_cases" / "artifacts" / "confirm_exchange.py"
    policy_source = policy.read_text(encoding="utf-8")
    preview_source = preview.read_text(encoding="utf-8")
    confirm_source = confirm.read_text(encoding="utf-8")
    assert "build_artifact_exchange_preview(" in policy_source
    assert "prepare_artifact_exchange_commit(" in policy_source
    assert "validate_metrics(" in policy_source
    assert "self._parser.parse(" in preview_source
    assert "self._gateway.load_context(" in preview_source
    assert "self._gateway.load_context(" in confirm_source
    assert "commit_validated(" in confirm_source


def test_aef_serialization_adapter_owns_external_contract_without_sqlite() -> None:
    path = PROJECT_ROOT / "infrastructure" / "serialization" / "aef_exchange.py"
    source = path.read_text(encoding="utf-8")
    assert "class AefArtifactDocumentParser" in source
    assert "AEF_VERSION" in source
    assert "DUPLICATE_CHARACTER_EVALUATION" in source
    assert "sqlalchemy" not in source
    assert "projectg.infrastructure.persistence" not in source


def test_aef_parser_has_no_sqlite_compatibility_reexport() -> None:
    path = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "artifacts" / "exchange.py"
    assert not path.exists(), "AEF parsing belongs only to serialization infrastructure."


def test_configuration_operations_god_modules_are_removed() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    legacy_modules = (
        "character_operations.py",
        "settings_operations.py",
        "team_operations.py",
        "tier_pack_operations.py",
    )
    returned = [name for name in legacy_modules if (sqlite_root / name).exists()]
    assert not returned, "Configuration workflows must not return to *_operations modules: " + ", ".join(returned)


def test_character_and_team_application_use_cases_own_input_policy() -> None:
    character = PROJECT_ROOT / "application" / "use_cases" / "characters" / "save_configuration.py"
    teams = PROJECT_ROOT / "application" / "use_cases" / "teams" / "save_teams.py"
    character_source = character.read_text(encoding="utf-8")
    teams_source = teams.read_text(encoding="utf-8")
    assert "validate_character_configuration(" in character_source
    assert "load_context(" in character_source
    assert "commit_validated(" in character_source
    assert "normalize_configured_teams(" in teams_source
    assert "commit_validated(" in teams_source


def test_settings_application_validates_before_sqlite_persistence() -> None:
    use_case = PROJECT_ROOT / "application" / "use_cases" / "settings" / "save_settings.py"
    gateway = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "settings_gateway.py"
    use_case_source = use_case.read_text(encoding="utf-8")
    gateway_source = gateway.read_text(encoding="utf-8")
    assert "config_from_payload(" in use_case_source
    assert "validate_quality_config(" in use_case_source
    assert "normalize_account_settings(" in use_case_source
    assert "commit_validated(" in use_case_source
    assert "Unsupported server region." not in gateway_source
    assert "World Level must be between" not in gateway_source


def test_planner_config_validation_is_owned_by_domain_not_sqlite() -> None:
    domain_config = PROJECT_ROOT / "domain" / "planning" / "config.py"
    sqlite_config = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "planner_config.py"
    domain_source = domain_config.read_text(encoding="utf-8")
    sqlite_source = sqlite_config.read_text(encoding="utf-8")
    assert "def config_from_payload(" in domain_source
    assert "Planner weights must sum to 1.0." in domain_source
    assert "def config_from_payload(" not in sqlite_source
    assert "from projectg.domain.planning.config import" in sqlite_source


def test_tier_pack_application_owns_validation_and_projection() -> None:
    save_use_case = PROJECT_ROOT / "application" / "use_cases" / "tier_packs" / "save_tier_pack.py"
    validate_use_case = PROJECT_ROOT / "application" / "use_cases" / "tier_packs" / "validate_tier_pack.py"
    projection = PROJECT_ROOT / "application" / "tier_packs" / "policy.py"
    gateway = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "tier_pack_gateway.py"
    combined = save_use_case.read_text(encoding="utf-8") + validate_use_case.read_text(encoding="utf-8")
    projection_source = projection.read_text(encoding="utf-8")
    gateway_source = gateway.read_text(encoding="utf-8")
    assert "validate_tier_pack(" in combined
    assert "build_tier_pack_view(" in projection_source
    assert "label_for(" in projection_source
    assert "def validate(" not in gateway_source
    assert "validate_tier_pack(" not in gateway_source
    assert "label_for(" not in gateway_source


def test_overview_planner_state_and_support_operations_modules_are_removed() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    legacy = (
        "overview_operations.py",
        "planner_state_operations.py",
        "support_operations.py",
    )
    returned = [name for name in legacy if (sqlite_root / name).exists()]
    assert not returned, (
        "Read-side workflows must not return to SQLite *_operations modules: "
        + ", ".join(returned)
    )


def test_overview_application_owns_read_model_projection() -> None:
    policy = (PROJECT_ROOT / "application" / "overview" / "policy.py").read_text(encoding="utf-8")
    use_case = (PROJECT_ROOT / "application" / "use_cases" / "overview" / "get_overview.py").read_text(encoding="utf-8")
    gateway = (PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "overview_gateway.py").read_text(encoding="utf-8")

    assert "build_overview(" in use_case
    assert "load_context()" in use_case
    assert '"priorityOverride": row.priority_override' in policy
    assert "label_for(" in policy
    assert "label_for(" not in gateway
    assert '"priorityOverride"' not in gateway


def test_planner_state_and_support_policies_stay_out_of_sqlite() -> None:
    planner_policy = (PROJECT_ROOT / "application" / "planner_state" / "policy.py").read_text(encoding="utf-8")
    preview_use_case = (PROJECT_ROOT / "application" / "use_cases" / "planner_state" / "preview_pin.py").read_text(encoding="utf-8")
    set_use_case = (PROJECT_ROOT / "application" / "use_cases" / "planner_state" / "set_pin.py").read_text(encoding="utf-8")
    planner_gateway = (PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "planner_state_gateway.py").read_text(encoding="utf-8")
    support_policy = (PROJECT_ROOT / "application" / "support" / "policy.py").read_text(encoding="utf-8")
    support_gateway = (PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "support_gateway.py").read_text(encoding="utf-8")

    assert "build_pin_preview(" in preview_use_case
    assert "load_pin_context(" in preview_use_case
    assert "owns_character(" in set_use_case
    assert "persist_pin(" in set_use_case
    assert "candidate =" in planner_policy
    assert "def preview_pin(" not in planner_gateway
    assert "def set_pin(" not in planner_gateway

    assert '"accountProgress"' in support_policy
    assert '"targetConfigChanges"' in support_policy
    assert '"completionChanges"' in support_policy
    assert '"accountProgress"' not in support_gateway
    assert '"targetConfigChanges"' not in support_gateway
    assert '"completionChanges"' not in support_gateway


def test_game_data_pack_operations_god_module_and_proxy_gateway_are_removed() -> None:
    json_root = PROJECT_ROOT / "infrastructure" / "game_data" / "json"
    assert not (json_root / "game_data_pack_operations.py").exists()
    assert not (json_root / "pack_gateway.py").exists()


def test_game_data_pack_storage_is_filesystem_only_and_sqlite_exposes_only_account_facts() -> None:
    storage = PROJECT_ROOT / "infrastructure" / "game_data" / "json" / "pack_storage.py"
    account_gateway = (
        PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "game_data_account_gateway.py"
    )
    storage_text = storage.read_text(encoding="utf-8")
    account_text = account_gateway.read_text(encoding="utf-8")

    assert "sqlalchemy" not in storage_text
    assert "projectg.infrastructure.persistence" not in storage_text
    assert "Account" not in storage_text
    assert "load_game_data(" in storage_text
    assert "os.replace(" in storage_text

    assert "load_game_data" not in account_text
    account_imports = {module for module, _ in _imports(
        ast.parse(account_text, filename=str(account_gateway)), account_gateway)}
    assert "projectg.domain.game_catalog.models" not in account_imports
    assert "projectg.infrastructure.game_data.json.loader" not in account_imports
    assert "AccountCatalogFacts" in account_text
    assert "SnapshotCharacter" in account_text
    assert "SnapshotWeapon" in account_text


def test_game_data_application_owns_pack_projection_and_workflow() -> None:
    policy = (PROJECT_ROOT / "application" / "game_data" / "policy.py").read_text(encoding="utf-8")
    preview = (
        PROJECT_ROOT / "application" / "use_cases" / "game_data" / "preview_pack.py"
    ).read_text(encoding="utf-8")
    install = (
        PROJECT_ROOT / "application" / "use_cases" / "game_data" / "install_pack.py"
    ).read_text(encoding="utf-8")

    assert "def catalog_coverage(" in policy
    assert "def account_coverage(" in policy
    assert '"dataVersion"' in policy
    assert "load_candidate(" in preview
    assert "load_installed(" in preview
    assert "build_pack_result(" in preview
    assert "load_candidate(" in install
    assert "install_candidate(" in install
    assert "load_installed(" in install
    assert "build_pack_result(" in install


def test_sqlite_mutation_side_effects_are_centralized_in_unit_of_work() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    uow = sqlite_root / "mutation_uow.py"
    text = uow.read_text(encoding="utf-8")
    assert "class SqliteMutationUnitOfWork" in text
    assert "class SqliteMutationEffects" in text
    assert "def finalize_existing_transaction(" in text
    assert "before_mutation(" in text
    assert "record_config_change(" in text
    assert "reconcile_completion(" in text
    assert "persist_snapshot_diff(" in text
    assert "db.commit()" in text
    assert "db.rollback()" in text

    mutation_gateways = (
        "account_import_gateway.py",
        "artifact_exchange_gateway.py",
        "character_configuration_gateway.py",
        "planner_state_gateway.py",
        "settings_gateway.py",
        "target_gateway.py",
        "teams_gateway.py",
        "tier_pack_gateway.py",
    )
    violations = []
    for name in mutation_gateways:
        source = (sqlite_root / name).read_text(encoding="utf-8")
        for forbidden in (
            "before_mutation(",
            "db.commit()",
            "db.rollback()",
            "history.service",
            "history.completion import",
        ):
            if forbidden in source:
                violations.append(f"{name}: {forbidden}")
        if "SqliteMutationUnitOfWork" not in source:
            violations.append(f"{name}: missing SqliteMutationUnitOfWork dependency")
        if "SqliteMutationUnitOfWork(" in source:
            violations.append(f"{name}: constructs SqliteMutationUnitOfWork internally")
    assert not violations, (
        "Mutation gateways must delegate transaction effects to the SQLite UoW:\n"
        + "\n".join(violations)
    )

    direct_transaction_calls = []
    for path in sqlite_root.rglob("*.py"):
        if path == uow:
            continue
        source = path.read_text(encoding="utf-8")
        if "db.commit()" in source or "db.rollback()" in source:
            direct_transaction_calls.append(str(path.relative_to(sqlite_root)))
    assert not direct_transaction_calls, (
        "SQLite transaction finalization must remain centralized in mutation_uow.py: "
        + ", ".join(direct_transaction_calls)
    )


def test_completion_reconciliation_is_a_uow_effect_not_a_gateway_side_effect() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    uow = (sqlite_root / "mutation_uow.py").read_text(encoding="utf-8")
    completion = (sqlite_root / "history" / "completion_reader.py").read_text(encoding="utf-8")
    assert "def reconcile_completion(" in uow
    assert "CHARACTER_COMPLETED" in uow
    assert "CHARACTER_REOPENED" in uow
    assert "def reconcile_completion(" not in completion
    assert "record_event(" not in completion


def test_mutation_unit_of_work_is_composed_at_bootstrap_boundary() -> None:
    bootstrap = (PROJECT_ROOT / "bootstrap" / "dependencies.py").read_text(encoding="utf-8")
    assert "def _build_mutation_uow(" in bootstrap
    assert "SqliteMutationUnitOfWork(" in bootstrap

    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    offenders = []
    for path in sqlite_root.glob("*_gateway.py"):
        source = path.read_text(encoding="utf-8")
        if "SqliteMutationUnitOfWork(" in source:
            offenders.append(path.name)
    assert not offenders, (
        "SQLite gateways must receive the UoW from composition instead of constructing it: "
        + ", ".join(offenders)
    )


def test_sqlite_target_gateway_is_a_facade_over_decomposed_persistence_primitives() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    gateway = (sqlite_root / "target_gateway.py").read_text(encoding="utf-8")
    targets_root = sqlite_root / "targets"

    required = {
        "context_reader.py": "class TargetContextReader",
        "target_writer.py": "class TargetWriter",
        "preset_repository.py": "class TargetPresetRepository",
        "idempotency_repository.py": "class TargetIdempotencyRepository",
    }
    for name, marker in required.items():
        path = targets_root / name
        assert path.exists(), f"Missing decomposed target persistence primitive: {name}"
        assert marker in path.read_text(encoding="utf-8")

    forbidden_gateway_markers = (
        "hashlib",
        "json.dumps",
        "select(",
        "func.max",
        "SnapshotCharacter",
        "CharacterTargetPreset",
        "CharacterTargetVersion",
        "IdempotencyReceipt",
        "def _payload_hash(",
        "def _next_target_version(",
        "def _save_target_row(",
    )
    violations = [marker for marker in forbidden_gateway_markers if marker in gateway]
    assert not violations, (
        "SqliteTargetGateway must remain a facade; query/hash/version mechanics belong in "
        "sqlite/targets primitives: " + ", ".join(violations)
    )


def test_target_preset_prepare_phase_does_not_mutate_before_checkpoint() -> None:
    path = (
        PROJECT_ROOT
        / "infrastructure"
        / "persistence"
        / "sqlite"
        / "targets"
        / "preset_repository.py"
    )
    source = path.read_text(encoding="utf-8")
    prepare = source.split("def prepare_activation(", 1)[1].split("def activate(", 1)[0]
    assert ".is_active =" not in prepare
    assert "db.flush()" not in prepare


def test_today_sqlite_adapter_is_decomposed_into_persistence_primitives() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    facade = sqlite_root / "today_planner.py"
    today_root = sqlite_root / "today"
    expected = {
        "context_reader.py",
        "state_repository.py",
        "plan_run_repository.py",
    }
    missing = [name for name in expected if not (today_root / name).exists()]
    assert not missing, "Today persistence primitives are missing: " + ", ".join(missing)

    source = facade.read_text(encoding="utf-8")
    forbidden_markers = (
        "select(",
        "CharacterTargetVersion",
        "PlanRun(",
        "TodayState(",
        "asdict(",
        "config_payload(",
    )
    violations = [marker for marker in forbidden_markers if marker in source]
    assert not violations, (
        "TodayPlanner must orchestrate small persistence primitives instead of owning ORM mechanics: "
        + ", ".join(violations)
    )
    assert "TodayContextReader(" in source
    assert "TodayStateRepository(" in source
    assert "TodayPlanRunRepository(" in source


def test_today_persistence_primitives_keep_their_responsibilities_separate() -> None:
    today_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "today"
    context = (today_root / "context_reader.py").read_text(encoding="utf-8")
    state = (today_root / "state_repository.py").read_text(encoding="utf-8")
    runs = (today_root / "plan_run_repository.py").read_text(encoding="utf-8")

    assert "Account" in context
    assert "TodayState" not in context
    assert "PlanRun" not in context

    assert "TodayState" in state
    assert "PlanRun" not in state
    assert "CharacterTargetVersion" not in state

    assert "PlanRun" in runs
    assert "CharacterTargetVersion" in runs
    assert "TodayState" not in runs
    assert "Account" not in runs


def test_artifact_exchange_sqlite_facade_is_decomposed_into_small_persistence_primitives() -> None:
    sqlite_root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite"
    facade = (sqlite_root / "artifact_exchange_gateway.py").read_text(encoding="utf-8")
    component_root = sqlite_root / "artifact_exchange"
    required = (
        "context_reader.py",
        "evaluation_writer.py",
        "history_effects.py",
    )
    missing = [name for name in required if not (component_root / name).exists()]
    assert not missing, "Artifact exchange persistence primitives are missing: " + ", ".join(missing)

    forbidden = (
        "SnapshotCharacter",
        "ArtifactEvaluation(",
        "latest_targets(",
        "latest_confirmed(",
        "target_is_complete(",
        "evaluation_payload(",
        "artifact_status(",
        ".query(",
    )
    violations = [marker for marker in forbidden if marker in facade]
    assert not violations, (
        "Artifact exchange facade must coordinate persistence primitives, not own their mechanics: "
        + ", ".join(violations)
    )
    assert "ArtifactExchangeContextReader" in facade
    assert "ArtifactEvaluationWriter" in facade
    assert "ArtifactExchangeHistoryEffects" in facade


def test_artifact_exchange_persistence_primitives_keep_read_write_event_responsibilities_separate() -> None:
    root = PROJECT_ROOT / "infrastructure" / "persistence" / "sqlite" / "artifact_exchange"
    context = (root / "context_reader.py").read_text(encoding="utf-8")
    writer = (root / "evaluation_writer.py").read_text(encoding="utf-8")
    history = (root / "history_effects.py").read_text(encoding="utf-8")

    assert "SnapshotCharacter" in context
    assert "current_artifact_fingerprint(" in context
    assert "load_quality_config(" in context
    assert "ArtifactEvaluation(" not in context
    assert "record_event(" not in context

    assert "ArtifactEvaluation(" in writer
    assert "EvaluationStatus.SUPERSEDED" in writer
    assert "target_is_complete(" not in writer
    assert "record_event(" not in writer

    assert "target_is_complete(" in history
    assert '"ARTIFACT_EVALUATION_CHANGED"' in history
    assert '"ARTIFACT_TARGET_REACHED"' in history
    assert '"CHARACTER_COMPLETED"' in history
    assert '"CHARACTER_REOPENED"' in history
    assert "ArtifactEvaluation(" not in history


def test_planner_gateway_remains_a_thin_reader_facade() -> None:
    path = PROJECT_ROOT / "infrastructure/persistence/sqlite/planner_gateway.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {module for module, _ in _imports(tree, path)}
    allowed = {
        "sqlalchemy.orm", "projectg.application.ports.outbound.planner_gateway",
        "projectg.domain.planning.config", "projectg.infrastructure.configuration.settings",
        *("projectg.infrastructure.persistence.sqlite.planner." + name for name in (
            "snapshot_reader", "configuration_reader", "team_reader", "tier_reader",
            "artifact_evaluation_reader")),
    }
    assert imports <= allowed
    forbidden_nodes = (ast.For, ast.While, ast.ListComp, ast.DictComp, ast.SetComp,
                       ast.GeneratorExp, ast.BinOp, ast.BoolOp, ast.Subscript)
    assert not any(isinstance(node, forbidden_nodes) for node in ast.walk(tree))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in {"scalar", "scalars", "query", "get", "execute", "add", "flush"}
    assert len(path.read_text().splitlines()) < 65


def test_planner_readers_have_narrow_independent_dependencies() -> None:
    root = PROJECT_ROOT / "infrastructure/persistence/sqlite/planner"
    model_owners = {
        "snapshot_reader": {"Account", "SnapshotCharacter", "SnapshotWeapon", "SnapshotArtifact"},
        "team_reader": {"SnapshotTeam", "PlannerTeam"},
        "artifact_evaluation_reader": {"ArtifactEvaluation"},
        "configuration_reader": {"CharacterPriority", "AccountPlanningIntent"}, "tier_reader": set(),
    }
    for name, models in model_owners.items():
        path = root / (name + ".py")
        tree = ast.parse(path.read_text())
        for module, _ in _imports(tree, path):
            assert not module.startswith("projectg.infrastructure.persistence.sqlite.planner.")
            assert not module.startswith(("projectg.application.planning", "projectg.application.use_cases"))
            assert module not in {"projectg.domain.planning.tiers", "projectg.domain.planning.engine",
                                  "projectg.domain.planning.models"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "projectg.infrastructure.persistence.sqlite.models":
                assert {alias.name for alias in node.names} <= models
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"add", "delete", "flush", "commit", "rollback"}
        source = path.read_text()
        for marker in ("PlannerInput", "freshnessStatus", "derive_profile_targets", "label_for",
                       "target_is_complete", "ELIGIBLE_MINIMUMS"):
            assert marker not in source


def test_production_planner_input_construction_is_application_only() -> None:
    for path in PROJECT_ROOT.rglob("*.py"):
        if "application" in path.relative_to(PROJECT_ROOT).parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = node.func
                assert not (isinstance(function, ast.Name) and function.id == "PlannerInput")
                assert not (isinstance(function, ast.Attribute) and function.attr == "PlannerInput")
