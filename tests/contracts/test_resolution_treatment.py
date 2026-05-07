"""Tests for lib.resolution_treatment — thread bible resolution_type into prompts.

production_bible.narrative.resolution_type is an enum set by bible-director:
``"relief" | "aspiration" | "social-validation" | "authority"``. It encodes
how the final beat should feel emotionally. Until now the field was set but
no downstream stage read it — the resolution scene's image/video prompt was
generic, regardless of whether the brief asked for relief, aspiration,
social validation, or authority.

This module is the missing thread: asset-director identifies the resolution
beat and wraps that scene's prompt with ``apply_resolution_treatment`` so
the generation lands on the right emotional register.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.resolution_treatment import (
    RESOLUTION_TREATMENT_PHRASES,
    apply_resolution_treatment,
)


# ── Pass-through cases ─────────────────────────────────────────────────────

def test_returns_prompt_unchanged_when_resolution_type_is_none():
    prompt = "Product hero shot, soft window light."
    assert apply_resolution_treatment(prompt, resolution_type=None) == prompt


def test_returns_prompt_unchanged_when_resolution_type_is_empty_string():
    prompt = "Product hero shot, soft window light."
    assert apply_resolution_treatment(prompt, resolution_type="") == prompt


def test_returns_prompt_unchanged_when_resolution_type_is_unknown():
    """Unknown enum values (typos, malformed bibles) pass through silently —
    the schema validator catches enum violations separately."""
    prompt = "Product hero shot."
    assert apply_resolution_treatment(prompt, resolution_type="made_up_type") == prompt


# ── Append cases ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("resolution_type", list(RESOLUTION_TREATMENT_PHRASES.keys()))
def test_appends_distinct_phrase_for_each_enum_value(resolution_type):
    """Every documented enum value produces a recognizable, non-empty phrase."""
    prompt = "Product hero shot."
    out = apply_resolution_treatment(prompt, resolution_type=resolution_type)
    assert prompt in out
    assert out != prompt
    phrase = RESOLUTION_TREATMENT_PHRASES[resolution_type]
    assert phrase
    assert phrase in out


def test_relief_phrase_evokes_calm_or_exhale():
    out = apply_resolution_treatment("x", resolution_type="relief")
    assert any(token in out.lower() for token in ("calm", "soft", "exhale", "peaceful"))


def test_aspiration_phrase_evokes_uplift_or_hope():
    out = apply_resolution_treatment("x", resolution_type="aspiration")
    assert any(token in out.lower() for token in ("uplift", "rise", "rising", "hopeful", "expansive"))


def test_social_validation_phrase_evokes_people_or_community():
    out = apply_resolution_treatment("x", resolution_type="social-validation")
    assert any(token in out.lower() for token in ("people", "group", "shared", "community", "authentic", "testimonial"))


def test_authority_phrase_evokes_confidence_or_trust():
    out = apply_resolution_treatment("x", resolution_type="authority")
    assert any(token in out.lower() for token in ("confident", "bold", "trust", "deliberate"))


# ── Distinctness ───────────────────────────────────────────────────────────

def test_each_enum_produces_distinct_output():
    """Each phrase must be unique — the four resolution types are emotionally
    different, the prompts must reflect that."""
    prompts = {
        kind: apply_resolution_treatment("x", resolution_type=kind)
        for kind in RESOLUTION_TREATMENT_PHRASES
    }
    assert len(set(prompts.values())) == len(RESOLUTION_TREATMENT_PHRASES)


# ── Idempotency / composition ─────────────────────────────────────────────

def test_idempotent_when_resolution_phrase_already_in_prompt():
    """Re-applying must not duplicate the phrase."""
    prompt = "Product hero shot."
    once = apply_resolution_treatment(prompt, resolution_type="aspiration")
    twice = apply_resolution_treatment(once, resolution_type="aspiration")
    assert once == twice


def test_handles_empty_prompt():
    out = apply_resolution_treatment("", resolution_type="authority")
    assert out  # non-empty
    assert RESOLUTION_TREATMENT_PHRASES["authority"] in out


def test_preserves_existing_punctuation_in_prompt():
    prompt = "Product hero shot, lit from above; clean backdrop!"
    out = apply_resolution_treatment(prompt, resolution_type="aspiration")
    assert prompt in out


def test_strips_whitespace_around_resolution_type():
    out_a = apply_resolution_treatment("x", resolution_type="aspiration")
    out_b = apply_resolution_treatment("x", resolution_type="  aspiration  ")
    assert out_a == out_b


# ── Schema enum coverage ───────────────────────────────────────────────────

def test_treatment_phrases_cover_all_schema_enum_values():
    """The bible schema declares exactly these four resolution_type values.
    The phrases dict must cover them all so no schema-valid enum value
    silently produces a no-op."""
    expected = {"relief", "aspiration", "social-validation", "authority"}
    assert set(RESOLUTION_TREATMENT_PHRASES.keys()) == expected


# ── HIGH-3 regression (parallel to color_direction) ────────────────────────

def test_idempotency_uses_full_suffix_not_phrase_substring():
    """Mirror the color_direction fix: idempotency must check for the full
    'Resolution treatment: <phrase>.' string, not just a phrase substring.
    Edge case — a prompt that already contains some token from the long
    phrase (e.g. 'calm') should NOT cause the suffix to be skipped."""
    prompt = "calm exhale of relief"
    out = apply_resolution_treatment(prompt, resolution_type="relief")
    # The full suffix must be appended; the original prompt's 'calm' / 'exhale'
    # tokens are not equivalent to having already applied the helper.
    assert "Resolution treatment:" in out, (
        f"resolution suffix dropped against prompt with overlapping tokens; got: {out!r}"
    )


def test_idempotency_still_works_when_full_suffix_already_present():
    """The corrected idempotency check still prevents duplicates."""
    prompt = "calm exhale. Resolution treatment: " + RESOLUTION_TREATMENT_PHRASES["relief"] + "."
    out = apply_resolution_treatment(prompt, resolution_type="relief")
    assert out == prompt
    assert out.count("Resolution treatment:") == 1


# ── MEDIUM-3 regression: trailing-comma separator ──────────────────────────

def test_separator_handles_prompt_ending_in_comma():
    """Trailing comma + suffix must not produce ', .' soup."""
    prompt = "cinematic, photorealistic, shallow depth of field,"
    out = apply_resolution_treatment(prompt, resolution_type="aspiration")
    assert ", . " not in out, f"trailing-comma + period sequence in: {out!r}"
    assert ",. " not in out, f"trailing-comma + period sequence in: {out!r}"
    assert "Resolution treatment:" in out
