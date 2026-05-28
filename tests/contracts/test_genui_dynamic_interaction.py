import jsonschema
import pytest
import yaml
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


def _dynamic_request() -> dict:
    return {
        "request_id": "proposal-visual-choice",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-1",
        "title": "Select the proposal direction",
        "prompt": "Compare the visual options, tradeoffs, and delivery risk before approving.",
        "interaction_kind": "option_comparison",
        "capabilities_needed": [
            "visual_demonstration",
            "multi_axis_selection",
            "structured_revision_capture",
        ],
        "media_items": [
            {
                "id": "ref-hero",
                "title": "Hero frame reference",
                "kind": "image",
                "path": "/media/ref-hero.png",
                "text": "Use this to judge product fidelity.",
            }
        ],
        "review_items": [
            {
                "option_id": "remotion",
                "label": "Remotion",
                "fidelity": "high",
                "iteration_speed": "fast",
            },
            {
                "option_id": "hyperframes",
                "label": "HyperFrames",
                "fidelity": "high",
                "iteration_speed": "medium",
            },
        ],
        "choices": [
            {
                "value": "remotion",
                "label": "Remotion",
                "description": "Best iteration speed for this brief.",
                "recommended": True,
                "preview": {"kind": "text", "text": "Fastest path to reviewed edits."},
            },
            {
                "value": "hyperframes",
                "label": "HyperFrames",
                "description": "More expressive, higher setup cost.",
            },
        ],
        "fields": [
            {
                "id": "revision_notes",
                "label": "Revision notes",
                "type": "textarea",
                "required": False,
                "binding": {
                    "artifact": "production_proposal",
                    "path": "human_feedback.revision_notes",
                },
            }
        ],
    }


def test_dynamic_policy_recommends_genui_when_linear_chat_is_insufficient():
    from lib.genui.interaction_policy import assess_interaction_need

    decision = assess_interaction_need(_dynamic_request())

    assert decision["recommended_mode"] == "media_review_room"
    assert decision["recommended_tool"] == "genui_interaction"
    assert decision["linear_chat_sufficient"] is False
    assert "visual_demonstration" in decision["reasons"]
    assert "multi_axis_selection" in decision["reasons"]


def test_dynamic_policy_keeps_cli_for_single_low_density_question():
    from lib.genui.interaction_policy import assess_interaction_need

    decision = assess_interaction_need(
        {
            "request_id": "quick-confirm",
            "project_id": "demo-ad",
            "pipeline_type": "ad-video",
            "stage": "intake",
            "gate": "clarification",
            "title": "Confirm duration",
            "prompt": "Should the video be 15 seconds?",
            "interaction_kind": "clarification",
            "choices": [
                {"value": "yes", "label": "Yes"},
                {"value": "no", "label": "No"},
            ],
        }
    )

    assert decision["recommended_mode"] == "cli"
    assert decision["linear_chat_sufficient"] is True
    assert decision["recommended_tool"] is None


def test_dynamic_policy_keeps_cli_for_short_approval_gate():
    from lib.genui.interaction_policy import assess_interaction_need

    decision = assess_interaction_need(
        {
            "request_id": "quick-approval",
            "project_id": "demo-ad",
            "pipeline_type": "ad-video",
            "stage": "publish",
            "gate": "final-approval",
            "title": "Approve publish",
            "prompt": "Approve publishing this reviewed output?",
            "interaction_kind": "approval",
            "capabilities_needed": ["approval_gate"],
            "choices": [
                {"value": "approve", "label": "Approve"},
                {"value": "revise", "label": "Revise"},
            ],
        }
    )

    assert decision["recommended_mode"] == "cli"
    assert decision["linear_chat_sufficient"] is True


def test_dynamic_policy_uses_interaction_kind_as_genui_signal():
    from lib.genui.interaction_policy import assess_interaction_need

    for interaction_kind, expected_reason, expected_mode in [
        ("media_review", "media_review", "media_review_room"),
        ("option_comparison", "side_by_side_comparison", "gate_workspace"),
        ("multi_axis_selection", "multi_axis_selection", "gate_workspace"),
        ("structured_revision", "structured_revision_capture", "gate_workspace"),
        ("dynamic_genui", "dynamic_genui", "gate_workspace"),
    ]:
        decision = assess_interaction_need(
            {
                "request_id": f"{interaction_kind}-round",
                "project_id": "demo-ad",
                "pipeline_type": "ad-video",
                "stage": "proposal",
                "gate": "G-1",
                "title": f"{interaction_kind} round",
                "prompt": "This interaction kind itself requires a GenUI surface.",
                "interaction_kind": interaction_kind,
            }
        )

        assert decision["recommended_mode"] == expected_mode
        assert expected_reason in decision["reasons"]


def test_dynamic_policy_uses_cli_fallback_when_browser_unavailable():
    from lib.genui.interaction_policy import assess_interaction_need

    request = _dynamic_request()
    request["browser_available"] = False

    decision = assess_interaction_need(request)

    assert decision["recommended_mode"] == "cli"
    assert decision["recommended_tool"] is None
    assert decision["reasons"] == ["browser_unavailable"]


def test_dynamic_interaction_request_schema_validates_request_shape():
    from lib.genui.dynamic import INTERACTION_REQUEST_SCHEMA, validate_interaction_request

    validate_interaction_request(_dynamic_request())

    bad = _dynamic_request()
    bad["media_items"][0]["path"] = "https://example.test/ref.png"

    with pytest.raises(jsonschema.ValidationError):
        validate_interaction_request(bad)

    traversal = _dynamic_request()
    traversal["media_items"][0]["path"] = "/media/../artifacts/ui/cfg/config.json"

    with pytest.raises(jsonschema.ValidationError):
        validate_interaction_request(traversal)


