import json
import math
from pathlib import Path

import jsonschema

from schemas.artifacts import ARTIFACT_NAMES, validate_artifact


ROOT = Path(__file__).resolve().parent.parent.parent


def _surface_config() -> dict:
    return {
        "contract": "genui_surface",
        "surface_id": "proposal-workspace",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "mode": "gate_workspace",
        "title": "Proposal Workspace",
        "description": "Compare runtime, reference, and delivery choices before approval.",
        "ag_ui": {
            "thread_id": "demo-ad",
            "run_id": "proposal-workspace",
        },
        "media_refs": [
            {
                "id": "sample_clip",
                "kind": "video",
                "title": "Sample preview",
                "path": "/media/renders/sample_preview.mp4",
            }
        ],
        "artifact_refs": [
            {
                "id": "proposal",
                "artifact": "production_proposal",
                "path": "visual_contract.render_runtime",
                "label": "Render runtime",
            }
        ],
        "trace_refs": [
            {
                "id": "runtime_rule",
                "label": "Runtime selection hard rule",
                "source": "AGENT_GUIDE.md",
                "summary": "Both Remotion and HyperFrames must be presented when available.",
            }
        ],
        "blocks": [
            {
                "id": "runtime",
                "type": "RuntimeComparison",
                "title": "Runtime comparison",
                "binding": {
                    "artifact": "production_proposal",
                    "path": "visual_contract.render_runtime",
                },
                "options": [
                    {
                        "id": "remotion",
                        "label": "Remotion",
                        "summary": "Fast iteration for structured ads.",
                        "tradeoff": "Less expressive for custom shot language.",
                        "recommended": True,
                    },
                    {
                        "id": "hyperframes",
                        "label": "HyperFrames",
                        "summary": "More expressive scene language.",
                        "tradeoff": "Higher setup cost.",
                    },
                ],
            },
            {
                "id": "sample",
                "type": "MediaCompare",
                "title": "Sample review",
                "media_ids": ["sample_clip"],
                "annotation_fields": [
                    {"id": "notes", "label": "Notes", "type": "textarea"},
                    {"id": "approved", "label": "Approve sample", "type": "approval", "required": True},
                ],
            },
            {
                "id": "trace",
                "type": "ArtifactTracePanel",
                "title": "Traceability",
                "artifact_ref_ids": ["proposal"],
                "trace_ref_ids": ["runtime_rule"],
            },
        ],
        "actions": [
            {"id": "approve", "label": "Approve workspace", "kind": "approve", "recommended": True},
            {"id": "revise", "label": "Request revisions", "kind": "revise"},
        ],
    }


def _surface_response() -> dict:
    return {
        "contract": "genui_surface_response",
        "response_id": "resp-proposal-workspace",
        "surface_id": "proposal-workspace",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "submitted_at": "2026-06-03T00:00:00+00:00",
        "action": "approve",
        "values": {"runtime.selection": "remotion", "sample.approved": True},
        "annotations": [
            {
                "block_id": "sample",
                "target_ref": "sample_clip",
                "comment": "Use this pacing.",
            }
        ],
        "selected_refs": ["remotion", "sample_clip"],
        "revision_patches": [
            {
                "artifact": "production_proposal",
                "path": "human_feedback.notes",
                "value": "Keep sample pacing.",
            }
        ],
        "approval_attestations": [
            {
                "id": "proposal-approval",
                "label": "Proposal approval",
                "approved": True,
            }
        ],
        "event_summary": {
            "event_count": 4,
            "last_event_type": "action_click",
        },
        "validation": {"status": "pending", "errors": []},
    }


def test_genui_surface_artifact_names_are_registered():
    assert "ui_form_config" not in ARTIFACT_NAMES
    assert "ui_response" not in ARTIFACT_NAMES
    assert "ui_surface_config" in ARTIFACT_NAMES
    assert "ui_surface_response" in ARTIFACT_NAMES


def test_legacy_genui_form_is_not_a_registered_interaction_tool():
    from tools.tool_registry import registry

    registry.clear()
    registry.discover()

    assert registry.get("genui_form") is None
    assert registry.get("genui_surface") is not None
    assert registry.get("genui_interaction") is not None


