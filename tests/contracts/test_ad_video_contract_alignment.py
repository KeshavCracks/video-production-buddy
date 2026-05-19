"""Ad-video schema/director/tool contract alignment regressions."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from schemas.artifacts import validate_artifact
from tools.validation.product_identity_consistency_check import (
    check_product_identity_consistency,
)
from tools.validation.runtime_consistency_check import check_runtime_consistency
from tools.validation.scene_fidelity_check import check_kvm_coverage
from tools.video.video_compose import VideoCompose


ROOT = Path(__file__).resolve().parent.parent.parent
AD_VIDEO_SKILLS = ROOT / "skills" / "pipelines" / "ad-video"
AD_VIDEO_MANIFEST = ROOT / "pipeline_defs" / "ad-video.yaml"


def _read_skill(name: str) -> str:
    return (AD_VIDEO_SKILLS / name).read_text(encoding="utf-8")


def _load_ad_video_manifest() -> dict:
    return yaml.safe_load(AD_VIDEO_MANIFEST.read_text(encoding="utf-8"))


def _json_fences(markdown: str) -> list[str]:
    return re.findall(r"```json\s*\n(.*?)\n```", markdown, flags=re.DOTALL)


def _minimal_production_proposal() -> dict:
    return {
        "version": "1.0",
        "selected_idea_id": "C2",
        "style_mode": "cinematic",
        "render_runtime": "ffmpeg",
        "product_reference_strategy": "generate_concept_reference",
        "subtitles": {"mode": "burnt-in", "language": "en", "user_confirmed": True},
        "dubbing": [],
        "derivatives_added": [],
        "budget_confirmed": True,
        "approved_budget_usd": 5.0,
        "music_strategy": "generative_loose",
        "audio_contract": {
            "voice_provider": "qwen3",
            "voice_id": "Dylan",
            "target_speed_wps": 2.5,
            "target_lufs": -14,
            "max_section_drift_pct": 5,
            "duck_depth_db": -18,
        },
        "visual_contract": {
            "style_direction": "editorial-tech",
            "typography_pairing": {
                "display": "Inter 800",
                "body": "Inter 400",
            },
            "color_rhythm": "held-accent",
            "atmosphere": {"default_layers": [{"type": "grain", "intensity": 0.04}]},
            "anti_template_checklist": ["hero product visible before the CTA"],
        },
    }


def test_scene_plan_schema_accepts_animated_scene_contract_fields() -> None:
    """Animated scene-director fields must validate under scene_plan.schema.json."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "animated",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-1",
                "type": "animation",
                "scene_type": "text_card",
                "description": "Hook text slams into frame.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": False,
                "product_visibility": "none",
                "product_reference_required": False,
                "fulfills_kvm": ["KVM-1"],
                "motion_specs": ["text_entrance_fade"],
                "style_layers": [
                    {"type": "grain", "intensity": 0.06},
                    {"type": "ambient_glow", "color": "#FF3B30", "pulse": True},
                ],
            }
        ],
    }

    validate_artifact("scene_plan", scene_plan)


def test_production_proposal_schema_requires_product_reference_strategy() -> None:
    """Proposal must lock the product-reference strategy before assets can run."""
    proposal = _minimal_production_proposal()
    validate_artifact("production_proposal", proposal)

    for strategy in [
        "not_applicable",
        "use_provided_reference",
        "generate_concept_reference",
        "risk_accepted",
    ]:
        proposal["product_reference_strategy"] = strategy
        validate_artifact("production_proposal", proposal)

    bad = _minimal_production_proposal()
    del bad["product_reference_strategy"]
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)

    bad = _minimal_production_proposal()
    bad["product_reference_strategy"] = "text_prompt_only"
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)


