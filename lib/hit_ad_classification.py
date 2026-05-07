"""Rule-based narrative-pattern classifier for analyzed hit ads.

Companion to :mod:`lib.hit_ad_pacing`. Where ``aggregate_pacing_from_hit_ads``
upgrades the *pacing* dimension from article inference to measured-from-video,
this module does the same for the *narrative pattern* dimension — ``arc_type``
and ``hook_mechanic``.

The signal source is :class:`tools.analysis.video_analyzer.VideoAnalyzer`'s
``VideoAnalysisBrief`` output, which already produces structured per-scene
``visual_type``, ``energy_level``, ``narration_text``, ``on_screen_text``,
plus a ``pacing_profile``. We derive arc_type and hook_mechanic from that
shape with deterministic rules — no LLM call. Phase 2 (later) may add an
LLM fallback for ambiguous cases; Phase 1 is rule-based only.

Schema enums (must match ``production_bible.narrative`` exactly):

* arc_type      — ``problem-solution`` | ``desire-fulfillment`` | ``contrast``
                  | ``journey`` | ``social-proof`` | ``demo-reveal``
* hook_mechanic — ``question`` | ``statement`` | ``visual-contrast``
                  | ``sound-interrupt`` | ``stat``

The classifier never emits ``sound-interrupt`` (would require audio energy
analysis the visual classifier can't do). The schema permits it, but the
deterministic rule path is intentionally narrower than the schema enum.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


# ── Energy ranking + visual-type buckets ────────────────────────────────────

_ENERGY_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "peak": 3}

_DEMO_VISUALS = {"screen_recording", "product_shot"}
_TALKING_HEAD = "talking_head"

# Question-word prefixes that indicate a question-mechanic hook.
_QUESTION_PREFIXES = (
    "who", "what", "when", "where", "why", "how",
    "are", "is", "do", "does", "can", "will", "should", "would", "could",
    "have", "has", "had",
)

_DIGIT_RE = re.compile(r"\d")


def _energy_rank(energy: Any) -> int:
    """Return the rank for an ``energy_level`` enum value, 1 (medium) on miss."""
    return _ENERGY_RANK.get(str(energy).lower(), 1)


def _visual_type_distribution(scenes: list[dict[str, Any]]) -> dict[str, int]:
    """Count of each ``visual_type`` value across the scene list."""
    return dict(Counter(str(s.get("visual_type", "other")) for s in scenes))


def _energy_profile(scenes: list[dict[str, Any]]) -> list[int]:
    """Per-scene energy ranks, used by several arc-type rules."""
    return [_energy_rank(s.get("energy_level")) for s in scenes]


# ── classify_arc_type_from_scenes ───────────────────────────────────────────

def classify_arc_type_from_scenes(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    """Map a scene list to an arc_type via deterministic rules.

    Rule evaluation order (first match wins):

      1. ``demo-reveal``: ≥50% of mid-section scenes are ``screen_recording``
         or ``product_shot``.
      2. ``social-proof``: ≥40% of scenes are ``talking_head``.
      3. ``contrast``: first-half visual_type majority differs from
         second-half majority (visual structural shift trumps energy shift).
      4. ``problem-solution``: first half is FLAT at low/medium AND last
         quarter is high/peak. The flat first half is what distinguishes
         this from journey, which CLIMBS throughout the first half.
      5. ``journey``: energy climbs steadily AND peak rank lands in the
         final 30% of scenes.
      6. Default: ``desire-fulfillment``.

    Returns ``{"arc_type": str, "signals": {...}}`` where ``signals`` carries
    the audit trail (energy_profile, visual_type_distribution, mid-section
    distribution) so a reviewer can verify the rule's evidence.
    """
    n = len(scenes)
    distribution = _visual_type_distribution(scenes)
    profile = _energy_profile(scenes)
    signals: dict[str, Any] = {
        "energy_profile": profile,
        "visual_type_distribution": distribution,
        "scene_count": n,
    }

    if n == 0:
        return {"arc_type": "desire-fulfillment", "signals": signals}

    # Rule 1 — demo-reveal: dominant screen_recording / product_shot mid-section.
    mid_start = n // 4
    mid_end = max(mid_start + 1, (3 * n) // 4)
    mid_scenes = scenes[mid_start:mid_end]
    if mid_scenes:
        mid_demo = sum(1 for s in mid_scenes if s.get("visual_type") in _DEMO_VISUALS)
        if mid_demo / len(mid_scenes) >= 0.5:
            signals["mid_demo_fraction"] = mid_demo / len(mid_scenes)
            return {"arc_type": "demo-reveal", "signals": signals}

    # Rule 2 — social-proof: ≥40% talking_head.
    talking_head_count = distribution.get(_TALKING_HEAD, 0)
    if n > 0 and talking_head_count / n >= 0.4:
        signals["talking_head_fraction"] = talking_head_count / n
        return {"arc_type": "social-proof", "signals": signals}

    # Rule 3 — contrast: first-half visual_type majority differs from
    # second-half majority. Evaluated BEFORE problem-solution because the
    # visual structural shift is a stronger signal than the energy shift
    # alone (visual change + energy change together = contrast, not p-s).
    if n >= 4:
        midpoint = n // 2
        first_dist = _visual_type_distribution(scenes[:midpoint])
        second_dist = _visual_type_distribution(scenes[midpoint:])
        first_majority = max(first_dist, key=first_dist.get) if first_dist else None
        second_majority = max(second_dist, key=second_dist.get) if second_dist else None
        if first_majority and second_majority and first_majority != second_majority:
            # Require both halves to be reasonably concentrated (>= 50% on the
            # majority value) so we don't trigger on noisy mixed-style ads.
            first_concentration = first_dist.get(first_majority, 0) / max(1, midpoint)
            second_concentration = second_dist.get(second_majority, 0) / max(1, n - midpoint)
            if first_concentration >= 0.5 and second_concentration >= 0.5:
                signals["first_half_majority"] = first_majority
                signals["second_half_majority"] = second_majority
                return {"arc_type": "contrast", "signals": signals}

    # Rule 4 — problem-solution: first half is FLAT at low/medium AND last
    # quarter sustains high. The flat first half (profile max == profile min
    # for the first half) is what distinguishes this from journey, which has
    # a CLIMBING first half.
    if n >= 3:
        midpoint = max(1, n // 2)
        first_half = profile[:midpoint]
        last_quarter_start = max(midpoint, n - max(1, n // 4))
        last_quarter = profile[last_quarter_start:]
        if (
            first_half
            and last_quarter
            and max(first_half) == min(first_half)   # first half is FLAT
            and max(first_half) <= 1                 # at low or medium
            and min(last_quarter) >= 2               # last quarter sustains high
        ):
            signals["first_half_flat_at"] = first_half[0]
            signals["last_quarter_min_rank"] = min(last_quarter)
            return {"arc_type": "problem-solution", "signals": signals}

    # Rule 5 — journey: energy climbs steadily AND peak is in the final 30%.
    if n >= 4 and len(profile) >= 4:
        peak_rank = max(profile)
        last_index_of_peak = max(i for i, v in enumerate(profile) if v == peak_rank)
        if last_index_of_peak >= int(n * 0.7):
            transitions = list(zip(profile, profile[1:]))
            non_decreasing = sum(1 for a, b in transitions if b >= a)
            if transitions and non_decreasing / len(transitions) >= 0.75:
                signals["peak_position"] = last_index_of_peak / max(1, n - 1)
                return {"arc_type": "journey", "signals": signals}

    # Default — desire-fulfillment.
    return {"arc_type": "desire-fulfillment", "signals": signals}


# ── classify_hook_mechanic_from_first_scene ─────────────────────────────────

def classify_hook_mechanic_from_first_scene(
    first_scene: dict[str, Any],
    *,
    next_scene: dict[str, Any] | None = None,
) -> str:
    """Map the first scene (with optional next-scene context) to a hook_mechanic.

    Rule evaluation order (first match wins):

      1. ``stat``: a digit appears in narration_text or on_screen_text.
      2. ``question``: narration_text starts with a question word
         (who/what/when/where/why/how/are/is/do/...).
      3. ``visual-contrast``: requires ``next_scene``; energy ranks differ by
         ≥2 OR visual_type changes between content-bearing types.
      4. Default: ``statement``.

    Never emits ``sound-interrupt`` — that requires audio analysis the
    visual classifier doesn't have.
    """
    narration = str(first_scene.get("narration_text", "") or "")
    on_screen = str(first_scene.get("on_screen_text", "") or "")

    # Rule 1 — stat.
    if _DIGIT_RE.search(narration) or _DIGIT_RE.search(on_screen):
        return "stat"

    # Rule 2 — question.
    if narration.strip():
        first_word = narration.strip().split()[0].lower().rstrip("?,.!:;")
        if first_word in _QUESTION_PREFIXES:
            return "question"

    # Rule 3 — visual-contrast (needs the next scene).
    if next_scene is not None:
        first_rank = _energy_rank(first_scene.get("energy_level"))
        next_rank = _energy_rank(next_scene.get("energy_level"))
        if abs(first_rank - next_rank) >= 2:
            return "visual-contrast"
        first_vt = first_scene.get("visual_type")
        next_vt = next_scene.get("visual_type")
        content_types = {"talking_head", "b_roll", "animation",
                         "screen_recording", "product_shot", "stock_footage"}
        if (
            first_vt in content_types
            and next_vt in content_types
            and first_vt != next_vt
        ):
            return "visual-contrast"

    # Default.
    return "statement"


# ── summarize_what_works ────────────────────────────────────────────────────

def summarize_what_works(brief: dict[str, Any], classification: dict[str, Any]) -> str:
    """Return a short mechanical summary of what makes this ad effective.

    Cites the hook mechanic, pacing, and dominant visual style. Pure
    description — not editorial — so the summary is reproducible across
    runs and traceable to the inputs.
    """
    hook = classification.get("hook_mechanic", "statement")
    arc = classification.get("arc_type", "desire-fulfillment")

    structure = brief.get("structure_analysis") or {}
    pacing = structure.get("pacing_profile") or {}
    cpm = pacing.get("cuts_per_minute")
    scenes = structure.get("scenes") or []

    parts: list[str] = [f"Opens with {hook} hook ({arc} arc)."]
    if isinstance(cpm, (int, float)) and cpm > 0:
        parts.append(f"Pacing: ~{cpm:.0f} cuts/min.")

    if scenes:
        distribution = _visual_type_distribution(scenes)
        if distribution:
            top_visual = max(distribution, key=distribution.get)
            parts.append(f"Visual style is dominantly {top_visual}.")

    return " ".join(parts)


# ── classify_hit_ad_from_video_brief (orchestrator) ─────────────────────────

def classify_hit_ad_from_video_brief(brief: dict[str, Any]) -> dict[str, Any]:
    """Run the full classifier on a VideoAnalysisBrief.

    Returns the classification block ready to attach to a hit_ads_analyzed
    entry as ``classification: {...}``.
    """
    structure = brief.get("structure_analysis") or {}
    scenes = structure.get("scenes") or []

    arc_result = classify_arc_type_from_scenes(scenes)
    hook = (
        classify_hook_mechanic_from_first_scene(
            scenes[0],
            next_scene=scenes[1] if len(scenes) > 1 else None,
        )
        if scenes else "statement"
    )

    classification = {
        "arc_type": arc_result["arc_type"],
        "hook_mechanic": hook,
        "what_works": "",   # filled below; needs the partial classification
        "source": "video_analyzer_classification",
        "signals": arc_result["signals"],
    }
    classification["what_works"] = summarize_what_works(brief, classification)
    return classification


# ── aggregate_classifications ───────────────────────────────────────────────

# Sample-size + agreement threshold for research-grounded confidence.
# Mirrors lib.hit_ad_pacing.MIN_SAMPLE_FOR_RESEARCH_GROUNDED in spirit:
# a sample of ≥2 with ≥75% majority agreement is research-grounded.
_MIN_SAMPLE_FOR_RESEARCH_GROUNDED = 2
_MIN_AGREEMENT_FOR_RESEARCH_GROUNDED = 0.75


def _modal_value(values: list[str]) -> tuple[str | None, float]:
    """Return (most_common_value, agreement_fraction) for a list of strings."""
    if not values:
        return None, 0.0
    counts = Counter(values)
    top_value, top_count = counts.most_common(1)[0]
    return top_value, top_count / len(values)


def aggregate_classifications(
    hit_ads: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Aggregate per-ad classifications across analyzed hit ads.

    Returns ``None`` when no ad carries a ``classification`` block (legacy
    briefs, or briefs whose hit ads were article-only). Otherwise:

    ::

        {
          "arc_type":                str,        # majority across analyzed ads
          "arc_type_agreement":      float,      # fraction agreeing 0..1
          "hook_mechanic":           str,
          "hook_mechanic_agreement": float,
          "sample_size":             int,        # count of ads contributing
          "confidence":              "research-grounded" | "pattern-inferred",
          "dissent":                 list,       # full classification of
                                                  # ads that disagreed on
                                                  # arc_type or hook_mechanic
        }

    ``confidence`` is ``research-grounded`` when both the sample is ≥
    ``_MIN_SAMPLE_FOR_RESEARCH_GROUNDED`` AND the majority agreement on
    arc_type is ≥ ``_MIN_AGREEMENT_FOR_RESEARCH_GROUNDED``. Hook_mechanic
    agreement is reported but does not gate the tier (axes are independent
    per design — agreement on arc_type is the load-bearing signal).
    """
    classifications = [
        ad["classification"]
        for ad in hit_ads
        if isinstance(ad.get("classification"), dict)
        and ad["classification"].get("arc_type")
        and ad["classification"].get("hook_mechanic")
    ]
    if not classifications:
        return None

    arc_values = [c["arc_type"] for c in classifications]
    hook_values = [c["hook_mechanic"] for c in classifications]
    arc, arc_agreement = _modal_value(arc_values)
    hook, hook_agreement = _modal_value(hook_values)

    sample_size = len(classifications)
    confidence = (
        "research-grounded"
        if (
            sample_size >= _MIN_SAMPLE_FOR_RESEARCH_GROUNDED
            and arc_agreement >= _MIN_AGREEMENT_FOR_RESEARCH_GROUNDED
        )
        else "pattern-inferred"
    )

    dissent = [
        {"arc_type": c["arc_type"], "hook_mechanic": c["hook_mechanic"]}
        for c in classifications
        if c["arc_type"] != arc or c["hook_mechanic"] != hook
    ]

    return {
        "arc_type": arc,
        "arc_type_agreement": arc_agreement,
        "hook_mechanic": hook,
        "hook_mechanic_agreement": hook_agreement,
        "sample_size": sample_size,
        "confidence": confidence,
        "dissent": dissent,
    }
