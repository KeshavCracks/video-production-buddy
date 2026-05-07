"""Ad-video schema/director/tool contract alignment regressions."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

from schemas.artifacts import validate_artifact
from tools.validation.runtime_consistency_check import check_runtime_consistency
from tools.validation.scene_fidelity_check import check_kvm_coverage
from tools.video.video_compose import VideoCompose


ROOT = Path(__file__).resolve().parent.parent.parent
AD_VIDEO_SKILLS = ROOT / "skills" / "pipelines" / "ad-video"


def _read_skill(name: str) -> str:
    return (AD_VIDEO_SKILLS / name).read_text(encoding="utf-8")


def _json_fences(markdown: str) -> list[str]:
    return re.findall(r"```json\s*\n(.*?)\n```", markdown, flags=re.DOTALL)


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


def test_production_bible_schema_allows_runtime_deferral_until_proposal() -> None:
    """Bible runs before proposal, so render_runtime must be optional there."""
    from tests.qa.test_artifact_chain import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["visual"].pop("render_runtime")

    validate_artifact("production_bible", bible)


def test_ad_video_ep_reads_proposal_locks_after_proposal_approval() -> None:
    """EP_STATE must use proposal-stage locks, not optional bible audit copies."""
    ep = _read_skill("executive-producer.md")

    assert "`style_mode` from `production_proposal.style_mode`" in ep
    assert "`render_runtime` from `production_proposal.render_runtime`" in ep
    assert "`derivative_variants` from `production_proposal.derivatives_added`" in ep
    assert "`render_runtime` from `production_bible.visual.render_runtime`" not in ep
    assert "`derivative_variants` from `production_bible.deliverables.derivatives`" not in ep
    assert "render_runtime locked in production_bible.visual.render_runtime" not in ep


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
