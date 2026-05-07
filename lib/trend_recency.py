"""Recency scoring and deduplication for intelligence_brief platform_trends.

The current ``intelligence_brief.platform_trends[]`` shape carries only
``{signal, source, relevance}`` — three free-form strings. Without
observed-at metadata or a decay window, a trend article from 2022 has the
same weight as a yesterday post when bible-director consumes the trends to
drive music direction (or anything else).

This module adds three pure helpers:

* :func:`score_trend_recency` — return a 0..1 freshness score from
  ``observed_at`` and ``decay_window_days``. Trends are full-weight inside
  the decay window, decay linearly to zero by 2× window, and stay zero
  after that. ``is_evergreen=True`` short-circuits to 1.0 regardless of age.

* :func:`filter_stale_trends` — drop fully-stale trends (score 0.0).

* :func:`dedupe_trends` — drop duplicate signals (case-insensitive,
  whitespace-trimmed).

Backward compatible: trends without ``observed_at`` are treated as current
(score 1.0). Legacy briefs without the metadata still flow through unharmed.
"""

from __future__ import annotations

from datetime import date
from typing import Any


DEFAULT_DECAY_WINDOW_DAYS: int = 180


def _parse_observed_at(raw: Any) -> date:
    """Parse an ISO 8601 date string. Wrap ValueError to make the field obvious."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"observed_at must be an ISO 8601 date string; got {raw!r}")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            f"observed_at must be an ISO 8601 date (YYYY-MM-DD); got {raw!r}"
        ) from exc


def score_trend_recency(trend: dict[str, Any], *, now: date) -> float:
    """Return a 0..1 freshness score for ``trend`` relative to ``now``.

    Algorithm:
      * If ``trend["is_evergreen"] is True`` → 1.0.
      * If ``trend`` has no ``observed_at`` → 1.0 (legacy backward compat).
      * If ``observed_at`` is in the future → 1.0 (clock skew tolerance).
      * Otherwise let ``window = trend.get("decay_window_days", DEFAULT)``,
        ``age_days = (now - observed_at).days``:
          - ``age_days <= window`` → 1.0  (still 'current')
          - ``age_days >= 2 * window`` → 0.0
          - otherwise → linear decay from 1.0 (at window) to 0.0 (at 2× window)

    Raises ``ValueError`` if ``observed_at`` is present but unparseable.
    """
    if trend.get("is_evergreen") is True:
        return 1.0

    raw = trend.get("observed_at")
    if raw is None:
        return 1.0

    observed = _parse_observed_at(raw)
    age_days = (now - observed).days
    if age_days <= 0:
        # Future-dated or same-day → current.
        return 1.0

    window = int(trend.get("decay_window_days", DEFAULT_DECAY_WINDOW_DAYS))
    if window < 1:
        window = 1

    if age_days <= window:
        return 1.0
    if age_days >= 2 * window:
        return 0.0
    # Linear decay from (window, 1.0) to (2*window, 0.0).
    return 1.0 - (age_days - window) / window


def filter_stale_trends(
    trends: list[dict[str, Any]], *, now: date
) -> list[dict[str, Any]]:
    """Return only trends whose recency score is > 0 at ``now``.

    Evergreen trends and undated (legacy) trends always pass. Empty input
    returns an empty list.
    """
    return [t for t in trends if score_trend_recency(t, now=now) > 0.0]


def _signal_key(trend: dict[str, Any]) -> str:
    """Normalize a trend's ``signal`` for case-insensitive whitespace-trimmed dedup."""
    return " ".join(str(trend.get("signal", "")).split()).lower()


def dedupe_trends(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop duplicate trends by ``signal`` (case-insensitive, whitespace-trimmed).

    The first occurrence of each signal wins; subsequent duplicates are dropped.
    Order of unique entries is preserved.
    """
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for trend in trends:
        key = _signal_key(trend)
        if key in seen:
            continue
        seen.add(key)
        out.append(trend)
    return out
