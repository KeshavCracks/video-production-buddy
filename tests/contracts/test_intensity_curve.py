"""Unit tests for lib.intensity_curve — derive and sample emotional intensity curves.

Path B Step 1 of the ad-video emotional-rhythm propagation work. The curve is
derived from production_bible.narrative.emotional_beat_sequence and consumed
downstream by edit-director (duck schedule), audio_mixer (volume envelope),
and asset-director (music-gen prompt).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.intensity_curve import (
    DEFAULT_DUCK_DB,
    HIGH_INTENSITY_DUCK_DB,
    LOW_INTENSITY_DUCK_DB,
    TTS_SPEED_AT_LOW_INTENSITY,
    TTS_SPEED_AT_HIGH_INTENSITY,
    check_editing_rhythm_consistency,
    compile_volume_schedule_to_ffmpeg_expr,
    derive_duck_schedule,
    derive_editing_rhythm_from_intensity,
    derive_intensity_curve,
    derive_tts_directive,
    describe_intensity_arc,
    duck_db_for_intensity,
    sample_at,
    sample_volume_schedule,
)


# ── derive_intensity_curve ──────────────────────────────────────────────────

def test_empty_sequence_returns_empty_curve():
    assert derive_intensity_curve([]) == []


def test_single_beat_emits_start_and_end_samples():
    beats = [{"beat_id": "B1", "duration_seconds": 10.0, "intensity": 0.4}]
    curve = derive_intensity_curve(beats)
    assert curve == [
        {"t_seconds": 0.0, "value": 0.4},
        {"t_seconds": 10.0, "value": 0.4},
    ]


def test_multiple_beats_emit_one_sample_per_boundary_plus_close():
    # 3 beats (5s, 10s, 5s) -> samples at t=0, 5, 15, 20.
    beats = [
        {"beat_id": "B1", "duration_seconds": 5.0,  "intensity": 0.3},
        {"beat_id": "B2", "duration_seconds": 10.0, "intensity": 0.8},
        {"beat_id": "B3", "duration_seconds": 5.0,  "intensity": 0.5},
    ]
    curve = derive_intensity_curve(beats)
    assert curve == [
        {"t_seconds": 0.0,  "value": 0.3},
        {"t_seconds": 5.0,  "value": 0.8},
        {"t_seconds": 15.0, "value": 0.5},
        {"t_seconds": 20.0, "value": 0.5},
    ]


def test_curve_is_monotonically_increasing_in_time():
    beats = [
        {"beat_id": "B1", "duration_seconds": 3.0, "intensity": 0.3},
        {"beat_id": "B2", "duration_seconds": 7.0, "intensity": 0.9},
        {"beat_id": "B3", "duration_seconds": 5.0, "intensity": 0.5},
    ]
    curve = derive_intensity_curve(beats)
    times = [s["t_seconds"] for s in curve]
    assert times == sorted(times)


def test_pacing_curve_escalating_produces_rising_intensity():
    # Mirror the bible-director "escalating" curve (0.3 → 0.5 → 0.7 → 0.9 → 0.7 → 0.5).
    beats = [
        {"beat_id": f"B{i+1}", "duration_seconds": 5.0, "intensity": v}
        for i, v in enumerate([0.3, 0.5, 0.7, 0.9, 0.7, 0.5])
    ]
    curve = derive_intensity_curve(beats)
    # Total duration 30s; 7 samples (6 starts + 1 close).
    assert len(curve) == 7
    assert curve[0]["t_seconds"] == 0.0 and curve[0]["value"] == 0.3
    assert curve[-1]["t_seconds"] == 30.0
    # Peak should be the 4th boundary sample.
    peak = max(curve, key=lambda s: s["value"])
    assert peak == {"t_seconds": 15.0, "value": 0.9}


def test_intensity_below_zero_raises():
    beats = [{"beat_id": "B1", "duration_seconds": 5.0, "intensity": -0.1}]
    with pytest.raises(ValueError, match="intensity"):
        derive_intensity_curve(beats)


def test_intensity_above_one_raises():
    beats = [{"beat_id": "B1", "duration_seconds": 5.0, "intensity": 1.5}]
    with pytest.raises(ValueError, match="intensity"):
        derive_intensity_curve(beats)


def test_zero_duration_beat_raises():
    beats = [{"beat_id": "B1", "duration_seconds": 0.0, "intensity": 0.5}]
    with pytest.raises(ValueError, match="duration"):
        derive_intensity_curve(beats)


def test_missing_intensity_field_raises():
    beats = [{"beat_id": "B1", "duration_seconds": 5.0}]
    with pytest.raises(KeyError):
        derive_intensity_curve(beats)


def test_missing_duration_field_raises():
    beats = [{"beat_id": "B1", "intensity": 0.5}]
    with pytest.raises(KeyError):
        derive_intensity_curve(beats)


# ── sample_at ───────────────────────────────────────────────────────────────

def test_sample_at_returns_exact_value_at_boundary():
    curve = [
        {"t_seconds": 0.0,  "value": 0.3},
        {"t_seconds": 5.0,  "value": 0.8},
        {"t_seconds": 10.0, "value": 0.5},
    ]
    assert sample_at(curve, 0.0) == 0.3
    assert sample_at(curve, 5.0) == 0.8
    assert sample_at(curve, 10.0) == 0.5


def test_sample_at_interpolates_linearly_between_boundaries():
    curve = [
        {"t_seconds": 0.0,  "value": 0.0},
        {"t_seconds": 10.0, "value": 1.0},
    ]
    assert sample_at(curve, 5.0) == pytest.approx(0.5)
    assert sample_at(curve, 2.5) == pytest.approx(0.25)
    assert sample_at(curve, 7.5) == pytest.approx(0.75)


def test_sample_at_clamps_before_first_sample():
    curve = [
        {"t_seconds": 5.0,  "value": 0.4},
        {"t_seconds": 15.0, "value": 0.9},
    ]
    assert sample_at(curve, -1.0) == 0.4
    assert sample_at(curve, 0.0) == 0.4


def test_sample_at_clamps_after_last_sample():
    curve = [
        {"t_seconds": 0.0,  "value": 0.3},
        {"t_seconds": 10.0, "value": 0.8},
    ]
    assert sample_at(curve, 12.0) == 0.8
    assert sample_at(curve, 100.0) == 0.8


def test_sample_at_empty_curve_raises():
    with pytest.raises(ValueError, match="empty"):
        sample_at([], 5.0)


def test_sample_at_single_sample_returns_that_value():
    curve = [{"t_seconds": 3.0, "value": 0.7}]
    assert sample_at(curve, 0.0) == 0.7
    assert sample_at(curve, 3.0) == 0.7
    assert sample_at(curve, 10.0) == 0.7


# ── duck_db_for_intensity ──────────────────────────────────────────────────

def test_duck_db_at_zero_is_deepest():
    assert duck_db_for_intensity(0.0) == pytest.approx(LOW_INTENSITY_DUCK_DB)


def test_duck_db_at_one_is_shallowest():
    assert duck_db_for_intensity(1.0) == pytest.approx(HIGH_INTENSITY_DUCK_DB)


def test_duck_db_interpolates_linearly():
    # At intensity 0.5, duck depth is the midpoint of the two extremes.
    midpoint = (LOW_INTENSITY_DUCK_DB + HIGH_INTENSITY_DUCK_DB) / 2
    assert duck_db_for_intensity(0.5) == pytest.approx(midpoint)


def test_duck_db_clamps_outside_range():
    assert duck_db_for_intensity(-0.5) == pytest.approx(LOW_INTENSITY_DUCK_DB)
    assert duck_db_for_intensity(1.5) == pytest.approx(HIGH_INTENSITY_DUCK_DB)


# ── derive_duck_schedule ───────────────────────────────────────────────────

def _curve(*samples: tuple[float, float]) -> list[dict]:
    return [{"t_seconds": t, "value": v} for t, v in samples]


def _window(start: float, end: float) -> dict:
    return {"start_seconds": start, "end_seconds": end}


def test_duck_schedule_empty_windows_returns_empty():
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    assert derive_duck_schedule(curve, []) == []


def test_duck_schedule_legacy_fallback_when_curve_is_empty():
    """No intensity_curve → flat default duck (-18 dB) inside windows, 0 outside."""
    schedule = derive_duck_schedule([], [_window(2.0, 8.0)], fade_seconds=0.3)
    # Expect: pre-fade at 1.7s (0 dB), duck at 2.0 (-18), duck at 8.0 (-18), post-fade at 8.3s (0).
    assert schedule == [
        {"t_seconds": pytest.approx(1.7),  "gain_db": pytest.approx(0.0)},
        {"t_seconds": pytest.approx(2.0),  "gain_db": pytest.approx(DEFAULT_DUCK_DB)},
        {"t_seconds": pytest.approx(8.0),  "gain_db": pytest.approx(DEFAULT_DUCK_DB)},
        {"t_seconds": pytest.approx(8.3),  "gain_db": pytest.approx(0.0)},
    ]


def test_duck_schedule_low_intensity_window_ducks_deep():
    curve = _curve((0.0, 0.2), (10.0, 0.2))
    schedule = derive_duck_schedule(curve, [_window(2.0, 8.0)], fade_seconds=0.3)
    # All four samples; the two duck samples are derived from intensity=0.2 → near-deep.
    inside = [s for s in schedule if 2.0 <= s["t_seconds"] <= 8.0]
    expected = duck_db_for_intensity(0.2)
    for s in inside:
        assert s["gain_db"] == pytest.approx(expected)
    # Deep duck means closer to LOW_INTENSITY_DUCK_DB than to HIGH.
    assert abs(expected - LOW_INTENSITY_DUCK_DB) < abs(expected - HIGH_INTENSITY_DUCK_DB)


def test_duck_schedule_high_intensity_window_ducks_shallow():
    curve = _curve((0.0, 0.9), (10.0, 0.9))
    schedule = derive_duck_schedule(curve, [_window(2.0, 8.0)], fade_seconds=0.3)
    inside = [s for s in schedule if 2.0 <= s["t_seconds"] <= 8.0]
    expected = duck_db_for_intensity(0.9)
    for s in inside:
        assert s["gain_db"] == pytest.approx(expected)
    # Shallow duck means closer to HIGH_INTENSITY_DUCK_DB.
    assert abs(expected - HIGH_INTENSITY_DUCK_DB) < abs(expected - LOW_INTENSITY_DUCK_DB)


def test_duck_schedule_tracks_intensity_within_window():
    """Window straddles a rising intensity — start sample and end sample differ."""
    curve = _curve((0.0, 0.2), (5.0, 0.9), (10.0, 0.9))
    schedule = derive_duck_schedule(curve, [_window(0.0, 5.0)], fade_seconds=0.3)
    # Pre-fade clamps to 0 (start - 0.3 < 0 still allowed; ffmpeg ignores negatives, but emit at 0).
    starts = [s for s in schedule if s["t_seconds"] == 0.0]
    ends = [s for s in schedule if s["t_seconds"] == 5.0]
    assert starts and ends
    # Gain at start corresponds to intensity 0.2; gain at end corresponds to intensity 0.9.
    assert starts[0]["gain_db"] == pytest.approx(duck_db_for_intensity(0.2))
    assert ends[0]["gain_db"] == pytest.approx(duck_db_for_intensity(0.9))


def test_duck_schedule_preserves_internal_curve_samples_inside_merged_window():
    """A continuous narration bed must not flatten internal emotional peaks."""
    curve = _curve(
        (0.0, 0.2),
        (12.0, 0.95),
        (24.0, 0.35),
        (36.0, 0.85),
        (48.0, 0.4),
        (60.0, 0.4),
    )
    schedule = derive_duck_schedule(
        curve,
        # Near-contiguous narration windows merge into one [2, 55] body.
        [_window(2.0, 20.0), _window(20.4, 40.0), _window(40.2, 55.0)],
        fade_seconds=0.3,
    )

    by_time = {round(sample["t_seconds"], 6): sample for sample in schedule}
    for t_seconds, intensity in [(12.0, 0.95), (24.0, 0.35), (36.0, 0.85), (48.0, 0.4)]:
        assert t_seconds in by_time, f"schedule missing internal curve boundary {t_seconds}s: {schedule}"
        assert by_time[t_seconds]["gain_db"] == pytest.approx(duck_db_for_intensity(intensity))


def test_duck_schedule_two_disjoint_windows_restore_between():
    curve = _curve((0.0, 0.5), (30.0, 0.5))
    schedule = derive_duck_schedule(
        curve,
        [_window(2.0, 8.0), _window(15.0, 25.0)],
        fade_seconds=0.3,
    )
    # Between windows we should have a 0 dB sample (post-fade of the first).
    rest_zeros = [s for s in schedule if 8.0 < s["t_seconds"] < 15.0 and s["gain_db"] == pytest.approx(0.0)]
    assert rest_zeros, f"expected a 0 dB sample in the gap, got {schedule}"


def test_duck_schedule_overlapping_windows_merge():
    """Overlapping narration windows should not produce 0 dB blip in the overlap region."""
    curve = _curve((0.0, 0.5), (30.0, 0.5))
    schedule = derive_duck_schedule(
        curve,
        [_window(2.0, 10.0), _window(8.0, 15.0)],
        fade_seconds=0.3,
    )
    # No sample inside the merged window [2.0, 15.0] should be at 0 dB.
    inside = [s for s in schedule if 2.0 <= s["t_seconds"] <= 15.0]
    assert all(s["gain_db"] != pytest.approx(0.0) for s in inside), (
        f"merged window should stay ducked throughout, got {inside}"
    )


def test_duck_schedule_is_time_sorted():
    curve = _curve((0.0, 0.5), (30.0, 0.5))
    schedule = derive_duck_schedule(
        curve,
        # Pass windows out of order on purpose — schedule must still come back sorted.
        [_window(15.0, 20.0), _window(2.0, 8.0)],
        fade_seconds=0.3,
    )
    times = [s["t_seconds"] for s in schedule]
    assert times == sorted(times)


def test_duck_schedule_clamps_pre_fade_to_zero():
    """Window starting at t=0 cannot pre-fade into negative time."""
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    schedule = derive_duck_schedule(curve, [_window(0.0, 5.0)], fade_seconds=0.3)
    assert schedule[0]["t_seconds"] >= 0.0


def test_duck_schedule_zero_duration_window_is_skipped():
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    schedule = derive_duck_schedule(curve, [_window(3.0, 3.0)], fade_seconds=0.3)
    assert schedule == []


def test_duck_schedule_negative_window_raises():
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    with pytest.raises(ValueError, match="end_seconds"):
        derive_duck_schedule(curve, [_window(5.0, 3.0)], fade_seconds=0.3)


def test_duck_schedule_custom_fade_seconds():
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    schedule = derive_duck_schedule(curve, [_window(2.0, 8.0)], fade_seconds=0.5)
    # Pre-fade at 1.5s, post-fade at 8.5s.
    assert schedule[0]["t_seconds"] == pytest.approx(1.5)
    assert schedule[-1]["t_seconds"] == pytest.approx(8.5)


def test_duck_schedule_negative_fade_seconds_raises():
    curve = _curve((0.0, 0.5), (10.0, 0.5))
    with pytest.raises(ValueError, match="fade_seconds"):
        derive_duck_schedule(curve, [_window(2.0, 8.0)], fade_seconds=-0.3)


def test_duck_schedule_custom_default_duck_db_for_legacy_path():
    schedule = derive_duck_schedule(
        [],
        [_window(0.0, 5.0)],
        fade_seconds=0.3,
        default_duck_db=-12.0,
    )
    inside = [s for s in schedule if 0.0 <= s["t_seconds"] <= 5.0]
    for s in inside:
        assert s["gain_db"] == pytest.approx(-12.0)


def test_duck_schedule_near_contiguous_windows_merge_via_fade():
    """Windows separated by less than 2*fade_seconds would otherwise produce
    interleaved 0 dB samples in the wrong temporal order (post-fade of window N
    landing AFTER pre-fade of window N+1). Merge them so music stays ducked
    across the short gap instead of blipping back to full volume."""
    curve = _curve((0.0, 0.5), (30.0, 0.5))
    schedule = derive_duck_schedule(
        curve,
        # Gap of 0.4s between window bodies; 2*fade = 0.6s. Should merge.
        [_window(2.0, 8.0), _window(8.4, 15.0)],
        fade_seconds=0.3,
    )
    # No 0 dB sample should appear inside the spanned region [2.0, 15.0].
    inside = [s for s in schedule if 2.0 <= s["t_seconds"] <= 15.0]
    assert all(s["gain_db"] != pytest.approx(0.0) for s in inside), (
        f"near-contiguous windows should stay ducked across the gap, got {inside}"
    )
    # And the schedule should be strictly time-sorted (no inverted edges).
    times = [s["t_seconds"] for s in schedule]
    assert times == sorted(times)


def test_duck_schedule_windows_separated_more_than_two_fades_stay_separate():
    """Windows separated by MORE than 2*fade_seconds remain independent and
    music returns to 0 dB between them."""
    curve = _curve((0.0, 0.5), (30.0, 0.5))
    schedule = derive_duck_schedule(
        curve,
        # Gap of 1.0s between window bodies; 2*fade = 0.6s. Should stay separate.
        [_window(2.0, 8.0), _window(9.0, 15.0)],
        fade_seconds=0.3,
    )
    rest_zeros = [s for s in schedule if 8.0 < s["t_seconds"] < 9.0 and s["gain_db"] == pytest.approx(0.0)]
    assert rest_zeros, f"separated windows should restore to 0 dB in the gap, got {schedule}"


def test_duck_schedule_all_zero_intensity_uses_deepest_duck_throughout():
    """Edge case: a curve where every beat has intensity 0.0 produces the
    deepest possible duck on every sample — no flipped sign, no clamping bug."""
    curve = _curve((0.0, 0.0), (30.0, 0.0))
    schedule = derive_duck_schedule(curve, [_window(0.0, 30.0)], fade_seconds=0.3)
    inside = [s for s in schedule if 0.0 <= s["t_seconds"] <= 30.0]
    for s in inside:
        assert s["gain_db"] == pytest.approx(LOW_INTENSITY_DUCK_DB)


def test_duck_schedule_rejects_positive_default_duck_db():
    """default_duck_db is meant to attenuate (negative dB). A positive value
    would boost the music — almost certainly a misuse. Reject explicitly."""
    with pytest.raises(ValueError, match="default_duck_db"):
        derive_duck_schedule(
            [],
            [_window(0.0, 5.0)],
            fade_seconds=0.3,
            default_duck_db=3.0,
        )


# ── sample_volume_schedule ─────────────────────────────────────────────────

def test_sample_volume_schedule_returns_unity_for_empty():
    assert sample_volume_schedule([], 5.0) == pytest.approx(1.0)


def test_sample_volume_schedule_db_to_linear_at_sample_points():
    # 0 dB → 1.0; -6 dB → ~0.501; -18 dB → ~0.126
    sched = [
        {"t_seconds": 0.0,  "gain_db": 0.0},
        {"t_seconds": 5.0,  "gain_db": -6.0},
        {"t_seconds": 10.0, "gain_db": -18.0},
    ]
    assert sample_volume_schedule(sched, 0.0)  == pytest.approx(1.0,    abs=1e-3)
    assert sample_volume_schedule(sched, 5.0)  == pytest.approx(0.5012, abs=1e-3)
    assert sample_volume_schedule(sched, 10.0) == pytest.approx(0.1259, abs=1e-3)


def test_sample_volume_schedule_clamps_outside_range():
    sched = [
        {"t_seconds": 5.0,  "gain_db": -18.0},
        {"t_seconds": 10.0, "gain_db": 0.0},
    ]
    assert sample_volume_schedule(sched, -1.0) == pytest.approx(0.1259, abs=1e-3)
    assert sample_volume_schedule(sched, 100.0) == pytest.approx(1.0,    abs=1e-3)


def test_sample_volume_schedule_interpolates_linearly_in_amplitude():
    # 0 dB (1.0 linear) at t=0; -120 dB (~0 linear) at t=10. Midpoint should be ~0.5.
    sched = [
        {"t_seconds": 0.0,  "gain_db": 0.0},
        {"t_seconds": 10.0, "gain_db": -120.0},
    ]
    assert sample_volume_schedule(sched, 5.0) == pytest.approx(0.5, abs=1e-2)


# ── compile_volume_schedule_to_ffmpeg_expr ─────────────────────────────────

def test_compile_empty_schedule_returns_unity():
    assert compile_volume_schedule_to_ffmpeg_expr([]) == "1.0"


def test_compile_single_sample_returns_constant_gain():
    expr = compile_volume_schedule_to_ffmpeg_expr([{"t_seconds": 0.0, "gain_db": 0.0}])
    # A single-sample schedule must produce a constant (no `t` reference, no `if`).
    assert "t" not in expr
    assert "if" not in expr
    # 0 dB → 1.0 linear.
    assert float(expr) == pytest.approx(1.0)


def test_compile_multi_sample_uses_only_supported_ffmpeg_tokens():
    """The compiled expression must contain only tokens FFmpeg's volume filter
    expression evaluator understands. No Python-isms, no banned constructs."""
    sched = [
        {"t_seconds": 0.0, "gain_db": 0.0},
        {"t_seconds": 2.0, "gain_db": -18.0},
        {"t_seconds": 5.0, "gain_db": 0.0},
    ]
    expr = compile_volume_schedule_to_ffmpeg_expr(sched)
    # Must reference t, must use the if/lt primitives.
    assert "t" in expr
    assert "if(" in expr
    assert "lt(" in expr
    # Must NOT contain Python operators or imports.
    forbidden = ["==", "**", "math.", "import", "lambda", "//"]
    for f in forbidden:
        assert f not in expr, f"compiled expression must not contain {f!r}: {expr}"


def test_compile_includes_all_sample_timestamps():
    sched = [
        {"t_seconds": 1.7, "gain_db": 0.0},
        {"t_seconds": 2.0, "gain_db": -18.0},
        {"t_seconds": 8.3, "gain_db": 0.0},
    ]
    expr = compile_volume_schedule_to_ffmpeg_expr(sched)
    # Each interior boundary timestamp must appear in a comparison.
    for ts in (2.0, 8.3):
        assert f"{ts:.6f}" in expr or str(ts) in expr, f"timestamp {ts} missing from {expr}"


def test_compile_agrees_with_sample_volume_schedule_at_boundaries():
    """The FFmpeg expression and sample_volume_schedule must compute the same
    linear amplitude at each schedule boundary. We can't run ffmpeg in this unit
    test, but we can verify by inspecting the generated expression contains the
    expected linear values."""
    sched = [
        {"t_seconds": 0.0, "gain_db": 0.0},     # 1.0 linear
        {"t_seconds": 2.0, "gain_db": -18.0},   # ~0.1259 linear
        {"t_seconds": 5.0, "gain_db": 0.0},     # 1.0 linear
    ]
    expr = compile_volume_schedule_to_ffmpeg_expr(sched)
    # The -18 dB linear (~0.1259) should appear in the expression.
    expected_linear = sample_volume_schedule(sched, 2.0)  # 0.1259...
    assert f"{expected_linear:.6f}" in expr, (
        f"expected linear gain {expected_linear} not found in expression: {expr}"
    )


def test_compile_output_never_uses_comma_decimal_separator():
    """Regression: Python's :.6f format spec is locale-independent (LC_NUMERIC
    only affects :n), so the compiled expression must always use '.' as the
    decimal separator regardless of the process locale. A comma decimal would
    break FFmpeg's expression parser silently — the wrapping single-quotes
    don't help because comma is the argument separator inside if(...) and
    lt(...). This test pins the contract."""
    sched = [
        {"t_seconds": 0.0,   "gain_db": 0.0},
        {"t_seconds": 1.7,   "gain_db": 0.0},
        {"t_seconds": 2.0,   "gain_db": -22.0},   # 0.07943... linear
        {"t_seconds": 8.0,   "gain_db": -10.0},   # 0.31623... linear
        {"t_seconds": 8.3,   "gain_db": 0.0},
    ]
    expr = compile_volume_schedule_to_ffmpeg_expr(sched)
    # Decimal separators must be '.', never ',' — except where ',' is the
    # legitimate FFmpeg `if(cond,a,b)` / `lt(a,b)` argument separator.
    # We verify by stripping all `if(...)` / `lt(...)` arg-separator commas
    # is overkill; instead assert that no DIGIT,DIGIT pattern appears.
    import re
    bad = re.findall(r"\d,\d", expr)
    assert not bad, (
        f"expression must use '.' decimal separator, got comma-decimal in: {expr}"
    )
    # Spot-check that expected float fragments DO appear with a dot.
    assert "0.079433" in expr or "0.07943" in expr, expr
    assert "0.316228" in expr or "0.31622" in expr, expr


# ── describe_intensity_arc ─────────────────────────────────────────────────

def test_describe_arc_empty_curve_returns_empty_string():
    assert describe_intensity_arc([]) == ""


def test_describe_arc_typical_escalating_pattern():
    """Curve that builds, peaks mid, then resolves should emit build/peak/resolve."""
    curve = [
        {"t_seconds": 0.0,  "value": 0.3},
        {"t_seconds": 5.0,  "value": 0.5},
        {"t_seconds": 10.0, "value": 0.7},
        {"t_seconds": 15.0, "value": 0.9},
        {"t_seconds": 20.0, "value": 0.7},
        {"t_seconds": 25.0, "value": 0.5},
        {"t_seconds": 30.0, "value": 0.5},
    ]
    arc = describe_intensity_arc(curve)
    assert arc, "expected a non-empty arc summary"
    # All three phases should be named.
    assert "build" in arc.lower()
    assert "peak" in arc.lower()
    assert "resolve" in arc.lower()
    # Peak window should cite times near the actual peak (15s).
    assert "15" in arc, f"peak time should appear in arc: {arc}"


def test_describe_arc_peak_at_start():
    """If intensity opens at the maximum, there is no build phase."""
    curve = [
        {"t_seconds": 0.0,  "value": 0.9},
        {"t_seconds": 5.0,  "value": 0.9},
        {"t_seconds": 10.0, "value": 0.5},
        {"t_seconds": 30.0, "value": 0.3},
    ]
    arc = describe_intensity_arc(curve)
    # No build phrase when peak starts at t=0.
    assert "build" not in arc.lower()
    assert "peak" in arc.lower()
    assert "resolve" in arc.lower()


def test_describe_arc_peak_at_end():
    """If intensity climbs to maximum at the end, there is no resolve phase."""
    curve = [
        {"t_seconds": 0.0,  "value": 0.3},
        {"t_seconds": 10.0, "value": 0.5},
        {"t_seconds": 20.0, "value": 0.7},
        {"t_seconds": 30.0, "value": 0.9},
    ]
    arc = describe_intensity_arc(curve)
    assert "build" in arc.lower()
    assert "peak" in arc.lower()
    # Resolve phrase optional — but if absent that's correct.
    # Just verify the climax is at the end (t=30 must be present).
    assert "30" in arc


def test_describe_arc_constant_curve_uses_sustained_descriptor():
    """A flat curve has no clear peak; output should describe sustained energy."""
    curve = [
        {"t_seconds": 0.0,  "value": 0.5},
        {"t_seconds": 30.0, "value": 0.5},
    ]
    arc = describe_intensity_arc(curve)
    assert "sustain" in arc.lower() or "constant" in arc.lower() or "even" in arc.lower(), (
        f"flat curve should describe sustained energy, got: {arc}"
    )


def test_describe_arc_under_200_chars():
    """Output must fit in MiniMax's 2000-char prompt budget — we cap at 200."""
    curve = [
        {"t_seconds": float(i),  "value": 0.3 + 0.6 * (i % 5) / 4}
        for i in range(0, 60, 2)
    ]
    arc = describe_intensity_arc(curve)
    assert len(arc) <= 200, f"arc summary exceeded 200 chars ({len(arc)}): {arc}"


