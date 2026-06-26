"""Ad-video artifact schema validation regressions."""

from __future__ import annotations

import copy
import json
from copy import deepcopy
from pathlib import Path

import pytest
import jsonschema

from schemas.artifacts import validate_artifact
from tools.compliance.compliance_check import ComplianceCheck

from tests.contracts.conftest import (
    _editing_rhythm_checkpoint,
    _minimal_production_proposal,
    _scene_plan_for_hallucination,
    _trend_alignment_block,
    _voice_performance_lock,
)


def _valid_idea_concept(concept_id: str, *, selected: bool) -> dict:
    return {
        "id": concept_id,
        "name": f"Concept {concept_id}",
        "scenario": f"A concrete execution scenario for {concept_id}.",
        "selected": selected,
        "hook_execution": "Open on a visible before/after gap in the first three seconds.",
        "visual_metaphor": "A messy launch board snapping into a clean launch line.",
        "beat_mapping": {
            "hook": "Show the before/after contrast immediately.",
            "build": "Prove the workflow through a concrete use moment.",
            "reveal": "Reveal the product benefit in one readable action.",
            "cta_brand": "Land the brand and CTA without reopening the premise.",
        },
        "why_this_works": "It turns the approved strategy into concrete visual proof.",
        "knowledge_alignment_refs": ["knowledge_alignment:hook.visual-contrast.001"],
    }


def _valid_ad_video_scene_plan() -> dict:
    return {
        "version": "1.0",
        "user_approved": True,
        "style_mode": "cinematic",
        "total_duration_seconds": 10,
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "First product moment.",
                "start_seconds": 0,
                "end_seconds": 4,
                "duration_seconds": 4,
                "core": True,
                "motion_required": True,
                "product_visibility": "hero",
                "product_reference_required": True,
            },
            {
                "id": "scene-2",
                "type": "generated",
                "description": "Second product moment.",
                "start_seconds": 4,
                "end_seconds": 10,
                "duration_seconds": 6,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
            },
        ],
    }


def _valid_ad_video_asset_manifest() -> dict:
    return {
        "version": "1.0",
        "assets": [
            {
                "id": "asset-1",
                "type": "video",
                "path": "assets/video/scene-1.mp4",
                "source_tool": "wan_video_api",
                "scene_id": "scene-1",
            },
            {
                "id": "asset-2",
                "type": "audio",
                "path": "assets/audio/narration.mp3",
                "source_tool": "tts_selector",
                "scene_id": "scene-1",
            },
        ],
        "costs": [
            {"tool": "wan_video_api", "cost_usd": 0.18},
            {"tool": "tts_selector", "cost_usd": 0.02},
        ],
        "total_cost_usd": 0.20,
    }


def _library_locked_music_alignment() -> dict:
    return {
        "strategy": "library_locked",
        "target_peak_seconds": 18.0,
        "selected_peak_seconds": 30.0,
        "aligned_peak_seconds": 18.2,
        "drift_seconds": 0.2,
        "timing_sidecar_path": "music_library/background.timing.json",
        "evidence": "Validated timing sidecar and trimmed the track to target.",
    }


def _search_align_music_alignment() -> dict:
    return {
        "strategy": "search_align",
        "target_peak_seconds": 18.0,
        "selected_peak_seconds": 26.4,
        "aligned_peak_seconds": 17.9,
        "drift_seconds": -0.1,
        "beat_detection_report": {
            "source": "lib.beat_detector",
            "drop_seconds": [26.4],
        },
        "evidence": "Detected stock track drop and trimmed it to target.",
    }


def _valid_ad_video_edit_decisions() -> dict:
    return {
        "version": "1.0",
        "render_runtime": "remotion",
        "music_strategy": "none",
        "total_duration_seconds": 10,
        "cuts": [
            {
                "id": "cut-1",
                "source": "asset-1",
                "in_seconds": 0,
                "out_seconds": 4,
                "maps_to_beat": "hook",
            },
            {
                "id": "cut-2",
                "source": "asset-2",
                "in_seconds": 4,
                "out_seconds": 10,
                "maps_to_beat": "cta",
            },
        ],
    }


def _valid_ad_video_script() -> dict:
    voice_performance = {
        "emotion": "calm urgency",
        "intonation": "clear lift then resolve",
        "rhythm": "short phrases with a breath",
        "pace": "measured",
        "pause_after_seconds": 0.2,
    }
    return {
        "version": "1.0",
        "title": "Proof Script",
        "style_mode": "cinematic",
        "total_duration_seconds": 10,
        "user_approved": True,
        "sections": [
            {
                "id": "hook",
                "beat": "hook",
                "text": "The first proof lands fast.",
                "start_seconds": 0,
                "end_seconds": 2,
                "duration_estimate_seconds": 2,
                "speaker_directions": "Measured opening with clean emphasis.",
                "voice_performance": dict(voice_performance),
                "tts_directive": {"speed_mult": 0.96},
            },
            {
                "id": "build",
                "beat": "build",
                "text": "The middle proof shows the product solving a real friction point.",
                "start_seconds": 2,
                "end_seconds": 6,
                "duration_estimate_seconds": 4,
                "speaker_directions": "Confident proof without hype.",
                "voice_performance": dict(voice_performance),
                "tts_directive": {"speed_mult": 0.98},
            },
            {
                "id": "reveal",
                "beat": "reveal",
                "text": "Then the product lands as the obvious next move.",
                "start_seconds": 6,
                "end_seconds": 8,
                "duration_estimate_seconds": 2,
                "speaker_directions": "Warmer reveal with controlled lift.",
                "voice_performance": dict(voice_performance),
                "tts_directive": {"speed_mult": 0.94},
            },
            {
                "id": "cta_brand",
                "beat": "cta_brand",
                "text": "Choose Flowcut today. Flowcut.",
                "start_seconds": 8,
                "end_seconds": 10,
                "duration_estimate_seconds": 2,
                "speaker_directions": "Confident low-pressure close.",
                "voice_performance": dict(voice_performance),
                "tts_directive": {"speed_mult": 0.96},
            },
        ],
    }


def test_production_proposal_audio_contract_locks_voice_performance_controls() -> None:
    """Proposal must lock the expressive voice controls before TTS generation."""
    proposal = _minimal_production_proposal()
    proposal["audio_contract"].update(_voice_performance_lock())

    validate_artifact("production_proposal", proposal)

    for required_field in [
        "voice_model",
        "voice_gender",
        "voice_persona",
        "voice_performance",
        "voice_sample_approved",
    ]:
        bad = deepcopy(proposal)
        del bad["audio_contract"][required_field]
        with pytest.raises(Exception):
            validate_artifact("production_proposal", bad)

    bad = deepcopy(proposal)
    del bad["audio_contract"]["voice_performance"]["rhythm"]
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)


def test_ad_video_proposal_requires_user_confirmed_budget_and_subtitles() -> None:
    proposal = _minimal_production_proposal()
    validate_artifact("production_proposal", proposal, pipeline_type="ad-video")

    budget_not_confirmed = deepcopy(proposal)
    budget_not_confirmed["budget_confirmed"] = False
    with pytest.raises(Exception, match="budget_confirmed"):
        validate_artifact(
            "production_proposal", budget_not_confirmed, pipeline_type="ad-video"
        )

    subtitles_not_confirmed = deepcopy(proposal)
    subtitles_not_confirmed["subtitles"]["user_confirmed"] = False
    with pytest.raises(Exception, match="subtitles.user_confirmed"):
        validate_artifact(
            "production_proposal", subtitles_not_confirmed, pipeline_type="ad-video"
        )

    missing_subtitle_confirmation = deepcopy(proposal)
    del missing_subtitle_confirmation["subtitles"]["user_confirmed"]
    with pytest.raises(Exception, match="subtitles.user_confirmed"):
        validate_artifact(
            "production_proposal",
            missing_subtitle_confirmation,
            pipeline_type="ad-video",
        )


