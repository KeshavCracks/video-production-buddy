"""Enforce production_bible.narrative.hook_window_seconds on the script.

The bible's ``hook_window_seconds`` is set per platform — TikTok's 3-second
scroll threshold, Instagram's ~5s, etc. It encodes a hard constraint: the
hook section's narration must finish within this window or viewers scroll
past before the ad's hook lands. Without enforcement, scripts that follow
the four-beat percentage structure (hook ~15% of total) routinely overshoot
short windows on short-form-video platforms.

This module is the missing enforcement. ``check_hook_window_compliance``
returns a warning string when the hook section's estimated duration exceeds
the window, or ``None`` when compliant or when the constraint is not set
(legacy briefs, or partial bibles before Step 2 has run).

The estimator prefers an explicit ``duration_estimate_seconds`` on the
section, falling back to ``word_count`` (or word-tokenized ``narration``)
divided by ``HOOK_WORDS_PER_MINUTE``. Same convention as
``tools/compliance/compliance_check.py``.
"""

from __future__ import annotations

from typing import Any

from lib.constants import WORDS_PER_MINUTE_VO


# Re-export the shared VO pacing constant under this module's local name so
# existing callers (`from lib.hook_window import HOOK_WORDS_PER_MINUTE`)
# don't break. Tests pin both to the same source via lib.constants.
HOOK_WORDS_PER_MINUTE: int = WORDS_PER_MINUTE_VO


def estimate_hook_duration_seconds(section: dict[str, Any]) -> float:
    """Estimate the duration of a script section.

    Preference order: explicit ``duration_estimate_seconds`` → ``word_count``
    field → tokenized ``narration``. An empty / missing narration returns 0.0.
    """
    explicit = section.get("duration_estimate_seconds")
    if isinstance(explicit, (int, float)):
        return float(explicit)

    word_count = section.get("word_count")
    if not isinstance(word_count, int):
        narration = str(section.get("narration", ""))
        word_count = len(narration.split()) if narration.strip() else 0

    if word_count <= 0:
        return 0.0
    return word_count / HOOK_WORDS_PER_MINUTE * 60.0


def _find_hook_section(script: dict[str, Any]) -> dict[str, Any] | None:
    """Return the hook section, matching by ``beat == "hook"`` or ``id == "hook"``.

    Returns ``None`` when no section matches. Raises ``ValueError`` when MORE
    than one section matches — silent first-match-wins would let a mistakenly
    tagged build section pass enforcement while the real (overshoot-prone)
    hook went unchecked.
    """
    matches: list[dict[str, Any]] = []
    for section in script.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        if section.get("beat") == "hook" or section.get("id") == "hook":
            matches.append(section)
    if not matches:
        return None
    if len(matches) > 1:
        labels = [s.get("id") or s.get("beat_id") or "<unnamed>" for s in matches]
        raise ValueError(
            f"Ambiguous hook: {len(matches)} sections satisfy the hook predicate "
            f"(beat=='hook' or id=='hook'): {labels}. Tag exactly one section as "
            f"the hook so check_hook_window_compliance enforces the right one."
        )
    return matches[0]


def check_hook_window_compliance(
    script: dict[str, Any], hook_window_seconds: float | None
) -> str | None:
    """Return a warning string when the hook section overshoots the window, else None.

    Returns ``None`` when:
      * ``hook_window_seconds`` is ``None``, ``0``, or negative (misconfigured /
        legacy / unset)
      * the script has no hook section
      * the hook section's estimated duration is within the window
    """
    if hook_window_seconds is None or hook_window_seconds <= 0:
        return None

    hook = _find_hook_section(script)
    if hook is None:
        return None

    estimated = estimate_hook_duration_seconds(hook)
    if estimated <= hook_window_seconds:
        return None

    return (
        f"hook section estimated at {estimated:.2f}s exceeds "
        f"hook_window_seconds={hook_window_seconds}; trim narration before "
        f"submitting (platform constraint — viewers scroll past at the window)"
    )