def test_describe_arc_includes_intensity_levels():
    """The arc string should communicate energy magnitude, not just timing,
    so MiniMax's prompt-conditioning has something to anchor on."""
    curve = [
        {"t_seconds": 0.0,  "value": 0.2},
        {"t_seconds": 15.0, "value": 0.9},
        {"t_seconds": 30.0, "value": 0.4},
    ]
    arc = describe_intensity_arc(curve)
    # Should reference low/high or mention numeric/qualitative magnitude.
    assert any(token in arc.lower() for token in ["low", "high", "energy", "intensity"]), (
        f"arc should communicate magnitude, got: {arc}"
    )


# ── derive_tts_directive ───────────────────────────────────────────────────

def test_tts_directive_at_zero_intensity_uses_low_intensity_speed():
    directive = derive_tts_directive(0.0)
    assert directive == {"speed_mult": pytest.approx(TTS_SPEED_AT_LOW_INTENSITY)}


def test_tts_directive_at_one_intensity_uses_high_intensity_speed():
    directive = derive_tts_directive(1.0)
    assert directive == {"speed_mult": pytest.approx(TTS_SPEED_AT_HIGH_INTENSITY)}


def test_tts_directive_at_half_intensity_is_midpoint():
    directive = derive_tts_directive(0.5)
    midpoint = (TTS_SPEED_AT_LOW_INTENSITY + TTS_SPEED_AT_HIGH_INTENSITY) / 2
    assert directive["speed_mult"] == pytest.approx(midpoint)