def test_ui_surface_config_schema_accepts_product_workspace():
    validate_artifact("ui_surface_config", _surface_config())


def test_ui_surface_config_schema_rejects_canonical_write_actions_and_unsafe_media():
    bad_action = _surface_config()
    bad_action["actions"][0]["canonical_artifact"] = "production_proposal"
    try:
        validate_artifact("ui_surface_config", bad_action)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("ui_surface_config accepted a canonical write action")

    bad_media = _surface_config()
    bad_media["media_refs"][0]["path"] = "https://example.test/sample.mp4"
    try:
        validate_artifact("ui_surface_config", bad_media)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("ui_surface_config accepted an unsafe media path")


def test_ui_surface_response_schema_accepts_agent_reviewable_submission():
    validate_artifact("ui_surface_response", _surface_response())


def test_wait_for_response_accepts_surface_response(tmp_path: Path):
    from lib.genui import wait_for_response

    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(_surface_response()))

    response = wait_for_response(response_path, timeout_seconds=0.05, poll_interval=0.01)

    assert response is not None
    assert response["contract"] == "genui_surface_response"
    assert response["surface_id"] == "proposal-workspace"


def test_wait_for_response_rejects_non_strict_response_json(
    tmp_path: Path, monkeypatch
):
    from lib import genui

    response_path = tmp_path / "response.json"
    response_path.write_text(
        '{"contract":"genui_surface_response","action":"approve","metadata":{"bad":NaN}}\n'
    )
    validated: list[dict] = []
    monkeypatch.setattr(
        genui,
        "validate_surface_response",
        lambda response: validated.append(response),
    )

    response = genui.wait_for_response(
        response_path,
        timeout_seconds=0.02,
        poll_interval=0.001,
    )

    assert response is None
    assert validated == []


def test_cleanup_server_rejects_non_strict_server_state_json(
    tmp_path: Path, monkeypatch
):
    from lib import genui

    state_path = tmp_path / "server.json"
    state_path.write_text('{"pid": NaN}\n')
    matched_pids: list[object] = []
    monkeypatch.setattr(
        genui,
        "_pid_matches_genui_server",
        lambda pid, path: matched_pids.append(pid) or False,
    )

    assert genui.cleanup_server(state_path) is False
    assert matched_pids == []
    assert state_path.exists()


def test_surface_view_spec_uses_product_workspace_components():
    from lib.genui.surface import compile_surface_view_spec

    spec = compile_surface_view_spec(
        _surface_config(),
        submit_url="http://127.0.0.1:8123/submit",
        submit_nonce="nonce",
    )

    element_types = {element["type"] for element in spec["elements"].values()}
    assert spec["contract"] == "genui_surface_view"
    assert spec["renderer"] == "json-render"
    assert "WorkspaceShell" in element_types
    assert "RuntimeComparison" in element_types
    assert "MediaCompare" in element_types
    assert "ArtifactTracePanel" in element_types
    assert spec["state"]["values"]["runtime.selection"] == "remotion"
    assert spec["metadata"]["ag_ui"]["run_id"] == "proposal-workspace"


def test_dynamic_request_builds_surface_gate_workspace_by_default():
    from lib.genui.surface import build_dynamic_surface_config

    request = {
        "request_id": "proposal-runtime",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "title": "Proposal runtime choice",
        "prompt": "Compare runtime options before approval.",
        "interaction_kind": "option_comparison",
        "capabilities_needed": ["side_by_side_comparison", "multi_axis_selection"],
        "choices": [
            {"value": "remotion", "label": "Remotion", "recommended": True},
            {"value": "hyperframes", "label": "HyperFrames"},
        ],
        "review_items": [
            {"option_id": "remotion", "speed": "fast"},
            {"option_id": "hyperframes", "speed": "medium"},
        ],
        "fields": [
            {"id": "revision_notes", "label": "Revision notes", "type": "textarea"}
        ],
    }

    config = build_dynamic_surface_config(request)

    validate_artifact("ui_surface_config", config)
    assert config["contract"] == "genui_surface"
    assert config["mode"] == "gate_workspace"
    assert config["surface_id"] == "proposal-runtime"
    assert {block["type"] for block in config["blocks"]} >= {
        "ConceptComparison",
        "RevisionPatch",
        "ApprovalChecklist",
        "ArtifactTracePanel",
    }


