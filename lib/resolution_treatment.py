"""Thread production_bible.narrative.resolution_type into resolution-beat prompts.

The bible's ``narrative.resolution_type`` is one of four enum values that
encodes how the final beat should feel emotionally:

    "relief"            — the calm-after-the-storm exhale
    "aspiration"        — uplift, rising-action hopefulness
    "social-validation" — group / community / authentic-people endorsement
    "authority"         — confident, bold, trustworthy product framing

Until now the field was set but no downstream stage read it — the
resolution scene's image / video prompt was generic, ignoring the bible's
emotional intent. ``apply_resolution_treatment`` is the missing thread:
asset-director identifies the resolution-beat scene and wraps its prompt
through this helper so the generated frame lands on the right register.

Pattern parallels ``lib/color_direction.py``: append an idempotent suffix
when set, pass-through when None / empty / unknown enum value.
"""

from __future__ import annotations


RESOLUTION_TREATMENT_PHRASES: dict[str, str] = {
    "relief": (
        "calm, soft lighting, peaceful exhale energy, the relief that follows "
        "tension"
    ),
    "aspiration": (
        "uplifting, rising hopeful composition, expansive forward motion, "
        "cinematic aspirational energy"
    ),
    "social-validation": (
        "warm group setting, authentic real people, shared community feel, "
        "testimonial energy"
    ),
    "authority": (
        "confident hero framing, bold deliberate composition, trust-evoking "
        "product focus"
    ),
}


def apply_resolution_treatment(prompt: str, resolution_type: str | None) -> str:
    """Append a resolution-treatment suffix to ``prompt`` when ``resolution_type``
    matches a known enum value.

    Returns ``prompt`` unchanged when ``resolution_type`` is ``None``, an empty
    string, whitespace-only, or unknown — keeping legacy briefs and malformed
    bibles compatible. The bible's JSON schema validator catches enum
    violations separately; this helper is silent on them at runtime.

    Idempotent: if the treatment phrase is already present in ``prompt``
    (case-insensitive substring), the prompt is returned unchanged.
    """
    if resolution_type is None:
        return prompt

    key = resolution_type.strip().lower()
    if not key:
        return prompt

    phrase = RESOLUTION_TREATMENT_PHRASES.get(key)
    if phrase is None:
        return prompt

    suffix = f"Resolution treatment: {phrase}."

    # Idempotency: only short-circuit when the full suffix is already present.
    # An earlier version checked `phrase.lower() in prompt.lower()` which
    # could collapse if the prompt happened to contain a long phrase
    # substring; the full-suffix check is the right semantic guard.
    if suffix.lower() in prompt.lower():
        return prompt

    if not prompt:
        return suffix

    # Strip a trailing comma before testing for sentence-ending punctuation so
    # a partial-clause prompt doesn't produce ", . " soup.
    trimmed = prompt.rstrip().rstrip(",")
    separator = " " if trimmed.endswith((".", "!", "?", ";")) else ". "
    return f"{trimmed}{separator}{suffix}"