def test_dynamic_interaction_request_accepts_renderer_field_hints():
    from lib.genui.dynamic import validate_interaction_request

    request = _dynamic_request()
    request["fields"][0]["display"] = {
        "component": "TextAreaField",
        "width": "full",
        "emphasis": "recommended",
    }
    request["fields"][0]["visible_if"] = {
        "field": "selection",
        "operator": "not_empty",
    }

    validate_interaction_request(request)


def test_dynamic_config_exposes_surface_blocks_and_submit_fields():
    import lib.genui.dynamic as dynamic
    from lib.genui.surface import build_dynamic_surface_config, compile_surface_view_spec

    assert not hasattr(dynamic, "build_dynamic_interaction_config")

    config = build_dynamic_surface_config(_dynamic_request())

    assert config["contract"] == "genui_surface"
    assert config["metadata"]["dynamic_interaction"] is True
    assert config["metadata"]["linear_chat_insufficient"] is True

    block_types = {block["type"] for block in config["blocks"]}
    assert "MediaCompare" in block_types
    assert "ConceptComparison" in block_types
    assert "RevisionPatch" in block_types
    assert "ApprovalChecklist" in block_types

    spec = compile_surface_view_spec(config, submit_url="http://127.0.0.1:8123/submit")
    element_types = {element["type"] for element in spec["elements"].values()}
    assert "MediaCompare" in element_types
    assert "ConceptComparison" in element_types
    assert "ApprovalChecklist" in element_types
    assert spec["state"]["values"]["comparison.selection"] == "remotion"
    assert "media.ref-hero" not in spec["state"]["values"]


def test_genui_interaction_tool_prepares_dynamic_round(tmp_path: Path):
    from tools.interaction.genui_interaction import GenUIInteraction
    from tools.tool_registry import registry

    project_dir = tmp_path / "projects" / "demo-ad"
    media_path = project_dir / "media" / "ref-hero.png"
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"sample")

    result = GenUIInteraction().execute(
        {
            "project_dir": str(project_dir),
            "interaction_request": _dynamic_request(),
            "mode": "prepare",
        }
    )

    assert result.success, result.error
    assert result.data["decision"]["recommended_mode"] == "media_review_room"
    assert result.data["renderer"] == "a2ui"
    assert result.data["session_contract"] == "genui_session"
    assert result.data["delegated_tool"] == "genui_session"
    assert result.data["dynamic_interaction"] is True
    assert Path(result.data["config_path"]).exists()
    assert Path(result.data["view_spec_path"]).exists()

    registry.clear()
    registry.discover()
    tool = registry.get("genui_interaction")
    assert tool is not None
    info = tool.get_info()
    assert info["capability"] == "interaction"
    assert "dynamic_genui" in info["capabilities"]
    assert info["input_schema"]["properties"]["interaction_request"]["required"] == [
        "request_id",
        "project_id",
        "pipeline_type",
        "stage",
        "gate",
        "title",
        "prompt",
        "interaction_kind",
    ]


def test_genui_interaction_output_schema_accepts_status_modes(tmp_path: Path):
    from tools.interaction.genui_interaction import GenUIInteraction

    tool = GenUIInteraction()
    validator = jsonschema.Draft202012Validator(tool.output_schema)

    for interaction_kind, expected_mode in [
        ("project_cockpit", "project_cockpit"),
        ("background_status", "background_status"),
    ]:
        result = tool.execute(
            {
                "project_dir": str(tmp_path / "projects" / interaction_kind),
                "interaction_request": {
                    "request_id": interaction_kind.replace("_", "-"),
                    "project_id": "demo-ad",
                    "pipeline_type": "ad-video",
                    "stage": "proposal",
                    "gate": interaction_kind,
                    "title": f"{interaction_kind} round",
                    "prompt": "Show status without mutating canonical artifacts.",
                    "interaction_kind": interaction_kind,
                    "capabilities_needed": ["status_timeline", "artifact_trace"],
                },
                "mode": "prepare",
            }
        )

        assert result.success, result.error
        assert result.data["recommended_mode"] == expected_mode
        validator.validate(result.data)


def test_every_human_approval_gate_exposes_dynamic_genui_router():
    violations: list[str] = []

    def scan_node(path: Path, node: object, label: str) -> None:
        if isinstance(node, dict):
            if node.get("human_approval_default") is True:
                tools = node.get("tools_available") or []
                if "genui_interaction" not in tools:
                    violations.append(f"{path.name}:{label}")
            for key, value in node.items():
                if isinstance(value, list):
                    for idx, item in enumerate(value):
                        if isinstance(item, dict):
                            child_label = item.get("name", idx)
                            scan_node(path, item, f"{label}.{key}.{child_label}" if label else f"{key}.{child_label}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                scan_node(path, item, f"{label}.{idx}")

    for path in sorted((ROOT / "pipeline_defs").glob("*.yaml")):
        if path.name == "framework-smoke.yaml":
            continue
        scan_node(path, yaml.safe_load(path.read_text()), "")

    assert violations == []


def test_agent_guide_requires_per_round_dynamic_genui_decision():
    guide = (ROOT / "AGENT_GUIDE.md").read_text().lower()
    protocol = (ROOT / "skills/meta/genui-interaction.md").read_text().lower()
    architecture = (ROOT / "docs/ARCHITECTURE.md").read_text().lower()

    combined = f"{guide}\n{protocol}\n{architecture}"

    assert "before each substantive human interaction" in combined
    assert "linear chat is sufficient" in combined
    assert "genui_interaction" in combined
    assert "visual demonstration" in combined
    assert "multi-axis selection" in combined