def test_tts_directive_low_intensity_is_faster_than_high():
    """Low-energy build sections should pace slightly faster than peak sections.
    This direction is intentional — the convention is set in the module."""
    low = derive_tts_directive(0.1)
    high = derive_tts_directive(0.9)
    assert low["speed_mult"] > high["speed_mult"], (
        "low-intensity sections should pace faster than high-intensity sections"
    )


def test_tts_directive_clamps_outside_range():
    assert derive_tts_directive(-0.5)["speed_mult"] == pytest.approx(TTS_SPEED_AT_LOW_INTENSITY)
    assert derive_tts_directive(1.5)["speed_mult"] == pytest.approx(TTS_SPEED_AT_HIGH_INTENSITY)


def test_tts_directive_speed_mult_stays_within_safe_range():
    """speed_mult passed to TTS providers must stay within a sane range so
    delivery is naturally adjusted, not robotic. Bounded to [0.85, 1.15]."""
    for intensity in (0.0, 0.25, 0.5, 0.75, 1.0):
        d = derive_tts_directive(intensity)
        assert 0.85 <= d["speed_mult"] <= 1.15, (
            f"speed_mult out of safe range for intensity={intensity}: {d}"
        )


# ── derive_editing_rhythm_from_intensity ────────────────────────────────────
#
# Closes the editing-rhythm/intensity overlap from the original critique.
# Path A/B made intensity own the audio side; this slice makes intensity the
# fallback source for the visual side when intelligence has only weak signal.
# Output enums match production_bible.visual.editing_rhythm[]:
#   cuts_density:    "rapid" | "moderate" | "slow" | "held"
#   transition_style: "hard_cut" | "dissolve" | "whip" | "match_cut"

