"""Pipeline manifest loader contract tests."""

from pathlib import Path

from lib.pipeline_loader import get_required_tools, load_pipeline


def test_load_pipeline_rejects_path_traversal_names():
    try:
        load_pipeline("../config")
    except ValueError as exc:
        assert "Pipeline name" in str(exc)
    else:
        raise AssertionError("Expected path-like pipeline name to be rejected")


def test_load_pipeline_rejects_duplicate_stage_names(tmp_path: Path):
    (tmp_path / "dup.yaml").write_text(
        "\n".join(
            [
                "name: dup",
                "version: '1.0'",
                "stages:",
                "  - name: script",
                "  - name: script",
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_pipeline("dup", defs_dir=tmp_path)
    except ValueError as exc:
        assert "Duplicate stage name" in str(exc)
    else:
        raise AssertionError("Expected duplicate stage names to be rejected")


def test_load_pipeline_rejects_forward_artifact_dependencies(tmp_path: Path):
    (tmp_path / "bad-dependency.yaml").write_text(
        "\n".join(
            [
                "name: bad-dependency",
                "version: '1.0'",
                "stages:",
                "  - name: script",
                "    required_artifacts_in: [scene_plan]",
                "    produces: [script]",
                "  - name: scene_plan",
                "    produces: [scene_plan]",
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_pipeline("bad-dependency", defs_dir=tmp_path)
    except ValueError as exc:
        assert "requires artifact" in str(exc)
    else:
        raise AssertionError("Expected forward artifact dependency to be rejected")


def test_get_required_tools_includes_production_mode_tools():
    manifest = load_pipeline("screen-demo")

    tools = get_required_tools(manifest)

    assert "screen_recorder" in tools
    assert "cap_recorder" in tools


def test_get_required_tools_includes_stage_required_and_optional_tools():
    manifest = {
        "stages": [
            {
                "name": "script",
                "required_tools": ["stage_required_tool"],
                "optional_tools": ["stage_optional_tool"],
            }
        ],
    }

    tools = get_required_tools(manifest)

    assert "stage_required_tool" in tools
    assert "stage_optional_tool" in tools
