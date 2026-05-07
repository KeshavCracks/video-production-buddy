"""Derive a sampled emotional-intensity curve from a bible's beat sequence.

The ad-video pipeline writes per-beat `intensity` (0.0-1.0) into
`production_bible.narrative.emotional_beat_sequence` from the pacing-model
table in bible-director. Until now no downstream stage read it. This module
turns the per-beat values into a time-indexed curve that edit-director
(duck schedule), audio_mixer (volume envelope), and asset-director
(music-gen prompt) can consume uniformly.

Output shape per sample: ``{"t_seconds": float, "value": float}``.

The curve is *piecewise linear over boundary samples*: one sample at the
start of each beat carrying that beat's intensity, plus a closing sample at
the total duration carrying the last beat's intensity. Consumers that want a
continuous value at an arbitrary time use :func:`sample_at`, which
interpolates linearly and clamps outside the curve.
"""

from __future__ import annotations

from typing import Any


_Sample = dict[str, float]


# Duck-depth policy. Quieter narration beats duck deeper so words land; peak
# beats duck shallower so music breathes through the climax. Linear map.
LOW_INTENSITY_DUCK_DB: float = -22.0
HIGH_INTENSITY_DUCK_DB: float = -10.0

# Legacy fallback used when intensity_curve is empty — matches the historical
# flat -18 dB rule from the ad-brand playbook.
DEFAULT_DUCK_DB: float = -18.0


# TTS pacing policy. Low-intensity build sections pace slightly faster to
# carry momentum; peak sections slow down for emphasis. The range is kept
# narrow (±3%) so delivery stays natural, not robotic. The center (0.95) is
# the historical asset-director default; Path A modulates around that baseline
# rather than around 1.0, so adopting Path A does not silently speed up TTS
# for production users who relied on the legacy default.
TTS_SPEED_AT_LOW_INTENSITY: float = 0.98
TTS_SPEED_AT_HIGH_INTENSITY: float = 0.92


def derive_intensity_curve(
    emotional_beat_sequence: list[dict[str, Any]],
) -> list[_Sample]:
    """Convert a bible's beat sequence into a time-indexed intensity curve.

    Each beat must carry ``duration_seconds`` (>0) and ``intensity`` (0.0-1.0),
    matching the production_bible schema. Returns an ordered list of samples
    suitable for piecewise-linear interpolation; an empty input yields ``[]``.
    """
    if not emotional_beat_sequence:
        return []

    samples: list[_Sample] = []
    cursor = 0.0
    for idx, beat in enumerate(emotional_beat_sequence):
        duration = float(beat["duration_seconds"])
        intensity = float(beat["intensity"])

        if duration <= 0:
            raise ValueError(
                f"beat {idx} has non-positive duration_seconds={duration!r}; "
                "every beat must have duration > 0"
            )
        if not 0.0 <= intensity <= 1.0:
            raise ValueError(
                f"beat {idx} has intensity={intensity!r} outside [0.0, 1.0]; "
                "the bible schema bounds intensity to that range"
            )

        samples.append({"t_seconds": cursor, "value": intensity})
        cursor += duration

    # Closing sample at total duration carries the last beat's intensity so
    # consumers interpolating up to the end don't fall off the curve.
    samples.append({"t_seconds": cursor, "value": float(emotional_beat_sequence[-1]["intensity"])})
    return samples


def sample_at(curve: list[_Sample], t_seconds: float) -> float:
    """Return the interpolated intensity at ``t_seconds``.

    Linear interpolation between adjacent samples; clamps to the first sample's
    value before the curve starts and the last sample's value after it ends.
    Raises ``ValueError`` on an empty curve.
    """
    if not curve:
        raise ValueError("cannot sample an empty curve")

    if t_seconds <= curve[0]["t_seconds"]:
        return float(curve[0]["value"])
    if t_seconds >= curve[-1]["t_seconds"]:
        return float(curve[-1]["value"])

    for left, right in zip(curve, curve[1:]):
        if left["t_seconds"] <= t_seconds <= right["t_seconds"]:
            span = right["t_seconds"] - left["t_seconds"]
            if span == 0:
                return float(left["value"])
            ratio = (t_seconds - left["t_seconds"]) / span
            return float(left["value"]) + ratio * (float(right["value"]) - float(left["value"]))

    # Unreachable given the clamps above, but keep the type-checker happy.
    return float(curve[-1]["value"])


