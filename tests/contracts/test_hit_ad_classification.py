"""Tests for lib.hit_ad_classification — rule-based narrative-pattern classifier.

intelligence_brief.hit_ads_analyzed[].arc_type / hook_mechanic / what_works
were previously agent-inferred from articles. tools/analysis/video_analyzer
already produces a structured VideoAnalysisBrief with per-scene visual_type,
energy_level, narration_text, on_screen_text, and pacing_profile — enough
signal to derive arc_type and hook_mechanic deterministically without
another LLM call.

This module is the rule-based classifier. Phase 1: pure rules; Phase 2 (later):
LLM fallback for ambiguous cases. The aggregator parallels
lib.hit_ad_pacing.aggregate_pacing_from_hit_ads — majority vote across
analyzed ads, sample-size + agreement-driven confidence tier, dissent list
surfaced for Round 2a review.

Schema enums (must match production_bible.narrative exactly):
  arc_type        problem-solution | desire-fulfillment | contrast |
                  journey | social-proof | demo-reveal
  hook_mechanic   question | statement | visual-contrast | sound-interrupt | stat

The classifier never emits ``sound-interrupt`` (would require audio energy
analysis; out of scope for video_analyzer's visual+text signals).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.hit_ad_classification import (
    aggregate_classifications,
    classify_arc_type_from_scenes,
    classify_hit_ad_from_video_brief,
    classify_hook_mechanic_from_first_scene,
    summarize_what_works,
)


# ── Fixture builders ───────────────────────────────────────────────────────

def _scene(
    idx: int, *,
    energy: str = "medium",
    visual_type: str = "b_roll",
    narration: str = "",
    on_screen: str = "",
    description: str = "",
) -> dict:
    return {
        "scene_index": idx,
        "start_time": idx * 3.0,
        "end_time": (idx + 1) * 3.0,
        "description": description or f"scene {idx}",
        "narration_text": narration,
        "on_screen_text": on_screen,
        "visual_type": visual_type,
        "energy_level": energy,
    }


def _brief(scenes: list[dict], cuts_per_minute: float = 20.0) -> dict:
    return {
        "version": "1.0",
        "source": {"type": "youtube", "duration_seconds": len(scenes) * 3.0},
        "content_analysis": {"summary": "x", "topics": [], "target_audience": "x"},
        "structure_analysis": {
            "total_scenes": len(scenes),
            "scenes": scenes,
            "pacing_profile": {
                "avg_scene_duration_seconds": 3.0,
                "shortest_scene_seconds": 2.0,
                "longest_scene_seconds": 4.0,
                "cuts_per_minute": cuts_per_minute,
                "pacing_style": "dynamic_social",
            },
        },
    }


# ── classify_arc_type_from_scenes ──────────────────────────────────────────

def test_arc_demo_reveal_when_screen_recording_dominates_mid():
    scenes = [
        _scene(0, visual_type="text_card", energy="medium"),
        _scene(1, visual_type="screen_recording", energy="high"),
        _scene(2, visual_type="screen_recording", energy="high"),
        _scene(3, visual_type="screen_recording", energy="high"),
        _scene(4, visual_type="product_shot", energy="peak"),
    ]
    result = classify_arc_type_from_scenes(scenes)
    assert result["arc_type"] == "demo-reveal"


def test_arc_demo_reveal_when_product_shot_dominates_mid():
    scenes = [
        _scene(0, visual_type="b_roll", energy="medium"),
        _scene(1, visual_type="product_shot", energy="medium"),
        _scene(2, visual_type="product_shot", energy="high"),
        _scene(3, visual_type="product_shot", energy="high"),
        _scene(4, visual_type="text_card", energy="peak"),
    ]
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "demo-reveal"


def test_arc_social_proof_when_talking_head_dominates():
    scenes = [
        _scene(0, visual_type="talking_head", energy="medium"),
        _scene(1, visual_type="talking_head", energy="medium"),
        _scene(2, visual_type="b_roll", energy="medium"),
        _scene(3, visual_type="talking_head", energy="high"),
        _scene(4, visual_type="talking_head", energy="high"),
    ]
    # 4/5 = 80% talking_head — well over the 40% threshold.
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "social-proof"


def test_arc_problem_solution_when_energy_climbs_from_low_to_high():
    scenes = [
        _scene(0, visual_type="b_roll", energy="low"),
        _scene(1, visual_type="b_roll", energy="low"),
        _scene(2, visual_type="b_roll", energy="medium"),
        _scene(3, visual_type="b_roll", energy="high"),
        _scene(4, visual_type="b_roll", energy="high"),
    ]
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "problem-solution"


def test_arc_contrast_when_first_half_visuals_differ_from_second():
    scenes = [
        _scene(0, visual_type="b_roll", energy="medium"),
        _scene(1, visual_type="b_roll", energy="medium"),
        _scene(2, visual_type="b_roll", energy="medium"),
        _scene(3, visual_type="animation", energy="high"),
        _scene(4, visual_type="animation", energy="high"),
        _scene(5, visual_type="animation", energy="high"),
    ]
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "contrast"


def test_arc_journey_when_energy_climbs_steadily_to_late_peak():
    scenes = [
        _scene(0, visual_type="b_roll", energy="low"),
        _scene(1, visual_type="b_roll", energy="medium"),
        _scene(2, visual_type="b_roll", energy="medium"),
        _scene(3, visual_type="b_roll", energy="high"),
        _scene(4, visual_type="b_roll", energy="high"),
        _scene(5, visual_type="b_roll", energy="peak"),
    ]
    # Steady climb to peak in the final 30% of scenes.
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "journey"


def test_arc_default_desire_fulfillment_when_no_pattern_matches():
    """Flat-energy, varied-visual sequence with no clear pattern → default."""
    scenes = [
        _scene(0, visual_type="b_roll", energy="medium"),
        _scene(1, visual_type="b_roll", energy="medium"),
        _scene(2, visual_type="b_roll", energy="medium"),
    ]
    assert classify_arc_type_from_scenes(scenes)["arc_type"] == "desire-fulfillment"


def test_arc_uses_schema_enum_values_only():
    valid = {"problem-solution", "desire-fulfillment", "contrast",
             "journey", "social-proof", "demo-reveal"}
    # Try a representative sample of scene shapes.
    for scenes in [
        [_scene(0, visual_type="screen_recording")] * 5,
        [_scene(0, visual_type="talking_head")] * 5,
        [_scene(0, energy="low"), _scene(1, energy="low"), _scene(2, energy="high"), _scene(3, energy="high")],
        [_scene(0)],  # single scene
        [],            # empty
    ]:
        result = classify_arc_type_from_scenes(scenes)
        assert result["arc_type"] in valid, f"unknown arc_type for scenes={scenes}: {result}"


def test_arc_returns_signals_audit_trail():
    scenes = [_scene(i, visual_type="screen_recording", energy="high") for i in range(5)]
    result = classify_arc_type_from_scenes(scenes)
    assert "signals" in result
    assert "visual_type_distribution" in result["signals"]
    assert "energy_profile" in result["signals"]


# ── classify_hook_mechanic_from_first_scene ────────────────────────────────

def test_hook_stat_when_first_scene_narration_contains_digit():
    first = _scene(0, narration="Forty-five minutes is gone before you start work — 45.")
    assert classify_hook_mechanic_from_first_scene(first) == "stat"


def test_hook_stat_when_first_scene_on_screen_text_contains_digit():
    first = _scene(0, narration="That much time wasted.", on_screen="45 MIN")
    assert classify_hook_mechanic_from_first_scene(first) == "stat"


def test_hook_question_when_first_scene_narration_starts_with_question_word():
    for prefix in ("What", "Why", "How", "Who", "When", "Where", "Are", "Is", "Do"):
        first = _scene(0, narration=f"{prefix} you tired of this commute?")
        assert classify_hook_mechanic_from_first_scene(first) == "question", (
            f"failed for prefix {prefix!r}"
        )


def test_hook_visual_contrast_when_energy_differs_sharply_between_first_two_scenes():
    """A single scene can't produce visual-contrast; the helper is named for
    the FIRST scene but with awareness of the next via the optional argument."""
    first = _scene(0, energy="low", visual_type="text_card", narration="One morning.")
    second = _scene(1, energy="peak", visual_type="product_shot", narration="Now.")
    assert classify_hook_mechanic_from_first_scene(first, next_scene=second) == "visual-contrast"


def test_hook_statement_when_no_other_rule_fires():
    first = _scene(0, narration="The future is here today.")
    assert classify_hook_mechanic_from_first_scene(first) == "statement"


def test_hook_never_emits_sound_interrupt():
    """sound-interrupt requires audio analysis the visual classifier can't do.
    The classifier must NEVER emit it, even on inputs that might evoke it."""
    valid_outputs = {"question", "statement", "visual-contrast", "stat"}
    sample_inputs = [
        _scene(0, narration="Crash!"),                # exclamation
        _scene(0, narration=""),                      # empty
        _scene(0, narration="Boom — listen."),        # sound-evocative
        _scene(0, narration="?"),                     # bare punctuation
    ]
    for first in sample_inputs:
        result = classify_hook_mechanic_from_first_scene(first)
        assert result != "sound-interrupt"
        assert result in valid_outputs


def test_hook_handles_empty_narration_and_no_text():
    first = _scene(0, narration="", on_screen="")
    # Falls back to statement (default).
    assert classify_hook_mechanic_from_first_scene(first) == "statement"


# ── summarize_what_works ───────────────────────────────────────────────────

def test_what_works_mentions_hook_mechanic_and_pacing():
    brief = _brief([
        _scene(0, narration="45 minutes lost.", visual_type="text_card", energy="medium"),
        _scene(1, visual_type="screen_recording", energy="high"),
        _scene(2, visual_type="screen_recording", energy="high"),
    ], cuts_per_minute=32.0)
    classification = {"arc_type": "demo-reveal", "hook_mechanic": "stat"}
    summary = summarize_what_works(brief, classification)
    assert "stat" in summary.lower()
    # Should reference pacing or visual style.
    assert "32" in summary or "cuts" in summary.lower() or "screen_recording" in summary.lower()


def test_what_works_returns_non_empty_string_for_minimal_brief():
    brief = _brief([_scene(0, narration="Hello.")])
    classification = {"arc_type": "desire-fulfillment", "hook_mechanic": "statement"}
    summary = summarize_what_works(brief, classification)
    assert summary  # non-empty


# ── classify_hit_ad_from_video_brief (orchestrator) ────────────────────────

def test_orchestrator_returns_full_classification_block():
    brief = _brief([
        _scene(0, narration="Are you wasting time?", visual_type="text_card", energy="low"),
        _scene(1, visual_type="screen_recording", energy="medium"),
        _scene(2, visual_type="screen_recording", energy="high"),
        _scene(3, visual_type="product_shot", energy="peak"),
    ], cuts_per_minute=28.0)
    result = classify_hit_ad_from_video_brief(brief)

    assert result["arc_type"] == "demo-reveal"
    assert result["hook_mechanic"] == "question"
    assert result["source"] == "video_analyzer_classification"
    assert "what_works" in result and result["what_works"]
    assert "signals" in result


def test_orchestrator_propagates_signals_from_arc_classifier():
    brief = _brief([_scene(i, visual_type="screen_recording", energy="high") for i in range(4)])
    result = classify_hit_ad_from_video_brief(brief)
    assert "visual_type_distribution" in result["signals"]


def test_orchestrator_handles_empty_scenes_gracefully():
    brief = _brief([])
    result = classify_hit_ad_from_video_brief(brief)
    # Default arc_type, default hook (statement), non-crashing summary.
    assert result["arc_type"] in {"problem-solution", "desire-fulfillment", "contrast",
                                   "journey", "social-proof", "demo-reveal"}
    assert result["hook_mechanic"] in {"question", "statement", "visual-contrast", "stat"}


# ── aggregate_classifications ──────────────────────────────────────────────

def _hit_ad_with_classification(arc_type: str, hook_mechanic: str = "statement") -> dict:
    return {
        "title": "x", "platform": "tiktok",
        "arc_type": arc_type,             # legacy top-level
        "hook_mechanic": hook_mechanic,
        "what_works": "x", "adopted": True,
        "classification": {
            "arc_type": arc_type,
            "hook_mechanic": hook_mechanic,
            "what_works": "x",
            "source": "video_analyzer_classification",
            "signals": {},
        },
    }


def _hit_ad_without_classification() -> dict:
    return {
        "title": "y", "platform": "tiktok",
        "arc_type": "desire-fulfillment", "hook_mechanic": "statement",
        "what_works": "x", "adopted": False,
    }


def test_aggregate_returns_none_when_no_ads_classified():
    assert aggregate_classifications([]) is None
    assert aggregate_classifications([_hit_ad_without_classification()] * 3) is None


def test_aggregate_single_classified_ad_is_pattern_inferred():
    ads = [_hit_ad_with_classification("problem-solution", "stat")]
    agg = aggregate_classifications(ads)
    assert agg is not None
    assert agg["sample_size"] == 1
    assert agg["confidence"] == "pattern-inferred"
    assert agg["arc_type"] == "problem-solution"
    assert agg["hook_mechanic"] == "stat"


def test_aggregate_two_agreeing_ads_is_research_grounded():
    ads = [
        _hit_ad_with_classification("problem-solution", "stat"),
        _hit_ad_with_classification("problem-solution", "stat"),
    ]
    agg = aggregate_classifications(ads)
    assert agg["sample_size"] == 2
    assert agg["confidence"] == "research-grounded"
    assert agg["arc_type_agreement"] == pytest.approx(1.0)
    assert agg["hook_mechanic_agreement"] == pytest.approx(1.0)
    assert agg["dissent"] == []


def test_aggregate_majority_with_high_agreement_is_research_grounded():
    """3 vs 1 = 75% agreement — at the threshold, still research-grounded."""
    ads = [
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_with_classification("demo-reveal"),
    ]
    agg = aggregate_classifications(ads)
    assert agg["sample_size"] == 4
    assert agg["confidence"] == "research-grounded"
    assert agg["arc_type"] == "problem-solution"
    assert agg["arc_type_agreement"] == pytest.approx(0.75)
    # Dissent block: the one disagreeing ad.
    assert len(agg["dissent"]) == 1
    assert agg["dissent"][0]["arc_type"] == "demo-reveal"


def test_aggregate_low_agreement_drops_to_pattern_inferred():
    """2 vs 1 = ~67% agreement → below 0.75 threshold → pattern-inferred."""
    ads = [
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_with_classification("demo-reveal"),
    ]
    agg = aggregate_classifications(ads)
    assert agg["confidence"] == "pattern-inferred"
    assert agg["arc_type"] == "problem-solution"


def test_aggregate_skips_ads_without_classification():
    ads = [
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_without_classification(),
        _hit_ad_with_classification("problem-solution"),
        _hit_ad_without_classification(),
    ]
    agg = aggregate_classifications(ads)
    assert agg["sample_size"] == 2
    assert agg["confidence"] == "research-grounded"


def test_aggregate_handles_independent_majorities_for_arc_and_hook():
    """arc_type can be unanimous while hook_mechanic disagrees, or vice versa.
    Each axis is voted independently."""
    ads = [
        _hit_ad_with_classification("problem-solution", "stat"),
        _hit_ad_with_classification("problem-solution", "question"),
        _hit_ad_with_classification("problem-solution", "stat"),
        _hit_ad_with_classification("problem-solution", "stat"),
    ]
    agg = aggregate_classifications(ads)
    assert agg["arc_type"] == "problem-solution"
    assert agg["arc_type_agreement"] == pytest.approx(1.0)
    assert agg["hook_mechanic"] == "stat"
    assert agg["hook_mechanic_agreement"] == pytest.approx(0.75)


def test_aggregate_dissent_lists_full_classification_of_dissenting_ads():
    """Dissent must carry both arc_type and hook_mechanic of the non-majority
    ad so Round 2a can show the user 'these N ads went a different way and
    here's what they chose'."""
    ads = [
        _hit_ad_with_classification("problem-solution", "stat"),
        _hit_ad_with_classification("problem-solution", "stat"),
        _hit_ad_with_classification("demo-reveal", "question"),
    ]
    agg = aggregate_classifications(ads)
    assert agg["arc_type"] == "problem-solution"
    # The dissenting ad chose "demo-reveal" + "question".
    assert any(
        d["arc_type"] == "demo-reveal" and d["hook_mechanic"] == "question"
        for d in agg["dissent"]
    )