def test_dynamic_surface_preserves_multiselect_and_typed_choice_fields():
    from lib.genui.surface import build_dynamic_surface_config, compile_surface_view_spec

    request = {
        "request_id": "multi-axis",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "title": "Multi-axis selection",
        "prompt": "Pick multiple derivatives and a subtitle mode.",
        "interaction_kind": "multi_axis_selection",
        "allow_multiple": True,
        "choices": [
            {"value": "9x16", "label": "9:16", "recommended": True},
            {"value": "1x1", "label": "1:1"},
        ],
        "fields": [
            {
                "id": "subtitle_mode",
                "label": "Subtitle mode",
                "type": "select",
                "choices": [
                    {"value": "burned_in", "label": "Burned in", "recommended": True},
                    {"value": "off", "label": "Off"},
                ],
            },
            {
                "id": "platforms",
                "label": "Platforms",
                "type": "multiselect",
                "choices": [
                    {"value": "tiktok", "label": "TikTok", "recommended": True},
                    {"value": "reels", "label": "Reels"},
                ],
            },
        ],
    }

    config = build_dynamic_surface_config(request)
    spec = compile_surface_view_spec(config)

    assert spec["state"]["values"]["comparison.selection"] == ["9x16"]
    assert spec["state"]["values"]["revisions.subtitle_mode"] == "burned_in"
    assert spec["state"]["values"]["revisions.platforms"] == ["tiktok"]


def test_dynamic_surface_accepts_renderer_field_hints_and_visibility():
    from lib.genui.surface import build_dynamic_surface_config, surface_response_payload_from_submission

    request = {
        "request_id": "field-hints",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "title": "Field hints",
        "prompt": "Capture revisions.",
        "interaction_kind": "structured_revision",
        "choices": [
            {"value": "approve", "label": "Approve current plan", "recommended": True},
            {"value": "revise", "label": "Request a revision"},
        ],
        "fields": [
            {
                "id": "revision_notes",
                "label": "Revision notes",
                "type": "textarea",
                "default": "stale hidden value",
                "display": {"component": "TextAreaField", "width": "full"},
                "visible_if": {"field": "selection", "operator": "equals", "value": "revise"},
            },
            {
                "id": "required_revision_detail",
                "label": "Required revision detail",
                "type": "textarea",
                "required": True,
                "visible_if": {"field": "selection", "operator": "equals", "value": "revise"},
            },
        ],
    }

    config = build_dynamic_surface_config(request)

    revision_block = next(block for block in config["blocks"] if block["id"] == "revisions")
    assert revision_block["fields"][0]["display"] == {"component": "TextAreaField", "width": "full"}
    assert revision_block["fields"][0]["visible_if"] == {
        "field": "selection",
        "operator": "equals",
        "value": "revise",
    }

    hidden_response = surface_response_payload_from_submission(
        config,
        {
            "action": "approve",
            "values": {
                "comparison.selection": "approve",
                "revisions.revision_notes": "stale hidden value",
                "revisions.required_revision_detail": "hidden required detail",
                "approval.reviewed": True,
            },
        },
    )
    assert "revisions.revision_notes" not in hidden_response["values"]
    assert "revisions.required_revision_detail" not in hidden_response["values"]

    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "comparison.selection": "revise",
                    "revisions.revision_notes": "",
                    "revisions.required_revision_detail": "",
                    "approval.reviewed": True,
                },
            },
        )
    except ValueError as exc:
        assert "Required GenUI compatibility field 'revisions.required_revision_detail' is missing" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a missing visible required field")