def duck_db_for_intensity(intensity: float) -> float:
    """Map an intensity value (0.0..1.0) to a music duck depth in dB.

    Clamps inputs outside [0, 1] to the nearest extreme so the policy is total.
    """
    clamped = max(0.0, min(1.0, intensity))
    return LOW_INTENSITY_DUCK_DB + clamped * (HIGH_INTENSITY_DUCK_DB - LOW_INTENSITY_DUCK_DB)


def _merge_windows(
    windows: list[dict[str, Any]],
    fade_seconds: float = 0.0,
) -> list[dict[str, float]]:
    """Sort and merge overlapping, contiguous, or near-contiguous narration windows.

    Two windows whose bodies are separated by less than ``2 * fade_seconds`` are
    merged: their post- and pre-fade samples would otherwise interleave in the
    wrong temporal order and the music would blip back to full volume between
    them. Merging keeps the music ducked across the short gap instead.
    Default ``fade_seconds=0`` preserves the strict overlap/contiguous rule.
    """
    cleaned: list[tuple[float, float]] = []
    for win in windows:
        start = float(win["start_seconds"])
        end = float(win["end_seconds"])
        if end < start:
            raise ValueError(
                f"narration window has end_seconds={end} < start_seconds={start}; "
                "windows must have non-decreasing time"
            )
        if end == start:
            continue  # zero-duration window contributes nothing
        cleaned.append((start, end))

    cleaned.sort()
    merge_gap = 2.0 * fade_seconds
    merged: list[list[float]] = []
    for start, end in cleaned:
        if merged and start <= merged[-1][1] + merge_gap:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [{"start_seconds": s, "end_seconds": e} for s, e in merged]


def derive_duck_schedule(
    intensity_curve: list[_Sample],
    narration_windows: list[dict[str, Any]],
    *,
    fade_seconds: float = 0.3,
    default_duck_db: float = DEFAULT_DUCK_DB,
) -> list[dict[str, float]]:
    """Produce a music volume schedule from an intensity curve and narration windows.

    Returns a list of ``{"t_seconds", "gain_db"}`` samples ordered ascending in time.
    Music sits at 0 dB outside narration. Inside each narration window the music
    ducks; the duck depth is derived from the intensity at the window edges so the
    duck contour tracks the emotional arc.

    When ``intensity_curve`` is empty (legacy briefs without a curve), every duck
    sample uses ``default_duck_db`` — this preserves the historical flat -18 dB
    behavior. The fade samples emit at ``window.start - fade_seconds`` and
    ``window.end + fade_seconds`` (clamped to t >= 0) so the music_mixer can
    smoothly transition into and out of the duck.

    Overlapping or contiguous narration windows are merged before sample emission
    so the schedule stays at the duck level across the merged region instead of
    blipping back to 0 dB between them.
    """
    if default_duck_db > 0:
        raise ValueError(
            f"default_duck_db must be <= 0 dB (got {default_duck_db}); "
            "positive values would boost the music instead of ducking it"
        )

    if not narration_windows:
        return []

    merged = _merge_windows(narration_windows, fade_seconds=fade_seconds)
    if not merged:
        return []

    have_curve = bool(intensity_curve)

    def _gain_at(t: float) -> float:
        if not have_curve:
            return default_duck_db
        return duck_db_for_intensity(sample_at(intensity_curve, t))

    schedule: list[dict[str, float]] = []
    for win in merged:
        start = win["start_seconds"]
        end = win["end_seconds"]
        pre = max(0.0, start - fade_seconds)
        post = end + fade_seconds

        # Skip the pre-fade 0 dB sample when there is no room to fade (window
        # touches t=0). Otherwise the 0 dB sample sits at the same timestamp
        # as the duck sample; downstream volume-envelope consumers treat the
        # later sample as authoritative, which would cancel the duck.
        if pre < start:
            schedule.append({"t_seconds": pre, "gain_db": 0.0})
        schedule.append({"t_seconds": start, "gain_db": _gain_at(start)})
        schedule.append({"t_seconds": end, "gain_db": _gain_at(end)})
        schedule.append({"t_seconds": post, "gain_db": 0.0})

    schedule.sort(key=lambda s: s["t_seconds"])
    return schedule


