"""Audit an intelligence_brief for uncited 'research-grounded' claims.

Bible-director's Step 1 (Override rule) only replaces an enriched_brief field
when the matching ``dimension_verdicts`` entry is ``CONTRADICTED`` AND
``confidence == "research-grounded"``. The rule is sound — but it relies on
the agent grading its own confidence honestly. An agent that marks a claim
"research-grounded" without citing real evidence can override the user's
brief with phantom data.

This auditor is a runtime guard. It scans every recommendation and
dimension_verdict marked ``research-grounded`` and returns demotion
suggestions for any that lack citable evidence. Bible-director consumes the
result before applying overrides; flagged claims fall back to
``pattern-inferred``, which still informs the bible but no longer overrides
the user's hypothesis.

The audit is intentionally permissive, but it still requires specificity. We
accept an explicit URL (http/https), a known named source, or a generic source
noun such as "report" / "study" / "campaign" only when the phrase is anchored
by a date, quoted title, or measurable metric. We flag "the report says X"
because it names no verifiable report.
"""

from __future__ import annotations

import re
from typing import Any


_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

# Named-entity tokens carry their own credibility without an explicit URL.
# These are specific brand / firm names. They are matched as tokens so short
# acronyms like IAB do not pass inside ordinary words such as "reliable".
_NAMED_ENTITY_TOKENS = (
    # Publications
    "adweek", "ad age", "marketing week", "campaign magazine", "the drum",
    "marketing dive", "wsj", "nyt", "ft.com", "bloomberg",
    # Research / analytics firms
    "nielsen", "kantar", "comscore", "similarweb", "gartner", "forrester",
    "mckinsey", "deloitte", "iab",
    # Platform first-party data
    "tiktok creative center", "youtube ads library", "meta ad library",
    "facebook ad library", "google trends",
)

# Generic noun signals — must match as whole words, otherwise prose like
# "reportedly", "studying", "campaigning" silently bypasses the audit even
# though it names no actual report / study / campaign.
_GENERIC_TOKEN_RE = re.compile(
    r"\b(?:report|reports|study|studies|white\s+paper|case\s+study|campaign|campaigns)\b",
    re.IGNORECASE,
)
_SOURCE_SPECIFICITY_RE = re.compile(
    r"\b(?:19|20)\d{2}\b"
    r"|\bq[1-4]\b"
    r"|\b\d+(?:\.\d+)?\s*(?:%|\b(?:percent|points?|x|times|seconds?|secs?"
    r"|minutes?|mins?|views?|clicks?|conversions?|lift|higher|lower)\b)",
    re.IGNORECASE,
)
_QUOTED_TITLE_RE = re.compile(r"""["'“‘][^"'“”‘’]{3,}["'”’]""")


def _has_named_entity_token(text: str) -> bool:
    lowered = text.lower()
    for token in _NAMED_ENTITY_TOKENS:
        pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])"
        if re.search(pattern, lowered):
            return True
    return False


def _has_citable_evidence(text: str) -> bool:
    """Return True iff ``text`` contains an explicit URL, a named-entity token,
    or a whole-word generic-noun signal ('report', 'study', 'campaign', etc.)
    anchored by a source-specificity signal.

    Empty or whitespace-only text always returns False. The URL test is liberal
    (accepts any http(s)://...). Named-entity tokens use case-insensitive
    substring matching. Generic-noun signals require both word-boundary
    matching and a date/quarter, metric, or quoted title so 'reportedly',
    'studying', 'campaigning', and bare phrases like 'the report says' do NOT
    pass."""
    if not text or not text.strip():
        return False
    if _URL_PATTERN.search(text):
        return True
    if _has_named_entity_token(text):
        return True
    if _GENERIC_TOKEN_RE.search(text) is None:
        return False
    return (
        _SOURCE_SPECIFICITY_RE.search(text) is not None
        or _QUOTED_TITLE_RE.search(text) is not None
    )


def audit_intelligence_provenance(intelligence_brief: dict[str, Any]) -> list[dict[str, Any]]:
    """Return demotion suggestions for research-grounded claims that lack provenance.

    Inspects two surfaces:
      * ``recommendations.<key>`` where ``confidence == "research-grounded"`` and
        the ``rationale`` lacks citable evidence. Top-level recommendation keys
        only — the nested ``editing_rhythm_by_beat`` map (per-beat dicts whose
        outer dict has no ``confidence`` field) is intentionally NOT recursed
        into. Bible-director's Step 1 override rule does not consult per-beat
        editing_rhythm confidence directly, so the audit gap is bounded; this
        will be revisited if a downstream stage starts overriding on it.
      * ``dimension_verdicts[]`` where ``verdict == "CONTRADICTED"`` AND
        ``confidence == "research-grounded"`` AND ``challenge_evidence`` lacks
        citable evidence (or is missing). SUPPORTED / INSUFFICIENT-DATA verdicts
        are not audited because they don't trigger the override rule downstream.

    Returns ``list[{path, path_type, key|index, current_confidence,
    suggested_confidence, reason}]``. Each flag carries a ``path_type``
    discriminator (``"recommendation"`` or ``"dimension_verdict"``) plus the
    structured locator (``key`` or ``index``) so consumers don't have to
    re-parse the human-readable ``path`` string. Empty list = nothing to
    demote. Demotion target is always ``pattern-inferred``.
    """
    flags: list[dict[str, Any]] = []

    recommendations = intelligence_brief.get("recommendations", {}) or {}
    for key, entry in recommendations.items():
        if not isinstance(entry, dict):
            continue
        if entry.get("confidence") != "research-grounded":
            continue
        rationale = str(entry.get("rationale", ""))
        if _has_citable_evidence(rationale):
            continue
        # Emit both the human-readable `path` (audit trail) and structured
        # fields (`path_type`, `key`) so consumers don't have to re-parse the
        # string. The string format is documented but the structured fields
        # are the stable contract.
        flags.append({
            "path": f"recommendations.{key}",
            "path_type": "recommendation",
            "key": key,
            "current_confidence": "research-grounded",
            "suggested_confidence": "pattern-inferred",
            "reason": (
                "rationale lacks citable evidence (no URL and no named publication, "
                "report, or campaign reference); cannot justify research-grounded tier"
            ),
        })

    for idx, verdict_entry in enumerate(intelligence_brief.get("dimension_verdicts", []) or []):
        if not isinstance(verdict_entry, dict):
            continue
        if verdict_entry.get("verdict") != "CONTRADICTED":
            continue
        if verdict_entry.get("confidence") != "research-grounded":
            continue
        evidence = str(verdict_entry.get("challenge_evidence", ""))
        if _has_citable_evidence(evidence):
            continue
        dim = verdict_entry.get("dimension", "?")
        flags.append({
            "path": f"dimension_verdicts[{idx}]",
            "path_type": "dimension_verdict",
            "index": idx,
            "current_confidence": "research-grounded",
            "suggested_confidence": "pattern-inferred",
            "reason": (
                f"CONTRADICTED verdict on '{dim}' lacks citable challenge_evidence; "
                "downstream override rule requires named, verifiable evidence"
            ),
        })

    return flags