def test_surface_abort_action_does_not_require_approval_values():
    from lib.genui.surface import (
        build_dynamic_surface_config,
        surface_response_payload_from_submission,
    )

    config = build_dynamic_surface_config(
        {
            "request_id": "abortable",
            "project_id": "demo-ad",
            "pipeline_type": "ad-video",
            "stage": "proposal",
            "gate": "G-2",
            "title": "Abortable gate",
            "prompt": "Acknowledge before approval.",
            "interaction_kind": "dynamic_genui",
        }
    )

    response = surface_response_payload_from_submission(
        config,
        {
            "action": "abort",
            "values": {},
        },
    )

    assert response["action"] == "abort"
    assert response["values"]["approval.reviewed"] is False


def test_surface_response_preserves_explicit_falsy_submitted_values():
    from lib.genui.surface import surface_response_payload_from_submission

    config = _surface_config()
    config["blocks"].append(
        {
            "id": "review",
            "type": "RevisionPatch",
            "title": "Review changes",
            "fields": [
                {
                    "id": "tagline",
                    "label": "Tagline",
                    "type": "textarea",
                    "default": "old tagline",
                    "binding": {
                        "artifact": "production_proposal",
                        "path": "human_feedback.tagline",
                    },
                },
                {
                    "id": "approved",
                    "label": "Optional approval",
                    "type": "approval",
                    "required": False,
                    "default": True,
                },
                {
                    "id": "channels",
                    "label": "Channels",
                    "type": "multiselect",
                    "choices": [
                        {"value": "youtube", "label": "YouTube", "recommended": True},
                        {"value": "reels", "label": "Reels"},
                    ],
                },
            ],
        }
    )

    response = surface_response_payload_from_submission(
        config,
        {
            "action": "approve",
            "values": {
                "runtime.selection": "remotion",
                "sample.notes": "",
                "sample.approved": True,
                "review.tagline": "",
                "review.approved": False,
                "review.channels": [],
            },
            "revision_patches": [
                {
                    "artifact": "production_proposal",
                    "path": "human_feedback.tagline",
                    "value": "",
                }
            ],
        },
    )

    assert response["values"]["review.tagline"] == ""
    assert response["values"]["review.approved"] is False
    assert response["values"]["review.channels"] == []
    assert response["revision_patches"] == [
        {
            "artifact": "production_proposal",
            "path": "human_feedback.tagline",
            "value": "",
        }
    ]


def test_surface_required_approval_rejects_explicit_false_even_when_default_true():
    from lib.genui.surface import surface_response_payload_from_submission

    config = _surface_config()
    config["blocks"].append(
        {
            "id": "must_ack",
            "type": "ApprovalChecklist",
            "title": "Required attestation",
            "items": [
                {
                    "id": "reviewed",
                    "label": "I reviewed the evidence",
                    "required": True,
                    "approved": True,
                }
            ],
        }
    )

    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "runtime.selection": "remotion",
                    "sample.notes": "",
                    "sample.approved": True,
                    "must_ack.reviewed": False,
                },
            },
        )
    except ValueError as exc:
        assert "Required GenUI compatibility field 'must_ack.reviewed' is missing" in str(exc)
    else:
        raise AssertionError("GenUI compatibility defaulted an explicit false required approval to true")


def test_surface_number_fields_enforce_min_and_max():
    from lib.genui.surface import surface_response_payload_from_submission

    config = _surface_config()
    config["blocks"].append(
        {
            "id": "budget",
            "type": "RevisionPatch",
            "title": "Budget",
            "fields": [
                {"id": "approved_budget", "label": "Budget", "type": "number", "min": 1, "max": 100}
            ],
        }
    )

    response = surface_response_payload_from_submission(
        config,
        {
            "action": "approve",
            "values": {
                "runtime.selection": "remotion",
                "sample.notes": "",
                "sample.approved": True,
                "budget.approved_budget": 20,
            },
        },
    )
    assert response["values"]["budget.approved_budget"] == 20.0

    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "runtime.selection": "remotion",
                    "sample.notes": "",
                    "sample.approved": True,
                    "budget.approved_budget": 101,
                },
            },
        )
    except ValueError as exc:
        assert "above maximum" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a number above configured max")


