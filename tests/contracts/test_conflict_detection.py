"""Tests for lib.conflict_detection.check_trend_knowledge_conflicts()."""

from __future__ import annotations

from lib.conflict_detection import check_trend_knowledge_conflicts


class TestNoConflictsWhenCompatible:
    """Trend instruction and knowledge avoid/overapply conditions don't overlap."""

    def test_no_conflicts_when_trends_and_knowledge_are_compatible(self) -> None:
        trend_alignments = [
            {
                "trend_id": "trend-visual-pop",
                "scene_usage": {
                    "visual_or_pacing_instruction": "Use bright saturated colors for the hook",
                },
            }
        ]

        knowledge_cards = [
            {
                "card_id": "hook.visual-contrast.001",
                "avoid_when": [
                    "The contrast would exaggerate the product claim beyond approved evidence.",
                ],
            }
        ]

        knowledge_alignments = [
            {
                "card_id": "hook.visual-contrast.001",
                "do_not_overapply": [
                    "Do not turn the hook into clickbait unrelated to the product promise.",
                ],
            }
        ]

        result = check_trend_knowledge_conflicts(
            trend_alignments, knowledge_cards, knowledge_alignments
        )

        assert result["ok"] is True
        assert result["conflicts"] == []


class TestConflictWhenTrendMatchesAvoidCondition:
    """Trend instruction overlaps with a knowledge card's avoid_when condition."""

    def test_conflict_detected_when_trend_matches_avoid_condition(self) -> None:
        trend_alignments = [
            {
                "trend_id": "trend-flash-transition",
                "scene_usage": {
                    "visual_or_pacing_instruction": (
                        "Use rapid flash transitions between unrelated shock imagery "
                        "for maximum visual contrast"
                    ),
                },
            }
        ]

        knowledge_cards = [
            {
                "card_id": "hook.visual-contrast.001",
                "avoid_when": [
                    (
                        "The contrast would exaggerate the product claim beyond approved "
                        "evidence unrelated to the product promise"
                    ),
                ],
            }
        ]

        knowledge_alignments = [
            {
                "card_id": "hook.visual-contrast.001",
            }
        ]

        result = check_trend_knowledge_conflicts(
            trend_alignments, knowledge_cards, knowledge_alignments
        )

        assert result["ok"] is False
        assert len(result["conflicts"]) >= 1
        assert result["conflicts"][0]["conflict_type"] == "trend_matches_avoid_condition"
        assert result["conflicts"][0]["trend_id"] == "trend-flash-transition"
        assert result["conflicts"][0]["card_id"] == "hook.visual-contrast.001"


class TestConflictWhenTrendTriggersOverapplyGuard:
    """Trend instruction overlaps with a knowledge alignment's do_not_overapply condition."""

    def test_conflict_detected_when_trend_triggers_overapply_guard(self) -> None:
        trend_alignments = [
            {
                "trend_id": "trend-contrast-everywhere",
                "scene_usage": {
                    "visual_or_pacing_instruction": (
                        "Apply visual contrast repeatedly across every scene "
                        "for constant visual surprise"
                    ),
                },
            }
        ]

        knowledge_cards = [
            {
                "card_id": "hook.visual-contrast.001",
            }
        ]

        knowledge_alignments = [
            {
                "card_id": "hook.visual-contrast.001",
                "do_not_overapply": [
                    (
                        "Do not turn the hook visual contrast into constant visual "
                        "surprise across every scene"
                    ),
                ],
            }
        ]

        result = check_trend_knowledge_conflicts(
            trend_alignments, knowledge_cards, knowledge_alignments
        )

        assert result["ok"] is False
        conflict_types = [c["conflict_type"] for c in result["conflicts"]]
        assert "trend_triggers_overapply_guard" in conflict_types


class TestMultipleConflictsDetected:
    """Two trends that each conflict with different cards produce multiple conflicts."""

    def test_multiple_conflicts_detected(self) -> None:
        trend_alignments = [
            {
                "trend_id": "trend-flash-transition",
                "scene_usage": {
                    "visual_or_pacing_instruction": (
                        "Use rapid flash transitions between unrelated shock imagery "
                        "for maximum visual contrast"
                    ),
                },
            },
            {
                "trend_id": "trend-contrast-everywhere",
                "scene_usage": {
                    "visual_or_pacing_instruction": (
                        "Apply visual contrast repeatedly across every scene "
                        "for constant visual surprise"
                    ),
                },
            },
        ]

        knowledge_cards = [
            {
                "card_id": "hook.visual-contrast.001",
                "avoid_when": [
                    (
                        "The contrast would exaggerate the product claim beyond approved "
                        "evidence unrelated to the product promise"
                    ),
                ],
            },
            {
                "card_id": "visual_rhetoric.depth-layering.001",
                "avoid_when": [
                    "Do not apply rapid flash transitions between unrelated shock imagery "
                    "for visual overload",
                ],
            },
        ]

        knowledge_alignments = [
            {
                "card_id": "hook.visual-contrast.001",
                "do_not_overapply": [
                    (
                        "Do not turn the hook visual contrast into constant visual "
                        "surprise across every scene"
                    ),
                ],
            },
            {
                "card_id": "visual_rhetoric.depth-layering.001",
            },
        ]

        result = check_trend_knowledge_conflicts(
            trend_alignments, knowledge_cards, knowledge_alignments
        )

        assert result["ok"] is False
        assert result["summary"]["conflicts_found"] >= 2


class TestEmptyInputsReturnOk:
    """Empty trend_alignments or knowledge_alignments returns ok: True."""

    def test_empty_trend_alignments_returns_ok(self) -> None:
        result = check_trend_knowledge_conflicts(
            trend_alignments=[],
            knowledge_cards=[{"card_id": "hook.visual-contrast.001"}],
            knowledge_alignments=[{"card_id": "hook.visual-contrast.001"}],
        )

        assert result["ok"] is True
        assert result["conflicts"] == []
        assert result["summary"]["trends_checked"] == 0

    def test_empty_knowledge_alignments_returns_ok(self) -> None:
        result = check_trend_knowledge_conflicts(
            trend_alignments=[
                {
                    "trend_id": "trend-visual-pop",
                    "scene_usage": {
                        "visual_or_pacing_instruction": "Use bright saturated colors",
                    },
                }
            ],
            knowledge_cards=[{"card_id": "hook.visual-contrast.001"}],
            knowledge_alignments=[],
        )

        assert result["ok"] is True
        assert result["conflicts"] == []
        assert result["summary"]["knowledge_cards_checked"] == 0

    def test_both_empty_returns_ok(self) -> None:
        result = check_trend_knowledge_conflicts(
            trend_alignments=[],
            knowledge_cards=[],
            knowledge_alignments=[],
        )

        assert result["ok"] is True
        assert result["conflicts"] == []