def test_derive_editing_rhythm_low_intensity_is_held():
    """The derive function uses four bands and never emits 'slow' — that
    enum value is reachable only when intelligence-director surfaces it from
    research. Pin the exact return so a future band-table edit must update
    this assertion deliberately, not silently."""
    rhythm = derive_editing_rhythm_from_intensity(0.1)
    assert rhythm["cuts_density"] == "held"
    assert rhythm["avg_shot_duration_seconds"] >= 4.0


def test_derive_editing_rhythm_mid_intensity_is_moderate():
    rhythm = derive_editing_rhythm_from_intensity(0.5)
    assert rhythm["cuts_density"] == "moderate"
    assert 1.5 < rhythm["avg_shot_duration_seconds"] < 5.0


def test_derive_editing_rhythm_high_intensity_is_rapid():
    rhythm = derive_editing_rhythm_from_intensity(0.8)
    assert rhythm["cuts_density"] == "rapid"
    assert rhythm["avg_shot_duration_seconds"] < 2.5


def test_derive_editing_rhythm_peak_intensity_is_rapid_with_short_shots():
    rhythm = derive_editing_rhythm_from_intensity(0.95)
    assert rhythm["cuts_density"] == "rapid"
    assert rhythm["avg_shot_duration_seconds"] < 1.5


