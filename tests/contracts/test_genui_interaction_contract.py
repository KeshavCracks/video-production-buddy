from pathlib import Path
import json

import jsonschema
import pytest

from schemas.artifacts import ARTIFACT_NAMES, validate_artifact


ROOT = Path(__file__).resolve().parent.parent.parent


def _surface_config() -> dict:
    return {
        "contract": "genui_surface",
        "surface_id": "cfg-ad-video-g0",
        "project_id": "demo-ad",
        "pipeline_type": "ad-video",
        "stage": "brief_enrichment",
        "gate": "G-0",
        "mode": "gate_workspace",
        "title": "Creative Requirements Workspace",
        "description": "Review the prefilled ad requirements before enrichment.",
        "ag_ui": {
            "thread_id": "demo-ad",
            "run_id": "cfg-ad-video-g0",
        },
        "media_refs": [],
        "artifact_refs": [
            {
                "id": "enriched-brief-product",
                "artifact": "enriched_brief",
                "path": "creative_requirements.product_model.value",
                "label": "Product model",
            }
        ],
        "trace_refs": [
            {
                "id": "agent-review-boundary",
                "label": "Agent review boundary",
                "source": "AGENT_GUIDE.md",
                "summary": "GenUI collects choices only; the agent validates before canonical writes.",
            }
        ],
        "blocks": [
            {
                "id": "context",
                "type": "BriefWorksheet",
                "title": "Context",
                "items": [{"label": "Product/model", "value": "OPPO Find X9 Pro"}],
            },
            {
                "id": "revisions",
                "type": "RevisionPatch",
                "title": "Structured revisions",
                "fields": [
                    {
                        "id": "product_model",
                        "label": "Product/model",
                        "type": "text",
                        "required": True,
                        "default": "OPPO Find X9 Pro",
                        "binding": {
                            "artifact": "enriched_brief",
                            "path": "creative_requirements.product_model.value",
                        },
                    }
                ],
                "artifact_ref_ids": ["enriched-brief-product"],
            },
            {
                "id": "approval",
                "type": "ApprovalChecklist",
                "title": "Approval contract",
                "items": [
                    {
                        "id": "reviewed",
                        "label": "I reviewed this workspace.",
                        "required": True,
                    }
                ],
            },
            {
                "id": "trace",
                "type": "ArtifactTracePanel",
                "title": "Traceability",
                "artifact_ref_ids": ["enriched-brief-product"],
                "trace_ref_ids": ["agent-review-boundary"],
            },
        ],
        "actions": [
            {
                "id": "approve",
                "label": "Approve workspace",
                "kind": "approve",
                "recommended": True,
            },
            {
                "id": "revise",
                "label": "Send revisions",
                "kind": "revise",
            },
        ],
    }


def test_genui_public_artifacts_include_journal_sessions_and_fallback_surfaces():
    assert "ui_form_config" not in ARTIFACT_NAMES
    assert "ui_response" not in ARTIFACT_NAMES
    assert "visual_need_assessment" in ARTIFACT_NAMES
    assert "ui_interaction_journal" in ARTIFACT_NAMES
    assert "ui_session_config" in ARTIFACT_NAMES
    assert "ui_session_response" in ARTIFACT_NAMES
    assert "ui_surface_config" in ARTIFACT_NAMES
    assert "ui_surface_response" in ARTIFACT_NAMES


def test_ui_surface_config_schema_accepts_workspace_config():
    validate_artifact("ui_surface_config", _surface_config())


def test_ui_surface_config_rejects_direct_canonical_write_action():
    bad = _surface_config()
    bad["actions"][0]["canonical_artifact"] = "enriched_brief"

    with pytest.raises(jsonschema.ValidationError):
        validate_artifact("ui_surface_config", bad)


def test_ad_video_skills_document_workspace_first_and_cli_fallback():
    skill_paths = [
        ROOT / "skills/pipelines/ad-video/brief-enrichment-director.md",
        ROOT / "skills/pipelines/ad-video/bible-director.md",
        ROOT / "skills/pipelines/ad-video/proposal-director.md",
        ROOT / "skills/pipelines/ad-video/script-director.md",
        ROOT / "skills/pipelines/ad-video/asset-director.md",
    ]
    combined = "\n".join(path.read_text() for path in skill_paths).lower()

    assert "genui" in combined
    assert "ui_session_response" in combined
    assert "cli fallback" in combined or "cli path" in combined
    assert "must not write canonical" in combined


def test_genui_cli_fallback_is_failure_or_explicit_decline_only():
    paths = [
        ROOT / "skills/meta/genui-interaction.md",
        ROOT / "skills/pipelines/ad-video/brief-enrichment-director.md",
        ROOT / "skills/pipelines/ad-video/bible-director.md",
        ROOT / "skills/pipelines/ad-video/proposal-director.md",
        ROOT / "skills/pipelines/ad-video/script-director.md",
        ROOT / "skills/pipelines/ad-video/asset-director.md",
    ]

    for path in paths:
        text = " ".join(path.read_text().lower().replace("`", "").split())
        assert "genui_session execution fails" in text, path
        assert "explicitly declines the browser path" in text, path
        assert "localhost url counts as browser path available" in text, path


def test_agent_guide_describes_genui_as_interaction_layer_not_orchestrator():
    guide = (ROOT / "AGENT_GUIDE.md").read_text().lower()

    assert "genui" in guide
    assert "interaction layer" in guide
    assert "not an orchestrator" in guide
    assert "canonical artifacts" in guide


def test_architecture_docs_include_genui_interaction_layer():
    architecture = (ROOT / "docs/ARCHITECTURE.md").read_text().lower()
    context = (ROOT / "PROJECT_CONTEXT.md").read_text().lower()
    agent_guide = (ROOT / "AGENT_GUIDE.md").read_text().lower()
    genui_skill = (ROOT / "skills/meta/genui-interaction.md").read_text().lower()
    combined = f"{architecture}\n{context}"

    assert "genui" in combined
    assert "ui_interaction_journal" in architecture
    assert "ui_session_config" in architecture
    assert "ui_session_response" in architecture
    assert "ui_surface_config" in architecture
    assert "ui_surface_response" in architecture
    assert "interaction layer" in combined
    assert "not an orchestrator" in combined
    assert "a2ui" in architecture
    assert "a2ui" in context
    assert "a2ui" in agent_guide
    assert "a2ui" in genui_skill
    assert "json-render" in architecture
    assert "json-render" in context
    assert "json-render" in agent_guide
    assert "json-render" in genui_skill


def test_genui_surface_view_spec_schema_accepts_compiled_json_render_spec():
    from lib.genui.surface import compile_surface_view_spec

    schema = jsonschema.Draft202012Validator(
        json.loads((ROOT / "schemas/genui/view_spec.schema.json").read_text())
    )
    spec = compile_surface_view_spec(_surface_config(), submit_url="http://127.0.0.1:8123/submit")

    schema.validate(spec)
    assert spec["renderer"] == "json-render"
    assert spec["elements"]["genui-root"]["type"] == "WorkspaceShell"


def test_genui_surface_view_spec_rejects_unknown_catalog_component():
    from lib.genui.surface import compile_surface_view_spec
    from lib.genui.view_spec import validate_view_spec

    spec = compile_surface_view_spec(_surface_config())
    spec["elements"]["genui-root"]["type"] = "ArbitraryGeneratedCode"

    with pytest.raises(ValueError, match="unknown json-render component"):
        validate_view_spec(spec)