def test_scene_plan_schema_requires_product_visibility_metadata_for_ad_video() -> None:
    """Ad-video scenes must declare whether product identity conditioning is needed."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "cinematic",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "Macro hero shot of the product camera module.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
            }
        ],
    }

    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)

    scene_plan["scenes"][0]["product_visibility"] = "hero"
    scene_plan["scenes"][0]["product_reference_required"] = True
    validate_artifact("scene_plan", scene_plan)

    scene_plan["scenes"][0]["product_reference_required"] = False
    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)


def test_asset_manifest_schema_accepts_product_identity_conditioning_metadata() -> None:
    """Product-visible generated assets must be able to record conditioning metadata."""
    manifest = {
        "version": "1.0",
        "assets": [
            {
                "id": "scene-1-video",
                "type": "video",
                "path": "assets/video/scene-1.mp4",
                "source_tool": "wan_video_api",
                "scene_id": "scene-1",
                "model": "wan2.7-i2v",
                "product_identity_conditioning": {
                    "approved_reference_id": "pir-001",
                    "approved_reference_path": "reference_assets/product_phone.png",
                    "conditioning_mode": "reference_to_video",
                    "generation_tool": "wan_video_api",
                    "generation_model": "wan2.7-i2v",
                    "fidelity_verdict": "PASS",
                },
            }
        ],
    }
    validate_artifact("asset_manifest", manifest)

    bad = deepcopy(manifest)
    del bad["assets"][0]["product_identity_conditioning"]["conditioning_mode"]
    with pytest.raises(Exception):
        validate_artifact("asset_manifest", bad)

    bad = deepcopy(manifest)
    del bad["assets"][0]["product_identity_conditioning"]["approved_reference_path"]
    with pytest.raises(Exception):
        validate_artifact("asset_manifest", bad)

    waived = deepcopy(manifest)
    conditioning = waived["assets"][0]["product_identity_conditioning"]
    conditioning["conditioning_mode"] = "text_only_waived"
    conditioning["waiver_decision_id"] = "d-002"
    del conditioning["approved_reference_id"]
    del conditioning["approved_reference_path"]
    validate_artifact("asset_manifest", waived)

    bad = deepcopy(waived)
    del bad["assets"][0]["product_identity_conditioning"]["waiver_decision_id"]
    with pytest.raises(Exception):
        validate_artifact("asset_manifest", bad)


def test_ad_video_scene_plan_schema_requires_scene_governance_fields() -> None:
    """Ad-video scene plans must carry fields used by derivative and motion gates."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "cinematic",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "A moving lifestyle scene.",
                "start_seconds": 0,
                "end_seconds": 5,
            }
        ],
    }

    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)