def test_derive_editing_rhythm_output_keys_match_schema():
    """Output must include exactly the three keys consumed by
    production_bible.visual.editing_rhythm[]."""
    for i in (0.0, 0.5, 1.0):
        rhythm = derive_editing_rhythm_from_intensity(i)
        assert set(rhythm.keys()) == {"cuts_density", "avg_shot_duration_seconds", "transition_style"}


def test_derive_editing_rhythm_uses_schema_enum_values_only():
    """cuts_density and transition_style must use the bible-schema enum values."""
    valid_density = {"rapid", "moderate", "slow", "held"}
    valid_transitions = {"hard_cut", "dissolve", "whip", "match_cut"}
    for i in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0):
        rhythm = derive_editing_rhythm_from_intensity(i)
        assert rhythm["cuts_density"] in valid_density, rhythm
        assert rhythm["transition_style"] in valid_transitions, rhythm


def test_derive_editing_rhythm_density_is_monotonic_with_intensity():
    """Higher intensity → never slower density. Tied or rapid; never reverses."""
    rank = {"held": 0, "slow": 1, "moderate": 2, "rapid": 3}
    last_rank = -1
    for i in [0.0, 0.2, 0.4, 0.5, 0.7, 0.85, 1.0]:
        rhythm = derive_editing_rhythm_from_intensity(i)
        cur = rank[rhythm["cuts_density"]]
        assert cur >= last_rank, (
            f"density rank regressed at intensity={i}: {rhythm['cuts_density']} after {last_rank}"
        )
        last_rank = cur


