"""Tests for lib.provenance_audit — flag uncited 'research-grounded' claims.

The auditor prevents silent self-grading bias: an agent might mark a
recommendation as 'research-grounded' without actually citing evidence. When
that claim then triggers a `verdict=CONTRADICTED, confidence=research-grounded`
override against the user's enriched_brief in bible-director, the user gets
overridden by phantom evidence.

The auditor scans every recommendation/verdict marked research-grounded and
returns demotion suggestions for any that lack citable evidence (URL in
rationale or challenge_evidence, OR cross-reference to a platform_trend /
hit_ad with a real source URL).
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.provenance_audit import audit_intelligence_provenance


# ── Helpers ─────────────────────────────────────────────────────────────────

def _minimal_brief() -> dict:
    """Build a minimal valid-shaped intelligence_brief used as a base."""
    return {
        "audience_psychographics": {
            "emotional_profile": "x", "core_pain_point": "x", "aspiration": "x",
        },
        "platform_trends": [
            {"signal": "fast cuts trending", "source": "https://example.com/post-1", "relevance": "high"},
        ],
        "hit_ads_analyzed": [
            {"title": "Acme 30s spot", "platform": "tiktok", "arc_type": "problem-solution",
             "hook_mechanic": "stat", "what_works": "opens with surprising number", "adopted": True},
        ],
        "rejected_approaches": [{"approach": "cliché X", "reason": "oversaturated"}],
        "recommendations": {
            "arc_type": {"value": "problem-solution", "confidence": "default-heuristic", "rationale": "x"},
            "pacing_model": {"value": "escalating", "confidence": "default-heuristic", "rationale": "x"},
            "hook_mechanic": {"value": "stat", "confidence": "default-heuristic", "rationale": "x"},
            "hook_window_seconds": {"value": 3, "confidence": "default-heuristic", "rationale": "x"},
            "overall_rationale": "x",
        },
    }


def _brief_with_recommendation(key: str, confidence: str, rationale: str) -> dict:
    """Return a brief whose `recommendations[key]` has the given confidence/rationale.

    Defensively reads the existing entry's ``value`` only when it is a dict
    (i.e. a real recommendation entry, not the scalar ``hook_window_seconds``
    or the string ``overall_rationale``). Otherwise substitutes a placeholder
    so the helper does not crash on those keys.
    """
    brief = _minimal_brief()
    existing = brief["recommendations"].get(key)
    value = existing["value"] if isinstance(existing, dict) and "value" in existing else "x"
    brief["recommendations"][key] = {
        "value": value,
        "confidence": confidence,
        "rationale": rationale,
    }
    return brief


# ── Recommendation-level checks ────────────────────────────────────────────

def test_research_grounded_with_url_in_rationale_passes():
    brief = _brief_with_recommendation(
        "arc_type", "research-grounded",
        rationale="Per https://adweek.com/article-2026 the dominant arc this year is...",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == [], f"URL-cited claim should not be flagged, got: {arc_flags}"


def test_research_grounded_without_url_or_cross_reference_is_flagged():
    brief = _brief_with_recommendation(
        "arc_type", "research-grounded",
        rationale="The data clearly shows this is the strongest arc.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert len(arc_flags) == 1, f"uncited research-grounded should be flagged, got: {flags}"
    flag = arc_flags[0]
    assert flag["current_confidence"] == "research-grounded"
    assert flag["suggested_confidence"] == "pattern-inferred"
    assert any(token in flag["reason"].lower() for token in ("citable", "url", "evidence", "source"))


def test_pattern_inferred_claims_are_never_flagged():
    """The auditor only inspects research-grounded claims; pattern-inferred
    is honest about its limits already."""
    brief = _brief_with_recommendation(
        "arc_type", "pattern-inferred", rationale="No citation here, but I'm not claiming research-grounded.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == [], f"pattern-inferred should not be audited, got: {arc_flags}"


def test_default_heuristic_claims_are_never_flagged():
    brief = _brief_with_recommendation(
        "arc_type", "default-heuristic", rationale="Platform norm, no specific citation.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == []


def test_research_grounded_with_http_url_passes():
    brief = _brief_with_recommendation(
        "arc_type", "research-grounded",
        rationale="See http://example.com/study for the underlying data.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == []


def test_research_grounded_with_named_publication_passes():
    """A specific named source (Adweek, Nielsen, etc.) is acceptable even
    without an explicit URL — the audit is about credibility, not URI scheme."""
    brief = _brief_with_recommendation(
        "arc_type", "research-grounded",
        rationale="Nielsen Q3 2025 brand-tracking report shows arc dominance.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == [], f"named-publication citation should pass, got: {arc_flags}"


# ── dimension_verdicts checks ──────────────────────────────────────────────

def test_contradicted_research_grounded_verdict_with_evidence_passes():
    brief = _minimal_brief()
    brief["dimension_verdicts"] = [
        {
            "dimension": "arc_type",
            "confidence": "research-grounded",
            "verdict": "CONTRADICTED",
            "challenge_evidence": "Three named campaigns from 2026: see https://example.com/campaign-list",
        },
    ]
    flags = audit_intelligence_provenance(brief)
    verdict_flags = [f for f in flags if f["path"].startswith("dimension_verdicts")]
    assert verdict_flags == [], f"verdict with evidence should pass, got: {verdict_flags}"


def test_contradicted_research_grounded_verdict_without_evidence_is_flagged():
    """A CONTRADICTED+research-grounded verdict that lacks challenge_evidence is
    the most dangerous shape — it overrides the user's brief on phantom data."""
    brief = _minimal_brief()
    brief["dimension_verdicts"] = [
        {
            "dimension": "arc_type",
            "confidence": "research-grounded",
            "verdict": "CONTRADICTED",
            # challenge_evidence missing
        },
    ]
    flags = audit_intelligence_provenance(brief)
    verdict_flags = [f for f in flags if f["path"].startswith("dimension_verdicts")]
    assert len(verdict_flags) == 1
    assert verdict_flags[0]["suggested_confidence"] == "pattern-inferred"


