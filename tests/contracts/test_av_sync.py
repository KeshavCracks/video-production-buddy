"""Tests for lib.av_sync — thread bible av_sync_notes into music-gen prompts.

production_bible.audio.av_sync_notes is a free-form prose field set by
bible-director (e.g. "Music swell on B3 solution reveal" or "snare on the
CTA word"). Until now it was set but never read — the music-gen prompt
ignored it, so synced beats had to be re-engineered post-hoc in the mix
instead of being baked into the generated track.

This module is the missing thread: asset-director's music-gen step appends
the av_sync_notes via ``apply_av_sync_notes`` so MiniMax (and similar
prompt-conditioned music models) can attempt the sync at generation time.

Pattern parallels lib.color_direction and lib.resolution_treatment.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.av_sync import apply_av_sync_notes


# ── Pass-through cases ─────────────────────────────────────────────────────

def test_returns_prompt_unchanged_when_av_sync_notes_is_none():
    prompt = "60s instrumental, lo-fi hip-hop."
    assert apply_av_sync_notes(prompt, av_sync_notes=None) == prompt


def test_returns_prompt_unchanged_when_av_sync_notes_is_empty_string():
    prompt = "60s instrumental, lo-fi hip-hop."
    assert apply_av_sync_notes(prompt, av_sync_notes="") == prompt


def test_returns_prompt_unchanged_when_av_sync_notes_is_whitespace_only():
    prompt = "60s instrumental, lo-fi hip-hop."
    assert apply_av_sync_notes(prompt, av_sync_notes="  \n\t  ") == prompt


# ── Append cases ───────────────────────────────────────────────────────────

def test_appends_sync_notes_suffix_when_set():
    prompt = "60s instrumental, lo-fi hip-hop."
    out = apply_av_sync_notes(prompt, av_sync_notes="Music swell on B3 solution reveal")
    assert prompt in out
    assert "Music swell on B3 solution reveal" in out
    assert "sync notes" in out.lower() or "sync" in out.lower()


def test_handles_empty_prompt():
    out = apply_av_sync_notes("", av_sync_notes="snare on the CTA word")
    assert "snare on the CTA word" in out


def test_strips_whitespace_around_av_sync_notes():
    prompt = "60s music."
    out = apply_av_sync_notes(prompt, av_sync_notes="  drop at 0:35  ")
    assert "  drop at 0:35  " not in out
    assert "drop at 0:35" in out


def test_preserves_existing_punctuation_in_prompt():
    prompt = "Energetic, building, cinematic; arc: build → peak → resolve!"
    out = apply_av_sync_notes(prompt, av_sync_notes="Music swell at 35s")
    assert prompt in out


# ── HIGH-3 regression: idempotency on full suffix, not bare token ──────────

def test_idempotent_on_full_suffix():
    """Re-applying with the same notes must not duplicate the suffix."""
    prompt = "Lo-fi loop."
    once = apply_av_sync_notes(prompt, av_sync_notes="snare on CTA")
    twice = apply_av_sync_notes(once, av_sync_notes="snare on CTA")
    assert once == twice
    assert twice.lower().count("snare on cta") == 1


def test_short_token_not_falsely_skipped_by_substring_match():
    """Regression mirroring the color_direction HIGH-3: a short notes value
    that happens to be a substring of an unrelated word in the prompt must
    NOT cause the suffix to be silently skipped. Idempotency must check the
    full suffix string, not the bare notes token."""
    prompt = "instrumental snareless ambient pad"  # contains 'snare' as substring of 'snareless'
    out = apply_av_sync_notes(prompt, av_sync_notes="snare")
    assert prompt in out
    assert "Sync notes: snare." in out, (
        f"short notes 'snare' must not be falsely skipped against 'snareless'; got: {out!r}"
    )


# ── MEDIUM-3 regression: trailing-comma separator ──────────────────────────

def test_separator_handles_prompt_ending_in_comma():
    """A prompt ending in ',' must not produce '<prompt>, . Sync notes: ...'
    — same fix as apply_color_direction and apply_resolution_treatment."""
    prompt = "lo-fi, calm, slow,"
    out = apply_av_sync_notes(prompt, av_sync_notes="snare on CTA")
    assert ", . " not in out, f"trailing-comma + period in: {out!r}"
    assert ",. " not in out, f"trailing-comma + period in: {out!r}"
    assert "snare on CTA" in out


# ── Composition with realistic music-gen prompt template ──────────────────

def test_composes_with_typical_music_prompt_template():
    """Realistic case: asset-director passes a fully-built prompt with
    base mood + intensity arc summary already appended. apply_av_sync_notes
    must work without truncating or reordering anything that came before."""
    prompt = (
        "60s instrumental, lo-fi hip-hop, focus-time texture. "
        "Arc: build from low energy to high energy by 35s, peak at 35-48s, "
        "resolve to mid energy by 60s."
    )
    out = apply_av_sync_notes(
        prompt,
        av_sync_notes="Music swell on the solution reveal at ~38s; downbeat on CTA word",
    )
    assert prompt in out
    assert "Music swell on the solution reveal at ~38s; downbeat on CTA word" in out
