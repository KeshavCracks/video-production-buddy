"""Thread production_bible.visual.color_direction into generation prompts.

The bible's ``visual.color_direction`` (e.g. ``"muted warm lo-fi palette"``)
constrains the visual treatment of generated assets — image-gen and video-gen
should generate within that palette so every still and clip lands on-brief.
Until now the field was set but never read; image-gen prompts ignored it
and the model produced its default-palette output regardless.

This module is the missing thread. ``apply_color_direction`` appends an
idempotent palette annotation to a prompt when ``color_direction`` is set,
or returns the prompt unchanged when it isn't (legacy briefs).

The annotation is a one-line "Color palette: ..." suffix joined to the
prompt with ". " — enough for diffusion-style models to pick up the palette
constraint without rewriting the original instruction.
"""

from __future__ import annotations


def apply_color_direction(prompt: str, color_direction: str | None) -> str:
    """Append a color-palette suffix to ``prompt`` when ``color_direction`` is set.

    Returns ``prompt`` unchanged when ``color_direction`` is ``None``, an empty
    string, or whitespace-only — keeping legacy briefs compatible.

    Idempotent: if the trimmed ``color_direction`` substring is already
    present in ``prompt`` (case-insensitive), the prompt is returned unchanged
    so callers can re-apply safely (e.g. when scene_description is built up
    incrementally and palette gets re-merged).
    """
    if color_direction is None:
        return prompt

    palette = color_direction.strip()
    if not palette:
        return prompt

    suffix = f"Color palette: {palette}."

    # Idempotency: only short-circuit when the full suffix is already present.
    # An earlier version checked `palette.lower() in prompt.lower()`, which
    # falsely triggered on prompts containing the palette token as a substring
    # of an unrelated word ("red" inside "tired", "warm" inside "lukewarm",
    # "gold" inside "golden", etc.) — silently dropping the suffix on common
    # short palettes. The full-suffix check is unique enough to avoid that.
    if suffix.lower() in prompt.lower():
        return prompt

    if not prompt:
        return suffix

    # Join with ". " so the suffix reads as a separate clause on diffusion-style
    # parsers. A trailing comma is treated as a partial-clause marker — strip
    # the comma before testing for sentence-ending punctuation so we don't
    # produce ", . " soup.
    trimmed = prompt.rstrip().rstrip(",")
    separator = " " if trimmed.endswith((".", "!", "?", ";")) else ". "
    return f"{trimmed}{separator}{suffix}"