def test_ad_video_scene_plan_schema_requires_crop_regions_for_derivatives() -> None:
    """Derivative variants are not renderable unless every scene has crop regions."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "cinematic",
        "total_duration_seconds": 5,
        "derivative_variants": ["9:16"],
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "A moving lifestyle scene.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
            }
        ],
    }

    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)

    scene_plan["scenes"][0]["crop_regions"] = {}
    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)

    scene_plan["scenes"][0]["crop_regions"] = {
        "1:1": {"x": 0, "y": 0, "w": 1080, "h": 1080}
    }
    with pytest.raises(Exception):
        validate_artifact("scene_plan", scene_plan)

    scene_plan["scenes"][0]["crop_regions"] = {
        "9:16": {"x": 656, "y": 0, "w": 608, "h": 1080}
    }
    scene_plan["scenes"][0]["product_visibility"] = "none"
    scene_plan["scenes"][0]["product_reference_required"] = False
    validate_artifact("scene_plan", scene_plan)


def test_production_bible_schema_allows_runtime_deferral_until_proposal() -> None:
    """Bible runs before proposal, so render_runtime must be optional there."""
    from tests.qa.test_artifact_chain import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["visual"].pop("render_runtime")

    validate_artifact("production_bible", bible)


def test_production_bible_schema_requires_kvm_motion_primitives() -> None:
    """Bible KVMs must name the scene motion primitives needed to fulfill them."""
    from tests.qa.test_artifact_chain import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    for kvm in bible["visual"]["key_visual_moments"]:
        kvm["required_motion_primitives"] = ["text_entrance_fade"]
    validate_artifact("production_bible", bible)

    bad = deepcopy(bible)
    del bad["visual"]["key_visual_moments"][0]["required_motion_primitives"]
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)

    bad = deepcopy(bible)
    bad["visual"]["key_visual_moments"][0]["required_motion_primitives"] = []
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)


def test_ad_video_ep_reads_proposal_locks_after_proposal_approval() -> None:
    """EP_STATE must use proposal-stage locks, not optional bible audit copies."""
    ep = _read_skill("executive-producer.md")

    assert "`style_mode` from `production_proposal.style_mode`" in ep
    assert "`render_runtime` from `production_proposal.render_runtime`" in ep
    assert "`derivative_variants` from `production_proposal.derivatives_added`" in ep
    assert "`render_runtime` from `production_bible.visual.render_runtime`" not in ep
    assert "`derivative_variants` from `production_bible.deliverables.derivatives`" not in ep
    assert "render_runtime locked in production_bible.visual.render_runtime" not in ep


def test_brief_enrichment_director_references_artifact_schema_path() -> None:
    """Skill prerequisites should point to the real schema location."""
    brief_enrichment = _read_skill("brief-enrichment-director.md")

    assert "schemas/artifacts/enriched_brief.schema.json" in brief_enrichment
    assert "schemas/enriched_brief.schema.json" not in brief_enrichment


def test_brief_enrichment_director_requires_creative_requirements_worksheet_before_g0() -> None:
    """Every ad-video brief must pass a structured creative-director worksheet before G-0."""
    brief_enrichment = _read_skill("brief-enrichment-director.md")

    assert "Creative Requirements Worksheet" in brief_enrichment
    assert "`creative_requirements`" in brief_enrichment
    assert "`product_model`" in brief_enrichment
    assert "`core_selling_points`" in brief_enrichment
    assert "`platform_duration`" in brief_enrichment
    assert "`target_audience`" in brief_enrichment
    assert "`tone_style`" in brief_enrichment
    assert "`visual_approach`" in brief_enrichment
    assert "`language_voiceover`" in brief_enrichment
    assert "`mandatory_marketing`" in brief_enrichment
    assert "`cta`" in brief_enrichment
    assert "`product_fidelity_references`" in brief_enrichment
    assert "RECOMMEND FOR ME" in brief_enrichment
    assert "FROM BRIEF or DELEGATED" in brief_enrichment


def test_intelligence_director_validates_delegated_dimensions() -> None:
    """Delegated dimensions are recommendations, so intelligence must validate them."""
    intelligence = _read_skill("intelligence-director.md")

    assert "status == \"INFERRED\" or status == \"DELEGATED\"" in intelligence
    assert "DELEGATED" in intelligence
    assert "FROM BRIEF" in intelligence


def test_executive_producer_gate_g0_checks_creative_requirements() -> None:
    """EP Gate G-0 must block if the worksheet is missing or silently inferred."""
    ep = _read_skill("executive-producer.md")

    assert "creative_requirements" in ep
    assert "product_model" in ep
    assert "product_fidelity_references" in ep
    assert "FROM BRIEF or DELEGATED" in ep


def test_ad_video_manifest_brief_enrichment_review_focus_checks_creative_requirements() -> None:
    """Manifest review focus should make worksheet completeness a stage contract."""
    manifest = _load_ad_video_manifest()
    brief_enrichment_stage = next(stage for stage in manifest["stages"] if stage["name"] == "brief_enrichment")
    focus_text = "\n".join(brief_enrichment_stage.get("review_focus", []))

    assert "creative_requirements" in focus_text
    assert "FROM BRIEF or DELEGATED" in focus_text
    assert "No required worksheet dimension is INFERRED" in focus_text


def test_ad_video_manifest_proposal_success_criteria_use_proposal_locks() -> None:
    """The manifest should not require back-writing proposal locks into bible."""
    manifest = _load_ad_video_manifest()
    proposal_stage = next(stage for stage in manifest["stages"] if stage["name"] == "proposal")
    success_text = "\n".join(proposal_stage.get("success_criteria", []))

    assert "production_proposal.render_runtime" in success_text
    assert "production_proposal.derivatives_added" in success_text
    assert "production_bible.visual.render_runtime" not in success_text
    assert "deliverables.derivatives populated in production_bible" not in success_text


def test_executive_producer_script_gate_uses_locked_audio_contract_rate() -> None:
    """EP script review must mirror script-director's target_speed_wps contract."""
    ep = _read_skill("executive-producer.md")

    assert "production_proposal.audio_contract.target_speed_wps" in ep
    assert "target_words = target_duration_seconds × 2.5" not in ep