def test_surface_rejects_unconfigured_semantic_submission_items():
    from lib.genui.surface import surface_response_payload_from_submission

    config = _surface_config()
    base_submission = {
        "action": "approve",
        "values": {
            "runtime.selection": "remotion",
            "sample.notes": "",
            "sample.approved": True,
        },
    }

    bad_revision = dict(base_submission)
    bad_revision["revision_patches"] = [
        {
            "artifact": "production_proposal",
            "path": "human_feedback.notes",
            "value": "unconfigured patch",
        }
    ]
    try:
        surface_response_payload_from_submission(config, bad_revision)
    except ValueError as exc:
        assert "revision patch is not configured" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted an unconfigured revision patch")

    bad_attestation = dict(base_submission)
    bad_attestation["approval_attestations"] = [
        {"id": "fake-approval", "label": "Fake approval", "approved": True}
    ]
    try:
        surface_response_payload_from_submission(config, bad_attestation)
    except ValueError as exc:
        assert "approval attestation is not configured" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted an unconfigured approval attestation")

    bad_annotation = dict(base_submission)
    bad_annotation["annotations"] = [
        {
            "block_id": "sample",
            "target_ref": "not_a_configured_media_ref",
            "comment": "Attach this to the wrong target.",
        }
    ]
    try:
        surface_response_payload_from_submission(config, bad_annotation)
    except ValueError as exc:
        assert "annotation is not configured" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted an unconfigured annotation target")

    bad_selected_ref = dict(base_submission)
    bad_selected_ref["selected_refs"] = ["not_configured"]
    try:
        surface_response_payload_from_submission(config, bad_selected_ref)
    except ValueError as exc:
        assert "selected_refs contains unconfigured refs" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted an unconfigured selected ref")


def test_surface_number_fields_reject_non_finite_values():
    from lib.genui.surface import surface_response_payload_from_submission

    config = _surface_config()
    config["blocks"].append(
        {
            "id": "budget",
            "type": "RevisionPatch",
            "title": "Budget",
            "fields": [
                {"id": "approved_budget", "label": "Budget", "type": "number", "min": 1, "max": 100}
            ],
        }
    )

    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "runtime.selection": "remotion",
                    "sample.notes": "",
                    "sample.approved": True,
                    "budget.approved_budget": float("nan"),
                },
            },
        )
    except ValueError as exc:
        assert "must be finite" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a non-finite number")


def test_surface_rejects_non_finite_freeform_config_and_response_values():
    from lib.genui.surface import surface_response_payload_from_submission, validate_surface_config

    bad_config = _surface_config()
    bad_config["blocks"].append(
        {
            "id": "freeform",
            "type": "RevisionPatch",
            "title": "Freeform",
            "fields": [
                {
                    "id": "notes",
                    "label": "Notes",
                    "type": "textarea",
                    "default": {"not_json": float("nan")},
                }
            ],
        }
    )
    try:
        validate_surface_config(bad_config)
    except ValueError as exc:
        assert "finite JSON number" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a non-finite config default")

    config = _surface_config()
    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "runtime.selection": "remotion",
                    "sample.notes": "",
                    "sample.approved": True,
                },
                "annotations": [
                    {
                        "block_id": "sample",
                        "target_ref": "sample_clip",
                        "comment": "Bad timestamp",
                        "timestamp_seconds": float("nan"),
                    }
                ],
            },
        )
    except ValueError as exc:
        assert "finite JSON number" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a non-finite annotation timestamp")

    try:
        surface_response_payload_from_submission(
            config,
            {
                "action": "approve",
                "values": {
                    "runtime.selection": "remotion",
                    "sample.notes": "",
                    "sample.approved": True,
                },
                "revision_patches": [
                    {
                        "artifact": "production_proposal",
                        "path": "human_feedback.score",
                        "value": float("inf"),
                    }
                ],
            },
        )
    except ValueError as exc:
        assert "finite JSON number" in str(exc)
    else:
        raise AssertionError("GenUI compatibility accepted a non-finite revision patch value")


