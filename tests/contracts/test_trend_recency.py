"""Tests for lib.trend_recency — recency scoring + deduplication for trends.

intelligence_brief.platform_trends[] currently stores trends as free-form
{signal, source, relevance} strings. Without observed_at / decay window
metadata, a trend article from 2022 has the same weight as a yesterday post
when bible-director consumes the trends to drive music direction etc.

This module adds three helpers:
  * score_trend_recency(trend, now)      → 0..1 freshness score
  * filter_stale_trends(trends, now)     → drops fully-stale trends
  * dedupe_trends(trends)                → drops duplicates by signal

Backward compatible: trends without `observed_at` are treated as current
(score = 1.0) so legacy briefs without the metadata still work.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.trend_recency import (
    DEFAULT_DECAY_WINDOW_DAYS,
    dedupe_trends,
    filter_stale_trends,
    score_trend_recency,
)


# ── score_trend_recency ────────────────────────────────────────────────────

def test_score_today_is_one():
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "https://x.com", "relevance": "x",
             "observed_at": "2026-04-26"}
    assert score_trend_recency(trend, now=now) == pytest.approx(1.0)


def test_score_within_window_decays_linearly_to_one_at_window_edge():
    """Inside [0, decay_window_days] the score is constant 1.0 (still 'current')."""
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2026-01-26",  # 90 days old
             "decay_window_days": 90}
    assert score_trend_recency(trend, now=now) == pytest.approx(1.0)


def test_score_just_past_window_drops_below_one():
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2026-01-25",  # 91 days old
             "decay_window_days": 90}
    score = score_trend_recency(trend, now=now)
    assert 0.0 < score < 1.0


def test_score_at_two_window_widths_is_zero():
    """Linear decay from window edge (1.0) to 2x window (0.0)."""
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2025-10-28",  # 180 days old
             "decay_window_days": 90}
    assert score_trend_recency(trend, now=now) == pytest.approx(0.0)


def test_score_far_past_window_stays_zero():
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2020-01-01",
             "decay_window_days": 90}
    assert score_trend_recency(trend, now=now) == pytest.approx(0.0)


def test_score_evergreen_trend_is_one_regardless_of_age():
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2010-01-01",
             "decay_window_days": 90,
             "is_evergreen": True}
    assert score_trend_recency(trend, now=now) == pytest.approx(1.0)


def test_score_missing_observed_at_treats_as_current():
    """Backward compat: trends without observed_at are score 1.0 (current).
    Legacy briefs predate the metadata; we don't penalize them."""
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x"}  # no observed_at
    assert score_trend_recency(trend, now=now) == pytest.approx(1.0)


def test_score_uses_default_decay_window_when_unspecified():
    """When decay_window_days is missing, fall back to DEFAULT_DECAY_WINDOW_DAYS."""
    now = date(2026, 4, 26)
    one_day_past_default = now - timedelta(days=DEFAULT_DECAY_WINDOW_DAYS + 1)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": one_day_past_default.isoformat()}
    score = score_trend_recency(trend, now=now)
    assert 0.0 < score < 1.0


def test_score_invalid_observed_at_raises():
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "not-a-date"}
    with pytest.raises(ValueError, match="observed_at"):
        score_trend_recency(trend, now=now)


def test_score_future_observed_at_clamps_to_one():
    """A trend dated in the future is presumably a clock skew; treat as current."""
    now = date(2026, 4, 26)
    trend = {"signal": "x", "source": "x", "relevance": "x",
             "observed_at": "2030-01-01"}
    assert score_trend_recency(trend, now=now) == pytest.approx(1.0)


# ── filter_stale_trends ────────────────────────────────────────────────────

def test_filter_drops_fully_stale_trends():
    now = date(2026, 4, 26)
    trends = [
        {"signal": "fresh", "source": "x", "relevance": "x", "observed_at": "2026-04-01"},
        {"signal": "stale", "source": "x", "relevance": "x",
         "observed_at": "2020-01-01", "decay_window_days": 90},
    ]
    out = filter_stale_trends(trends, now=now)
    signals = [t["signal"] for t in out]
    assert signals == ["fresh"]