def test_derive_editing_rhythm_clamps_outside_range():
    low = derive_editing_rhythm_from_intensity(-0.5)
    high = derive_editing_rhythm_from_intensity(1.5)
    assert low["cuts_density"] in ("held", "slow")
    assert high["cuts_density"] == "rapid"


# ── check_editing_rhythm_consistency ───────────────────────────────────────

def test_consistency_returns_empty_list_when_aligned_low_intensity():
    rhythm = {"cuts_density": "held", "avg_shot_duration_seconds": 6.0,
              "transition_style": "dissolve"}
    assert check_editing_rhythm_consistency(0.15, rhythm) == []


def test_consistency_returns_empty_list_when_aligned_peak_intensity():
    rhythm = {"cuts_density": "rapid", "avg_shot_duration_seconds": 1.0,
              "transition_style": "match_cut"}
    assert check_editing_rhythm_consistency(0.95, rhythm) == []


def test_consistency_flags_held_cuts_at_peak_intensity():
    """Peak emotional intensity (0.9) with held shots is the canonical
    parallel-signals divergence — must be flagged."""
    rhythm = {"cuts_density": "held", "avg_shot_duration_seconds": 1.0,
              "transition_style": "dissolve"}
    warnings = check_editing_rhythm_consistency(0.9, rhythm)
    assert len(warnings) == 1
    w = warnings[0].lower()
    assert "intensity" in w
    assert "held" in w or "rapid" in w


