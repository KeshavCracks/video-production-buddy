"""Tests for lib.color_direction — thread bible color palette into prompts.

production_bible.visual.color_direction is set by bible-director (e.g.
"muted warm lo-fi palette" or "vibrant neon retrofuturism") to constrain
the visual treatment of generated assets. Until now it was set but never
read — image-gen and video-gen prompts ignored it, so every generated still
or clip used the default model palette regardless of brief intent.

This module is the missing thread: asset-director wraps image-gen and
video-gen prompts in ``apply_color_direction`` before calling the
provider so the bible's palette steers the generation.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.color_direction import apply_color_direction


# ── Pass-through cases ─────────────────────────────────────────────────────

def test_returns_prompt_unchanged_when_color_direction_is_none():
    prompt = "A smiling face on a beach at sunset."
    assert apply_color_direction(prompt, color_direction=None) == prompt


def test_returns_prompt_unchanged_when_color_direction_is_empty_string():
    prompt = "A smiling face on a beach at sunset."
    assert apply_color_direction(prompt, color_direction="") == prompt


def test_returns_prompt_unchanged_when_color_direction_is_whitespace_only():
    prompt = "A smiling face on a beach at sunset."
    assert apply_color_direction(prompt, color_direction="   \n\t  ") == prompt


# ── Append cases ───────────────────────────────────────────────────────────

def test_appends_color_palette_suffix_when_set():
    prompt = "A smiling face on a beach at sunset."
    out = apply_color_direction(prompt, color_direction="muted warm lo-fi palette")
    assert prompt in out
    # The suffix must mention the palette so the generation model picks it up.
    assert "muted warm lo-fi palette" in out
    assert "color palette" in out.lower() or "palette" in out.lower()


def test_appends_after_existing_prompt_with_separator():
    """The separator should make it a clear suffix, not a run-on sentence."""
    prompt = "A smiling face on a beach at sunset."
    out = apply_color_direction(prompt, color_direction="vibrant neon retrofuturism")
    # Must contain a clear separator between original and palette annotation.
    assert "." in out or ";" in out or "—" in out


def test_handles_empty_prompt():
    """Empty prompt + valid color_direction: emit just the palette annotation."""
    out = apply_color_direction("", color_direction="emerald and gold")
    assert "emerald and gold" in out


def test_idempotent_when_color_direction_already_in_prompt():
    """Re-applying the same color_direction must not duplicate the annotation."""
    prompt = "A face on a beach."
    once = apply_color_direction(prompt, color_direction="muted warm lo-fi palette")
    twice = apply_color_direction(once, color_direction="muted warm lo-fi palette")
    assert once == twice
    # Sanity: the palette text appears exactly once in the doubly-applied output.
    assert twice.lower().count("muted warm lo-fi palette") == 1


def test_strips_whitespace_around_color_direction():
    prompt = "A face."
    out = apply_color_direction(prompt, color_direction="  muted warm lo-fi palette  ")
    # Palette should appear without surrounding whitespace.
    assert "  muted warm lo-fi palette  " not in out
    assert "muted warm lo-fi palette" in out


def test_preserves_existing_punctuation_in_prompt():
    """Don't strip or alter the original prompt's content."""
    prompt = "A face, smiling; on a beach!"
    out = apply_color_direction(prompt, color_direction="emerald and gold")
    assert "A face, smiling; on a beach!" in out


# ── Composition with image-gen prefix patterns ────────────────────────────

def test_composes_with_typical_image_prompt_template():
    """Realistic case: asset-director passes a fully-built prompt with a
    playbook prefix. apply_color_direction must work on that without
    truncating or reordering it."""
    prompt = (
        "Cinematic, photorealistic. Close-up of a hand picking up a steaming "
        "ceramic cup, morning light through window."
    )
    out = apply_color_direction(prompt, color_direction="warm autumnal palette")
    assert prompt in out
    assert "warm autumnal palette" in out


# ── HIGH-3 regression: bare-token idempotency must not false-positive ──────

def test_short_palette_token_inside_unrelated_word_still_appends():
    """Regression: a 3-letter palette like 'red' was a substring of 'tired',
    'blurred', 'restored', etc. The bare-token idempotency check skipped the
    suffix on any prompt containing those words — silently producing the same
    'computed but unread' bug class this slice was meant to fix.

    The fix: idempotency must check for the full suffix string
    'Color palette: <palette>.' not the bare palette substring."""
    prompt = "blurred streetlight in a tired city"
    out = apply_color_direction(prompt, color_direction="red")
    assert prompt in out
    assert "Color palette: red." in out, (
        f"short palette 'red' must not be falsely skipped just because 'red' is "
        f"a substring of 'tired'/'blurred'; got: {out!r}"
    )


@pytest.mark.parametrize("palette,prompt_with_substring", [
    ("red",  "a tired commuter"),         # 'red' inside 'tired'
    ("warm", "lukewarm coffee on counter"),  # 'warm' inside 'lukewarm'
    ("gold", "golden retriever runs across grass"),  # 'gold' inside 'golden'
    ("dark", "a darkened kitchen, embers glowing"),  # 'dark' inside 'darkened'
    ("cool", "scoolbus in motion"),          # 'cool' inside 'scoolbus'
    ("rich", "enriched flour on a wooden counter"),  # 'rich' inside 'enriched'
])
def test_common_short_palettes_not_falsely_skipped_by_substring_match(
    palette, prompt_with_substring,
):
    """Common short palette tokens are all common-English-word substrings.
    The idempotency check must not collapse on any of them."""
    out = apply_color_direction(prompt_with_substring, color_direction=palette)
    assert f"Color palette: {palette}." in out, (
        f"palette {palette!r} dropped against prompt {prompt_with_substring!r}; got: {out!r}"
    )


def test_idempotency_still_works_when_full_suffix_already_present():
    """Confirm the corrected idempotency check still prevents duplicate
    suffixes when the helper has already run."""
    prompt = "blurred streetlight in a tired city. Color palette: red."
    out = apply_color_direction(prompt, color_direction="red")
    assert out == prompt
    assert out.count("Color palette: red.") == 1


# ── MEDIUM-3 regression: trailing-comma separator ──────────────────────────

def test_separator_handles_prompt_ending_in_comma():
    """A prompt ending in ',' should not produce '<prompt>, . Color palette: ...'
    (double-punctuation soup). The separator logic must treat trailing commas
    as a partial-clause marker and emit the suffix with a single space."""
    prompt = "cinematic, photorealistic, shallow depth of field,"
    out = apply_color_direction(prompt, color_direction="warm autumnal palette")
    assert ", . " not in out, f"trailing-comma + period sequence in: {out!r}"
    assert ",. " not in out, f"trailing-comma + period sequence in: {out!r}"
    assert "warm autumnal palette" in out