# ── Volume schedule consumption ──────────────────────────────────────────────

def _db_to_linear(gain_db: float) -> float:
    """Convert a dB gain to a linear amplitude multiplier."""
    return 10.0 ** (gain_db / 20.0)


def sample_volume_schedule(schedule: list[dict[str, float]], t_seconds: float) -> float:
    """Return the linear amplitude that a duck schedule prescribes at ``t_seconds``.

    Useful for testing and for callers that want to inspect the envelope without
    going through FFmpeg. Linearly interpolates in *amplitude* space between
    adjacent schedule samples (which matches how the FFmpeg ``volume`` filter
    multiplies the audio signal). Empty schedule → 1.0 (no attenuation).
    Clamps to the first/last sample outside the curve's range.
    """
    if not schedule:
        return 1.0

    samples = sorted(schedule, key=lambda s: s["t_seconds"])
    if t_seconds <= samples[0]["t_seconds"]:
        return _db_to_linear(samples[0]["gain_db"])
    if t_seconds >= samples[-1]["t_seconds"]:
        return _db_to_linear(samples[-1]["gain_db"])

    for left, right in zip(samples, samples[1:]):
        if left["t_seconds"] <= t_seconds <= right["t_seconds"]:
            span = right["t_seconds"] - left["t_seconds"]
            if span == 0:
                return _db_to_linear(left["gain_db"])
            ratio = (t_seconds - left["t_seconds"]) / span
            v_left = _db_to_linear(left["gain_db"])
            v_right = _db_to_linear(right["gain_db"])
            return v_left + ratio * (v_right - v_left)

    return _db_to_linear(samples[-1]["gain_db"])  # unreachable


def derive_editing_rhythm_from_intensity(intensity: float) -> dict[str, Any]:
    """Map a beat's intensity (0..1) to an editing_rhythm dict.

    Mirrors the bible-schema enum (`cuts_density`, `transition_style`) and
    matches the audio-side propagation:

      ``[0.0, 0.3)``   → held / 6.0s / dissolve
      ``[0.3, 0.6)``   → moderate / 3.0s / hard_cut
      ``[0.6, 0.85)``  → rapid / 1.5s / hard_cut
      ``[0.85, 1.0]``  → rapid / 1.0s / match_cut

    Bands are half-open (``<``); a beat at exactly 0.6 lands in "rapid", not
    "moderate". This matches ``_expected_density_rank`` so the consistency
    check and the derive function agree on boundary cases.

    Note: this function never emits ``"slow"`` (only ``held|moderate|rapid``).
    The schema enum allows ``"slow"`` because intelligence-director may surface
    it from research, but the deterministic fallback uses the four bands above.

    Used by bible-director Step 3 as a fallback when intelligence-director
    returned only ``default-heuristic`` editing_rhythm signal — the curve table
    is more honest than a guessed cuts_density.

    Inputs outside [0, 1] are clamped.
    """
    clamped = max(0.0, min(1.0, intensity))
    if clamped < 0.3:
        return {
            "cuts_density": "held",
            "avg_shot_duration_seconds": 6.0,
            "transition_style": "dissolve",
        }
    if clamped < 0.6:
        return {
            "cuts_density": "moderate",
            "avg_shot_duration_seconds": 3.0,
            "transition_style": "hard_cut",
        }
    if clamped < 0.85:
        return {
            "cuts_density": "rapid",
            "avg_shot_duration_seconds": 1.5,
            "transition_style": "hard_cut",
        }
    return {
        "cuts_density": "rapid",
        "avg_shot_duration_seconds": 1.0,
        "transition_style": "match_cut",
    }


