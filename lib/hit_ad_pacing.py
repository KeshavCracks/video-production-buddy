"""Aggregate measured pacing across analyzed hit ads.

intelligence_brief.hit_ads_analyzed[] previously stored only article-summary
fields — no real video analysis. The original intelligence-director skill was
honest about this: "Web search returns summaries, not video analysis. Pacing
data is rarely stated — most editing_rhythm entries will be pattern-inferred
or default-heuristic."

Now intelligence-director can invoke ``video_analyzer`` on hit ads with
public URLs and capture real measured pacing (``cuts_per_minute``,
``avg_scene_duration_seconds``) into the additive ``pacing_measured`` field.
This module aggregates those measurements across the list, returning mean
pacing plus a confidence tier so bible-director can upgrade editing_rhythm
from ``pattern-inferred`` to ``research-grounded`` when the sample is large
enough.

The aggregation is intentionally simple: arithmetic mean of ``cuts_per_minute``
and ``avg_scene_duration_seconds``, sample-size-driven confidence tier, and a
derived ``cuts_density`` (schema enum) computed from the mean shot duration.
"""

from __future__ import annotations

from typing import Any


# Two analyzed ads is the threshold for research-grounded — single-sample
# evidence is honestly pattern-inferred. Bible-director uses this confidence
# tier to decide whether intelligence's recommendation can override the
# user's enriched_brief.
MIN_SAMPLE_FOR_RESEARCH_GROUNDED: int = 2


def cuts_density_from_shot_duration(avg_seconds: float) -> str:
    """Map an average shot duration in seconds to a cuts_density enum value.

    Bands (matching ``production_bible.visual.editing_rhythm[].cuts_density``
    enum subset used by deterministic mappings):

      ``avg < 2.0``       → ``"rapid"``
      ``2.0 ≤ avg < 4.5`` → ``"moderate"``
      ``4.5 ≤ avg < 6.0`` → ``"slow"``
      ``avg ≥ 6.0``       → ``"held"``
    """
    if avg_seconds < 2.0:
        return "rapid"
    if avg_seconds < 4.5:
        return "moderate"
    if avg_seconds < 6.0:
        return "slow"
    return "held"


def _has_valid_measurement(pacing: Any) -> bool:
    """Return True iff ``pacing`` has the two numeric fields the aggregate needs."""
    if not isinstance(pacing, dict):
        return False
    cpm = pacing.get("cuts_per_minute")
    avg = pacing.get("avg_scene_duration_seconds")
    return isinstance(cpm, (int, float)) and isinstance(avg, (int, float))


def aggregate_pacing_from_hit_ads(
    hit_ads: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Aggregate measured pacing across analyzed hit ads.

    Returns ``None`` when no ads carry a valid ``pacing_measured`` block
    (legacy briefs, or briefs where every hit ad was article-only). Otherwise
    returns:

    ::

        {
          "avg_cuts_per_minute":         float,
          "avg_shot_duration_seconds":   float,
          "sample_size":                 int,
          "confidence":                  "research-grounded" | "pattern-inferred",
          "cuts_density":                "rapid" | "moderate" | "held",
        }

    The confidence tier is ``research-grounded`` when at least
    ``MIN_SAMPLE_FOR_RESEARCH_GROUNDED`` ads contributed measured pacing,
    else ``pattern-inferred``. Hit ads with malformed ``pacing_measured``
    blocks (missing required numeric fields) are silently skipped — they
    don't crash the aggregation, they just don't contribute.
    """
    samples = [
        ad["pacing_measured"]
        for ad in hit_ads
        if _has_valid_measurement(ad.get("pacing_measured"))
    ]
    if not samples:
        return None

    n = len(samples)
    avg_cpm = sum(s["cuts_per_minute"] for s in samples) / n
    avg_dur = sum(s["avg_scene_duration_seconds"] for s in samples) / n
    confidence = (
        "research-grounded"
        if n >= MIN_SAMPLE_FOR_RESEARCH_GROUNDED
        else "pattern-inferred"
    )
    return {
        "avg_cuts_per_minute": avg_cpm,
        "avg_shot_duration_seconds": avg_dur,
        "sample_size": n,
        "confidence": confidence,
        "cuts_density": cuts_density_from_shot_duration(avg_dur),
    }
