from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DIRS = (REPO_ROOT / "lib", REPO_ROOT / "tools")
OUTPUT_METHODS = {"write", "write_text"}


def _is_json_call(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "json"
    )


def _has_strict_allow_nan(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "allow_nan":
            return (
                isinstance(keyword.value, ast.Constant)
                and keyword.value.value is False
            )
    return False


def _is_print_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    )


def _is_output_method_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in OUTPUT_METHODS
    )


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _strict_json_offenders() -> list[str]:
    offenders: list[str] = []
    for directory in PRODUCTION_DIRS:
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            parents = _parent_map(tree)
            for node in ast.walk(tree):
                if _is_json_call(node, "dump") and not _has_strict_allow_nan(node):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} json.dump")
                    continue

                if not _is_json_call(node, "dumps") or _has_strict_allow_nan(node):
                    continue

                parent = parents.get(node)
                if _is_print_call(parent) or _is_output_method_call(parent):
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno} json.dumps"
                    )
    return offenders


def test_production_json_outputs_are_strict_json():
    assert _strict_json_offenders() == []


def test_production_json_dumps_reject_non_finite_numbers():
    offenders: list[str] = []
    for directory in PRODUCTION_DIRS:
        for path in sorted(directory.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    (_is_json_call(node, "dump") or _is_json_call(node, "dumps"))
                    and not _has_strict_allow_nan(node)
                ):
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno} "
                        f"json.{node.func.attr}"
                    )

    assert offenders == []