_DENSITY_RANK = {"held": 0, "slow": 1, "moderate": 2, "rapid": 3}


def _expected_density_rank(intensity: float) -> int:
    """Map intensity to the expected cuts_density rank used by consistency check."""
    if intensity < 0.3:
        return _DENSITY_RANK["held"]
    if intensity < 0.6:
        return _DENSITY_RANK["moderate"]
    return _DENSITY_RANK["rapid"]


def check_editing_rhythm_consistency(
    intensity: float, editing_rhythm: dict[str, Any]
) -> list[str]:
    """Return all warning strings where ``editing_rhythm`` sharply disagrees
    with ``intensity`` for a beat. Empty list when consistent.

    The check is deliberately conservative — only flags divergence ≥ 2 tiers
    apart on the cuts_density axis (e.g. peak intensity with held shots).
    Adjacent tiers do not warn, so the agent isn't drowned in noise. Also
    catches the long-shots-at-peak case independently on the
    avg_shot_duration_seconds axis. **Both branches can fire on the same
    beat** — callers must record every entry; do not assume singular.

    Unknown / missing fields are silent (the bible's JSON-schema validator
    catches enum violations; this helper focuses on semantic divergence).
    """
    warnings: list[str] = []

    density = editing_rhythm.get("cuts_density")
    if density in _DENSITY_RANK:
        observed = _DENSITY_RANK[density]
        expected = _expected_density_rank(intensity)
        if abs(observed - expected) >= 2:
            warnings.append(
                f"intensity {intensity:.2f} suggests rank {expected} cuts but "
                f"editing_rhythm specifies cuts_density={density!r} (rank {observed}); "
                f"these are 2+ tiers apart"
            )

    avg = editing_rhythm.get("avg_shot_duration_seconds")
    if isinstance(avg, (int, float)) and intensity >= 0.7 and avg >= 4.0:
        warnings.append(
            f"intensity {intensity:.2f} (peak) but avg_shot_duration_seconds={avg} "
            f"(long shots disagree with peak emotional contour)"
        )

    return warnings


def derive_tts_directive(intensity: float) -> dict[str, float]:
    """Map a beat's intensity (0..1) to a provider-agnostic TTS directive.

    Returns ``{"speed_mult": float}``. Asset-director maps ``speed_mult`` to the
    active provider's parameter (cosyvoice ``speed``, ElevenLabs voice settings,
    etc.). The range stays inside ±3% so delivery is shaped, not robotic.

    Clamps inputs outside [0, 1] to the nearest extreme so the policy is total
    and downstream callers do not need to validate before calling.
    """
    clamped = max(0.0, min(1.0, intensity))
    speed_mult = TTS_SPEED_AT_LOW_INTENSITY + clamped * (
        TTS_SPEED_AT_HIGH_INTENSITY - TTS_SPEED_AT_LOW_INTENSITY
    )
    return {"speed_mult": speed_mult}


