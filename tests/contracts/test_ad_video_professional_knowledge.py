"""Professional ad-video knowledge retrieval and threading contracts."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from schemas.artifacts import validate_artifact


def _knowledge_alignment_block() -> dict:
    return {
        "selected_card_ids": ["hook.visual-contrast.001"],
        "alignments": [
            {
                "card_id": "hook.visual-contrast.001",
                "domain": "hook_mechanic",
                "summary": "Use visible contrast in the opening second to create a fast comprehension gap.",
                "source_ref": "knowledge_alignment:hook.visual-contrast.001",
                "application_targets": ["hook", "script", "scene_plan", "visual"],
                "target_beat": "hook",
                "script_usage": {
                    "required_section_ids": ["hook"],
                    "source_ref": "knowledge_alignment:hook.visual-contrast.001",
                    "usage_note": "The hook copy must create a visible before/after gap without explaining the whole product.",
                },
                "scene_usage": {
                    "required": True,
                    "required_scene_count": 1,
                    "visual_or_pacing_instruction": "Open on a visual contradiction or before/after contrast that resolves into the product promise.",
                },
                "do_not_overapply": [
                    "Do not turn the hook into clickbait unrelated to the product promise.",
                ],
            }
        ],
    }


def test_ad_video_knowledge_cards_validate_and_cover_core_domains() -> None:
    from lib.ad_knowledge import load_ad_knowledge_cards

    cards = load_ad_knowledge_cards()
    ids = [card["card_id"] for card in cards]
    domains = {card["domain"] for card in cards}

    assert len(cards) >= 6
    assert len(ids) == len(set(ids))
    assert {
        "hook_mechanic",
        "emotional_rhythm",
        "positioning",
        "proof_logic",
        "visual_rhetoric",
        "commercial_compliance",
    }.issubset(domains)


def test_ad_video_knowledge_card_content_hash_detects_tampering(tmp_path) -> None:
    from lib.ad_knowledge import load_ad_knowledge_cards

    card = deepcopy(load_ad_knowledge_cards()[0])
    card["summary"] = card["summary"] + " Tampered."
    (tmp_path / "tampered.json").write_text(json.dumps(card), encoding="utf-8")

    with pytest.raises(ValueError, match="content_hash mismatch"):
        load_ad_knowledge_cards(tmp_path)


def test_bm25_retrieval_returns_relevant_cards_with_stable_source_refs() -> None:
    from lib.ad_knowledge import retrieve_ad_knowledge
    from tests.qa.test_artifact_chain import INTELLIGENCE_BRIEF_VALID

    result = retrieve_ad_knowledge(
        {
            "product_category": "smartphone camera",
            "platform": "tiktok",
            "audience": "global photography enthusiasts",
            "objectives": ["premium launch", "visual contrast hook"],
            "validation_targets": ["hook_mechanic", "emotional_rhythm", "proof_logic"],
            "backend": "auto",
        }
    )

    assert result["retrieval_backend"] == "bm25"
    assert "backend_used" not in result
    assert "retrieved_cards" not in result
    assert result["cards_used"]
    assert any(card["domain"] == "hook_mechanic" for card in result["cards_used"])
    assert any(card["domain"] == "emotional_rhythm" for card in result["cards_used"])
    assert all(card["source_ref"].startswith("knowledge_alignment:") for card in result["cards_used"])
    assert all(0 < card["relevance_score"] <= 1 for card in result["cards_used"])

    brief = deepcopy(INTELLIGENCE_BRIEF_VALID)
    brief["professional_knowledge"] = result
    validate_artifact("intelligence_brief", brief)


def test_embedding_backend_request_falls_back_to_bm25_with_warning() -> None:
    from tools.analysis.ad_knowledge_retriever import AdKnowledgeRetriever

    result = AdKnowledgeRetriever().execute(
        {
            "product_category": "productivity app",
            "platform": "tiktok",
            "audience": "busy professionals",
            "objectives": ["problem-solution launch"],
            "validation_targets": ["hook_mechanic"],
            "backend": "embedding",
        }
    )

    assert result.success is True
    assert result.data["retrieval_backend"] == "bm25"
    assert "backend_used" not in result.data
    assert "retrieved_cards" not in result.data
    assert any("Embedding backend" in warning for warning in result.data["warnings"])


def test_intelligence_brief_schema_requires_professional_knowledge_block() -> None:
    from tests.qa.test_artifact_chain import INTELLIGENCE_BRIEF_VALID

    validate_artifact("intelligence_brief", deepcopy(INTELLIGENCE_BRIEF_VALID))

    missing = deepcopy(INTELLIGENCE_BRIEF_VALID)
    del missing["professional_knowledge"]
    with pytest.raises(Exception):
        validate_artifact("intelligence_brief", missing)

    bad = deepcopy(INTELLIGENCE_BRIEF_VALID)
    bad["professional_knowledge"]["cards_used"][0]["source_ref"] = "trend_alignment:wrong"
    with pytest.raises(Exception):
        validate_artifact("intelligence_brief", bad)


def test_production_bible_schema_requires_knowledge_alignment_block() -> None:
    from tests.qa.test_artifact_chain import PRODUCTION_BIBLE_VALID

    validate_artifact("production_bible", deepcopy(PRODUCTION_BIBLE_VALID))

    missing = deepcopy(PRODUCTION_BIBLE_VALID)
    del missing["intelligence"]["knowledge_alignment"]
    with pytest.raises(Exception):
        validate_artifact("production_bible", missing)

    bad = deepcopy(PRODUCTION_BIBLE_VALID)
    bad["intelligence"]["knowledge_alignment"]["alignments"][0]["source_ref"] = "trend_alignment:wrong"
    with pytest.raises(Exception):
        validate_artifact("production_bible", bad)


def test_knowledge_alignment_requires_script_and_scene_threading() -> None:
    from lib.knowledge_alignment import check_ad_video_planning_knowledge_alignment

    bible = {"intelligence": {"knowledge_alignment": _knowledge_alignment_block()}}
    script = {
        "sections": [
            {
                "id": "hook",
                "beat": "hook",
                "text": "Two photos, same night, only one remembers the color.",
            }
        ]
    }
    scene_plan = {
        "scenes": [
            {
                "id": "scene-hook",
                "beat": "hook",
                "knowledge_alignment_refs": ["knowledge_alignment:hook.visual-contrast.001"],
                "knowledge_alignment_notes": "Before/after night color contrast lands in the opening second.",
            }
        ]
    }

    report = check_ad_video_planning_knowledge_alignment(bible, script, scene_plan)

    assert report["ok"] is False
    assert any(issue["kind"] == "missing_knowledge_source_ref" for issue in report["issues"])

    script["sections"][0]["source_ref"] = "knowledge_alignment:hook.visual-contrast.001"
    assert check_ad_video_planning_knowledge_alignment(bible, script, scene_plan)["ok"] is True

    scene_plan["scenes"][0]["knowledge_alignment_refs"] = ["hook.visual-contrast.001"]
    report = check_ad_video_planning_knowledge_alignment(bible, script, scene_plan)
    assert report["ok"] is False
    assert any(issue["kind"] == "missing_scene_knowledge_alignment" for issue in report["issues"])

    scene_plan["scenes"][0]["knowledge_alignment_refs"] = []
    report = check_ad_video_planning_knowledge_alignment(bible, script, scene_plan)
    assert report["ok"] is False
    assert any(issue["kind"] == "missing_scene_knowledge_alignment" for issue in report["issues"])


def test_knowledge_alignment_rejects_mismatched_nested_source_refs() -> None:
    from lib.knowledge_alignment import check_ad_video_planning_knowledge_alignment

    bible = {"intelligence": {"knowledge_alignment": _knowledge_alignment_block()}}
    bible["intelligence"]["knowledge_alignment"]["alignments"][0]["script_usage"][
        "source_ref"
    ] = "knowledge_alignment:proof.specific-demonstration.001"
    wrong_ref = "knowledge_alignment:proof.specific-demonstration.001"
    script = {
        "sections": [
            {
                "id": "hook",
                "beat": "hook",
                "text": "Two photos, same night, only one remembers the color.",
                "source_ref": wrong_ref,
            }
        ]
    }
    scene_plan = {
        "scenes": [
            {
                "id": "scene-hook",
                "beat": "hook",
                "knowledge_alignment_refs": [wrong_ref],
                "knowledge_alignment_notes": "Before/after night color contrast lands in the opening second.",
            }
        ]
    }

    report = check_ad_video_planning_knowledge_alignment(bible, script, scene_plan)

    assert report["ok"] is False
    assert any(issue["kind"] == "inconsistent_knowledge_source_ref" for issue in report["issues"])
    assert any(
        issue["kind"] == "missing_knowledge_source_ref"
        and issue["expected_ref"] == "knowledge_alignment:hook.visual-contrast.001"
        for issue in report["issues"]
    )


def test_scene_plan_rejects_bare_knowledge_alignment_refs() -> None:
    scene_plan = {
        "version": "1.0",
        "style_mode": "animated",
        "total_duration_seconds": 4,
        "scenes": [
            {
                "id": "scene-hook",
                "type": "generated",
                "description": "Native overlay text lands on the first visual beat.",
                "start_seconds": 0,
                "end_seconds": 4,
                "beat": "hook",
                "product_visibility": "none",
                "product_reference_required": False,
                "core": True,
                "motion_required": True,
                "knowledge_alignment_refs": ["knowledge_alignment:hook.visual-contrast.001"],
                "knowledge_alignment_notes": "Opening scene uses a visible before/after contrast without turning into clickbait.",
            }
        ],
    }

    validate_artifact("scene_plan", deepcopy(scene_plan), pipeline_type="ad-video")

    bad = deepcopy(scene_plan)
    bad["scenes"][0]["knowledge_alignment_refs"] = ["hook.visual-contrast.001"]
    with pytest.raises(Exception):
        validate_artifact("scene_plan", bad, pipeline_type="ad-video")
