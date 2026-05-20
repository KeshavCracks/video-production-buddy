"""Pipeline manifest loader contract tests."""

from lib.pipeline_loader import get_required_tools, load_pipeline


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
                "tools_available": [],
            }
        ],
    }

    tools = get_required_tools(manifest)

    assert "stage_required_tool" in tools
    assert "stage_optional_tool" in tools
