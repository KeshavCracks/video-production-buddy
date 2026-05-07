"""Tests for lib.hit_ad_pacing — aggregate measured pacing from hit ads.

intelligence_brief.hit_ads_analyzed[] previously stored only text-inferred
fields (arc_type, hook_mechanic, what_works) with no measured pacing data.
The skill itself was honest: 'Web search returns summaries, not video
analysis. Pacing data is rarely stated — most editing_rhythm entries will be
pattern-inferred or default-heuristic.'

Now intelligence-director invokes video_analyzer on hit ads with public URLs
and captures real measured pacing in `pacing_measured`. This module
aggregates those measurements across the hit_ads_analyzed list, returning
mean cuts_per_minute / avg_shot_duration_seconds plus a confidence tier so
bible-director can upgrade editing_rhythm from pattern-inferred to
research-grounded when the sample is large enough.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.hit_ad_pacing import (
    MIN_SAMPLE_FOR_RESEARCH_GROUNDED,
    aggregate_pacing_from_hit_ads,
    cuts_density_from_shot_duration,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _hit_ad(
    *,
    title: str = "Hit Ad",
    pacing: dict | None = None,
    url: str | None = None,
) -> dict:
    """Build a hit_ad dict with the required fields plus optional measured pacing."""
    ad = {
        "title": title,
        "platform": "tiktok",
        "arc_type": "problem-solution",
        "hook_mechanic": "stat",
        "what_works": "x",
        "adopted": True,
    }
    if url is not None:
        ad["url"] = url
    if pacing is not None:
        ad["pacing_measured"] = pacing
    return ad


def _measured(cpm: float, avg: float, scenes: int = 12) -> dict:
    return {
        "cuts_per_minute": cpm,
        "avg_scene_duration_seconds": avg,
        "total_scenes": scenes,
        "source": "video_analyzer",
    }


# ── aggregate_pacing_from_hit_ads ──────────────────────────────────────────

def test_aggregate_returns_none_when_no_ads_analyzed():
    """Backward compat: a brief whose hit ads have no pacing_measured returns
    None — bible-director keeps the legacy pattern-inferred / default-heuristic
    path."""
    hit_ads = [_hit_ad(title="Article-only ad 1"), _hit_ad(title="Article-only ad 2")]
    assert aggregate_pacing_from_hit_ads(hit_ads) is None


def test_aggregate_returns_none_for_empty_list():
    assert aggregate_pacing_from_hit_ads([]) is None


def test_aggregate_single_analyzed_ad_is_pattern_inferred():
    """One sample isn't enough for research-grounded — it's a sample of one."""
    hit_ads = [_hit_ad(title="A", pacing=_measured(cpm=40.0, avg=1.5, scenes=20))]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg is not None
    assert agg["sample_size"] == 1
    assert agg["confidence"] == "pattern-inferred"
    assert agg["avg_cuts_per_minute"] == pytest.approx(40.0)
    assert agg["avg_shot_duration_seconds"] == pytest.approx(1.5)


def test_aggregate_two_or_more_analyzed_ads_is_research_grounded():
    """Two analyzed ads cross the threshold for research-grounded."""
    hit_ads = [
        _hit_ad(title="A", pacing=_measured(cpm=40.0, avg=1.5, scenes=20)),
        _hit_ad(title="B", pacing=_measured(cpm=30.0, avg=2.0, scenes=15)),
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["sample_size"] == 2
    assert agg["confidence"] == "research-grounded"
    assert agg["avg_cuts_per_minute"] == pytest.approx(35.0)
    assert agg["avg_shot_duration_seconds"] == pytest.approx(1.75)


def test_aggregate_threshold_constant_governs_research_grounded():
    """The threshold should be exactly MIN_SAMPLE_FOR_RESEARCH_GROUNDED."""
    n = MIN_SAMPLE_FOR_RESEARCH_GROUNDED
    hit_ads = [_hit_ad(title=f"A{i}", pacing=_measured(40.0, 1.5)) for i in range(n)]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["sample_size"] == n
    assert agg["confidence"] == "research-grounded"

    # One under threshold → pattern-inferred.
    fewer = [_hit_ad(title=f"A{i}", pacing=_measured(40.0, 1.5)) for i in range(n - 1)]
    agg_fewer = aggregate_pacing_from_hit_ads(fewer)
    assert agg_fewer["confidence"] == "pattern-inferred"


def test_aggregate_skips_ads_without_pacing_measured():
    """Mixed list: only ads with pacing_measured contribute to the average."""
    hit_ads = [
        _hit_ad(title="article-only"),
        _hit_ad(title="A", pacing=_measured(cpm=40.0, avg=1.5)),
        _hit_ad(title="B", pacing=_measured(cpm=20.0, avg=3.0)),
        _hit_ad(title="another article-only"),
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["sample_size"] == 2
    assert agg["avg_cuts_per_minute"] == pytest.approx(30.0)


def test_aggregate_includes_derived_cuts_density():
    """Aggregate should expose a derived cuts_density (matching schema enum)
    so bible-director can populate editing_rhythm without re-deriving."""
    hit_ads = [
        _hit_ad(title="A", pacing=_measured(40.0, 1.0)),
        _hit_ad(title="B", pacing=_measured(40.0, 1.2)),
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["cuts_density"] == "rapid"


def test_aggregate_cuts_density_is_held_for_long_shots():
    hit_ads = [
        _hit_ad(title="A", pacing=_measured(8.0, 8.0)),
        _hit_ad(title="B", pacing=_measured(10.0, 6.0)),
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["cuts_density"] == "held"


def test_aggregate_cuts_density_is_moderate_for_mid_shots():
    hit_ads = [
        _hit_ad(title="A", pacing=_measured(20.0, 3.0)),
        _hit_ad(title="B", pacing=_measured(25.0, 2.4)),
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["cuts_density"] == "moderate"


def test_aggregate_skips_malformed_pacing_silently():
    """Defensive: a hit ad whose pacing_measured is missing required fields
    is treated as if pacing wasn't measured at all (skipped, not crashed)."""
    hit_ads = [
        _hit_ad(title="A", pacing=_measured(40.0, 1.5)),
        _hit_ad(title="B", pacing={"source": "video_analyzer"}),  # missing the numbers
    ]
    agg = aggregate_pacing_from_hit_ads(hit_ads)
    assert agg["sample_size"] == 1


# ── cuts_density_from_shot_duration ────────────────────────────────────────

@pytest.mark.parametrize("avg, expected", [
    (0.5, "rapid"),
    (1.2, "rapid"),
    (1.99, "rapid"),
    (2.0, "moderate"),
    (3.5, "moderate"),
    (4.49, "moderate"),
    (4.5, "held"),
    (10.0, "held"),
])
def test_cuts_density_band_boundaries(avg, expected):
    assert cuts_density_from_shot_duration(avg) == expected


def test_cuts_density_uses_schema_enum():
    valid = {"rapid", "moderate", "slow", "held"}
    for avg in [0.1, 1.0, 2.0, 4.0, 6.0, 10.0]:
        assert cuts_density_from_shot_duration(avg) in valid
