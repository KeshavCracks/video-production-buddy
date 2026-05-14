"""Tests for lib.hook_window — enforce production_bible hook_window_seconds.

The bible's narrative.hook_window_seconds is set per platform (TikTok 3s
scroll threshold, Instagram ~5s, etc.) by intelligence-director and
bible-director Step 2. It encodes a hard platform constraint: the hook
section's narration must finish within this window or viewers scroll past
before the ad lands.

Until now, the field was set but no downstream stage enforced it. This
module is the missing enforcement: script-director invokes it before
submitting the script artifact and edit-director can re-check at compose.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.hook_window import (
    HOOK_WORDS_PER_MINUTE,
    check_hook_window_compliance,
    estimate_hook_duration_seconds,
)
from lib.constants import WORDS_PER_MINUTE_VO


def test_hook_wpm_constant_is_sourced_from_shared_constants_module():
    """Regression: HOOK_WORDS_PER_MINUTE used to duplicate the same value
    in tools/compliance/compliance_check.py (_WORDS_PER_MINUTE = 150). If
    one was updated and the other wasn't, the helper's estimate would
    diverge from compliance_check's estimate. Both must now come from
    lib.constants.WORDS_PER_MINUTE_VO."""
    assert HOOK_WORDS_PER_MINUTE == WORDS_PER_MINUTE_VO

    # And compliance_check must read from the same source.
    from tools.compliance import compliance_check as cc
    assert cc._WORDS_PER_MINUTE == WORDS_PER_MINUTE_VO


# ── estimate_hook_duration_seconds ─────────────────────────────────────────

def test_estimate_uses_explicit_duration_when_present():
    """When a section carries duration_estimate_seconds, prefer it over WPM math."""
    section = {"narration": "x " * 100, "duration_estimate_seconds": 4.5}
    assert estimate_hook_duration_seconds(section) == pytest.approx(4.5)


def test_estimate_falls_back_to_word_count_at_pace():
    """No duration_estimate_seconds → estimate from word count at HOOK_WORDS_PER_MINUTE."""
    # 7 words at HOOK_WPM is exactly 7 / HOOK_WPM * 60 seconds.
    section = {"narration": " ".join(["word"] * 7)}
    expected = 7 / HOOK_WORDS_PER_MINUTE * 60
    assert estimate_hook_duration_seconds(section) == pytest.approx(expected)


def test_estimate_uses_word_count_field_when_present():
    """If word_count is set, prefer it over re-tokenizing narration."""
    section = {"narration": "ignored text", "word_count": 12}
    expected = 12 / HOOK_WORDS_PER_MINUTE * 60
    assert estimate_hook_duration_seconds(section) == pytest.approx(expected)


def test_estimate_zero_for_empty_section():
    section = {"narration": ""}
    assert estimate_hook_duration_seconds(section) == 0.0


# ── check_hook_window_compliance ───────────────────────────────────────────

def _hook_section(narration: str, *, duration: float | None = None) -> dict:
    s = {"id": "hook", "beat": "hook", "beat_id": "B1", "narration": narration}
    if duration is not None:
        s["duration_estimate_seconds"] = duration
    return s


def _script(sections: list[dict]) -> dict:
    return {"total_duration_seconds": 60, "sections": sections}


def test_compliance_passes_when_hook_fits_window():
    """Hook with 5 words at HOOK_WPM ≈ 2s — fits the TikTok 3s window."""
    script = _script([_hook_section("Every morning you waste hours.")])
    assert check_hook_window_compliance(script, hook_window_seconds=3.0) is None


def test_compliance_fails_when_hook_overshoots_window():
    """Hook with explicit 5s duration exceeds a 3s window."""
    script = _script([_hook_section("Every morning, you waste hours.", duration=5.0)])
    warning = check_hook_window_compliance(script, hook_window_seconds=3.0)
    assert warning is not None
    assert "hook" in warning.lower()
    assert "3" in warning
    assert "5" in warning


def test_compliance_fails_when_hook_word_count_implies_overshoot():
    """A 25-word hook at HOOK_WPM is well over a 3s TikTok window even
    without an explicit duration_estimate_seconds."""
    long_narration = " ".join(["word"] * 25)
    script = _script([_hook_section(long_narration)])
    warning = check_hook_window_compliance(script, hook_window_seconds=3.0)
    assert warning is not None


def test_compliance_returns_none_when_hook_window_seconds_is_none():
    """Backward compat: legacy briefs without hook_window_seconds skip the
    check entirely. Bible-director sets it but a partial bible may not yet
    have it during early synthesis."""
    script = _script([_hook_section("Anything at all.", duration=10.0)])
    assert check_hook_window_compliance(script, hook_window_seconds=None) is None


def test_compliance_returns_none_when_hook_window_seconds_is_zero():
    """A 0 or negative hook_window_seconds is a misconfiguration, not a
    constraint to enforce. Skip silently rather than error — the schema
    validator catches the malformed value separately."""
    script = _script([_hook_section("x", duration=2.0)])
    assert check_hook_window_compliance(script, hook_window_seconds=0) is None


def test_compliance_finds_hook_by_id_when_beat_field_missing():
    """Some pipelines set 'id': 'hook' but no 'beat' field. Find by either."""
    section = {"id": "hook", "narration": "Way too long " * 30,
               "duration_estimate_seconds": 12.0}
    warning = check_hook_window_compliance(_script([section]), hook_window_seconds=3.0)
    assert warning is not None


def test_compliance_finds_hook_by_beat_when_id_is_arbitrary():
    """Conversely, beat='hook' should match even if id is non-standard."""
    section = {"id": "section-1", "beat": "hook", "narration": "x",
               "duration_estimate_seconds": 8.0}
    warning = check_hook_window_compliance(_script([section]), hook_window_seconds=3.0)
    assert warning is not None


def test_compliance_returns_none_when_no_hook_section_present():
    """If the script has no hook section at all, the compliance check has
    nothing to validate. Return None (the four-beat-structure check in
    script-director catches missing hooks separately)."""
    script = _script([
        {"id": "build_1", "beat": "build", "narration": "x",
         "duration_estimate_seconds": 5.0},
    ])
    assert check_hook_window_compliance(script, hook_window_seconds=3.0) is None


def test_compliance_only_inspects_hook_section_not_others():
    """A 12s build section is fine — only the hook section is constrained
    by hook_window_seconds."""
    script = _script([
        _hook_section("Quick.", duration=2.0),
        {"id": "build_1", "beat": "build", "narration": "x",
         "duration_estimate_seconds": 12.0},
    ])
    assert check_hook_window_compliance(script, hook_window_seconds=3.0) is None


def test_compliance_warning_includes_estimated_and_target_durations():
    """The warning message must include both numbers so the user / agent
    can see exactly how far off the hook is."""
    script = _script([_hook_section("Long hook copy.", duration=4.5)])
    warning = check_hook_window_compliance(script, hook_window_seconds=3.0)
    assert warning is not None
    assert "4.5" in warning or "4.50" in warning
    assert "3" in warning


# ── HIGH-1 regression: ambiguous duplicate hook tags ───────────────────────

def test_compliance_raises_on_two_sections_both_tagged_hook():
    """Regression: if a build section is mistakenly tagged beat='hook', the
    helper must NOT silently validate the first match in document order. That
    would let a too-long actual hook pass the gate while only the mis-tagged
    short build is checked. Surface the ambiguity loudly."""
    script = _script([
        # Mistakenly tagged build section (short, would pass).
        {"id": "build_1", "beat": "hook", "narration": "x",
         "duration_estimate_seconds": 1.0},
        # The actual hook (long, should fail the 3s window).
        {"id": "hook", "beat": "hook", "narration": "Way too long for tiktok " * 5,
         "duration_estimate_seconds": 8.0},
    ])
    with pytest.raises(ValueError, match=r"(?i)ambiguous.*hook"):
        check_hook_window_compliance(script, hook_window_seconds=3.0)


def test_compliance_raises_when_id_hook_and_beat_hook_appear_on_different_sections():
    """A section with id='hook' AND a different section with beat='hook' is
    also ambiguous — the predicate matches both."""
    script = _script([
        {"id": "hook", "beat": "build", "narration": "x",
         "duration_estimate_seconds": 1.0},
        {"id": "section-2", "beat": "hook", "narration": "x",
         "duration_estimate_seconds": 8.0},
    ])
    with pytest.raises(ValueError, match=r"(?i)ambiguous.*hook"):
        check_hook_window_compliance(script, hook_window_seconds=3.0)
