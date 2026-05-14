"""Ad-video collapsed-stage child gate contract tests."""

import json
from pathlib import Path

import jsonschema
import pytest

from lib.pipeline_loader import (
    SCHEMA_PATH,
    get_checkpoint_stage_order,
    get_required_tools,
    get_stage_order,
    get_stage_review_focus,
    get_stage_skill,
    load_pipeline,
)


def _write_manifest(tmp_path: Path, name: str, stage_lines: list[str]) -> None:
    (tmp_path / f"{name}.yaml").write_text(
        "\n".join(
            [
                f"name: {name}",
                "version: '1.0'",
                "stages:",
                *stage_lines,
            ]
        ),
        encoding="utf-8",
    )


def test_ad_video_top_level_stages_are_generic() -> None:
    manifest = load_pipeline("ad-video")

    assert get_stage_order(manifest) == [
        "research",
        "proposal",
        "script",
        "scene_plan",
        "assets",
        "edit",
        "compose",
        "publish",
    ]


def test_ad_video_checkpoint_order_preserves_governance_child_gates() -> None:
    manifest = load_pipeline("ad-video")

    assert get_checkpoint_stage_order(manifest)[:6] == [
        "research.intake",
        "research.brief_enrichment",
        "research.intelligence",
        "proposal.bible",
        "proposal.idea",
        "proposal.technical_proposal",
    ]


def test_ad_video_child_gates_own_existing_artifacts() -> None:
    manifest = load_pipeline("ad-video")
    gates = {
        unit_id: gate
        for stage in manifest["stages"]
        for gate in stage.get("sub_stages", [])
        for unit_id in [f"{stage['name']}.{gate['name']}"]
    }

    assert gates["research.intake"]["produces"] == ["intake_brief"]
    assert gates["research.brief_enrichment"]["produces"] == ["enriched_brief"]
    assert gates["research.intelligence"]["produces"] == ["intelligence_brief"]
    assert gates["proposal.bible"]["produces"] == ["production_bible"]
    assert gates["proposal.idea"]["produces"] == ["idea_options"]
    assert gates["proposal.technical_proposal"]["produces"] == [
        "production_proposal",
        "decision_log",
    ]


def test_stage_helpers_resolve_dotted_child_gates() -> None:
    manifest = load_pipeline("ad-video")

    assert get_stage_skill(manifest, "proposal.technical_proposal") == (
        "pipelines/ad-video/technical-proposal-director"
    )
    assert any(
        "strategic_approved" in item
        for item in get_stage_review_focus(manifest, "proposal.bible")
    )


def test_required_tools_includes_child_gate_tools() -> None:
    manifest = load_pipeline("ad-video")
    tools = get_required_tools(manifest)

    assert "ad_knowledge_retriever" in tools
    assert "genui_interaction" in tools
    assert "genui_session" in tools


def test_schema_allows_artifact_producing_child_gates_without_lifecycle() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    manifest = {
        "name": "schema-child-gates",
        "version": "1.0",
        "stages": [
            {
                "name": "research",
                "sub_stages": [
                    {
                        "name": "intake",
                        "skill": "pipelines/ad-video/intake-director",
                        "produces": ["intake_brief"],
                        "checkpoint_required": False,
                        "human_approval_default": False,
                    }
                ],
            }
        ],
    }

    jsonschema.validate(instance=manifest, schema=schema)


def test_schema_rejects_dotted_top_level_stage_names(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        "dotted-stage",
        [
            "  - name: research.intake",
        ],
    )

    with pytest.raises(jsonschema.ValidationError, match="does not match"):
        load_pipeline("dotted-stage", defs_dir=tmp_path)


def test_schema_rejects_dotted_child_gate_names(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        "dotted-child",
        [
            "  - name: research",
            "    sub_stages:",
            "      - name: intake.first",
        ],
    )

    with pytest.raises(jsonschema.ValidationError, match="does not match"):
        load_pipeline("dotted-child", defs_dir=tmp_path)


def test_load_pipeline_rejects_duplicate_child_gate_names(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        "duplicate-child",
        [
            "  - name: research",
            "    sub_stages:",
            "      - name: intake",
            "      - name: intake",
        ],
    )

    with pytest.raises(ValueError, match="Duplicate sub-stage name"):
        load_pipeline("duplicate-child", defs_dir=tmp_path)


def test_load_pipeline_validates_artifact_dependencies_across_child_gates(
    tmp_path: Path,
) -> None:
    _write_manifest(
        tmp_path,
        "missing-child-artifact",
        [
            "  - name: research",
            "    sub_stages:",
            "      - name: intelligence",
            "        required_artifacts_in: [enriched_brief]",
            "        produces: [intelligence_brief]",
        ],
    )

    with pytest.raises(ValueError, match="requires artifact"):
        load_pipeline("missing-child-artifact", defs_dir=tmp_path)