def test_filter_keeps_evergreen_even_when_old():
    now = date(2026, 4, 26)
    trends = [
        {"signal": "old-but-evergreen", "source": "x", "relevance": "x",
         "observed_at": "2010-01-01", "is_evergreen": True},
    ]
    out = filter_stale_trends(trends, now=now)
    assert len(out) == 1


def test_filter_keeps_undated_legacy_trends():
    """Backward compat: trends without observed_at are kept (score=1.0)."""
    now = date(2026, 4, 26)
    trends = [{"signal": "legacy", "source": "x", "relevance": "x"}]
    out = filter_stale_trends(trends, now=now)
    assert len(out) == 1


def test_filter_empty_input_returns_empty():
    assert filter_stale_trends([], now=date(2026, 4, 26)) == []


# ── dedupe_trends ──────────────────────────────────────────────────────────

def test_dedupe_drops_duplicate_signals():
    trends = [
        {"signal": "fast cuts trending", "source": "https://a.com", "relevance": "x"},
        {"signal": "fast cuts trending", "source": "https://b.com", "relevance": "x"},
        {"signal": "slow cinematic returning", "source": "https://c.com", "relevance": "x"},
    ]
    out = dedupe_trends(trends)
    signals = [t["signal"] for t in out]
    assert signals == ["fast cuts trending", "slow cinematic returning"]


def test_dedupe_is_case_insensitive_and_whitespace_trimmed():
    """'fast cuts' / 'Fast Cuts' / ' fast cuts ' are the same signal."""
    trends = [
        {"signal": "fast cuts", "source": "x", "relevance": "x"},
        {"signal": "Fast Cuts", "source": "y", "relevance": "x"},
        {"signal": "  fast cuts  ", "source": "z", "relevance": "x"},
    ]
    out = dedupe_trends(trends)
    assert len(out) == 1


def test_dedupe_preserves_first_occurrence():
    """The first entry wins when duplicates exist (most-recently-discovered or
    most-relevant should be ordered first by the caller)."""
    trends = [
        {"signal": "x", "source": "https://first.com", "relevance": "high"},
        {"signal": "x", "source": "https://second.com", "relevance": "low"},
    ]
    out = dedupe_trends(trends)
    assert out[0]["source"] == "https://first.com"


def test_dedupe_preserves_order_of_unique_entries():
    trends = [
        {"signal": "a", "source": "x", "relevance": "x"},
        {"signal": "b", "source": "x", "relevance": "x"},
        {"signal": "a", "source": "y", "relevance": "x"},
        {"signal": "c", "source": "x", "relevance": "x"},
    ]
    out = dedupe_trends(trends)
    assert [t["signal"] for t in out] == ["a", "b", "c"]


def test_dedupe_empty_input_returns_empty():
    assert dedupe_trends([]) == []


# ── Composition ────────────────────────────────────────────────────────────

def test_filter_then_dedupe_typical_pipeline():
    now = date(2026, 4, 26)
    trends = [
        {"signal": "fast cuts", "source": "https://a.com", "relevance": "high",
         "observed_at": "2026-04-01"},
        {"signal": "fast cuts", "source": "https://b.com", "relevance": "low",
         "observed_at": "2026-04-15"},
        {"signal": "stale fad", "source": "https://c.com", "relevance": "x",
         "observed_at": "2020-01-01", "decay_window_days": 90},
        {"signal": "evergreen brand-led storytelling", "source": "https://d.com",
         "relevance": "x", "observed_at": "2010-01-01", "is_evergreen": True},
    ]
    fresh = filter_stale_trends(trends, now=now)
    final = dedupe_trends(fresh)
    signals = [t["signal"] for t in final]
    assert signals == ["fast cuts", "evergreen brand-led storytelling"]