def test_supported_research_grounded_verdict_does_not_require_evidence():
    """Only CONTRADICTED+research-grounded triggers the override rule downstream;
    SUPPORTED verdicts agree with the user's brief and don't need challenge evidence."""
    brief = _minimal_brief()
    brief["dimension_verdicts"] = [
        {"dimension": "arc_type", "confidence": "research-grounded", "verdict": "SUPPORTED"},
    ]
    flags = audit_intelligence_provenance(brief)
    verdict_flags = [f for f in flags if f["path"].startswith("dimension_verdicts")]
    assert verdict_flags == []


def test_insufficient_data_verdict_is_never_flagged():
    brief = _minimal_brief()
    brief["dimension_verdicts"] = [
        {"dimension": "arc_type", "confidence": "research-grounded", "verdict": "INSUFFICIENT-DATA"},
    ]
    flags = audit_intelligence_provenance(brief)
    verdict_flags = [f for f in flags if f["path"].startswith("dimension_verdicts")]
    assert verdict_flags == []


# ── Output shape & guards ──────────────────────────────────────────────────

def test_flag_output_shape():
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale="No source.")
    flags = audit_intelligence_provenance(brief)
    assert flags
    flag = flags[0]
    for key in ("path", "current_confidence", "suggested_confidence", "reason"):
        assert key in flag, f"missing key '{key}' in flag: {flag}"


def test_empty_brief_returns_no_flags():
    """A minimally-honest brief (everything default-heuristic) has nothing to audit."""
    assert audit_intelligence_provenance(_minimal_brief()) == []


def test_audit_returns_one_flag_per_uncited_claim():
    """Multiple uncited research-grounded claims each produce their own flag."""
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale="x")
    brief["recommendations"]["pacing_model"] = {
        "value": "escalating", "confidence": "research-grounded", "rationale": "y",
    }
    flags = audit_intelligence_provenance(brief)
    paths = sorted(f["path"] for f in flags)
    assert "recommendations.arc_type" in paths
    assert "recommendations.pacing_model" in paths


# ── Generic-token word-boundary regression tests ───────────────────────────
#
# Bare substring matching on tokens like "report", "study", "campaign" lets
# bypass phrases like "reportedly", "studying", "campaigning" pass the audit
# even though they are NOT actual citations. The auditor must require a
# whole-word match on the generic-token allowlist.

@pytest.mark.parametrize("phrase", [
    "This arc format is reportedly popular among brands.",
    "The reporter said it's the dominant arc.",
    "I'll be reporting on results next week.",
    "We are studying alternatives now.",
    "The team is campaigning for this approach.",
    "We've been campaigning internally.",
])
def test_research_grounded_with_generic_token_inside_other_word_is_flagged(phrase):
    """'reportedly' / 'studying' / 'campaigning' contain the generic tokens but
    do NOT name an actual report / study / campaign. The auditor must catch them."""
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale=phrase)
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert len(arc_flags) == 1, (
        f"phrase {phrase!r} should be flagged (no actual citation), got: {flags}"
    )


