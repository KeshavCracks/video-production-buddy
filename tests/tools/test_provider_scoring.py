from __future__ import annotations

import json
import math
from typing import Any

from lib.scoring import (
    ProductionPathScore,
    ProviderScore,
    format_ranking,
    normalize_task_context,
    score_provider,
)
from tools.base_tool import ToolStatus


class _ScoringTool:
    def __init__(
        self,
        *,
        name: str,
        provider: str = "test-provider",
        capability: str = "video_generation",
        supports: dict[str, Any] | None = None,
        best_for: list[str] | None = None,
    ) -> None:
        self.name = name
        self.provider = provider
        self.capability = capability
        self.supports = supports or {}
        self.best_for = best_for or ["cinematic trailers and premium launch films"]

    def get_info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "capability": self.capability,
            "status": "available",
            "stability": "production",
            "tier": "generate",
            "runtime": "api",
            "supports": self.supports,
            "best_for": self.best_for,
        }

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    def estimate_cost(self, _inputs: dict[str, Any]) -> float:
        return 0.1


class _NonFiniteScoringTool(_ScoringTool):
    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info.update(
            {
                "historical_success_rate": math.nan,
                "quality_score": math.inf,
                "latency_p50_seconds": -math.inf,
            }
        )
        return info

    def estimate_cost(self, _inputs: dict[str, Any]) -> float:
        return math.nan


def test_youtube_short_stock_request_does_not_imply_generated_visuals() -> None:
    context = normalize_task_context(
        None,
        capability="video_generation",
        prompt="Find stock footage for a YouTube Short about commuter routines.",
    )

    assert context["prefers_generated_visuals"] is False


def test_explicit_stock_terms_override_cinematic_generated_visual_signal() -> None:
    context = normalize_task_context(
        None,
        capability="video_generation",
        prompt="Use cinematic stock b-roll footage for a premium launch cut.",
    )

    assert context["prefers_generated_visuals"] is False


def test_premium_cinematic_bonus_handles_punctuation_adjacent_trailer_terms() -> None:
    base = _ScoringTool(name="base")
    premium = _ScoringTool(
        name="premium",
        supports={
            "native_audio": True,
            "multi_shot": True,
            "camera_direction": True,
            "lip_sync": True,
            "cinematic_quality": True,
        },
    )
    context = normalize_task_context(
        None,
        capability="video_generation",
        prompt="trailer,",
    )

    base_score = score_provider(base, context)
    premium_score = score_provider(premium, context)

    assert premium_score.task_fit > base_score.task_fit
    assert premium_score.output_quality > base_score.output_quality


def test_image_to_video_operation_sets_reference_conditioning_signal() -> None:
    context = normalize_task_context(
        None,
        capability="video_generation",
        operation="image_to_video",
        prompt="Animate this frame.",
    )

    assert context["wants_reference_conditioning"] is True


def test_image_to_video_support_improves_reference_conditioning_score() -> None:
    text_only = _ScoringTool(name="text_only", supports={})
    image_to_video = _ScoringTool(
        name="image_to_video",
        supports={"image_to_video": True},
    )
    context = normalize_task_context(
        None,
        capability="video_generation",
        operation="image_to_video",
        prompt="Animate this frame.",
    )

    text_score = score_provider(text_only, context)
    image_to_video_score = score_provider(image_to_video, context)

    assert image_to_video_score.task_fit > text_score.task_fit
    assert image_to_video_score.control > text_score.control


def test_provider_score_replaces_non_finite_tool_telemetry() -> None:
    score = score_provider(
        _NonFiniteScoringTool(name="non_finite"),
        normalize_task_context(
            None,
            capability="video_generation",
            prompt="cinematic launch trailer",
        ),
    )

    assert math.isfinite(score.weighted_score)
    assert 0.0 <= score.weighted_score <= 1.0

    payload = score.to_dict()

    for field in (
        "task_fit",
        "output_quality",
        "control",
        "reliability",
        "cost_efficiency",
        "latency",
        "continuity",
        "weighted_score",
    ):
        assert math.isfinite(payload[field])
    json.dumps(payload, allow_nan=False)


def test_provider_score_to_dict_is_strict_json_safe_for_non_finite_inputs() -> None:
    score = ProviderScore(
        tool_name="direct_provider",
        provider="direct",
        task_fit=math.nan,
        output_quality=math.inf,
        control=-math.inf,
        reliability=2.0,
        cost_efficiency=-1.0,
        latency=0.5,
        continuity=math.nan,
    )

    assert math.isfinite(score.weighted_score)
    assert 0.0 <= score.weighted_score <= 1.0

    payload = score.to_dict()

    for field in (
        "task_fit",
        "output_quality",
        "control",
        "reliability",
        "cost_efficiency",
        "latency",
        "continuity",
        "weighted_score",
    ):
        assert math.isfinite(payload[field])
        assert 0.0 <= payload[field] <= 1.0
    json.dumps(payload, allow_nan=False)


def test_production_path_score_to_dict_is_strict_json_safe_for_non_finite_inputs() -> None:
    score = ProductionPathScore(
        path_label="direct_path",
        delivery_fit=math.nan,
        quality_fit=math.inf,
        capability_confidence=-math.inf,
        fallback_integrity=2.0,
        budget_fit=-1.0,
        speed_fit=0.5,
        controllability=math.nan,
        consistency_fit=math.inf,
    )

    assert math.isfinite(score.weighted_score)
    assert 0.0 <= score.weighted_score <= 1.0

    payload = score.to_dict()

    for field in (
        "delivery_fit",
        "quality_fit",
        "capability_confidence",
        "fallback_integrity",
        "budget_fit",
        "speed_fit",
        "controllability",
        "consistency_fit",
        "weighted_score",
    ):
        assert math.isfinite(payload[field])
        assert 0.0 <= payload[field] <= 1.0
    json.dumps(payload, allow_nan=False)


def test_provider_score_display_helpers_use_sanitized_score_fields() -> None:
    score = ProviderScore(
        tool_name="display_provider",
        provider="direct",
        task_fit=math.nan,
        output_quality=math.inf,
        control=-math.inf,
        reliability=2.0,
        cost_efficiency=-1.0,
        latency=0.5,
        continuity=math.nan,
    )

    rendered = "\n".join([score.explain(), format_ranking([score])]).lower()

    assert "nan" not in rendered
    assert "inf" not in rendered