def test_consistency_flags_rapid_cuts_at_low_intensity():
    """Inverse divergence: very low intensity but rapid cuts."""
    rhythm = {"cuts_density": "rapid", "avg_shot_duration_seconds": 1.0,
              "transition_style": "hard_cut"}
    warnings = check_editing_rhythm_consistency(0.1, rhythm)
    assert len(warnings) == 1


def test_consistency_does_not_flag_one_step_off():
    """Adjacent density tiers (e.g. moderate at 0.7) are not flagged — the
    auditor only catches sharp divergence to avoid noise."""
    rhythm = {"cuts_density": "moderate", "avg_shot_duration_seconds": 3.0,
              "transition_style": "hard_cut"}
    assert check_editing_rhythm_consistency(0.7, rhythm) == []


def test_consistency_flags_long_shots_at_peak_intensity():
    """Even if cuts_density is on-tier, very long shot durations at peak
    intensity should be flagged on the avg_shot_duration_seconds axis."""
    rhythm = {"cuts_density": "rapid", "avg_shot_duration_seconds": 8.0,
              "transition_style": "hard_cut"}
    warnings = check_editing_rhythm_consistency(0.9, rhythm)
    assert len(warnings) == 1
    w = warnings[0].lower()
    assert "shot_duration" in w or "long" in w


