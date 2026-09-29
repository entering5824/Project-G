"""Prevent resource scoring and inventory semantics returning to decisions."""
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "src/projectg"


def test_strategic_ranking_cannot_import_costs_catalog_or_today_availability():
    for name in ("scorer.py", "simulator.py", "today/selection.py"):
        tree = ast.parse((ROOT / "domain/planning" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert not any(token in module for token in ("costs", "game_catalog", "availability", "persistence"))


def test_runtime_has_no_resource_priority_or_inventory_output_fields():
    forbidden = {"missingResources", "missing_resources", "missingSummary", "requiredResources",
                 "sharedBonus", "batchContribution", "sourceRoadmap", "sourceRoadmapEnabled", "farmRoadmap"}
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in forbidden, (path, node.value)
            if isinstance(node, ast.Attribute):
                assert node.attr not in forbidden, (path, node.attr)


def test_today_checks_availability_only_behind_explicit_resource_policy():
    source = (ROOT / "domain/planning/today/compiler.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Attribute) and node.func.attr == "is_available"]
    assert len(calls) == 1
    guarded = [node for node in ast.walk(tree) if isinstance(node, ast.If)
               and "TALENT_BOOK_AFFECTS_TODAY" in ast.unparse(node.test)
               and calls[0] in list(ast.walk(node))]
    assert len(guarded) == 1


def test_removed_source_ranking_modules_do_not_reappear():
    assert not (ROOT / "domain/planning/farm_sources.py").exists()
    assert not (ROOT / "domain/planning/farm_priority.py").exists()