def test_dynamic_surface_preserves_text_media_refs():
    from lib.genui.surface import build_dynamic_surface_config, compile_surface_view_spec

    config = build_dynamic_surface_config(
        {
            "request_id": "text-media",
            "project_id": "demo-ad",
            "pipeline_type": "ad-video",
            "stage": "bible",
            "gate": "G-I",
            "title": "Text evidence",
            "prompt": "Review text evidence.",
            "interaction_kind": "media_review",
            "media_items": [
                {
                    "id": "source-note",
                    "title": "Evidence note",
                    "kind": "text",
                    "text": "The source says product color must remain silver.",
                }
            ],
        }
    )
    spec = compile_surface_view_spec(config)

    assert config["media_refs"][0]["kind"] == "text"
    assert config["media_refs"][0]["text"] == "The source says product color must remain silver."
    media_block = spec["elements"]["block-media"]
    assert media_block["props"]["mediaRefs"][0]["kind"] == "text"


def test_genui_interaction_uses_surface_tool_for_visual_round(tmp_path: Path):
    from tools.interaction.genui_interaction import GenUIInteraction
    from tools.tool_registry import registry

    result = GenUIInteraction().execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "interaction_request": {
                "request_id": "proposal-runtime",
                "project_id": "demo-ad",
                "pipeline_type": "ad-video",
                "stage": "proposal",
                "gate": "G-2",
                "title": "Proposal runtime choice",
                "prompt": "Compare runtime options before approval.",
                "interaction_kind": "option_comparison",
                "choices": [
                    {"value": "remotion", "label": "Remotion", "recommended": True},
                    {"value": "hyperframes", "label": "HyperFrames"},
                ],
            },
            "mode": "prepare",
            "compatibility_mode": "surface",
        }
    )

    assert result.success, result.error
    assert result.data["surface_contract"] == "genui_surface"
    assert result.data["delegated_tool"] == "genui_surface"
    assert result.data["renderer"] == "json-render"
    assert Path(result.data["config_path"]).exists()
    assert Path(result.data["view_spec_path"]).exists()

    registry.clear()
    registry.discover()
    tool = registry.get("genui_surface")
    assert tool is not None
    info = tool.get_info()
    assert info["capability"] == "interaction"
    assert "project_cockpit" in info["capabilities"]
    assert "gate_workspace" in info["capabilities"]

    router = registry.get("genui_interaction")
    assert router is not None
    assert router.get_info().get("fallback") in (None, "")


def test_genui_surface_serve_does_not_open_browser_by_default(tmp_path: Path, monkeypatch):
    from tools.interaction.genui_surface import GenUISurface

    class FakeProcess:
        pid = 42002

        def poll(self):
            return None

        def terminate(self):
            return None

    tool = GenUISurface()
    opened_urls: list[str] = []
    monkeypatch.setattr(tool, "_choose_port", lambda host: 8124)
    monkeypatch.setattr(tool, "_start_server", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr(tool, "_wait_until_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "_try_open_browser", lambda url: opened_urls.append(url) or True)

    result = tool.execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "config": _surface_config(),
            "mode": "serve",
        }
    )

    assert result.success, result.error
    assert result.data["server_state"] == "running"
    assert result.data["browser_url"]
    assert result.data["browser_opened"] is False
    assert opened_urls == []
    assert not result.data["instructions"].startswith("Open ")
    assert result.data["browser_url"] in result.data["instructions"]

    opt_in_config = {**_surface_config(), "surface_id": "proposal-workspace-open"}
    opt_in_config["ag_ui"] = {
        **opt_in_config["ag_ui"],
        "run_id": "proposal-workspace-open",
    }
    opt_in_result = tool.execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "config": opt_in_config,
            "mode": "serve",
            "open_browser": True,
        }
    )

    assert opt_in_result.success, opt_in_result.error
    assert opt_in_result.data["browser_opened"] is True
    assert opened_urls == [opt_in_result.data["browser_url"]]


