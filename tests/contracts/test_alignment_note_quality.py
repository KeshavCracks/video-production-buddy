"""Contract tests for the alignment note quality filter.

Validates that ``apply_alignment_notes`` filters out short or vague notes
(under 15 characters after condensation) while preserving substantive
creative direction.
"""

import pytest

from lib.emotional_prompt import apply_alignment_notes


def test_substantive_note_passes_filter() -> None:
    """A substantive knowledge_alignment_notes string appears in the output."""
    note = (
        "Before/after night color contrast lands in the opening second "
        "for maximum hook impact."
    )
    scene = {"knowledge_alignment_notes": note}
    result = apply_alignment_notes("A dark city skyline at night", scene)

    # The condensed note (before the separator) should appear in the suffix
    assert note.split("—")[0].split(" - ")[0].strip()[:30] in result


def test_short_note_filtered_out() -> None:
    """A knowledge note under 15 chars does not appear in the output."""
    scene = {"knowledge_alignment_notes": "Too short"}
    result = apply_alignment_notes("A dark city skyline at night", scene)

    assert "Too short" not in result
    assert "Creative direction" not in result


def test_trend_note_short_filtered_out() -> None:
    """A trend note under 15 chars does not appear in the output."""
    scene = {"trend_alignment_notes": "Brief"}
    result = apply_alignment_notes("A dark city skyline at night", scene)

    assert "Brief" not in result
    assert "Creative direction" not in result


def test_both_notes_short_returns_unchanged_prompt() -> None:
    """When both notes are too short the original prompt is returned unchanged."""
    scene = {
        "trend_alignment_notes": "Hi",
        "knowledge_alignment_notes": "X",
    }
    original = "original prompt"
    result = apply_alignment_notes(original, scene)

    assert result == original


def test_one_note_passes_one_filtered() -> None:
    """Only the substantive trend note survives; the short knowledge note is dropped."""
    trend_note = "This is a substantive trend note about visual pacing direction"
    scene = {
        "trend_alignment_notes": trend_note,
        "knowledge_alignment_notes": "X",
    }
    result = apply_alignment_notes("A dark city skyline at night", scene)

    assert trend_note in result
    assert "X" not in result or "X." not in result.replace(trend_note, "")
    assert "Creative direction" in result


def test_existing_behavior_preserved_for_good_notes() -> None:
    """Both substantive notes appear in the suffix when each exceeds 15 chars."""
    trend_note = "Rapid cuts with high-energy transitions match hook window pacing"
    knowledge_note = "Warm amber backlighting creates aspirational product halo"
    scene = {
        "trend_alignment_notes": trend_note,
        "knowledge_alignment_notes": knowledge_note,
    }
    result = apply_alignment_notes("Laptop on desk", scene)

    assert trend_note in result
    assert knowledge_note in result
    assert "Creative direction" in result
