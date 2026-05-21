"""Artifact schema loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_DIR = Path(__file__).parent

ARTIFACT_NAMES = [
    "user_request",
    "research_brief",
    "proposal_packet",
    "brief",
    "intake_brief",
    "enriched_brief",
    "intelligence_brief",
    "production_bible",
    "idea_options",
    "production_proposal",
    "product_identity_reference",
    "script",
    "character_design",
    "rig_plan",
    "pose_library",
    "scene_plan",
    "action_timeline",
    "asset_manifest",
    "edit_decisions",
    "render_report",
    "publish_log",
    "review",
    "cost_log",
    "decision_log",
    "ui_form_config",
    "ui_response",
    "source_media_review",
    "final_review",
    "character_qa_report",
    "video_analysis_brief",
]


def load_schema(name: str) -> dict:
    """Load a JSON schema by artifact name."""
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    with open(path) as f:
        return json.load(f)


def _validate_ad_video_script(data: dict[str, Any]) -> None:
    """Enforce ad-video script requirements that need pipeline context."""
    required_voice_performance = [
        "emotion",
        "intonation",
        "rhythm",
        "pace",
        "pause_after_seconds",
    ]
    for idx, section in enumerate(data.get("sections", []) or []):
        section_id = section.get("id", f"section-{idx}")
        speaker_directions = section.get("speaker_directions")
        if not isinstance(speaker_directions, str) or not speaker_directions.strip():
            raise jsonschema.ValidationError(
                "ad-video script section "
                f"{section_id!r} must include non-empty speaker_directions"
            )

        voice_performance = section.get("voice_performance")
        if not isinstance(voice_performance, dict):
            raise jsonschema.ValidationError(
                "ad-video script section "
                f"{section_id!r} must include voice_performance"
            )

        missing = [
            field
            for field in required_voice_performance
            if field not in voice_performance
        ]
        if missing:
            raise jsonschema.ValidationError(
                "ad-video script section "
                f"{section_id!r} voice_performance missing fields: {missing}"
            )

        if not isinstance(section.get("tts_directive"), dict):
            raise jsonschema.ValidationError(
                "ad-video script section "
                f"{section_id!r} must include tts_directive"
            )


def _validate_ad_video_production_bible(data: dict[str, Any]) -> None:
    """Enforce derived emotional rhythm data for ad-video bibles."""
    from lib.intensity_curve import derive_intensity_curve

    narrative = data.get("narrative") or {}
    beats = narrative.get("emotional_beat_sequence") or []
    curve = narrative.get("intensity_curve")
    if not isinstance(curve, list) or not curve:
        raise jsonschema.ValidationError(
            "ad-video production_bible.narrative.intensity_curve is required"
        )

    expected = derive_intensity_curve(beats)
    if len(curve) != len(expected):
        raise jsonschema.ValidationError(
            "ad-video production_bible.narrative.intensity_curve must match "
            "lib.intensity_curve.derive_intensity_curve(emotional_beat_sequence); "
            f"expected {len(expected)} samples, got {len(curve)}"
        )

    for idx, (actual, wanted) in enumerate(zip(curve, expected)):
        actual_t = float(actual.get("t_seconds"))
        actual_value = float(actual.get("value"))
        wanted_t = float(wanted["t_seconds"])
        wanted_value = float(wanted["value"])
        if abs(actual_t - wanted_t) > 1e-6 or abs(actual_value - wanted_value) > 1e-6:
            raise jsonschema.ValidationError(
                "ad-video production_bible.narrative.intensity_curve must match "
                "lib.intensity_curve.derive_intensity_curve(emotional_beat_sequence); "
                f"sample {idx} expected {wanted!r}, got {actual!r}"
            )


def _validate_ad_video_scene_plan(data: dict[str, Any]) -> None:
    """Enforce ad-video scene metadata that needs pipeline context."""
    for idx, scene in enumerate(data.get("scenes", []) or []):
        scene_id = scene.get("id", f"scene-{idx}")
        if "product_visibility" not in scene:
            raise jsonschema.ValidationError(
                "ad-video scene_plan scene "
                f"{scene_id!r} must include product_visibility"
            )
        if "product_reference_required" not in scene:
            raise jsonschema.ValidationError(
                "ad-video scene_plan scene "
                f"{scene_id!r} must include product_reference_required"
            )


def _validate_ad_video_edit_decisions(data: dict[str, Any]) -> None:
    """Enforce ad-video edit decisions that carry emotional rhythm to render."""
    audio = data.get("audio")
    music = audio.get("music") if isinstance(audio, dict) else None
    schedule = music.get("volume_schedule") if isinstance(music, dict) else None
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    music_strategy = data.get("music_strategy") or metadata.get("music_strategy")
    if music_strategy != "none" and (not isinstance(schedule, list) or not schedule):
        raise jsonschema.ValidationError(
            "ad-video edit_decisions.audio.music.volume_schedule is required"
        )

    for idx, cut in enumerate(data.get("cuts", []) or []):
        cut_id = cut.get("id", f"cut-{idx}")
        if not any(
            isinstance(cut.get(field), str) and cut[field].strip()
            for field in ("maps_to_beat", "beat_id", "beat")
        ):
            raise jsonschema.ValidationError(
                "ad-video edit_decisions cut "
                f"{cut_id!r} must include a beat label "
                "(maps_to_beat, beat_id, or beat)"
            )


def _is_ad_video_script(data: dict[str, Any], pipeline_type: str | None) -> bool:
    if pipeline_type == "ad-video":
        return True
    if pipeline_type is not None:
        return False
    if data.get("pipeline") == "ad-video":
        return True
    metadata = data.get("metadata") or {}
    if isinstance(metadata, dict) and metadata.get("pipeline") == "ad-video":
        return True
    return data.get("style_mode") in {"animated", "cinematic"}


def _is_ad_video_scene_plan(pipeline_type: str | None) -> bool:
    return pipeline_type == "ad-video"


def _is_ad_video_production_bible(data: dict[str, Any], pipeline_type: str | None) -> bool:
    return pipeline_type == "ad-video" or data.get("pipeline") == "ad-video"


def _is_ad_video_edit_decisions(pipeline_type: str | None) -> bool:
    return pipeline_type == "ad-video"


def validate_artifact(
    name: str,
    data: dict[str, Any],
    *,
    pipeline_type: str | None = None,
) -> None:
    """Validate artifact data against its schema. Raises on failure."""
    schema = load_schema(name)
    jsonschema.validate(instance=data, schema=schema)
    if name == "production_bible" and _is_ad_video_production_bible(data, pipeline_type):
        _validate_ad_video_production_bible(data)
    if name == "script" and _is_ad_video_script(data, pipeline_type):
        _validate_ad_video_script(data)
    if name == "scene_plan" and _is_ad_video_scene_plan(pipeline_type):
        _validate_ad_video_scene_plan(data)
    if name == "edit_decisions" and _is_ad_video_edit_decisions(pipeline_type):
        _validate_ad_video_edit_decisions(data)


def list_schemas() -> list[str]:
    """List all available artifact schema names."""
    return [p.stem.replace(".schema", "") for p in SCHEMA_DIR.glob("*.schema.json")]