def describe_intensity_arc(intensity_curve: list[_Sample]) -> str:
    """Render a curve as a short prose summary for music-gen prompts.

    MiniMax (and other text-prompted music models) cannot hit exact timestamps
    but they do respect arc language. This helper turns a curve into a phrase
    like ``"build to high energy by 15s, peak at 15-20s, resolve to mid energy
    by 30s"`` that a director skill can paste into the prompt deterministically.

    Empty curve → ``""``. Flat curves describe sustained energy. The output is
    capped at ~200 chars so it fits comfortably inside the 2000-char prompt.
    """
    if not intensity_curve:
        return ""

    samples = sorted(intensity_curve, key=lambda s: s["t_seconds"])
    values = [s["value"] for s in samples]
    times = [s["t_seconds"] for s in samples]
    v_max = max(values)
    v_min = min(values)
    end_t = times[-1]

    # Flat curve → no peak to identify.
    if (v_max - v_min) < 0.05:
        level = _level_word(v_max)
        return f"sustained {level} energy throughout 0-{_fmt_t(end_t)}s"

    # Peak window: contiguous range above 0.8 * v_max.
    threshold = 0.8 * v_max
    peak_start_idx = next(i for i, v in enumerate(values) if v >= threshold)
    peak_end_idx = len(values) - 1 - next(
        i for i, v in enumerate(reversed(values)) if v >= threshold
    )
    peak_t_start = times[peak_start_idx]
    peak_t_end = times[peak_end_idx]
    peak_level = _level_word(v_max)

    parts: list[str] = []
    if peak_t_start > times[0]:
        opening_level = _level_word(values[0])
        parts.append(f"build from {opening_level} to {peak_level} by {_fmt_t(peak_t_start)}s")
    if peak_t_end > peak_t_start:
        parts.append(f"peak at {_fmt_t(peak_t_start)}-{_fmt_t(peak_t_end)}s")
    else:
        parts.append(f"peak at {_fmt_t(peak_t_start)}s")
    if peak_t_end < end_t:
        closing_level = _level_word(values[-1])
        parts.append(f"resolve to {closing_level} by {_fmt_t(end_t)}s")

    arc = ", ".join(parts)
    if len(arc) > 200:
        arc = arc[:197] + "..."
    return arc


def _level_word(value: float) -> str:
    """Map a 0..1 intensity value to a qualitative energy descriptor."""
    if value < 0.35:
        return "low energy"
    if value < 0.65:
        return "mid energy"
    return "high energy"


def _fmt_t(seconds: float) -> str:
    """Format a time as an int when whole, otherwise one decimal."""
    if seconds == int(seconds):
        return str(int(seconds))
    return f"{seconds:.1f}"


def compile_volume_schedule_to_ffmpeg_expr(schedule: list[dict[str, float]]) -> str:
    """Compile a duck schedule into an FFmpeg ``volume`` filter expression.

    The returned expression is suitable for use with ``volume='<expr>':eval=frame``.
    It reproduces the same piecewise-linear amplitude envelope as
    :func:`sample_volume_schedule`, expressed using only the ``if(...)`` and
    ``lt(...)`` primitives understood by FFmpeg's expression evaluator.

    Empty schedule → ``"1.0"`` (constant unity gain — pass-through).
    Single sample → constant linear amplitude (no ``t`` reference).
    """
    if not schedule:
        return "1.0"

    samples = sorted(schedule, key=lambda s: s["t_seconds"])
    linear = [(s["t_seconds"], _db_to_linear(s["gain_db"])) for s in samples]

    if len(linear) == 1:
        return f"{linear[0][1]:.6f}"

    # Build outwards from the post-curve clamp.
    expr = f"{linear[-1][1]:.6f}"
    for i in range(len(linear) - 2, -1, -1):
        t_a, v_a = linear[i]
        t_b, v_b = linear[i + 1]
        if t_b == t_a:
            interp = f"{v_b:.6f}"
        else:
            slope = (v_b - v_a) / (t_b - t_a)
            interp = f"({v_a:.6f}+({slope:.6f})*(t-{t_a:.6f}))"
        expr = f"if(lt(t,{t_b:.6f}),{interp},{expr})"

    # Outer clamp for t before the first sample.
    t_0, v_0 = linear[0]
    expr = f"if(lt(t,{t_0:.6f}),{v_0:.6f},{expr})"
    return expr