@pytest.mark.parametrize("phrase", [
    "The report shows this approach works.",
    "A study supports this recommendation.",
    "The campaign proves the hook is best.",
    "The case study says this pattern wins.",
    "Industry reports show this is common.",
])
def test_research_grounded_with_bare_generic_source_noun_is_flagged(phrase):
    """Bare nouns like report/study/campaign are not named, verifiable evidence.

    Intelligence-director requires a named ad campaign, measurable metric, or
    dated industry report; accepting "the report says" recreates the phantom
    evidence gap this auditor exists to close.
    """
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale=phrase)
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert len(arc_flags) == 1, (
        f"phrase {phrase!r} should be flagged (generic source noun only), got: {flags}"
    )


@pytest.mark.parametrize("phrase", [
    "The 2025 Nielsen report on this category shows X.",
    "See the McKinsey study on ad effectiveness.",
    "Per the Q3 brand-tracking white paper.",
    "Three named campaigns from 2026 demonstrate X.",
    "An IAB case study covers exactly this.",
    "The 'Shot on iPhone' campaign demonstrates repeated proof-through-output framing.",
    "A category report cites 42% higher completion for this hook pattern.",
])
def test_research_grounded_with_whole_word_generic_token_passes(phrase):
    """Specific generic-source references still pass.

    The generic noun must be anchored by a named source/campaign, date/quarter,
    quoted title, or measurable metric.
    """
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale=phrase)
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == [], (
        f"phrase {phrase!r} should pass (real citation), got: {flags}"
    )


def test_research_grounded_with_named_entity_only_passes():
    """Isolate the named-entity path: rationale contains a named publication
    but NO generic tokens (no 'report', 'study', 'campaign', etc.). Verifies
    the named-entity matcher works independently of the generic-token path."""
    brief = _brief_with_recommendation(
        "arc_type", "research-grounded",
        rationale="Adweek's analysis of the category shows arc dominance.",
    )
    flags = audit_intelligence_provenance(brief)
    arc_flags = [f for f in flags if f["path"] == "recommendations.arc_type"]
    assert arc_flags == [], f"named-entity-only citation should pass, got: {arc_flags}"


# ── path_type discriminator (HIGH-2 fix) ───────────────────────────────────

def test_flag_includes_path_type_discriminator():
    """Consumers should not have to re-parse path strings. The flag carries an
    explicit path_type ('recommendation' | 'dimension_verdict') so callers
    can dispatch on a stable enum instead of string parsing."""
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale="x")
    flags = audit_intelligence_provenance(brief)
    assert flags
    assert flags[0]["path_type"] == "recommendation"

    brief2 = _minimal_brief()
    brief2["dimension_verdicts"] = [
        {"dimension": "arc_type", "confidence": "research-grounded",
         "verdict": "CONTRADICTED"},
    ]
    flags2 = audit_intelligence_provenance(brief2)
    assert flags2
    assert flags2[0]["path_type"] == "dimension_verdict"


def test_flag_emits_index_field_for_dimension_verdicts():
    """For dimension_verdict flags, emit `index` (int) so consumers don't have
    to parse the path string with regex."""
    brief = _minimal_brief()
    brief["dimension_verdicts"] = [
        {"dimension": "x", "confidence": "research-grounded", "verdict": "CONTRADICTED"},
        {"dimension": "y", "confidence": "research-grounded", "verdict": "CONTRADICTED"},
    ]
    flags = audit_intelligence_provenance(brief)
    verdict_flags = [f for f in flags if f["path_type"] == "dimension_verdict"]
    assert len(verdict_flags) == 2
    indices = sorted(f["index"] for f in verdict_flags)
    assert indices == [0, 1]


def test_flag_emits_key_field_for_recommendations():
    """For recommendation flags, emit `key` (str) so consumers don't have to
    parse the path string."""
    brief = _brief_with_recommendation("arc_type", "research-grounded", rationale="x")
    brief["recommendations"]["pacing_model"] = {
        "value": "x", "confidence": "research-grounded", "rationale": "x",
    }
    flags = audit_intelligence_provenance(brief)
    keys = sorted(f["key"] for f in flags if f["path_type"] == "recommendation")
    assert keys == ["arc_type", "pacing_model"]
