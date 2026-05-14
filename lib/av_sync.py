"""Thread production_bible.audio.av_sync_notes into music-gen prompts.

The bible's ``audio.av_sync_notes`` is a free-form prose hint about
audio-visual sync points (e.g. ``"Music swell on B3 solution reveal"`` or
``"snare on the CTA word"``). Until now it was set but never read — the
music-gen prompt ignored it, so synced beats had to be re-engineered
post-hoc in the mix instead of being baked into the generated track.

``apply_av_sync_notes`` is the missing thread: asset-director's music-gen
step appends the notes via this helper so prompt-conditioned music models
can attempt the sync at generation time.

Pattern parallels ``lib/color_direction.py`` and ``lib/resolution_treatment.py``:
append an idempotent suffix when set, pass-through when None / empty /
whitespace. Idempotency uses full-suffix matching (not bare-token) to avoid
the false-positive class found in the previous review (HIGH-3).
"""

from __future__ import annotations


def apply_av_sync_notes(prompt: str, av_sync_notes: str | None) -> str:
    """Append a sync-notes suffix to ``prompt`` when ``av_sync_notes`` is set.

    Returns ``prompt`` unchanged when ``av_sync_notes`` is ``None``, an empty
    string, or whitespace-only — keeping legacy briefs compatible.

    Idempotent: the full ``Sync notes: <notes>.`` suffix is checked
    case-insensitively against the prompt; if already present, the prompt is
    returned unchanged. Checking the full suffix (not the bare notes token)
    avoids false positives where a short notes value is a substring of an
    unrelated word in the prompt (e.g. notes ``"snare"`` against prompt
    ``"snareless ambient pad"``).
    """
    if av_sync_notes is None:
        return prompt

    notes = av_sync_notes.strip()
    if not notes:
        return prompt

    suffix = f"Sync notes: {notes}."

    if suffix.lower() in prompt.lower():
        return prompt

    if not prompt:
        return suffix

    # Strip a trailing comma before testing for sentence-ending punctuation
    # so partial-clause prompts don't produce ", . " soup.
    trimmed = prompt.rstrip().rstrip(",")
    separator = " " if trimmed.endswith((".", "!", "?", ";")) else ". "
    return f"{trimmed}{separator}{suffix}"