def test_consistency_collects_both_divergences_when_both_fire():
    """Regression: a beat with mismatched density AND long shots at peak
    intensity must report BOTH warnings, not silently drop one. Previously the
    function returned the first warning and never reached the second branch.
    The audit trail in production_bible.intelligence.rhythm_warnings must
    capture every divergence on each beat."""
    rhythm = {"cuts_density": "held", "avg_shot_duration_seconds": 6.0,
              "transition_style": "dissolve"}
    warnings = check_editing_rhythm_consistency(0.9, rhythm)
    assert len(warnings) == 2, f"both branches should fire; got: {warnings}"
    joined = " ".join(warnings).lower()
    # Must mention both the density divergence AND the long-shots divergence.
    assert ("held" in joined or "rank" in joined)
    assert "shot_duration" in joined or "long" in joined


def test_consistency_handles_missing_fields_gracefully():
    """Partial editing_rhythm dicts (missing fields) don't crash; return []."""
    assert check_editing_rhythm_consistency(0.5, {}) == []
    assert check_editing_rhythm_consistency(0.5, {"cuts_density": "moderate"}) == []
    assert check_editing_rhythm_consistency(0.5, {"avg_shot_duration_seconds": 3.0}) == []


def test_consistency_unknown_density_value_is_silent():
    """If editing_rhythm carries a density value not in the schema enum, do
    not crash; return [] (the schema validator catches enum violations)."""
    rhythm = {"cuts_density": "supersonic", "avg_shot_duration_seconds": 1.0}
    assert check_editing_rhythm_consistency(0.9, rhythm) == []
