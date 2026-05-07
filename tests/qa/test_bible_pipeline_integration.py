"""End-to-end composition test for the bible/intelligence helper chain.

Each helper has its own unit-test file. This file is the cross-helper
integration: it builds a single synthetic intelligence_brief →
production_bible → script and runs every helper in the order
bible-director / script-director / asset-director would. Catches contract
drift between helpers that unit tests miss (e.g., a future change that
renames `aggregate_pacing_from_hit_ads.confidence` would break this test
even if every individual unit test still passes).

The chain exercised:

  Stage 0 (intelligence-director output → bible-director Step 0)
    → audit_intelligence_provenance demotes uncited research-grounded
    → filter_stale_trends drops 2020 trend
    → dedupe_trends drops duplicate signal

  Stage 1 (bible-director Step 2/3)
    → derive_intensity_curve produces sampled curve
    → aggregate_pacing_from_hit_ads turns measured pacing into research-grounded
    → derive_editing_rhythm_from_intensity provides per-beat fallback
    → check_editing_rhythm_consistency catches divergence

  Stage 2 (edit-director / asset-director audio)
    → derive_duck_schedule produces gain envelope
    → compile_volume_schedule_to_ffmpeg_expr renders FFmpeg expression
    → sample_volume_schedule and FFmpeg expr agree at boundary samples
    → describe_intensity_arc produces music-gen prompt arc

  Stage 3 (script-director / asset-director TTS+visual)
    → derive_tts_directive per section
    → check_hook_window_compliance enforces platform window
    → apply_color_direction injects palette
    → apply_resolution_treatment injects resolution register on resolution beat
"""

import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.color_direction import apply_color_direction
from lib.constants import WORDS_PER_MINUTE_VO
from lib.hit_ad_classification import (
    aggregate_classifications,
    classify_hit_ad_from_video_brief,
)
from lib.hit_ad_pacing import aggregate_pacing_from_hit_ads
from lib.hook_window import check_hook_window_compliance
from lib.intensity_curve import (
    check_editing_rhythm_consistency,
    compile_volume_schedule_to_ffmpeg_expr,
    derive_duck_schedule,
    derive_editing_rhythm_from_intensity,
    derive_intensity_curve,
    derive_tts_directive,
    describe_intensity_arc,
    sample_volume_schedule,
)
from lib.provenance_audit import audit_intelligence_provenance
from lib.resolution_treatment import apply_resolution_treatment
from lib.trend_recency import dedupe_trends, filter_stale_trends


# ── Synthetic inputs ────────────────────────────────────────────────────────