def test_ad_video_proposal_rejects_unimplemented_subtitle_sidecar_mode() -> None:
    """Do not offer subtitle sidecars until publish/render delivery models them."""
    proposal = _minimal_production_proposal()
    proposal["subtitles"]["mode"] = "sidecar"

    with pytest.raises(Exception, match="subtitles"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_ad_video_proposal_requires_locked_music_strategy() -> None:
    proposal = _minimal_production_proposal()
    del proposal["music_strategy"]

    with pytest.raises(Exception, match="music_strategy"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_ad_video_proposal_requires_visual_asset_provider_locks() -> None:
    proposal = _minimal_production_proposal()
    del proposal["visual_contract"]["visual_asset_provider_locks"]

    with pytest.raises(Exception, match="visual_asset_provider_locks"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_ad_video_asset_manifest_accepts_strict_music_alignment_evidence() -> None:
    manifest = _valid_ad_video_asset_manifest()
    manifest["assets"].append(
        {
            "id": "music-1",
            "type": "music",
            "path": "assets/music/background.mp3",
            "source_tool": "music_library",
            "scene_id": "global",
            "music_alignment": _library_locked_music_alignment(),
        }
    )
    manifest["costs"].append({"tool": "music_library", "cost_usd": 0.0})

    validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")

    search_manifest = deepcopy(manifest)
    search_manifest["assets"][-1]["source_tool"] = "pixabay_music"
    search_manifest["assets"][-1]["music_alignment"] = _search_align_music_alignment()
    search_manifest["costs"][-1]["tool"] = "pixabay_music"
    validate_artifact("asset_manifest", search_manifest, pipeline_type="ad-video")


def test_ad_video_asset_manifest_rejects_malformed_music_alignment() -> None:
    manifest = _valid_ad_video_asset_manifest()
    manifest["assets"].append(
        {
            "id": "music-1",
            "type": "music",
            "path": "assets/music/background.mp3",
            "source_tool": "music_library",
            "scene_id": "global",
            "music_alignment": _library_locked_music_alignment(),
        }
    )
    manifest["costs"].append({"tool": "music_library", "cost_usd": 0.0})

    missing_sidecar = deepcopy(manifest)
    del missing_sidecar["assets"][-1]["music_alignment"]["timing_sidecar_path"]
    with pytest.raises(Exception, match="timing_sidecar_path"):
        validate_artifact("asset_manifest", missing_sidecar, pipeline_type="ad-video")

    missing_report = deepcopy(manifest)
    missing_report["assets"][-1]["source_tool"] = "pixabay_music"
    missing_report["assets"][-1]["music_alignment"] = _search_align_music_alignment()
    missing_report["assets"][-1]["music_alignment"].pop("beat_detection_report")
    missing_report["costs"][-1]["tool"] = "pixabay_music"
    with pytest.raises(Exception):
        validate_artifact("asset_manifest", missing_report, pipeline_type="ad-video")


def test_production_proposal_rejects_duplicate_derivative_variants() -> None:
    proposal = _minimal_production_proposal()
    proposal["derivatives_added"] = ["9:16", "9:16"]

    with pytest.raises(Exception, match="derivatives_added"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_production_proposal_rejects_unknown_derivative_variants() -> None:
    proposal = _minimal_production_proposal()
    proposal["derivatives_added"] = ["portrait_crop"]

    with pytest.raises(Exception, match="derivatives_added"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_production_proposal_rejects_duplicate_dubbing_languages() -> None:
    proposal = _minimal_production_proposal()
    proposal["dubbing"] = [
        {"language": "es-ES", "voice_id": "narrator-es-a"},
        {"language": "es-ES", "voice_id": "narrator-es-b"},
    ]

    with pytest.raises(Exception, match="dubbing"):
        validate_artifact("production_proposal", proposal, pipeline_type="ad-video")


def test_production_proposal_rejects_non_instruct_qwen_voice_model() -> None:
    """Qwen narration with delivery controls must lock an instruct-capable model."""
    proposal = _minimal_production_proposal()

    bad = deepcopy(proposal)
    bad["audio_contract"]["voice_model"] = "qwen3-tts-flash"
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)


def test_production_proposal_rejects_qwen_flash_even_when_provider_is_cosyvoice() -> None:
    """Qwen model rules must follow the model family, not only voice_provider."""
    proposal = _minimal_production_proposal()
    proposal["audio_contract"]["voice_provider"] = "cosyvoice"
    proposal["audio_contract"]["voice_id"] = "Dylan"

    bad = deepcopy(proposal)
    bad["audio_contract"]["voice_model"] = "qwen3-tts-flash"
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)


def test_production_proposal_rejects_known_qwen_voice_gender_mismatch() -> None:
    """Known gendered Qwen voices must match the approved voice_gender lock."""
    proposal = _minimal_production_proposal()

    bad = deepcopy(proposal)
    bad["audio_contract"]["voice_id"] = "Dylan"
    bad["audio_contract"]["voice_gender"] = "female"
    with pytest.raises(Exception):
        validate_artifact("production_proposal", bad)

    female_voice = deepcopy(proposal)
    female_voice["audio_contract"]["voice_id"] = "Cherry"
    female_voice["audio_contract"]["voice_gender"] = "female"
    validate_artifact("production_proposal", female_voice)


def test_production_proposal_schema_requires_version_pin() -> None:
    proposal = _minimal_production_proposal()
    proposal.pop("version")

    with pytest.raises(Exception, match="version"):
        validate_artifact("production_proposal", proposal)


def test_idea_options_requires_exactly_one_matching_selected_concept() -> None:
    idea_options = {
        "version": "1.0",
        "concepts": [
            _valid_idea_concept("C1", selected=False),
            _valid_idea_concept("C2", selected=True),
        ],
        "selected_concept_id": "C2",
    }
    validate_artifact("idea_options", idea_options)

    no_selected = deepcopy(idea_options)
    no_selected["concepts"][1]["selected"] = False
    with pytest.raises(Exception, match="selected"):
        validate_artifact("idea_options", no_selected)

    two_selected = deepcopy(idea_options)
    two_selected["concepts"][0]["selected"] = True
    with pytest.raises(Exception, match="exactly one"):
        validate_artifact("idea_options", two_selected)

    mismatched_id = deepcopy(idea_options)
    mismatched_id["selected_concept_id"] = "C1"
    with pytest.raises(Exception, match="selected_concept_id"):
        validate_artifact("idea_options", mismatched_id)


def test_idea_options_schema_requires_version_pin() -> None:
    idea_options = {
        "concepts": [
            _valid_idea_concept("C1", selected=False),
            _valid_idea_concept("C2", selected=True),
        ],
        "selected_concept_id": "C2",
    }

    with pytest.raises(Exception, match="version"):
        validate_artifact("idea_options", idea_options)


def test_idea_options_requires_execution_details_for_each_concept() -> None:
    """Idea concepts need enough substance for proposal and scene planning."""
    idea_options = {
        "version": "1.0",
        "concepts": [
            {
                "id": "C1",
                "name": "Quiet Proof",
                "scenario": "A compact product proof story.",
                "selected": True,
            },
            {
                "id": "C2",
                "name": "Tactile Reveal",
                "scenario": "A tactile reveal with the product in use.",
                "selected": False,
            },
        ],
        "selected_concept_id": "C1",
    }

    with pytest.raises(Exception, match="hook_execution"):
        validate_artifact("idea_options", idea_options)

    for concept in idea_options["concepts"]:
        concept.update(
            {
                "hook_execution": "Open on a visible before/after gap in the first three seconds.",
                "visual_metaphor": "A messy launch board snapping into a clean launch line.",
                "beat_mapping": {
                    "hook": "Show the before/after contrast immediately.",
                    "build": "Prove the workflow through a concrete use moment.",
                    "reveal": "Reveal the product benefit in one readable action.",
                    "cta_brand": "Land the brand and CTA without reopening the premise.",
                },
                "why_this_works": "It turns the approved strategy into concrete visual proof.",
                "knowledge_alignment_refs": ["knowledge_alignment:hook.visual-contrast.001"],
            }
        )
    validate_artifact("idea_options", idea_options)


def test_idea_options_rejects_duplicate_concept_ids() -> None:
    idea_options = {
        "version": "1.0",
        "concepts": [
            _valid_idea_concept("C1", selected=True),
            _valid_idea_concept("C1", selected=False),
        ],
        "selected_concept_id": "C1",
    }

    with pytest.raises(Exception, match="duplicate concept id"):
        validate_artifact("idea_options", idea_options)


def test_script_schema_accepts_structured_voice_performance_per_section() -> None:
    """Ad-video scripts need structured delivery cues, not just raw narration text."""
    script = {
        "version": "1.0",
        "title": "Voice Performance Script",
        "total_duration_seconds": 6,
        "sections": [
            {
                "id": "hook",
                "text": "Night changes when the lens starts listening.",
                "start_seconds": 0,
                "end_seconds": 3,
                "speaker_directions": "Hushed, intimate, slightly breathy; do not sell.",
                "voice_performance": {
                    "emotion": "intrigue",
                    "intonation": "soft rise on 'Night', downward resolve on 'listening'",
                    "rhythm": "slow first phrase, tiny breath before the final clause",
                    "pace": "measured",
                    "pause_after_seconds": 0.35,
                },
            }
        ],
    }

    validate_artifact("script", script)

    bad = deepcopy(script)
    del bad["sections"][0]["voice_performance"]["intonation"]
    with pytest.raises(Exception):
        validate_artifact("script", bad)


def test_ad_video_script_validation_requires_section_voice_cues() -> None:
    """Ad-video checkpoint validation must reject scripts that would drop TTS delivery controls."""
    script = {
        "version": "1.0",
        "title": "Missing Voice Cues",
        "style_mode": "cinematic",
        "total_duration_seconds": 6,
        "sections": [
            {
                "id": "hook",
                "text": "Night changes when the lens starts listening.",
                "start_seconds": 0,
                "end_seconds": 6,
            }
        ],
    }

    with pytest.raises(Exception, match="speaker_directions"):
        validate_artifact("script", script)

    contextual_script = deepcopy(script)
    contextual_script.pop("style_mode")
    with pytest.raises(Exception, match="speaker_directions"):
        validate_artifact("script", contextual_script, pipeline_type="ad-video")

    generic_script = deepcopy(contextual_script)
    validate_artifact("script", generic_script)

    script["sections"][0]["speaker_directions"] = "Hushed, intimate, slightly breathy."
    with pytest.raises(Exception, match="voice_performance"):
        validate_artifact("script", script, pipeline_type="ad-video")

    script["sections"][0]["voice_performance"] = {
        "emotion": "intrigue",
        "intonation": "soft rise on 'Night', downward resolve on 'listening'",
        "rhythm": "slow first phrase, tiny breath before the final clause",
        "pace": "measured",
        "pause_after_seconds": 0.35,
    }
    with pytest.raises(Exception, match="tts_directive"):
        validate_artifact("script", script, pipeline_type="ad-video")

    script["sections"][0]["tts_directive"] = {"speed_mult": 0.94}
    script = _valid_ad_video_script()
    del script["user_approved"]
    with pytest.raises(Exception, match="user_approved"):
        validate_artifact("script", script, pipeline_type="ad-video")

    script["user_approved"] = True
    validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_requires_complete_four_beat_sequence() -> None:
    """A valid ad script must preserve hook/build/reveal/cta structure."""
    script = _valid_ad_video_script()

    missing_reveal = deepcopy(script)
    missing_reveal["sections"] = [
        section
        for section in missing_reveal["sections"]
        if section["beat"] != "reveal"
    ]
    missing_reveal["sections"][2]["start_seconds"] = 6
    missing_reveal["sections"][2]["end_seconds"] = 10
    missing_reveal["sections"][2]["duration_estimate_seconds"] = 4
    with pytest.raises(Exception, match="required beats"):
        validate_artifact("script", missing_reveal, pipeline_type="ad-video")

    wrong_order = deepcopy(script)
    wrong_order["sections"][2], wrong_order["sections"][3] = (
        wrong_order["sections"][3],
        wrong_order["sections"][2],
    )
    wrong_order["sections"][2]["start_seconds"] = 6
    wrong_order["sections"][2]["end_seconds"] = 8
    wrong_order["sections"][2]["duration_estimate_seconds"] = 2
    wrong_order["sections"][3]["start_seconds"] = 8
    wrong_order["sections"][3]["end_seconds"] = 10
    wrong_order["sections"][3]["duration_estimate_seconds"] = 2
    with pytest.raises(Exception, match="beat order"):
        validate_artifact("script", wrong_order, pipeline_type="ad-video")

    validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_duplicate_section_ids() -> None:
    """Section IDs must be unique because scene_plan maps back to script sections."""
    script = _valid_ad_video_script()
    script["sections"][1]["id"] = "hook"

    with pytest.raises(Exception, match="duplicate section id"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_non_positive_section_duration() -> None:
    """Script sections must have positive time windows before TTS generation."""
    script = _valid_ad_video_script()
    script["sections"][0]["end_seconds"] = 0

    with pytest.raises(Exception, match="end_seconds.*greater than start_seconds"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_overlapping_sections() -> None:
    """Script timing must be ordered and non-overlapping."""
    script = _valid_ad_video_script()
    script["sections"][1]["start_seconds"] = 1.5

    with pytest.raises(Exception, match="overlaps previous section"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_timeline_gaps() -> None:
    """Script sections should cover the narration timeline without blank gaps."""
    script = _valid_ad_video_script()
    script["sections"][1]["start_seconds"] = 5
    script["sections"][1]["duration_estimate_seconds"] = 5

    with pytest.raises(Exception, match="gap before section"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_duration_estimate_drift() -> None:
    """duration_estimate_seconds must agree with start/end when present."""
    script = _valid_ad_video_script()
    script["sections"][0]["duration_estimate_seconds"] = 9

    with pytest.raises(Exception, match="duration_estimate_seconds"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_ad_video_script_rejects_total_duration_mismatch() -> None:
    """Script total duration must match the final section end."""
    script = _valid_ad_video_script()
    script["total_duration_seconds"] = 8

    with pytest.raises(Exception, match="total_duration_seconds"):
        validate_artifact("script", script, pipeline_type="ad-video")


def test_explicit_non_ad_pipeline_context_does_not_apply_ad_video_script_heuristics() -> None:
    """An explicit non-ad pipeline must not be overridden by shared style_mode."""
    script = {
        "version": "1.0",
        "title": "Explainer Script",
        "style_mode": "animated",
        "total_duration_seconds": 6,
        "sections": [
            {
                "id": "intro",
                "text": "A neural network learns by adjusting tiny weights.",
                "start_seconds": 0,
                "end_seconds": 6,
            }
        ],
    }

    validate_artifact("script", script, pipeline_type="animated-explainer")


def test_scene_plan_schema_accepts_animated_scene_contract_fields() -> None:
    """Animated scene-director fields must validate under scene_plan.schema.json."""
    scene_plan = {
        "version": "1.0",
        "user_approved": True,
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


def test_scene_plan_schema_accepts_screenshot_scene_contract_fields() -> None:
    """Synthetic screenshot UI scenes need their Remotion props in scene_plan."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "animated",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-ui-1",
                "type": "screen_recording",
                "scene_type": "screenshot_scene",
                "description": "Animate a cursor and callout over a static dashboard screenshot.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
                "backgroundImage": "assets/images/dashboard.png",
                "screenshotSize": {"width": 1440, "height": 900},
                "cursorStartAt": [0.9, 0.1],
                "screenshotSteps": [
                    {"kind": "cursor_move", "to": [0.42, 0.58], "durationSeconds": 0.8},
                    {"kind": "highlight_box", "region": {"x": 0.3, "y": 0.4, "w": 0.2, "h": 0.1}},
                ],
            }
        ],
    }

    validate_artifact("scene_plan", scene_plan)


@pytest.mark.parametrize(
    ("step", "missing_field"),
    [
        ({"kind": "cursor_move"}, "to"),
        ({"kind": "click_pulse"}, "at"),
        (
            {"kind": "type_into", "text": "Launch"},
            "region",
        ),
        (
            {"kind": "type_into", "region": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}},
            "text",
        ),
        (
            {"kind": "bubble_append", "text": "Ready"},
            "region",
        ),
        (
            {"kind": "bubble_append", "region": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.1}},
            "text",
        ),
        ({"kind": "typing_dots"}, "at"),
        ({"kind": "highlight_box"}, "region"),
        ({"kind": "callout_balloon", "text": "Notice this"}, "anchor"),
        ({"kind": "callout_balloon", "anchor": [0.42, 0.58]}, "text"),
        ({"kind": "pause"}, "seconds"),
    ],
)
def test_scene_plan_schema_rejects_incomplete_screenshot_steps_by_kind(
    step: dict,
    missing_field: str,
) -> None:
    """screenshot_scene steps must include the fields ScreenshotScene dereferences."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "animated",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-ui-1",
                "type": "screen_recording",
                "scene_type": "screenshot_scene",
                "description": "Animate a cursor and callout over a static dashboard screenshot.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
                "backgroundImage": "assets/images/dashboard.png",
                "screenshotSize": {"width": 1440, "height": 900},
                "screenshotSteps": [step],
            }
        ],
    }

    with pytest.raises(Exception, match=missing_field):
        validate_artifact("scene_plan", scene_plan)


def test_ad_video_animated_scene_plan_requires_scene_type() -> None:
    scene_plan = {
        "version": "1.0",
        "user_approved": True,
        "style_mode": "animated",
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-1",
                "type": "animation",
                "description": "Animated brand-card CTA.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
                "fulfills_kvm": [],
                "motion_specs": ["letter_spring"],
            }
        ],
    }

    with pytest.raises(Exception, match="scene_type"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["scenes"][0]["scene_type"] = "brand_card"
    validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


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


def test_ad_video_scene_plan_requires_product_metadata_without_style_mode() -> None:
    """Pipeline context, not optional style_mode, must trigger ad-video product metadata."""
    scene_plan = {
        "version": "1.0",
        "user_approved": True,
        "total_duration_seconds": 5,
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "Macro hero shot of the product camera module.",
                "start_seconds": 0,
                "end_seconds": 5,
            }
        ],
    }

    validate_artifact("scene_plan", scene_plan)

    with pytest.raises(Exception, match="product_visibility"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["scenes"][0]["product_visibility"] = "none"
    with pytest.raises(Exception, match="product_reference_required"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["scenes"][0]["product_reference_required"] = False
    with pytest.raises(Exception, match="motion_required"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["scenes"][0]["motion_required"] = True
    validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


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


def test_ad_video_asset_manifest_requires_ass_subtitle_paths() -> None:
    manifest = {
        "version": "1.0",
        "subtitle_file": "assets/subtitles.srt",
        "assets": [
            {
                "id": "subtitle-1",
                "type": "subtitle",
                "path": "assets/subtitles.srt",
                "source_tool": "subtitle_gen",
                "scene_id": "global",
            }
        ],
        "costs": [{"tool": "subtitle_gen", "cost_usd": 0.0}],
        "total_cost_usd": 0.0,
    }

    with pytest.raises(Exception, match="ASS"):
        validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")

    manifest["subtitle_file"] = "assets/subtitles.ass"
    manifest["assets"][0]["path"] = "assets/subtitles.ass"
    validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")


def test_ad_video_asset_manifest_rejects_duplicate_asset_ids() -> None:
    """Asset IDs must be unique because edit and review artifacts reference them."""
    manifest = _valid_ad_video_asset_manifest()
    manifest["assets"][1]["id"] = "asset-1"

    with pytest.raises(Exception, match="duplicate asset id"):
        validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")


def test_ad_video_asset_manifest_requires_cost_log_for_assets() -> None:
    """Ad-video assets must carry an auditable per-tool cost log."""
    manifest = _valid_ad_video_asset_manifest()
    del manifest["costs"]

    with pytest.raises(Exception, match="costs"):
        validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")


def test_ad_video_asset_manifest_rejects_total_cost_mismatch() -> None:
    """The manifest total must match the per-tool cost log."""
    manifest = _valid_ad_video_asset_manifest()
    manifest["total_cost_usd"] = 0.01

    with pytest.raises(Exception, match="total_cost_usd"):
        validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")


def test_ad_video_asset_manifest_requires_cost_entry_for_each_source_tool() -> None:
    """Every generated or sourced asset tool must be represented in costs[]."""
    manifest = _valid_ad_video_asset_manifest()
    manifest["costs"] = [{"tool": "tts_selector", "cost_usd": 0.02}]
    manifest["total_cost_usd"] = 0.02

    with pytest.raises(Exception, match="wan_video_api"):
        validate_artifact("asset_manifest", manifest, pipeline_type="ad-video")


def test_ad_video_edit_decisions_reject_duplicate_cut_ids() -> None:
    """Cut IDs must be unique for deterministic review and render diagnostics."""
    edit_decisions = _valid_ad_video_edit_decisions()
    edit_decisions["cuts"][1]["id"] = "cut-1"

    with pytest.raises(Exception, match="duplicate cut id"):
        validate_artifact("edit_decisions", edit_decisions, pipeline_type="ad-video")


def test_ad_video_edit_decisions_require_locked_music_strategy() -> None:
    edit_decisions = _valid_ad_video_edit_decisions()
    del edit_decisions["music_strategy"]

    with pytest.raises(Exception, match="music_strategy"):
        validate_artifact("edit_decisions", edit_decisions, pipeline_type="ad-video")


def test_ad_video_edit_decisions_reject_non_positive_cut_duration() -> None:
    """Cut source ranges must have positive duration before composition."""
    edit_decisions = _valid_ad_video_edit_decisions()
    edit_decisions["cuts"][0]["out_seconds"] = 0

    with pytest.raises(Exception, match="out_seconds.*greater than in_seconds"):
        validate_artifact("edit_decisions", edit_decisions, pipeline_type="ad-video")


def test_ad_video_edit_decisions_reject_total_duration_mismatch() -> None:
    """Edit duration should preserve the approved scene/script runtime."""
    edit_decisions = _valid_ad_video_edit_decisions()
    edit_decisions["total_duration_seconds"] = 7

    with pytest.raises(Exception, match="total_duration_seconds"):
        validate_artifact("edit_decisions", edit_decisions, pipeline_type="ad-video")


def test_edit_decisions_schema_accepts_screenshot_scene_contract_fields() -> None:
    """Composer-supported screenshot_scene props must pass edit_decisions schema."""
    edit_decisions = {
        "version": "1.0",
        "render_runtime": "remotion",
        "music_strategy": "none",
        "total_duration_seconds": 5,
        "cuts": [
            {
                "id": "cut-ui-1",
                "type": "screenshot_scene",
                "source": "remotion:screenshot_scene",
                "in_seconds": 0,
                "out_seconds": 5,
                "maps_to_beat": "demo",
                "backgroundImage": "assets/images/dashboard.png",
                "screenshotSize": {"width": 1440, "height": 900},
                "cursorStartAt": [0.9, 0.1],
                "screenshotSteps": [
                    {"kind": "cursor_move", "to": [0.42, 0.58], "durationSeconds": 0.8},
                    {"kind": "click_pulse", "at": [0.42, 0.58]},
                ],
            }
        ],
    }

    validate_artifact("edit_decisions", edit_decisions)


def test_edit_decisions_schema_rejects_incomplete_screenshot_steps_by_kind() -> None:
    """edit_decisions duplicates screenshot_step and must enforce the same render contract."""
    edit_decisions = {
        "version": "1.0",
        "render_runtime": "remotion",
        "music_strategy": "none",
        "total_duration_seconds": 5,
        "cuts": [
            {
                "id": "cut-ui-1",
                "type": "screenshot_scene",
                "source": "remotion:screenshot_scene",
                "in_seconds": 0,
                "out_seconds": 5,
                "maps_to_beat": "demo",
                "backgroundImage": "assets/images/dashboard.png",
                "screenshotSize": {"width": 1440, "height": 900},
                "screenshotSteps": [{"kind": "type_into"}],
            }
        ],
    }

    with pytest.raises(Exception, match="region|text"):
        validate_artifact("edit_decisions", edit_decisions)


def test_enriched_brief_schema_requires_truth_and_safety_constraints_dimension() -> None:
    """G-0 must capture explicit truth/safety constraints before enrichment."""
    brief = _minimal_enriched_brief()
    validate_artifact("enriched_brief", brief)

    bad = deepcopy(brief)
    del bad["creative_requirements"]["truth_and_safety_constraints"]
    with pytest.raises(Exception):
        validate_artifact("enriched_brief", bad)

    bad = deepcopy(brief)
    bad["creative_requirements"]["truth_and_safety_constraints"]["source"] = "INFERRED"
    with pytest.raises(Exception):
        validate_artifact("enriched_brief", bad)


def test_enriched_brief_schema_requires_explicit_brand_name() -> None:
    """Brand identity must survive separately from product/model naming."""
    brief = _minimal_enriched_brief()
    brief["product_brief"]["brand_name"] = "Acme"
    validate_artifact("enriched_brief", brief)

    del brief["product_brief"]["brand_name"]
    with pytest.raises(Exception, match="brand_name"):
        validate_artifact("enriched_brief", brief)

    brief = _minimal_enriched_brief()
    brief["product_brief"]["brand_name"] = ""
    with pytest.raises(Exception, match="brand_name"):
        validate_artifact("enriched_brief", brief)


def test_ad_video_enriched_brief_requires_explicit_user_approval() -> None:
    brief = _minimal_enriched_brief()
    brief["user_approved"] = True
    validate_artifact("enriched_brief", brief, pipeline_type="ad-video")

    brief["user_approved"] = False
    with pytest.raises(Exception, match="user_approved"):
        validate_artifact("enriched_brief", brief, pipeline_type="ad-video")


def test_production_bible_schema_requires_truth_contract() -> None:
    """The bible must carry the broader truth contract used by scene/assets gates."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    validate_artifact("production_bible", bible)

    bad = deepcopy(bible)
    del bad["truth_contract"]
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)

    bad = deepcopy(bible)
    bad["truth_contract"]["product_geometry_rules"] = []
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)


def test_production_bible_validation_requires_derived_intensity_curve() -> None:
    """Ad-video bibles must carry the exact curve derived from emotional beats."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    validate_artifact("production_bible", bible)

    missing = deepcopy(bible)
    del missing["narrative"]["intensity_curve"]
    with pytest.raises(Exception, match="intensity_curve"):
        validate_artifact("production_bible", missing)

    drifted = deepcopy(bible)
    drifted["narrative"]["intensity_curve"][1]["value"] = 0.1
    with pytest.raises(Exception, match="derive_intensity_curve"):
        validate_artifact("production_bible", drifted)


def test_production_bible_rejects_duplicate_narrative_beat_ids() -> None:
    """Beat ids must be unique because script, scene, edit, and compliance refs key by them."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["narrative"]["emotional_beat_sequence"][1]["beat_id"] = "B1"

    with pytest.raises(Exception, match="duplicate beat_id"):
        validate_artifact("production_bible", bible, pipeline_type="ad-video")


def _trend_alignment_block() -> dict:
    return {
        "selected_trend_ids": ["trend-tiktok-text-hooks"],
        "alignments": [
            {
                "trend_id": "trend-tiktok-text-hooks",
                "signal": "Native text-first hooks are lifting completion rates.",
                "source": "https://example.com/current-hook",
                "sentiment": "positive",
                "brand_safety": "safe",
                "trend_type": "visual_style",
                "application_targets": ["hook", "build", "scene_plan", "visual"],
                "target_beat": "hook",
                "script_usage": {
                    "required_section_ids": ["hook", "build"],
                    "source_ref": "trend_alignment:trend-tiktok-text-hooks",
                    "usage_note": "Let the hook/build borrow the native text-first pacing pattern.",
                },
                "scene_usage": {
                    "required": True,
                    "required_scene_count": 1,
                    "visual_or_pacing_instruction": "Use native overlay text and rapid visual confirmation without copying a viral layout.",
                },
                "do_not_imitate": [
                    "Do not copy creator identity, captions, audio, choreography, or shot sequence from the source.",
                ],
            }
        ],
    }


def test_production_bible_schema_requires_trend_alignment_block() -> None:
    """The bible must make selected trend usage observable to downstream stages."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["intelligence"]["trend_alignment"] = _trend_alignment_block()
    validate_artifact("production_bible", bible)

    bad = deepcopy(bible)
    del bad["intelligence"]["trend_alignment"]
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)

    unsafe = deepcopy(bible)
    unsafe["intelligence"]["trend_alignment"]["alignments"][0]["brand_safety"] = "unsafe"
    with pytest.raises(Exception):
        validate_artifact("production_bible", unsafe)


def test_production_bible_selected_trends_must_resolve_to_alignment_rows() -> None:
    """Selected trend ids are canonical refs, not advisory labels."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["intelligence"]["trend_alignment"]["selected_trend_ids"] = ["trend-missing"]

    with pytest.raises(Exception, match="selected_trend_ids"):
        validate_artifact("production_bible", bible, pipeline_type="ad-video")


def test_production_bible_trend_source_refs_must_match_alignment_id() -> None:
    """Script refs must use the canonical trend_alignment:<trend_id> value."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["intelligence"]["trend_alignment"]["alignments"][0]["script_usage"][
        "source_ref"
    ] = "trend_alignment:wrong-trend"

    with pytest.raises(Exception, match="source_ref"):
        validate_artifact("production_bible", bible, pipeline_type="ad-video")


def test_production_bible_selected_knowledge_cards_must_resolve_to_alignment_rows() -> None:
    """Selected knowledge card ids must have a matching alignment contract."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["intelligence"]["knowledge_alignment"]["selected_card_ids"] = [
        "missing.card",
    ]

    with pytest.raises(Exception, match="selected_card_ids"):
        validate_artifact("production_bible", bible, pipeline_type="ad-video")


def test_production_bible_knowledge_source_refs_must_match_alignment_id() -> None:
    """Professional-knowledge refs must survive as knowledge_alignment:<card_id>."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["intelligence"]["knowledge_alignment"]["alignments"][0][
        "source_ref"
    ] = "knowledge_alignment:wrong.card"

    with pytest.raises(Exception, match="source_ref"):
        validate_artifact("production_bible", bible, pipeline_type="ad-video")


def test_production_bible_schema_accepts_structured_editing_rhythm_checkpoint() -> None:
    """CP-E checkpoints need a structured form so compliance_check can inspect cuts."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["compliance_manifest"]["checkpoints"].append(
        {
            "id": "CP-E-STRUCTURED",
            "applies_to_stage": "edit",
            "description": "B3 edit rhythm",
            "check_type": "timing",
            "evaluation_method": "structural",
            "criterion": "Cuts in beat B3 match rapid/match-cut rhythm",
            "structured": {
                "kind": "editing_rhythm",
                "beat_id": "B3",
                "cuts_density": "rapid",
                "avg_shot_duration_seconds": 1.2,
                "transition_style": "match_cut",
                "tolerance": 0.25,
            },
            "source_confidence": "research-grounded",
            "failure_action": "revise",
        }
    )

    validate_artifact("production_bible", bible)


def _editing_rhythm_checkpoint(**overrides: object) -> dict:
    structured = {
        "kind": "editing_rhythm",
        "beat_id": "B3",
        "cuts_density": "rapid",
        "avg_shot_duration_seconds": 1.2,
        "transition_style": "match_cut",
        "tolerance": 0.25,
    }
    structured.update(overrides)
    return {
        "id": "CP-E3",
        "applies_to_stage": "edit",
        "description": "B3 edit rhythm",
        "check_type": "timing",
        "evaluation_method": "structural",
        "criterion": "Cuts in beat B3 match rapid/match-cut rhythm",
        "structured": structured,
        "source_confidence": "research-grounded",
        "failure_action": "revise",
    }


def test_compliance_beat_mapping_checks_edit_decision_cuts() -> None:
    """Beat mapping is not only a scene-plan check; edit cuts must preserve it."""
    result = ComplianceCheck().execute(
        {
            "stage_output": {
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": "asset-1",
                        "in_seconds": 0,
                        "out_seconds": 1.2,
                        "maps_to_beat": "B3",
                    }
                ]
            },
            "checkpoint": {
                "id": "CP-E-BEAT",
                "evaluation_method": "structural",
                "check_type": "structural",
                "structured": {"kind": "beat_mapping", "beat_id": "B3"},
                "failure_action": "revise",
            },
        }
    )

    assert result.success is True
    assert result.data["pass"] is True


def test_compliance_editing_rhythm_passes_matching_cuts() -> None:
    result = ComplianceCheck().execute(
        {
            "stage_output": {
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": "asset-1",
                        "in_seconds": 0.0,
                        "out_seconds": 1.2,
                        "maps_to_beat": "B3",
                        "transition_out": "match_cut",
                    },
                    {
                        "id": "cut-2",
                        "source": "asset-2",
                        "in_seconds": 1.2,
                        "out_seconds": 2.4,
                        "maps_to_beat": "B3",
                        "transition_in": "match_cut",
                    },
                ]
            },
            "checkpoint": _editing_rhythm_checkpoint(),
        }
    )

    assert result.success is True
    assert result.data["pass"] is True


def test_compliance_editing_rhythm_rejects_flattened_long_cuts() -> None:
    result = ComplianceCheck().execute(
        {
            "stage_output": {
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": "asset-1",
                        "in_seconds": 0.0,
                        "out_seconds": 7.4,
                        "maps_to_beat": "B3",
                        "transition_out": "dissolve",
                    },
                    {
                        "id": "cut-2",
                        "source": "asset-2",
                        "in_seconds": 7.4,
                        "out_seconds": 15.2,
                        "maps_to_beat": "B3",
                        "transition_in": "dissolve",
                    },
                ]
            },
            "checkpoint": _editing_rhythm_checkpoint(),
        }
    )

    assert result.success is True
    assert result.data["pass"] is False
    assert "avg_shot_duration_seconds" in result.data["deviation"]
    assert "transition_style" in result.data["deviation"]


def test_compliance_editing_rhythm_accepts_schema_valid_slow_density() -> None:
    result = ComplianceCheck().execute(
        {
            "stage_output": {
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": "asset-1",
                        "in_seconds": 0.0,
                        "out_seconds": 4.5,
                        "maps_to_beat": "B3",
                        "transition_out": "match_cut",
                    },
                    {
                        "id": "cut-2",
                        "source": "asset-2",
                        "in_seconds": 4.5,
                        "out_seconds": 9.0,
                        "maps_to_beat": "B3",
                        "transition_in": "match_cut",
                    },
                ]
            },
            "checkpoint": _editing_rhythm_checkpoint(
                cuts_density="slow",
                avg_shot_duration_seconds=4.5,
                transition_style="match_cut",
                tolerance=0.10,
            ),
        }
    )

    assert result.success is True
    assert result.data["pass"] is True


def test_scene_plan_schema_accepts_hallucination_checks() -> None:
    """Scene plans must carry explicit checks for generated high-risk visuals."""
    scene_plan = _scene_plan_for_hallucination()
    validate_artifact("scene_plan", scene_plan)

    bad = deepcopy(scene_plan)
    del bad["scenes"][0]["hallucination_checks"][0]["prohibited_failure"]
    with pytest.raises(Exception):
        validate_artifact("scene_plan", bad)


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


def test_ad_video_scene_plan_validation_requires_user_approval() -> None:
    """Approved ad-video scene plans are the final human visual gate before assets."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan.pop("user_approved")

    with pytest.raises(Exception, match="user_approved"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["user_approved"] = False
    with pytest.raises(Exception, match="user_approved"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

    scene_plan["user_approved"] = True
    validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_duplicate_scene_ids() -> None:
    """Scene ids must be unique because asset/review gates key by scene_id."""
    scene_plan = {
        "version": "1.0",
        "user_approved": True,
        "style_mode": "cinematic",
        "total_duration_seconds": 10,
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "First product moment.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "hero",
                "product_reference_required": True,
            },
            {
                "id": "scene-1",
                "type": "generated",
                "description": "Second product moment with the same id.",
                "start_seconds": 5,
                "end_seconds": 10,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
            },
        ],
    }

    with pytest.raises(Exception, match="duplicate scene id"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_bare_trend_alignment_refs() -> None:
    """Trend refs must use the canonical trend_alignment:<id> form."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["scenes"][0]["trend_alignment_refs"] = ["trend-tiktok-lofi-hook"]
    scene_plan["scenes"][0]["trend_alignment_notes"] = (
        "Use warm native pacing without copying source captions or shot order."
    )

    with pytest.raises(Exception, match="trend_alignment"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_non_positive_scene_duration() -> None:
    """Scenes must have positive timeline duration before assets/edit can key timing."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["scenes"][0]["end_seconds"] = 0

    with pytest.raises(Exception, match="end_seconds.*greater than start_seconds"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_overlapping_timeline() -> None:
    """Scene timelines must be ordered and non-overlapping for deterministic edits."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["scenes"][1]["start_seconds"] = 3.5

    with pytest.raises(Exception, match="overlaps previous scene"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_timeline_gaps() -> None:
    """Scene durations must cover the timeline instead of hiding blank gaps."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["scenes"][1]["start_seconds"] = 5
    scene_plan["scenes"][1]["duration_seconds"] = 5

    with pytest.raises(Exception, match="gap before scene"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_duration_seconds_drift() -> None:
    """Optional duration_seconds must agree with start/end when present."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["scenes"][0]["duration_seconds"] = 9

    with pytest.raises(Exception, match="duration_seconds"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_rejects_total_duration_mismatch() -> None:
    """Scene-plan total duration must match the final timeline end."""
    scene_plan = _valid_ad_video_scene_plan()
    scene_plan["total_duration_seconds"] = 8

    with pytest.raises(Exception, match="total_duration_seconds"):
        validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")


def test_ad_video_scene_plan_schema_requires_crop_regions_for_aspect_ratio_derivatives() -> None:
    """Aspect-ratio derivatives are not renderable unless every scene has crop regions."""
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


def test_ad_video_scene_plan_schema_does_not_require_crop_regions_for_duration_only_derivatives() -> None:
    """Duration cuts are handled by core-scene filtering, not crop rectangles."""
    scene_plan = {
        "version": "1.0",
        "style_mode": "cinematic",
        "total_duration_seconds": 15,
        "derivative_variants": ["15s_short"],
        "scenes": [
            {
                "id": "scene-1",
                "type": "generated",
                "description": "A moving lifestyle scene kept in the short cut.",
                "start_seconds": 0,
                "end_seconds": 5,
                "core": True,
                "motion_required": True,
                "product_visibility": "none",
                "product_reference_required": False,
            }
        ],
    }

    validate_artifact("scene_plan", scene_plan)

    with_aspect_ratio = deepcopy(scene_plan)
    with_aspect_ratio["derivative_variants"] = ["15s_short", "9:16"]
    with pytest.raises(Exception):
        validate_artifact("scene_plan", with_aspect_ratio)

    with_aspect_ratio["scenes"][0]["crop_regions"] = {
        "9:16": {"x": 656, "y": 0, "w": 608, "h": 1080}
    }
    validate_artifact("scene_plan", with_aspect_ratio)

    duration_key_as_crop = deepcopy(scene_plan)
    duration_key_as_crop["scenes"][0]["crop_regions"] = {
        "15s_short": {"x": 0, "y": 0, "w": 1920, "h": 1080}
    }
    with pytest.raises(Exception):
        validate_artifact("scene_plan", duration_key_as_crop)


def test_production_bible_schema_allows_runtime_deferral_until_proposal() -> None:
    """Bible runs before proposal, so render_runtime must be optional there."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    bible["visual"].pop("render_runtime")

    validate_artifact("production_bible", bible)


def test_ad_video_production_bible_requires_approval_flags_and_cta() -> None:
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

    bible = deepcopy(PRODUCTION_BIBLE_VALID)
    validate_artifact("production_bible", bible, pipeline_type="ad-video")

    not_approved = deepcopy(bible)
    not_approved["approval"]["execution_approved"] = False
    with pytest.raises(Exception, match="execution_approved"):
        validate_artifact("production_bible", not_approved, pipeline_type="ad-video")

    missing_cta = deepcopy(bible)
    missing_cta["identity"]["cta"] = None
    with pytest.raises(Exception, match="cta"):
        validate_artifact("production_bible", missing_cta, pipeline_type="ad-video")


def test_production_bible_schema_requires_kvm_motion_primitives() -> None:
    """Bible KVMs must name the scene motion primitives needed to fulfill them."""
    from tests.contracts.test_ad_video_chain_integrity import PRODUCTION_BIBLE_VALID

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


def test_ad_video_publish_log_requires_complete_output_file_matrix() -> None:
    publish_log = {
        "version": "1.0",
        "pipeline": "ad-video",
        "brand_name": "Acme",
        "entries": [
            {
                "platform": "local-export",
                "status": "exported",
                "timestamp": "2026-05-25T00:00:00Z",
                "export_path": "renders/output_16x9.mp4",
            }
        ],
    }

    with pytest.raises(Exception):
        validate_artifact("publish_log", publish_log, pipeline_type="ad-video")

    publish_log["output_file_matrix"] = []
    with pytest.raises(Exception):
        validate_artifact("publish_log", publish_log, pipeline_type="ad-video")

    publish_log["output_file_matrix"] = [
        {
            "file": "renders/output_16x9.mp4",
            "variant": "16:9",
            "duration_seconds": 30.0,
            "target_platforms": ["youtube"],
            "metadata": {
                "title": "Acme Launch",
                "description": "A direct product story.",
                "tags": ["Acme", "ad"],
                "cta_url": "https://example.com",
            },
            "thumbnail_concept": "Product hero frame with short headline",
        }
    ]
    validate_artifact("publish_log", publish_log, pipeline_type="ad-video")

    missing_metadata = deepcopy(publish_log)
    del missing_metadata["output_file_matrix"][0]["metadata"]["title"]
    with pytest.raises(Exception):
        validate_artifact("publish_log", missing_metadata, pipeline_type="ad-video")


def test_ad_video_render_report_requires_verified_stereo_outputs() -> None:
    render_report = {
        "version": "1.0",
        "renderer": "remotion",
        "outputs": [
            {
                "path": "renders/output_16x9.mp4",
                "format": "mp4",
                "resolution": "1920x1080",
                "duration_seconds": 30.0,
                "variant": "16:9",
                "audio_channels": 2,
            }
        ],
        "probe_results": {
            "16:9": {
                "duration_check": "PASS",
                "resolution_check": "PASS",
                "audio_check": "PASS",
            }
        },
    }

    missing_audio = deepcopy(render_report)
    del missing_audio["outputs"][0]["audio_channels"]
    with pytest.raises(Exception, match="audio_channels"):
        validate_artifact("render_report", missing_audio, pipeline_type="ad-video")

    failed_probe = deepcopy(render_report)
    failed_probe["probe_results"]["16:9"]["audio_check"] = "FAIL"
    with pytest.raises(Exception, match="probe_results"):
        validate_artifact("render_report", failed_probe, pipeline_type="ad-video")

    missing_probe_check = deepcopy(render_report)
    del missing_probe_check["probe_results"]["16:9"]["audio_check"]
    with pytest.raises(Exception, match="audio_check"):
        validate_artifact(
            "render_report", missing_probe_check, pipeline_type="ad-video"
        )

    zero_duration = deepcopy(render_report)
    zero_duration["outputs"][0]["duration_seconds"] = 0
    with pytest.raises(Exception, match="duration_seconds"):
        validate_artifact("render_report", zero_duration, pipeline_type="ad-video")

    validate_artifact("render_report", render_report, pipeline_type="ad-video")

# ---------------------------------------------------------------------------
# Preproduction artifact schema regressions
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = ROOT / "schemas" / "artifacts"


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.schema.json"
    assert path.exists(), f"Schema not found: {path}"
    with open(path) as f:
        return json.load(f)


def load_schema_at(path: Path) -> dict:
    assert path.exists(), f"Schema not found: {path}"
    with open(path) as f:
        return json.load(f)


def validate(instance: dict, schema: dict) -> None:
    jsonschema.validate(instance, schema, format_checker=jsonschema.FormatChecker())


# ============================================================
# TestProductIdentityReferenceSchema
# ============================================================

def _minimal_product_identity_reference() -> dict:
    return {
        "version": "1.0",
        "reference_id": "pir-001",
        "product_name": "OPPO Find X9 Pro",
        "source_type": "generated",
        "approval_status": "approved",
        "selected_reference_image_path": "reference_assets/product_oppo_reference.png",
        "candidate_reference_paths": [
            "assets/images/product_reference_candidate_01.png",
            "assets/images/product_reference_candidate_02.png",
        ],
        "required_visual_features": [
            "large circular rear camera island",
            "OPPO wordmark placement",
        ],
        "prohibited_variations": [
            "generic phone silhouette",
            "different lens count",
        ],
        "user_approval": {
            "approved": True,
            "approved_by": "user",
            "approved_at": "2026-05-19T09:00:00Z",
            "decision_id": "d-001",
        },
    }


class TestProductIdentityReferenceSchema:
    def setup_method(self):
        self.schema = load_schema("product_identity_reference")

    def test_valid_generated_reference(self):
        validate(_minimal_product_identity_reference(), self.schema)

    def test_user_provided_reference_requires_selected_path(self):
        instance = _minimal_product_identity_reference()
        instance["source_type"] = "user_provided"
        del instance["selected_reference_image_path"]
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for missing selected_reference_image_path"
        except jsonschema.ValidationError:
            pass

    def test_risk_accepted_requires_user_approved_waiver(self):
        instance = {
            "version": "1.0",
            "reference_id": "pir-risk",
            "product_name": "OPPO Find X9 Pro",
            "source_type": "risk_accepted",
            "approval_status": "approved",
            "required_visual_features": [],
            "prohibited_variations": ["generic phone silhouette"],
            "risk_waiver": {
                "reason": "No reference image is available.",
                "user_approved": True,
                "approved_by": "user",
                "approved_at": "2026-05-19T09:00:00Z",
                "decision_id": "d-002",
            },
        }
        validate(instance, self.schema)

        instance["risk_waiver"]["user_approved"] = False
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError because risk waiver is not user-approved"
        except jsonschema.ValidationError:
            pass

    def test_not_applicable_requires_not_required_status(self):
        instance = {
            "version": "1.0",
            "reference_id": "pir-none",
            "product_name": "Acme SaaS",
            "source_type": "not_applicable",
            "approval_status": "not_required",
            "required_visual_features": [],
            "prohibited_variations": [],
        }
        validate(instance, self.schema)

        instance["approval_status"] = "approved"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for approved status on not_applicable reference"
        except jsonschema.ValidationError:
            pass


# ============================================================
# TestEnrichedBriefSchema
# ============================================================

def _minimal_beat(n: int, start: int, end: int) -> dict:
    return {
        "beat_name": f"BEAT {n}",
        "time_range": f"{start}-{end}s",
        "visual_description": "Close-up of product on textured surface, soft natural light.",
        "emotional_target": "curiosity",
        "key_action": "Camera slowly zooms in on product label.",
    }


def _minimal_creative_requirements() -> dict:
    def delegated() -> dict:
        return {
            "value": "Recommend a category-fit value from the brief.",
            "source": "DELEGATED",
            "basis": "User explicitly delegated this worksheet dimension to the creative director.",
        }

    return {
        "product_model": {
            "value": "Acme Floral Water summer edition",
            "source": "FROM BRIEF",
            "basis": "User specified the exact product name.",
        },
        "core_selling_points": {
            "value": "Cooling sensation, natural citronella, pocketable frosted bottle",
            "source": "FROM BRIEF",
            "basis": "User listed the product benefits.",
        },
        "platform_duration": {
            "value": "TikTok, 9:16, 30 seconds",
            "source": "FROM BRIEF",
            "basis": "User selected TikTok and 30s delivery.",
        },
        "target_audience": {
            "value": "Urban women 20-35, active outdoors in summer evenings",
            "source": "FROM BRIEF",
            "basis": "User described the audience and usage occasion.",
        },
        "tone_style": delegated(),
        "visual_approach": delegated(),
        "language_voiceover": {
            "value": "English narration with English burnt-in subtitles",
            "source": "FROM BRIEF",
            "basis": "User requested English narration.",
        },
        "mandatory_marketing": {
            "value": "Include 'Cool. Calm. Protected.' and show the product bottle clearly.",
            "source": "FROM BRIEF",
            "basis": "User supplied slogan and product-visibility requirement.",
        },
        "cta": {
            "value": "Shop Acme Floral Water today",
            "source": "FROM BRIEF",
            "basis": "User supplied CTA copy.",
        },
        "product_fidelity_references": delegated(),
        "truth_and_safety_constraints": {
            "value": (
                "Preserve product facts, packaging geometry, physically plausible use, "
                "and avoid unsupported medical or safety claims."
            ),
            "source": "FROM BRIEF",
            "basis": "User supplied product-fidelity and prohibited-claim requirements.",
        },
    }


def _minimal_enriched_brief() -> dict:
    return {
        "creative_requirements": _minimal_creative_requirements(),
        "product_brief": {
            "brand_name": "Acme",
            "product_name": "Acme Floral Water",
            "product_type": "Personal care / mosquito-repellent floral water",
            "tagline": "Cool. Calm. Protected.",
            "product_description": (
                "Acme Floral Water combines natural citronella extract with a cooling "
                "rose-water base. A single spritz leaves skin pleasantly chilled for up "
                "to four hours. Packaged in a frosted emerald glass bottle."
            ),
            "target_demographic": "Urban women 20-35, active outdoors in summer evenings.",
        },
        "ad_specification": {
            "duration_seconds": 30,
            "platform": "tiktok",
            "language": "English",
            "visual_style": "cinematic",
            "aspect_ratio": "9:16",
            "tone": "fresh, playful, confident",
            "music_direction": (
                "Opens with light guzheng plucks over ambient summer sounds (0-5s). "
                "Mid-section builds to upbeat indie-pop energy (5-22s). "
                "Climaxes at the product hero moment with a bright synth sting (22-26s). "
                "Outro resolves to a gentle fade (26-30s). "
                "Music ducks to -18 dB under narration."
            ),
        },
        "narrative_arc": [
            _minimal_beat(1, 0, 6),
            _minimal_beat(2, 6, 13),
            _minimal_beat(3, 13, 20),
            _minimal_beat(4, 20, 26),
            _minimal_beat(5, 26, 30),
        ],
        "brand_guideline": {
            "primary_color": "#006B3F",
            "accent_color": "#F5E6C8",
            "font_style": "Headline: light sans-serif; Body: clean sans-serif",
            "logo_placement": "Bottom-right from beat 4 onward",
            "prohibited_elements": [
                "No competitor brand names or logos",
                "No claims of medical efficacy (e.g. 'kills mosquitoes')",
                "No dark or threatening imagery of insects",
            ],
        },
        "narration_notes": {
            "voice_description": "Female, mid-20s. Warm, clear, gently energetic. Delivery: conversational.",
            "key_lines": [
                "Summer nights just got a whole lot cooler.",
                "One spritz and you're protected — naturally.",
                "Cool. Calm. Protected. Acme Floral Water.",
            ],
            "target_word_count": 75,
        },
        "hypothesis_flags": [
            {"dimension": "arc_type", "status": "INFERRED", "basis": "problem-solution dominant in personal-care TikTok ads"},
            {"dimension": "music_direction", "status": "INFERRED", "basis": "platform norm: upbeat for summer personal-care"},
            {"dimension": "target_demographic", "status": "FROM BRIEF", "basis": "user stated 'young women'"},
            {"dimension": "visual_approach", "status": "DELEGATED", "basis": "user chose recommend-for-me in the creative requirements worksheet"},
        ],
        "user_approved": False,
    }


class TestEnrichedBriefSchema:
    def setup_method(self):
        self.schema = load_schema_at(ROOT / "schemas" / "artifacts" / "enriched_brief.schema.json")

    def test_valid_minimal(self):
        validate(_minimal_enriched_brief(), self.schema)

    def test_user_approved_true_is_valid(self):
        instance = _minimal_enriched_brief()
        instance["user_approved"] = True
        validate(instance, self.schema)

    def test_rejects_fewer_than_5_narrative_beats(self):
        instance = _minimal_enriched_brief()
        instance["narrative_arc"] = instance["narrative_arc"][:4]  # 4 beats — below minItems:5
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for fewer than 5 beats"
        except jsonschema.ValidationError:
            pass

    def test_rejects_more_than_5_narrative_beats(self):
        instance = _minimal_enriched_brief()
        instance["narrative_arc"].append(_minimal_beat(6, 30, 35))  # 6 beats — above maxItems:5
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for more than 5 beats"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_primary_color_hex(self):
        instance = _minimal_enriched_brief()
        instance["brand_guideline"]["primary_color"] = "green"  # not #RRGGBB
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for non-hex primary_color"
        except jsonschema.ValidationError:
            pass

    def test_rejects_fewer_than_3_prohibited_elements(self):
        instance = _minimal_enriched_brief()
        instance["brand_guideline"]["prohibited_elements"] = ["rule1", "rule2"]  # below minItems:3
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for fewer than 3 prohibited_elements"
        except jsonschema.ValidationError:
            pass

    def test_rejects_fewer_than_3_key_lines(self):
        instance = _minimal_enriched_brief()
        instance["narration_notes"]["key_lines"] = ["line1", "line2"]  # below minItems:3
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for fewer than 3 key_lines"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_platform_enum(self):
        instance = _minimal_enriched_brief()
        instance["ad_specification"]["platform"] = "snapchat"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for platform 'snapchat'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_visual_style_enum(self):
        instance = _minimal_enriched_brief()
        instance["ad_specification"]["visual_style"] = "3d"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for visual_style '3d'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_hypothesis_flag_status(self):
        instance = _minimal_enriched_brief()
        instance["hypothesis_flags"][0]["status"] = "ASSUMED"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for status 'ASSUMED'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_empty_hypothesis_flags(self):
        instance = _minimal_enriched_brief()
        instance["hypothesis_flags"] = []  # below minItems:1
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for empty hypothesis_flags"
        except jsonschema.ValidationError:
            pass

    def test_rejects_missing_product_brief(self):
        instance = _minimal_enriched_brief()
        del instance["product_brief"]
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for missing product_brief"
        except jsonschema.ValidationError:
            pass

    def test_user_edits_optional(self):
        instance = _minimal_enriched_brief()
        instance["user_edits"] = [
            {"section": "Narrative Arc", "field": "arc_type", "original": "problem-solution", "revised": "contrast"}
        ]
        validate(instance, self.schema)

    def test_rejects_missing_creative_requirement_dimension(self):
        instance = _minimal_enriched_brief()
        del instance["creative_requirements"]["cta"]
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for missing cta creative requirement"
        except jsonschema.ValidationError:
            pass

    def test_rejects_inferred_required_creative_requirement(self):
        instance = _minimal_enriched_brief()
        instance["creative_requirements"]["tone_style"]["source"] = "INFERRED"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError because required worksheet dimensions must be FROM_BRIEF or DELEGATED"
        except jsonschema.ValidationError:
            pass

    def test_accepts_delegated_hypothesis_flag_status(self):
        instance = _minimal_enriched_brief()
        instance["hypothesis_flags"] = [
            {"dimension": "tone_style", "status": "DELEGATED", "basis": "user asked the creative director to recommend it"}
        ]
        validate(instance, self.schema)


# ============================================================
# TestIntakeBriefSchema
# ============================================================

class TestIntakeBriefSchema:
    def setup_method(self):
        self.schema = load_schema("intake_brief")

    def _minimal(self) -> dict:
        return {
            "product": "Acme App",
            "platform": "tiktok",
            "duration_target_seconds": 30,
            "intake_completeness": "thin",
            "round1_questions_asked": ["What are you advertising?"],
        }

    def test_valid_minimal(self):
        validate(self._minimal(), self.schema)

    def test_valid_rich(self):
        rich = {
            "product": "Acme App",
            "brand_name": "Acme Inc.",
            "platform": "youtube",
            "duration_target_seconds": 60,
            "demographic": "25-34 urban professionals",
            "emotional_intent": "aspiration",
            "key_message": "Work smarter, not harder.",
            "cta": "Download free",
            "tone": "confident",
            "reference_files": [
                {
                    "filename": "brand_guide.pdf",
                    "inferred_role": "brand_guideline",
                    "reason": "Contains logo usage and typography rules",
                }
            ],
            "style_mode_candidate": "animated",
            "round1_questions_asked": [
                "What is your core message?",
                "Who is the target audience?",
            ],
            "intake_completeness": "rich",
        }
        validate(rich, self.schema)

    def test_rejects_more_than_3_questions(self):
        instance = self._minimal()
        instance["round1_questions_asked"] = [
            "Q1?",
            "Q2?",
            "Q3?",
            "Q4?",  # exceeds maxItems: 3
        ]
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for more than 3 questions"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_platform(self):
        instance = self._minimal()
        instance["platform"] = "snapchat"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for invalid platform 'snapchat'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_missing_required(self):
        instance = {"product": "X"}  # missing platform, duration_target_seconds, etc.
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for missing required fields"
        except jsonschema.ValidationError:
            pass


# ============================================================
# TestIntelligenceBriefSchema
# ============================================================

class TestIntelligenceBriefSchema:
    def setup_method(self):
        self.schema = load_schema("intelligence_brief")

    def _valid_base(self) -> dict:
        return {
            "professional_knowledge": {
                "retrieval_backend": "bm25",
                "cards_used": [
                    {
                        "card_id": "hook.visual-contrast.001",
                        "domain": "hook_mechanic",
                        "source_ref": "knowledge_alignment:hook.visual-contrast.001",
                        "summary": "Use visible contrast in the opening second.",
                        "principles": ["Create a concrete contrast before explaining the product."],
                        "relevance_score": 0.9,
                        "why_relevant": "Short-form placement needs instant comprehension.",
                        "avoid_when": ["The contrast would exaggerate the claim."],
                        "failure_patterns": ["Generic shock image unrelated to the product."],
                        "execution_techniques": ["Open with a before/after visual gap."],
                    }
                ],
                "application_recommendations": [
                    {
                        "card_id": "hook.visual-contrast.001",
                        "target": "hook",
                        "recommendation": "Make the first second show a visible gap.",
                        "confidence": "producer-doctrine",
                    }
                ],
                "contraindications": [
                    {
                        "card_id": "hook.visual-contrast.001",
                        "avoid_when": "The contrast would exaggerate the claim.",
                        "reason": "Truth contract must permit the hook.",
                    }
                ],
                "gaps": [],
                "warnings": [],
            },
            "audience_psychographics": {
                "emotional_profile": "Overwhelmed but optimistic",
                "core_pain_point": "Too much admin work steals creative time",
                "aspiration": "Reclaim hours to do meaningful work",
            },
            "platform_trends": [
                {
                    "signal": "Hook-first short videos under 3 seconds dominate",
                    "source": "TikTok Insights Q1 2026",
                    "relevance": "Audiences skip after 2s — hook must be immediate",
                }
            ],
            "hit_ads_analyzed": [
                {
                    "title": "Notion — Feel the difference",
                    "platform": "youtube",
                    "arc_type": "problem-solution",
                    "hook_mechanic": "question",
                    "what_works": "Relatable chaos before calm payoff",
                    "adopted": True,
                    "adaptation": "Adapt problem montage to product's context",
                }
            ],
            "rejected_approaches": [
                {
                    "approach": "Celebrity testimonial",
                    "reason": "Budget constraint and low brand recognition fit",
                }
            ],
            "recommendations": {
                "arc_type": {
                    "value": "problem-solution",
                    "confidence": "research-grounded",
                    "rationale": "Dominant pattern in top-performing SaaS ads",
                },
                "pacing_model": {
                    "value": "punchy",
                    "confidence": "pattern-inferred",
                    "rationale": "TikTok audience retention drops after 2s",
                },
                "hook_mechanic": {
                    "value": "question",
                    "confidence": "research-grounded",
                    "rationale": "Questions create cognitive gap",
                },
                "hook_window_seconds": {
                    "value": 2,
                    "confidence": "research-grounded",
                    "rationale": "Platform data shows 2s drop-off",
                },
                "overall_rationale": "Pattern from 5 analyzed hit ads converges on fast hook + social proof.",
            },
        }

    def test_valid_base(self):
        validate(self._valid_base(), self.schema)

    def test_rejects_empty_rejected_approaches(self):
        instance = self._valid_base()
        instance["rejected_approaches"] = []  # minItems: 1 violated
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for empty rejected_approaches"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_confidence_tier(self):
        instance = self._valid_base()
        instance["recommendations"]["arc_type"]["confidence"] = "guessed"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for invalid confidence tier 'guessed'"
        except jsonschema.ValidationError:
            pass

    def test_valid_with_dimension_verdicts(self):
        instance = self._valid_base()
        instance["dimension_verdicts"] = [
            {"dimension": "arc_type", "confidence": "research-grounded", "verdict": "SUPPORTED"},
            {"dimension": "music_direction", "confidence": "pattern-inferred", "verdict": "INSUFFICIENT-DATA"},
            {
                "dimension": "hook_mechanic",
                "confidence": "research-grounded",
                "verdict": "CONTRADICTED",
                "challenge_evidence": "Notion 2024 TikTok campaign used question hook with 52% completion rate vs 31% for statement hook.",
            },
        ]
        validate(instance, self.schema)

    def test_dimension_verdicts_rejects_invalid_verdict(self):
        instance = self._valid_base()
        instance["dimension_verdicts"] = [
            {"dimension": "arc_type", "confidence": "research-grounded", "verdict": "MAYBE"}
        ]
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for verdict 'MAYBE'"
        except jsonschema.ValidationError:
            pass

    def test_note_default_heuristic_contradicted_passes_schema(self):
        # The rule "default-heuristic → verdict must be INSUFFICIENT-DATA" is enforced by
        # intelligence-director skill logic, not the JSON schema.
        # Schema cannot express cross-field conditionals without if/then/else.
        # EP runtime and skill instructions enforce this — schema intentionally allows it.
        instance = self._valid_base()
        instance["dimension_verdicts"] = [
            {"dimension": "pacing_model", "confidence": "default-heuristic", "verdict": "CONTRADICTED"}
        ]
        validate(instance, self.schema)  # must pass schema validation


# ============================================================
# TestProductionBibleSchema
# ============================================================

MINIMAL_BIBLE = {
    "version": "1.0",
    "pipeline": "ad-video",
    "project_id": "proj-acme-001",
    "approval": {
        "strategic_approved": False,
        "execution_approved": False,
        "modifications_log": [],
    },
    "identity": {
        "product": "Acme App",
        "platform": "tiktok",
        "duration_target_seconds": 30,
        "key_message": "Work smarter with Acme.",
        "cta": "Download free",
        "tone": "energetic",
    },
    "narrative": {
        "arc_type": "problem-solution",
        "pacing_model": "punchy",
        "hook_mechanic": "question",
        "hook_window_seconds": 2,
        "tension_peak_at_seconds": 15,
        "resolution_type": "relief",
        "emotional_beat_sequence": [
            {
                "beat_id": "b1",
                "name": "hook",
                "duration_seconds": 3,
                "emotional_target": "curiosity",
                "intensity": 0.7,
                "script_constraint": "Open with a provocative question",
                "visual_constraint": "Single tight face shot",
            },
            {
                "beat_id": "b2",
                "name": "resolution",
                "duration_seconds": 5,
                "emotional_target": "relief",
                "intensity": 0.9,
                "script_constraint": "Deliver the payoff line",
                "visual_constraint": "Product UI reveal",
            },
        ],
    },
    "intelligence": {
        "trend_alignment": {
            "selected_trend_ids": [],
            "alignments": [],
        },
        "knowledge_alignment": {
            "selected_card_ids": [],
            "alignments": [],
        },
        "rejected_approaches": [
            {"approach": "Celebrity endorsement", "reason": "Budget out of scope"}
        ]
    },
    "truth_contract": {
        "objective_facts": [
            {
                "rule_id": "TC-FACT-1",
                "requirement": "Advertised product is Acme App.",
                "prohibited_failure": "Rename or imply a different app.",
                "evidence_source": "enriched_brief.product_brief.product_name",
                "source_confidence": "source-backed",
            }
        ],
        "physical_constraints": [
            {
                "rule_id": "TC-PHYS-1",
                "requirement": "Phone and hand interactions remain physically plausible.",
                "prohibited_failure": "Impossible hand pose, floating UI without context, or warped device.",
                "evidence_source": "director physical plausibility review",
                "source_confidence": "director-verified",
            }
        ],
        "product_geometry_rules": [
            {
                "rule_id": "TC-GEO-1",
                "requirement": "Preserve Acme app UI identity and brand mark placement.",
                "prohibited_failure": "Invented app name, unrelated UI, or missing Acme mark.",
                "evidence_source": "brand_constraints.mandatory_elements",
                "source_confidence": "source-backed",
            }
        ],
        "motion_coherence_rules": [
            {
                "rule_id": "TC-MOTION-1",
                "requirement": "UI and gesture motion remain continuous across keyframes.",
                "prohibited_failure": "Teleporting UI, discontinuous gesture, or impossible perspective jump.",
                "evidence_source": "production_bible.visual.key_visual_moments",
                "source_confidence": "director-verified",
            }
        ],
        "values_guardrails": [
            {
                "rule_id": "TC-VALUES-1",
                "requirement": "No unsupported productivity, safety, or competitor claims.",
                "prohibited_failure": "Unapproved quantified claim or competitor disparagement.",
                "evidence_source": "brand_constraints.prohibited_elements",
                "source_confidence": "source-backed",
            }
        ],
    },
    "visual": {
        "style_mode": "animated",
        "render_runtime": "remotion",
    },
    "audio": {
        "voice_character": {
            "tone": "warm and direct",
            "pacing": "energetic",
            "persona": "trusted peer narrator",
        },
        "music_direction": {
            "mood": "focused optimism",
            "tempo": "medium",
            "genre_direction": "lo-fi indie",
            "arc": "sparse at hook, fuller at reveal",
        },
        "av_sync_notes": "Music swell on product reveal.",
    },
    "brand_constraints": {
        "brand_name_in_final_frame": True,
    },
    "deliverables": {
        "primary": {
            "aspect_ratio": "9:16",
            "duration_seconds": 30,
        }
    },
    "compliance_manifest": {
        "checkpoints": [
            {
                "id": "C-001",
                "applies_to_stage": "script",
                "description": "Hook must appear within first 2 seconds",
                "check_type": "timing",
                "evaluation_method": "structural",
                "criterion": "first_scene.start_seconds <= 2",
                "source_confidence": "research-grounded",
                "failure_action": "revise",
            }
        ]
    },
}


class TestProductionBibleSchema:
    def setup_method(self):
        self.schema = load_schema("production_bible")

    def test_valid_minimal_bible(self):
        validate(MINIMAL_BIBLE, self.schema)

    def test_rejects_wrong_pipeline(self):
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["pipeline"] = "animated-explainer"  # const: "ad-video" violated
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for pipeline != 'ad-video'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_arc_type(self):
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["narrative"]["arc_type"] = "mystery-reveal"  # not in enum
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for invalid arc_type 'mystery-reveal'"
        except jsonschema.ValidationError:
            pass

    def test_rejects_invalid_evaluation_method(self):
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["compliance_manifest"]["checkpoints"][0]["evaluation_method"] = "heuristic"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for invalid evaluation_method 'heuristic'"
        except jsonschema.ValidationError:
            pass

    def test_brand_name_in_final_frame_must_be_true(self):
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["brand_constraints"]["brand_name_in_final_frame"] = False  # const: true violated
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError: brand_name_in_final_frame must be true"
        except jsonschema.ValidationError:
            pass

    def test_accepts_arc_specific_beat_names(self):
        # Beat name is not enum-constrained — the schema accepts any non-empty string.
        # This confirms that all arc-type-specific beat names pass validation.
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["narrative"]["emotional_beat_sequence"] = [
            {
                "beat_id": "b1",
                "name": "hook",
                "duration_seconds": 3,
                "emotional_target": "curiosity",
                "intensity": 0.7,
                "script_constraint": "Open provocatively",
                "visual_constraint": "Tight face shot",
            },
            {
                "beat_id": "b2",
                "name": "problem",
                "duration_seconds": 5,
                "emotional_target": "frustration",
                "intensity": 0.6,
                "script_constraint": "Show the pain point",
                "visual_constraint": "Chaotic screen montage",
            },
            {
                "beat_id": "b3",
                "name": "solution_intro",
                "duration_seconds": 5,
                "emotional_target": "curiosity",
                "intensity": 0.5,
                "script_constraint": "Introduce the product gently",
                "visual_constraint": "Product first glimpse",
            },
            {
                "beat_id": "b4",
                "name": "proof",
                "duration_seconds": 7,
                "emotional_target": "confidence",
                "intensity": 0.8,
                "script_constraint": "Social proof stats",
                "visual_constraint": "Testimonial split-screen",
            },
            {
                "beat_id": "b5",
                "name": "resolution",
                "duration_seconds": 5,
                "emotional_target": "relief",
                "intensity": 0.9,
                "script_constraint": "Payoff line",
                "visual_constraint": "Product UI reveal",
            },
            {
                "beat_id": "b6",
                "name": "cta",
                "duration_seconds": 5,
                "emotional_target": "motivation",
                "intensity": 0.85,
                "script_constraint": "Clear call to action",
                "visual_constraint": "Brand end card",
            },
        ]
        # Must pass — no enum constraint on beat name.
        validate(instance, self.schema)

    def test_note_cta_null_with_execution_approved_passes_schema(self):
        # Schema allows this — cta is null but execution_approved is true.
        # EP gate G-I MUST reject this at runtime.
        instance = copy.deepcopy(MINIMAL_BIBLE)
        instance["approval"]["strategic_approved"] = True
        instance["approval"]["execution_approved"] = True
        instance["identity"]["cta"] = None  # null CTA is valid per schema
        # Must pass schema validation — the runtime gate, not the schema, enforces CTA presence.
        validate(instance, self.schema)


MINIMAL_PRODUCTION_PROPOSAL = {
    "version": "1.0",
    "selected_idea_id": "C1",
    "style_mode": "animated",
    "render_runtime": "remotion",
    "product_reference_strategy": "generate_concept_reference",
    "subtitles": {
        "mode": "burnt-in",
        "language": "en",
        "user_confirmed": True,
    },
    "dubbing": [],
    "derivatives_added": [],
    "budget_confirmed": True,
    "approved_budget_usd": 5.0,
    "music_strategy": "generative_loose",
    "audio_contract": {
        "voice_provider": "qwen3",
        "voice_id": "Dylan",
        "voice_model": "qwen3-tts-instruct-flash",
        "voice_gender": "male",
        "voice_persona": "warm product narrator with documentary restraint",
        "voice_performance": {
            "tone": "warm, confident, and precise; not an announcer",
            "baseline_emotion": "calm assurance",
            "emotion_arc": "curiosity -> tactile reveal -> confident CTA",
            "intonation": "natural conversational rises and gentle downward resolves",
            "rhythm": "varied phrase lengths with breath room around reveals",
            "pause_policy": "0.3-0.5s after major claims and before the CTA",
        },
        "voice_sample_approved": True,
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
        "atmosphere": {
            "default_layers": [],
        },
        "anti_template_checklist": [
            "non-uniform spacing across scenes",
        ],
        "visual_asset_provider_locks": [
            {
                "asset_type": "image",
                "source_tool": "wanx_image",
                "model": "wan2.7-image-pro",
                "usage": "packshots and still product cards",
            },
            {
                "asset_type": "video",
                "source_tool": "wan_video_api",
                "model": "wan2.6-t2v",
                "usage": "generated product/lifestyle motion scenes",
            },
            {
                "asset_type": "video",
                "source_tool": "pexels_video",
                "usage": "free stock establishing shots",
            },
        ],
    },
}


class TestProductionProposalSchema:
    def setup_method(self):
        self.schema = load_schema("production_proposal")

    def test_valid_qwen_instruction_model(self):
        validate(copy.deepcopy(MINIMAL_PRODUCTION_PROPOSAL), self.schema)

    def test_valid_openai_instruction_model(self):
        instance = copy.deepcopy(MINIMAL_PRODUCTION_PROPOSAL)
        instance["audio_contract"]["voice_provider"] = "openai"
        instance["audio_contract"]["voice_id"] = "alloy"
        instance["audio_contract"]["voice_model"] = "gpt-4o-mini-tts"
        instance["audio_contract"]["voice_gender"] = "neutral"
        validate(instance, self.schema)

    def test_rejects_cosyvoice_family_model_for_locked_instructions(self):
        instance = copy.deepcopy(MINIMAL_PRODUCTION_PROPOSAL)
        instance["audio_contract"]["voice_model"] = "cosyvoice-v3-flash"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for CosyVoice model that drops instructions"
        except jsonschema.ValidationError:
            pass

    def test_rejects_unknown_qwen_model_typo(self):
        instance = copy.deepcopy(MINIMAL_PRODUCTION_PROPOSAL)
        instance["audio_contract"]["voice_model"] = "qwen3-tts-instruct"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for unsupported qwen3 TTS model"
        except jsonschema.ValidationError:
            pass

    def test_rejects_qwen_provider_with_cosyvoice_voice_id(self):
        instance = copy.deepcopy(MINIMAL_PRODUCTION_PROPOSAL)
        instance["audio_contract"]["voice_id"] = "longanyang"
        try:
            validate(instance, self.schema)
            assert False, "Expected ValidationError for voice id unsupported by qwen3 instruct"
        except jsonschema.ValidationError:
            pass