def test_ad_video_manifest_script_gate_uses_locked_audio_contract_rate() -> None:
    """The manifest script-stage review contract must match the EP/script-director gate."""
    manifest = _load_ad_video_manifest()
    script_stage = next(stage for stage in manifest["stages"] if stage["name"] == "script")
    gate_text = "\n".join(
        script_stage.get("review_focus", []) + script_stage.get("success_criteria", [])
    )

    assert "production_proposal.audio_contract.target_speed_wps" in gate_text
    assert "target_duration_seconds × 2.5" not in gate_text


def test_proposal_director_does_not_teach_backwriting_locks_to_bible() -> None:
    """Proposal should produce production_proposal locks instead of mutating bible locks."""
    proposal = _read_skill("proposal-director.md")

    assert "Populate `deliverables.derivatives` in production_bible" not in proposal
    assert "Lock `visual.style_mode` in production_bible" not in proposal
    assert "Lock `visual.render_runtime` in production_bible" not in proposal
    assert "`production_proposal.derivatives_added[]`" in proposal
    assert "`production_proposal.render_runtime`" in proposal


def test_kvm_coverage_reads_visual_key_visual_moments() -> None:
    bible = {
        "visual": {
            "key_visual_moments": [
                {
                    "moment_id": "KVM-1",
                    "description": "Product reveal lands at the emotional peak.",
                    "maps_to_beat": "B3",
                    "mandatory": True,
                }
            ]
        }
    }
    scene_plan = {"scenes": [{"id": "scene-1", "fulfills_kvm": []}]}

    report = check_kvm_coverage(bible, scene_plan)

    assert report["summary"]["kvms_checked"] == 1
    assert report["ok"] is False
    assert report["issues"][0]["kvm_id"] == "KVM-1"


def test_runtime_consistency_accepts_user_approved_decision_log_swap() -> None:
    proposal = {"render_runtime": "remotion"}
    edit_decisions = {"render_runtime": "hyperframes"}
    decision_log = {
        "version": "1.0",
        "project_id": "runtime-swap-regression",
        "decisions": [
            {
                "decision_id": "d-001",
                "stage": "proposal",
                "category": "render_runtime_selection",
                "subject": "Composition runtime",
                "options_considered": [
                    {
                        "option_id": "remotion",
                        "label": "Remotion",
                        "score": 0.8,
                        "reason": "Available baseline",
                    },
                    {
                        "option_id": "hyperframes",
                        "label": "HyperFrames",
                        "score": 0.9,
                        "reason": "Better for the approved kinetic typography route",
                    },
                ],
                "selected": "hyperframes",
                "reason": "User approved HyperFrames after seeing the tradeoff.",
                "user_visible": True,
                "user_approved": True,
            }
        ],
    }

    verdict = check_runtime_consistency(proposal, edit_decisions, decision_log)

    assert verdict["status"] == "PASS"
    assert verdict["decision_present"] is True
    assert verdict["decision_user_approved"] is True
    assert verdict["decision_selected_runtime"] == "hyperframes"
    assert verdict["decision_matches_actual"] is True