def _intelligence_brief() -> dict:
    """A realistic intelligence_brief: mixed confidence tiers, mixed trend
    freshness, mixed measured/unmeasured hit ads."""
    return {
        "audience_psychographics": {
            "emotional_profile": "burned-out millennial commuter",
            "core_pain_point": "morning commute eats focus time",
            "aspiration": "reclaim 45 minutes for deep work",
        },
        "platform_trends": [
            # Fresh trend with measured engagement.
            {"signal": "vertical text-first hooks rising on TikTok",
             "source": "https://tiktokcreativecenter.com/insights/2026-q1",
             "relevance": "Aligns with our 9:16 hero deliverable",
             "observed_at": "2026-04-01",
             "decay_window_days": 90,
             "engagement_proxy": {"note": "Q1 2026 internal data"}},
            # Duplicate of the above — should be deduped.
            {"signal": "Vertical Text-First Hooks Rising on TikTok",
             "source": "https://socialmediatoday.com/post-456",
             "relevance": "Same signal from a second source"},
            # Stale trend — far past decay window.
            {"signal": "synthwave music for SaaS ads dominant",
             "source": "https://oldblog.example.com/2020-throwback",
             "relevance": "Probably over",
             "observed_at": "2020-01-01",
             "decay_window_days": 90},
        ],
        "hit_ads_analyzed": [
            {"title": "Acme '60-second Productivity'",
             "platform": "tiktok", "arc_type": "problem-solution",
             "hook_mechanic": "stat", "what_works": "opens with hard number",
             "adopted": True,
             "url": "https://example.com/ad-1",
             "analyzed_at": "2026-04-26",
             "pacing_measured": {
                 "cuts_per_minute": 36.0,
                 "avg_scene_duration_seconds": 1.6,
                 "total_scenes": 16,
                 "source": "video_analyzer",
             }},
            {"title": "Beta 'Stop Scrolling'",
             "platform": "tiktok", "arc_type": "problem-solution",
             "hook_mechanic": "question", "what_works": "direct address",
             "adopted": True,
             "url": "https://example.com/ad-2",
             "analyzed_at": "2026-04-26",
             "pacing_measured": {
                 "cuts_per_minute": 32.0,
                 "avg_scene_duration_seconds": 1.8,
                 "total_scenes": 14,
                 "source": "video_analyzer",
             }},
            {"title": "Gamma 'Article-only summary'",
             "platform": "instagram", "arc_type": "demo-reveal",
             "hook_mechanic": "stat", "what_works": "cited in trade article",
             "adopted": False},
        ],
        "rejected_approaches": [
            {"approach": "self-help cliche montage", "reason": "oversaturated"},
        ],
        "recommendations": {
            # Properly cited research-grounded — should pass the auditor.
            "arc_type": {"value": "problem-solution",
                         "confidence": "research-grounded",
                         "rationale": "Adweek 2026 analysis confirms problem-solution arc dominance for this category."},
            # Uncited research-grounded — should be DEMOTED.
            "pacing_model": {"value": "escalating",
                             "confidence": "research-grounded",
                             "rationale": "The data clearly shows this works."},
            "hook_mechanic": {"value": "stat", "confidence": "pattern-inferred",
                              "rationale": "Multiple ads use stats."},
            "hook_window_seconds": {"value": 3, "confidence": "research-grounded",
                                    "rationale": "TikTok 3s scroll threshold per Nielsen 2025 report."},
            "overall_rationale": "x",
        },
    }


def _emotional_beat_sequence() -> list[dict]:
    """5-beat sequence summing to 60s, escalating intensity then resolving."""
    return [
        {"beat_id": "B1", "name": "hook",       "duration_seconds": 5,
         "intensity": 0.4, "emotional_target": "curiosity",
         "script_constraint": "x", "visual_constraint": "x"},
        {"beat_id": "B2", "name": "problem",    "duration_seconds": 18,
         "intensity": 0.6, "emotional_target": "recognition",
         "script_constraint": "x", "visual_constraint": "x"},
        {"beat_id": "B3", "name": "solution_intro", "duration_seconds": 12,
         "intensity": 0.85, "emotional_target": "hope",
         "script_constraint": "x", "visual_constraint": "x"},
        {"beat_id": "B4", "name": "proof",      "duration_seconds": 18,
         "intensity": 0.95, "emotional_target": "trust",
         "script_constraint": "x", "visual_constraint": "x"},
        {"beat_id": "cta_brand", "name": "cta_brand", "duration_seconds": 7,
         "intensity": 0.7, "emotional_target": "action",
         "script_constraint": "x", "visual_constraint": "x"},
    ]


# ── The integration test ───────────────────────────────────────────────────