def test_genui_surface_rejects_non_finite_server_state_before_writing(
    tmp_path: Path, monkeypatch
):
    from tools.interaction.genui_surface import GenUISurface

    class FakeProcess:
        pid = math.nan
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True
            return None

    project_dir = tmp_path / "projects" / "demo-ad"
    tool = GenUISurface()
    fake_process = FakeProcess()
    monkeypatch.setattr(tool, "_choose_port", lambda host: 8124)
    monkeypatch.setattr(tool, "_start_server", lambda *args, **kwargs: fake_process)
    monkeypatch.setattr(tool, "_wait_until_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(tool, "_try_open_browser", lambda url: True)

    result = tool.execute(
        {
            "project_dir": str(project_dir),
            "config": _surface_config(),
            "mode": "serve",
        }
    )

    assert not result.success
    assert "strict JSON" in result.error
    assert fake_process.terminated is True
    assert not (
        project_dir / "artifacts" / "ui" / "proposal-workspace" / "server.json"
    ).exists()


def test_project_cockpit_snapshot_is_read_only_and_traceable(tmp_path: Path):
    from lib.genui.project_snapshot import build_project_cockpit_config

    project_dir = tmp_path / "projects" / "demo-ad"
    artifact_dir = project_dir / "artifacts"
    renders_dir = project_dir / "renders"
    image_dir = project_dir / "assets" / "images"
    artifact_dir.mkdir(parents=True)
    renders_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    (project_dir / "checkpoint_proposal.json").write_text(
        '{"stage":"proposal","status":"approved","approved":true}\n'
    )
    (project_dir / "checkpoint_script.json").write_text(
        '{"stage":"script","status":"awaiting_human","approved":false}\n'
    )
    (artifact_dir / "decision_log.json").write_text(
        '{"decisions":[{"id":"runtime","category":"render_runtime_selection","selected":"remotion","stage":"proposal"}]}\n'
    )
    (artifact_dir / "production_proposal.json").write_text(
        '{"render_runtime":"remotion","budget":{"approved_budget_usd":150},"cost_estimate":{"total_usd":82.5}}\n'
    )
    (renders_dir / "sample_preview.mp4").write_bytes(b"sample")
    (image_dir / "product_ref.png").write_bytes(b"sample")
    (image_dir / "animated_ref.apng").write_bytes(b"sample")
    outputs_dir = project_dir / "outputs"
    outputs_dir.mkdir()
    (outputs_dir / "final.mp4").write_bytes(b"sample")

    config = build_project_cockpit_config(
        project_dir,
        project_id="demo-ad",
        pipeline_type="ad-video",
        active_stage="proposal",
    )

    validate_artifact("ui_surface_config", config)
    assert config["mode"] == "project_cockpit"
    block_types = {block["type"] for block in config["blocks"]}
    assert "CockpitTimeline" in block_types
    assert "CockpitArtifactGallery" in block_types
    assert any(ref["path"] == "/media/renders/sample_preview.mp4" for ref in config["media_refs"])
    assert any(ref["path"] == "/media/assets/images/product_ref.png" for ref in config["media_refs"])
    assert any(ref["path"] == "/media/assets/images/animated_ref.apng" for ref in config["media_refs"])
    assert any(ref["path"] == "/media/outputs/final.mp4" for ref in config["media_refs"])
    assert all(action["kind"] != "approve" for action in config["actions"])

    blocks = {block["id"]: block for block in config["blocks"]}
    timeline_items = {item["id"]: item for item in blocks["timeline"]["items"]}
    assert timeline_items["proposal"]["status"] == "approved"
    assert timeline_items["script"]["status"] == "awaiting_human"
    assert timeline_items["proposal"]["checkpoint"] == "checkpoint_proposal.json"
    assert blocks["decision_history"]["items"][0]["category"] == "render_runtime_selection"
    assert blocks["budget_cost"]["items"][0]["approved_budget_usd"] == 150
    assert blocks["budget_cost"]["items"][0]["estimated_cost_usd"] == 82.5
    assert set(blocks["media_outputs"]["media_ids"]) == {ref["id"] for ref in config["media_refs"]}

    from lib.genui.server import _validate_media_request_path

    assert _validate_media_request_path("/media/outputs/final.mp4", project_dir) == (
        project_dir / "outputs" / "final.mp4"
    ).resolve()
    assert _validate_media_request_path("/media/assets/images/animated_ref.apng", project_dir) == (
        project_dir / "assets" / "images" / "animated_ref.apng"
    ).resolve()


def test_project_cockpit_rejects_direct_submit_actions(tmp_path: Path):
    from lib.genui.project_snapshot import build_project_cockpit_config
    from lib.genui.surface import surface_response_payload_from_submission

    config = build_project_cockpit_config(
        tmp_path / "projects" / "demo-ad",
        project_id="demo-ad",
        pipeline_type="ad-video",
        active_stage="proposal",
    )
    config["actions"] = [{"id": "refresh", "label": "Refresh", "kind": "refresh"}]

    try:
        surface_response_payload_from_submission(config, {"action": "refresh", "values": {}})
    except ValueError as exc:
        assert "does not accept submissions" in str(exc)
    else:
        raise AssertionError("Read-only project cockpit accepted direct response POST")


def test_surface_docs_and_manifest_keep_surface_as_compatibility_fallback():
    guide = (ROOT / "AGENT_GUIDE.md").read_text().lower()
    protocol = (ROOT / "skills/meta/genui-interaction.md").read_text().lower()
    manifest = (ROOT / "pipeline_defs/ad-video.yaml").read_text().lower()

    combined = f"{guide}\n{protocol}\n{manifest}"

    assert "genui" in combined
    assert "ui_session_config" in combined
    assert "ui_session_response" in combined
    assert "genui_session" in combined
    assert "genui_surface" in combined
    assert "compatibility fallback" in combined
    assert "ui_surface_config" in combined
    assert "ui_surface_response" in combined
    assert "genui_surface" in combined
    assert "project cockpit" in combined
    assert "genui_form" not in manifest


def test_genui_docs_forbid_native_agent_ui_as_genui_substitute():
    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    protocol = (ROOT / "skills/meta/genui-interaction.md").read_text(encoding="utf-8")
    agent_behavior = (ROOT / "project_profile/agent_behavior.md").read_text(
        encoding="utf-8"
    )

    combined = f"{guide}\n{protocol}\n{agent_behavior}"
    normalized = combined.lower()

    assert "agent-native question or form tools are not genui" in normalized
    assert "claude code `askuserquestion`" in normalized
    assert "codex `request_user_input`" in normalized
    assert "genui_interaction" in combined
    assert "genui_session" in combined
    assert (
        "user-declined browser path" in normalized
        or "user declines the browser path" in normalized
    )


def test_genui_protocol_includes_registry_invocation_template():
    protocol = (ROOT / "skills/meta/genui-interaction.md").read_text(
        encoding="utf-8"
    )

    assert "Registry Invocation Template" in protocol
    assert "from tools.tool_registry import registry" in protocol
    assert 'registry.get("genui_interaction")' in protocol
    assert '"mode": "serve"' in protocol
    assert '"open_browser": False' in protocol
    assert 'result.data["browser_url"]' in protocol
    assert 'result.data["response_path"]' in protocol


def test_genui_docs_include_required_gate_evidence_check():
    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    protocol = (ROOT / "skills/meta/genui-interaction.md").read_text(
        encoding="utf-8"
    )
    agent_behavior = (ROOT / "project_profile/agent_behavior.md").read_text(
        encoding="utf-8"
    )

    combined = f"{guide}\n{protocol}\n{agent_behavior}"
    normalized = combined.lower()

    assert "genui_required_gate_evidence_report" in combined
    assert "genui_evidence_check" in combined
    assert 'registry.get("genui_evidence_check")' in combined
    assert "make genui-evidence-check" in combined
    assert "python -m tools.validation.genui_evidence_check" in combined
    assert "ui_interaction_journal" in combined
    assert "ui_session_response" in combined
    assert "ui_surface_response" in combined
    assert "schema-valid" in normalized
    assert "fallback reason" in normalized
    assert "genui_evidence_required" in combined
    assert "genui_evidence_gate" in combined
    assert "completed checkpoint" in normalized