def test_runtime_consistency_rejects_approved_old_selection_for_new_actual() -> None:
    proposal = {"render_runtime": "remotion"}
    edit_decisions = {"render_runtime": "hyperframes"}
    decision_log = {
        "version": "1.0",
        "project_id": "runtime-swap-regression",
        "decisions": [
            {
                "decision_id": "d-001",
                "stage": "proposal",
                "category": "render_runtime_selection",
                "subject": "Composition runtime",
                "options_considered": [
                    {
                        "option_id": "remotion",
                        "label": "Remotion",
                        "score": 0.9,
                        "reason": "User originally approved Remotion",
                    },
                    {
                        "option_id": "hyperframes",
                        "label": "HyperFrames",
                        "score": 0.7,
                        "reason": "Considered but rejected",
                    },
                ],
                "selected": "remotion",
                "reason": "Initial proposal approval selected Remotion.",
                "user_visible": True,
                "user_approved": True,
            }
        ],
    }

    verdict = check_runtime_consistency(proposal, edit_decisions, decision_log)

    assert verdict["status"] == "FAIL"
    assert verdict["decision_present"] is True
    assert verdict["decision_user_approved"] is True
    assert verdict["decision_selected_runtime"] == "remotion"
    assert verdict["decision_matches_actual"] is False
    assert any("selected 'remotion'" in issue for issue in verdict["issues"])


def test_runtime_consistency_rejects_approved_swap_without_selected_runtime() -> None:
    proposal = {"render_runtime": "remotion"}
    edit_decisions = {"render_runtime": "hyperframes"}
    decision_log = {
        "version": "1.0",
        "project_id": "runtime-swap-regression",
        "decisions": [
            {
                "decision_id": "d-001",
                "stage": "edit",
                "category": "render_runtime_selection",
                "subject": "Composition runtime",
                "options_considered": [],
                "reason": "User approved a runtime swap, but the selected runtime was not recorded.",
                "user_visible": True,
                "user_approved": True,
            }
        ],
    }

    verdict = check_runtime_consistency(proposal, edit_decisions, decision_log)

    assert verdict["status"] == "FAIL"
    assert verdict["decision_selected_runtime"] is None
    assert verdict["decision_matches_actual"] is False
    assert any("does not select actual runtime 'hyperframes'" in issue for issue in verdict["issues"])


def test_decision_log_accepts_product_identity_reference_selection_category() -> None:
    decision_log = {
        "version": "1.0",
        "project_id": "product-reference-regression",
        "decisions": [
            {
                "decision_id": "d-001",
                "stage": "proposal",
                "category": "product_identity_reference_selection",
                "subject": "Product identity reference strategy",
                "options_considered": [
                    {
                        "option_id": "generate_concept_reference",
                        "label": "Generate concept reference",
                        "score": 0.8,
                        "reason": "No user product photo was available.",
                    }
                ],
                "selected": "generate_concept_reference",
                "reason": "User approved generated reference candidates before video generation.",
                "user_visible": True,
                "user_approved": True,
            }
        ],
    }

    validate_artifact("decision_log", decision_log)


def _approved_product_identity_reference(source_type: str = "generated") -> dict:
    return {
        "version": "1.0",
        "reference_id": "pir-001",
        "product_name": "OPPO Find X9 Pro",
        "source_type": source_type,
        "approval_status": "approved",
        "selected_reference_image_path": "reference_assets/product_oppo.png",
        "required_visual_features": [
            "large circular camera island",
            "OPPO wordmark placement",
        ],
        "prohibited_variations": [
            "different lens count",
            "generic phone silhouette",
        ],
        "user_approval": {
            "approved": True,
            "approved_by": "user",
            "approved_at": "2026-05-19T09:00:00Z",
            "decision_id": "d-001",
        },
    }