def test_full_helper_chain_composes_correctly():
    """Run every helper landed this session in the order bible-director and
    script-director would invoke them. Assert each link's output flows
    correctly into the next. A future change that breaks any cross-helper
    contract will fail this test even if individual unit tests still pass."""

    intel = _intelligence_brief()
    today = date(2026, 4, 26)

    # ── Stage 0: provenance audit ──────────────────────────────────────
    flags = audit_intelligence_provenance(intel)
    paths_flagged = [f["path"] for f in flags]
    assert "recommendations.pacing_model" in paths_flagged, (
        f"uncited research-grounded pacing_model must be flagged; got: {flags}"
    )
    assert "recommendations.arc_type" not in paths_flagged, (
        f"Adweek-cited arc_type must NOT be flagged; got: {flags}"
    )
    # Apply demotions (as bible-director Step 0 would).
    for flag in flags:
        if flag["path_type"] == "recommendation":
            intel["recommendations"][flag["key"]]["confidence"] = "pattern-inferred"

    # ── Stage 0b: trend recency ────────────────────────────────────────
    fresh = filter_stale_trends(intel["platform_trends"], now=today)
    deduped = dedupe_trends(fresh)
    signals = [t["signal"] for t in deduped]
    assert "synthwave music for SaaS ads dominant" not in signals, "stale trend must be filtered"
    # The duplicate trends collapse to one.
    assert len([s for s in signals if "vertical text-first" in s.lower()]) == 1

    # ── Stage 1: hit-ad pacing aggregation ─────────────────────────────
    agg = aggregate_pacing_from_hit_ads(intel["hit_ads_analyzed"])
    assert agg is not None, "two analyzed ads must produce an aggregate"
    assert agg["sample_size"] == 2
    assert agg["confidence"] == "research-grounded"
    # Means of (36, 32) cpm and (1.6, 1.8) avg.
    assert agg["avg_cuts_per_minute"] == pytest.approx(34.0)
    assert agg["avg_shot_duration_seconds"] == pytest.approx(1.7)
    assert agg["cuts_density"] == "rapid"  # avg < 2.0 → rapid

    # ── Stage 1a: hit-ad narrative-pattern classification (Project B) ──
    # Synthesize a per-ad classification block as intelligence-director would
    # have done by running classify_hit_ad_from_video_brief on each
    # video_analyzer brief. Two agreeing ads → research-grounded aggregate.
    intel["hit_ads_analyzed"][0]["classification"] = {
        "arc_type": "demo-reveal",
        "hook_mechanic": "stat",
        "what_works": "Opens with stat hook (demo-reveal arc).",
        "source": "video_analyzer_classification",
        "signals": {"scene_count": 16},
    }
    intel["hit_ads_analyzed"][1]["classification"] = {
        "arc_type": "demo-reveal",
        "hook_mechanic": "stat",
        "what_works": "Opens with stat hook (demo-reveal arc).",
        "source": "video_analyzer_classification",
        "signals": {"scene_count": 14},
    }
    classification_agg = aggregate_classifications(intel["hit_ads_analyzed"])
    assert classification_agg is not None
    assert classification_agg["sample_size"] == 2
    assert classification_agg["confidence"] == "research-grounded"
    assert classification_agg["arc_type"] == "demo-reveal"
    assert classification_agg["arc_type_agreement"] == pytest.approx(1.0)
    assert classification_agg["hook_mechanic"] == "stat"
    assert classification_agg["dissent"] == []

    # ── Stage 1b: intensity curve ─────────────────────────────────────
    beats = _emotional_beat_sequence()
    curve = derive_intensity_curve(beats)
    # 5 beats + closing sample.
    assert len(curve) == 6
    assert curve[0]["t_seconds"] == 0.0 and curve[0]["value"] == pytest.approx(0.4)
    # Total duration 60s.
    assert curve[-1]["t_seconds"] == pytest.approx(60.0)

    # ── Stage 1c: editing-rhythm fallback + consistency ───────────────
    # For each beat, derive an editing rhythm from intensity. Spot-check the
    # peak beat (B4, intensity 0.95) — should be rapid + sub-second shots.
    rhythm_b4 = derive_editing_rhythm_from_intensity(0.95)
    assert rhythm_b4["cuts_density"] == "rapid"
    assert rhythm_b4["avg_shot_duration_seconds"] <= 1.5
    # Consistency check: the helper should NOT warn when intensity and rhythm
    # agree (both peak).
    assert check_editing_rhythm_consistency(0.95, rhythm_b4) == []
    # But should warn when peak intensity is paired with held shots.
    held_at_peak = {"cuts_density": "held", "avg_shot_duration_seconds": 6.0}
    warnings = check_editing_rhythm_consistency(0.95, held_at_peak)
    assert len(warnings) == 2  # density + long-shots both fire

    # ── Stage 2: duck schedule + FFmpeg envelope ──────────────────────
    # Fake narration windows aligned with the beat starts (rough timeline).
    narration_windows = [
        {"start_seconds": 0.5,  "end_seconds": 4.5},   # hook
        {"start_seconds": 5.5,  "end_seconds": 22.5},  # problem
        {"start_seconds": 23.5, "end_seconds": 34.5},  # solution_intro
        {"start_seconds": 35.5, "end_seconds": 52.5},  # proof
        {"start_seconds": 53.5, "end_seconds": 59.5},  # cta_brand
    ]
    schedule = derive_duck_schedule(curve, narration_windows, fade_seconds=0.3)
    assert schedule, "duck schedule must produce samples for non-empty curve"
    # Sampled at mid-narration the gain should be deeply negative (ducked).
    mid_narration_amp = sample_volume_schedule(schedule, t_seconds=10.0)
    assert mid_narration_amp < 0.5, (
        f"music must be ducked mid-narration, got linear amp {mid_narration_amp}"
    )
    # Outside narration windows should be near unity.
    pre_narration_amp = sample_volume_schedule(schedule, t_seconds=0.0)
    assert pre_narration_amp == pytest.approx(1.0, abs=0.05)

    # FFmpeg expression must compile and use only ffmpeg-volume primitives.
    expr = compile_volume_schedule_to_ffmpeg_expr(schedule)
    assert "if(lt(t," in expr
    # No locale corruption (regression from earlier reviewer finding).
    import re as _re
    assert not _re.search(r"\d,\d", expr), f"comma decimal in expr: {expr}"

    # ── Stage 2b: music arc summary ───────────────────────────────────
    arc = describe_intensity_arc(curve)
    assert arc, "arc summary must be non-empty for non-flat curve"
    assert "peak" in arc.lower()
    assert len(arc) <= 200  # MiniMax prompt budget guard

    # ── Stage 3: TTS directives per section ───────────────────────────
    # Build a script aligned to beats; assert speed_mult tracks intensity.
    tts_directives = {
        beat["beat_id"]: derive_tts_directive(beat["intensity"])
        for beat in beats
    }
    # Quieter hook (0.4) paces faster than peak proof beat (0.95).
    assert tts_directives["B1"]["speed_mult"] > tts_directives["B4"]["speed_mult"]
    # All speed_mults stay within the safe range.
    for d in tts_directives.values():
        assert 0.85 <= d["speed_mult"] <= 1.15

    # ── Stage 3b: hook window enforcement ─────────────────────────────
    # Hook window comes from intelligence-director (3s for TikTok).
    hook_window_seconds = intel["recommendations"]["hook_window_seconds"]["value"]
    # Compliant short hook script: 6 words ≈ 2.4s at 150 WPM.
    short_script = {
        "total_duration_seconds": 60,
        "sections": [
            {"id": "hook", "beat": "hook", "narration": "Stop wasting your morning."},
            {"id": "build_1", "beat": "build", "narration": "x" * 30},
        ],
    }
    assert check_hook_window_compliance(short_script, hook_window_seconds) is None
    # Overshoot script: 25-word hook at 150 WPM ≈ 10s, way over 3s.
    long_script = {
        "total_duration_seconds": 60,
        "sections": [
            {"id": "hook", "beat": "hook",
             "narration": " ".join(["overshoot"] * 25)},
        ],
    }
    warning = check_hook_window_compliance(long_script, hook_window_seconds)
    assert warning is not None and "hook" in warning.lower()

    # ── Stage 3c: visual prompt threading ─────────────────────────────
    color_direction = "muted warm autumnal palette"
    resolution_type = "aspiration"
    base_prompt = "Close-up of a hand picking up a steaming ceramic cup."

    # On a non-resolution beat scene: only color_direction injected.
    non_res_prompt = apply_color_direction(base_prompt, color_direction)
    assert color_direction in non_res_prompt
    assert "Resolution treatment:" not in non_res_prompt

    # On the resolution beat scene: both injected.
    res_prompt = apply_resolution_treatment(
        apply_color_direction(base_prompt, color_direction),
        resolution_type,
    )
    assert color_direction in res_prompt
    assert "Resolution treatment:" in res_prompt
    # Idempotency: applying both helpers again must NOT duplicate.
    res_prompt_twice = apply_resolution_treatment(
        apply_color_direction(res_prompt, color_direction),
        resolution_type,
    )
    assert res_prompt_twice == res_prompt
    assert res_prompt_twice.count("Color palette:") == 1
    assert res_prompt_twice.count("Resolution treatment:") == 1

    # ── Sanity: shared WPM constant is consistent across modules ──────
    from tools.compliance import compliance_check as cc
    assert WORDS_PER_MINUTE_VO == cc._WORDS_PER_MINUTE
