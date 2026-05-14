"""Tests for cross-domain co-presence checks in
lib.knowledge_alignment.check_ad_video_planning_knowledge_alignment()."""

from __future__ import annotations

from lib.knowledge_alignment import check_ad_video_planning_knowledge_alignment


def _production_bible(
    alignments: list[dict],
    selected_card_ids: list[str] | None = None,
) -> dict:
    """Build a minimal production_bible with the given knowledge alignment entries."""
    if selected_card_ids is None:
        selected_card_ids = [a["card_id"] for a in alignments]
    return {
        "intelligence": {
            "knowledge_alignment": {
                "selected_card_ids": selected_card_ids,
                "alignments": alignments,
            }
        }
    }


def _scene_plan(scenes: list[dict]) -> dict:
    """Build a minimal scene_plan."""
    return {"scenes": scenes}


MINIMAL_SCRIPT: dict = {"sections": []}


class TestCoPresentCardsPass:
    """Cards with cross_domain_notes that reference each other and share
    application_targets must co-occur in at least one scene."""

    def test_co_present_cards_pass(self) -> None:
        card_a = "hook_mechanic.contrast-gap.001"
        card_b = "emotional_rhythm.tension-release.001"

        alignments = [
            {
                "card_id": card_a,
                "domain": "hook_mechanic",
                "source_ref": f"knowledge_alignment:{card_a}",
                "application_targets": ["hook", "visual"],
                "cross_domain_notes": [
                    {"domain": "emotional_rhythm", "note": "Contrast gap should align with tension peak."},
                ],
            },
            {
                "card_id": card_b,
                "domain": "emotional_rhythm",
                "source_ref": f"knowledge_alignment:{card_b}",
                "application_targets": ["hook", "visual"],
                "cross_domain_notes": [
                    {"domain": "hook_mechanic", "note": "Tension peak should land on the contrast gap."},
                ],
            },
        ]

        production_bible = _production_bible(alignments)
        scene_plan = _scene_plan([
            {
                "scene_id": "scene-01",
                "knowledge_alignment_refs": [
                    f"knowledge_alignment:{card_a}",
                    f"knowledge_alignment:{card_b}",
                ],
                "knowledge_alignment_notes": "Contrast gap at tension peak.",
            },
        ])

        result = check_ad_video_planning_knowledge_alignment(
            production_bible, MINIMAL_SCRIPT, scene_plan
        )

        cross_domain_issues = [
            i for i in result["issues"]
            if i["kind"] == "missing_cross_domain_co_presence"
        ]
        assert cross_domain_issues == []


class TestMissingCoPresenceDetected:
    """When scenes reference only one of two cross-domain partners,
    a missing_cross_domain_co_presence issue is raised."""

    def test_missing_co_presence_detected(self) -> None:
        card_a = "hook_mechanic.contrast-gap.001"
        card_b = "emotional_rhythm.tension-release.001"

        alignments = [
            {
                "card_id": card_a,
                "domain": "hook_mechanic",
                "source_ref": f"knowledge_alignment:{card_a}",
                "application_targets": ["hook", "visual"],
                "cross_domain_notes": [
                    {"domain": "emotional_rhythm", "note": "Contrast gap should align with tension peak."},
                ],
            },
            {
                "card_id": card_b,
                "domain": "emotional_rhythm",
                "source_ref": f"knowledge_alignment:{card_b}",
                "application_targets": ["hook", "visual"],
                "cross_domain_notes": [
                    {"domain": "hook_mechanic", "note": "Tension peak should land on the contrast gap."},
                ],
            },
        ]

        production_bible = _production_bible(alignments)
        # Scenes only reference card_a, not card_b
        scene_plan = _scene_plan([
            {
                "scene_id": "scene-01",
                "knowledge_alignment_refs": [
                    f"knowledge_alignment:{card_a}",
                ],
                "knowledge_alignment_notes": "Contrast gap opener.",
            },
        ])

        result = check_ad_video_planning_knowledge_alignment(
            production_bible, MINIMAL_SCRIPT, scene_plan
        )

        cross_domain_issues = [
            i for i in result["issues"]
            if i["kind"] == "missing_cross_domain_co_presence"
        ]
        assert len(cross_domain_issues) >= 1
        pair_ids = {
            (issue["card_id"], issue["partner_card_id"])
            for issue in cross_domain_issues
        }
        assert (card_a, card_b) in pair_ids or (card_b, card_a) in pair_ids


class TestNoCrossDomainNotesSkipped:
    """Entries without cross_domain_notes field should not trigger co-presence checks."""

    def test_no_cross_domain_notes_skipped(self) -> None:
        card_a = "hook_mechanic.contrast-gap.001"

        alignments = [
            {
                "card_id": card_a,
                "domain": "hook_mechanic",
                "source_ref": f"knowledge_alignment:{card_a}",
                "application_targets": ["hook", "visual"],
                # No cross_domain_notes field at all
            }
        ]

        production_bible = _production_bible(alignments)
        scene_plan = _scene_plan([
            {
                "scene_id": "scene-01",
                "knowledge_alignment_refs": [
                    f"knowledge_alignment:{card_a}",
                ],
                "knowledge_alignment_notes": "Contrast gap opener.",
            },
        ])

        result = check_ad_video_planning_knowledge_alignment(
            production_bible, MINIMAL_SCRIPT, scene_plan
        )

        cross_domain_issues = [
            i for i in result["issues"]
            if i["kind"] == "missing_cross_domain_co_presence"
        ]
        assert cross_domain_issues == []


class TestNonOverlappingTargetsNoCheck:
    """Two cards with cross_domain_notes referencing each other but completely
    disjoint application_targets should NOT require co-presence."""

    def test_non_overlapping_targets_no_check(self) -> None:
        card_a = "hook_mechanic.contrast-gap.001"
        card_b = "emotional_rhythm.tension-release.001"

        alignments = [
            {
                "card_id": card_a,
                "domain": "hook_mechanic",
                "source_ref": f"knowledge_alignment:{card_a}",
                "application_targets": ["hook", "visual"],
                "cross_domain_notes": [
                    {"domain": "emotional_rhythm", "note": "Contrast gap should consider emotional arc."},
                ],
            },
            {
                "card_id": card_b,
                "domain": "emotional_rhythm",
                "source_ref": f"knowledge_alignment:{card_b}",
                "application_targets": ["cta_brand", "script"],
                "cross_domain_notes": [
                    {"domain": "hook_mechanic", "note": "Emotional arc starts from the hook."},
                ],
            },
        ]

        production_bible = _production_bible(alignments)
        # Scene only references card_a; card_b is not in any scene
        scene_plan = _scene_plan([
            {
                "scene_id": "scene-01",
                "knowledge_alignment_refs": [
                    f"knowledge_alignment:{card_a}",
                ],
                "knowledge_alignment_notes": "Contrast gap opener.",
            },
        ])

        result = check_ad_video_planning_knowledge_alignment(
            production_bible, MINIMAL_SCRIPT, scene_plan
        )

        cross_domain_issues = [
            i for i in result["issues"]
            if i["kind"] == "missing_cross_domain_co_presence"
        ]
        assert cross_domain_issues == []