def _product_visible_scene_plan() -> dict:
    return {
        "version": "1.0",
        "style_mode": "cinematic",
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "Hero push-in on OPPO Find X9 Pro camera island.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "hero",
                "product_reference_required": True,
            }
        ],
    }


def _conditioned_asset_manifest(conditioning_mode: str = "reference_to_video") -> dict:
    return {
        "version": "1.0",
        "assets": [
            {
                "id": "scene-1-video",
                "type": "video",
                "path": "assets/video/scene-1.mp4",
                "source_tool": "wan_video_api",
                "scene_id": "scene-1",
                "model": "wan2.7-i2v",
                "product_identity_conditioning": {
                    "approved_reference_id": "pir-001",
                    "approved_reference_path": "reference_assets/product_oppo.png",
                    "conditioning_mode": conditioning_mode,
                    "generation_tool": "wan_video_api",
                    "generation_model": "wan2.7-i2v",
                    "fidelity_verdict": "PASS",
                },
            }
        ],
    }


def test_product_identity_consistency_rejects_visible_scene_without_reference_or_waiver() -> None:
    reference = {
        "version": "1.0",
        "reference_id": "pir-none",
        "product_name": "OPPO Find X9 Pro",
        "source_type": "not_applicable",
        "approval_status": "not_required",
        "required_visual_features": [],
        "prohibited_variations": [],
    }

    verdict = check_product_identity_consistency(
        reference,
        _product_visible_scene_plan(),
        {"version": "1.0", "assets": []},
    )

    assert verdict["status"] == "FAIL"
    assert any("approved product identity reference" in issue for issue in verdict["issues"])


def test_product_identity_consistency_accepts_approved_generated_reference_and_conditioned_assets() -> None:
    verdict = check_product_identity_consistency(
        _approved_product_identity_reference(),
        _product_visible_scene_plan(),
        _conditioned_asset_manifest(),
    )

    assert verdict["status"] == "PASS"
    assert verdict["summary"]["product_visible_scenes"] == 1
    assert verdict["summary"]["conditioned_assets_checked"] == 1


def test_product_identity_consistency_rejects_risk_waiver_without_user_approval() -> None:
    reference = {
        "version": "1.0",
        "reference_id": "pir-risk",
        "product_name": "OPPO Find X9 Pro",
        "source_type": "risk_accepted",
        "approval_status": "pending",
        "required_visual_features": [],
        "prohibited_variations": ["generic phone silhouette"],
        "risk_waiver": {
            "reason": "User has no product photos.",
            "user_approved": False,
            "decision_id": "d-001",
        },
    }
    manifest = _conditioned_asset_manifest(conditioning_mode="text_only_waived")
    manifest["assets"][0]["product_identity_conditioning"].pop("approved_reference_path")

    verdict = check_product_identity_consistency(
        reference,
        _product_visible_scene_plan(),
        manifest,
    )

    assert verdict["status"] == "FAIL"
    assert any("risk waiver" in issue for issue in verdict["issues"])


def test_product_identity_consistency_accepts_non_product_visible_not_applicable() -> None:
    reference = {
        "version": "1.0",
        "reference_id": "pir-none",
        "product_name": "Acme SaaS",
        "source_type": "not_applicable",
        "approval_status": "not_required",
        "required_visual_features": [],
        "prohibited_variations": [],
    }
    scene_plan = {
        "version": "1.0",
        "style_mode": "animated",
        "scenes": [
            {
                "id": "scene-1",
                "type": "text_card",
                "description": "Animated headline card.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": False,
                "product_visibility": "none",
                "product_reference_required": False,
            }
        ],
    }

    verdict = check_product_identity_consistency(
        reference,
        scene_plan,
        {"version": "1.0", "assets": []},
    )

    assert verdict["status"] == "PASS"
    assert verdict["summary"]["product_visible_scenes"] == 0


