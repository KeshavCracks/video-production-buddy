"""Thread production_bible.narrative emotional data into generation prompts.

The bible's ``emotional_beat_sequence`` defines per-beat ``emotional_target``,
``intensity``, and ``visual_constraint`` — rich creative direction for how each
section of the video should make the viewer feel. Until now this data influenced
TTS pacing and music arc prompting but never reached visual generation prompts.
Image and video models produced technically correct but emotionally flat output
because their prompts described only what is on screen, not what the viewer should
feel.

``apply_emotional_mood`` looks up the scene's beat in the emotional_beat_sequence
and appends a concise mood/atmosphere suffix derived from the beat's
emotional_target and intensity. Video generation models (Wan, Kling, Seedance)
respond strongly to mood and atmosphere language — the suffix gives them the
emotional register they need to produce footage that evokes the intended feeling.

Pattern follows ``lib/color_direction.py`` and ``lib/resolution_treatment.py``:
idempotent suffix, pass-through when data is absent.
"""

from __future__ import annotations

from typing import Any


def _intensity_descriptor(intensity: float) -> str:
    """Map a beat's intensity (0..1) to a concise visual mood word pair."""
    if intensity < 0.3:
        return "calm contemplative"
    if intensity < 0.6:
        return "warm building"
    if intensity < 0.85:
        return "dynamic driving"
    return "intense electric"


def _condense_target(emotional_target: str) -> str:
    """Extract the core emotion phrase from an emotional_target string.

    Targets are often formatted as "Emotion — explanation" or
    "Emotion - explanation". The core emotion before the separator is the
    part that matters for prompt conditioning; the explanation is for the
    agent's understanding and bloats the prompt if included.
    """
    for sep in ("—", "–", " - ", " — "):
        if sep in emotional_target:
            emotional_target = emotional_target.split(sep)[0].strip()
            break

    if len(emotional_target) > 80:
        return emotional_target[:77] + "..."
    return emotional_target


def apply_emotional_mood(
    prompt: str,
    beat: dict[str, Any] | None,
) -> str:
    """Append a mood/atmosphere suffix derived from the scene's emotional beat.

    ``beat`` is a single entry from
    ``production_bible.narrative.emotional_beat_sequence`` that matches the
    current scene. It must carry ``emotional_target`` (str) and ``intensity``
    (0.0-1.0).

    Returns ``prompt`` unchanged when ``beat`` is ``None`` or lacks a non-empty
    ``emotional_target`` — keeping legacy briefs and partial bibles compatible.

    Idempotent: if the suffix is already present in ``prompt``
    (case-insensitive), the prompt is returned unchanged so callers can
    re-apply safely.
    """
    if beat is None:
        return prompt

    emotional_target = beat.get("emotional_target", "")
    if not emotional_target or not emotional_target.strip():
        return prompt

    intensity = float(beat.get("intensity", 0.5))
    mood_word = _intensity_descriptor(intensity)
    target = _condense_target(emotional_target.strip())

    suffix = f"Mood: {mood_word}, {target}."

    if suffix.lower() in prompt.lower():
        return prompt

    if not prompt:
        return suffix

    trimmed = prompt.rstrip().rstrip(",")
    separator = " " if trimmed.endswith((".", "!", "?", ";")) else ". "
    return f"{trimmed}{separator}{suffix}"


def find_beat_for_scene(
    emotional_beat_sequence: list[dict[str, Any]] | None,
    scene: dict[str, Any],
) -> dict[str, Any] | None:
    """Look up the beat matching a scene's ``beat_id`` or ``beat`` field.

    Scenes carry ``beat_id`` or ``beat`` (the label). Match against
    ``beat_id`` first (authoritative identifier), then ``name`` as a fallback.
    Returns ``None`` when no match is found (legacy briefs, unmatched scenes,
    or empty sequence).
    """
    if not emotional_beat_sequence:
        return None

    scene_beat_id = scene.get("beat_id") or scene.get("beat")
    if not scene_beat_id:
        return None

    for b in emotional_beat_sequence:
        if b.get("beat_id") == scene_beat_id:
            return b

    for b in emotional_beat_sequence:
        if b.get("name", "").lower() == str(scene_beat_id).lower():
            return b

    return None