def test_video_compose_render_accepts_artifact_paths(tmp_path: Path) -> None:
    """The tool may receive path strings from older directors; it must coerce them."""
    edit_path = tmp_path / "edit_decisions.json"
    asset_path = tmp_path / "asset_manifest.json"
    edit_path.write_text(
        json.dumps({"version": "1.0", "render_runtime": "ffmpeg", "cuts": []}),
        encoding="utf-8",
    )
    asset_path.write_text(json.dumps({"assets": []}), encoding="utf-8")

    result = VideoCompose().execute(
        {
            "operation": "render",
            "edit_decisions": str(edit_path),
            "asset_manifest": str(asset_path),
        }
    )

    assert result.success is False
    assert result.error == "No cuts in edit_decisions"


def test_edit_director_json_examples_do_not_teach_legacy_shape() -> None:
    text = _read_skill("edit-director.md")

    for block in _json_fences(text):
        assert '"timeline"' not in block
        assert '"source_file"' not in block
        assert '"burn_in"' not in block


def test_ad_video_directors_reference_current_contract_names() -> None:
    asset = _read_skill("asset-director.md")
    proposal = _read_skill("proposal-director.md")
    compose = _read_skill("compose-director.md")
    publish = _read_skill("publish-director.md")
    animated_scene = _read_skill("scene-director-animated.md")

    assert 'production_plan["voice_selection"]["voice_id"]' not in asset
    assert 'audio_contract = production_proposal["audio_contract"]' in asset
    assert 'audio_contract["voice_id"]' in asset

    assert 'either `"remotion"` or `"hyperframes"`' not in proposal
    assert '"ffmpeg"' in proposal
    assert "Populate `deliverables.derivatives` in production_bible" not in proposal
    assert "Lock `visual.render_runtime` in production_bible" not in proposal

    assert '"edit_decisions": "projects/<name>/artifacts/edit_decisions.json"' not in compose
    assert '"asset_manifest": "projects/<name>/artifacts/asset_manifest.json"' not in compose
    assert "render_report.output_files" not in publish
    assert "render_report.outputs" in publish

    assert "production_bible.kvms" not in animated_scene
    assert "production_bible.visual.key_visual_moments" in animated_scene


def test_ad_video_contract_mentions_product_identity_reference_flow() -> None:
    manifest = _load_ad_video_manifest()
    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    brief_enrichment = _read_skill("brief-enrichment-director.md")
    proposal = _read_skill("proposal-director.md")
    scene = _read_skill("scene-director.md")
    asset = _read_skill("asset-director.md")
    ep = _read_skill("executive-producer.md")

    proposal_stage = next(stage for stage in manifest["stages"] if stage["name"] == "proposal")
    scene_stage = next(stage for stage in manifest["stages"] if stage["name"] == "scene_plan")
    asset_stage = next(stage for stage in manifest["stages"] if stage["name"] == "assets")
    asset_substage_names = [substage["name"] for substage in asset_stage.get("sub_stages", [])]
    contract_text = "\n".join(
        proposal_stage.get("review_focus", [])
        + proposal_stage.get("success_criteria", [])
        + scene_stage.get("review_focus", [])
        + scene_stage.get("success_criteria", [])
        + asset_stage.get("review_focus", [])
        + asset_stage.get("success_criteria", [])
    )

    assert "product_reference_strategy" in contract_text
    assert "product_identity_reference" in asset_stage.get("produces", [])
    assert "product_reference" in asset_substage_names
    assert "no text-only" in contract_text.lower()
    assert "Product Identity Reference" in brief_enrichment
    assert "`product_reference_strategy`" in proposal
    assert "`product_visibility`" in scene
    assert "`product_reference_required`" in scene
    assert "product_identity_consistency_check" in asset
    assert asset.index("## Product Reference Sub-Stage") < asset.index("## Sample Sub-Stage")
    assert "sample sub-stage first" not in asset
    assert "product_identity_reference_selection" in proposal
    assert "product_identity_reference_selection" in ep
    assert "`product_identity_reference` + `asset_manifest`" in guide
