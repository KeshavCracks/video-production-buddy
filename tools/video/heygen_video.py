"""HeyGen-backed cloud video generation."""

from __future__ import annotations

import os
import time
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)
from tools.video._shared import (
    HEYGEN_PROVIDERS,
    estimate_quality_cost,
    estimate_speed_runtime,
    generate_heygen_video,
    require_generated_video_output_path,
    validate_video_operation,
)


class HeyGenVideo(BaseTool):
    name = "heygen_video"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "heygen"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:HEYGEN_API_KEY"]
    install_instructions = (
        "Set the HEYGEN_API_KEY environment variable:\n"
        "  set HEYGEN_API_KEY=your_key_here\n"
        "Get a key at https://app.heygen.com/settings/api"
    )
    fallback = "wan_video"
    fallback_tools = ["wan_video", "hunyuan_video", "ltx_video_local", "cogvideo_video", "ltx_video_modal", "image_selector"]
    agent_skills = ["ai-video-gen", "create-video"]

    capabilities = ["text_to_video", "image_to_video", "provider_selection"]
    supports = {
        "reference_image": True,
        "offline": False,
        "native_audio": False,
        "cloud_generation": True,
    }
    best_for = [
        "premium cloud video generation without local GPU setup",
        "fast access to VEO, Sora, Kling, Runway, and Seedance providers",
    ]
    not_good_for = [
        "offline or privacy-constrained rendering",
        "free local-first production",
    ]
    provider_matrix = {
        key: {"tool": "heygen_video", **value, "mode": "api"} for key, value in HEYGEN_PROVIDERS.items()
    }

    input_schema = {
        "type": "object",
        "required": ["prompt", "output_path"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {
                "type": "string",
                "enum": ["text_to_video", "image_to_video"],
                "default": "text_to_video",
            },
            "provider_variant": {
                "type": "string",
                "enum": sorted(HEYGEN_PROVIDERS),
                "default": "veo_3_1",
            },
            "reference_image_url": {"type": "string"},
            "reference_image_path": {"type": "string"},
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16", "1:1"],
                "default": "16:9",
            },
            "output_path": {"type": "string"},
        },
    }
    output_schema = {
        "type": "object",
        "required": [
            "provider",
            "provider_variant",
            "provider_name",
            "mode",
            "prompt",
            "aspect_ratio",
            "operation",
            "execution_id",
            "output",
            "output_path",
            "format",
        ],
        "properties": {
            "provider": {"type": "string", "const": "heygen"},
            "provider_variant": {"type": "string"},
            "provider_name": {"type": "string"},
            "mode": {"type": "string", "const": "api"},
            "prompt": {"type": "string"},
            "aspect_ratio": {"type": "string"},
            "operation": {"type": "string", "enum": ["text_to_video", "image_to_video"]},
            "execution_id": {"type": "string"},
            "output": {"type": "string"},
            "output_path": {"type": "string"},
            "format": {"type": "string", "const": "mp4"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, backoff_seconds=10.0, retryable_errors=["rate_limit", "timeout", "server_error"])
    idempotency_key_fields = [
        "prompt",
        "output_path",
        "operation",
        "provider_variant",
        "reference_image_url",
        "reference_image_path",
        "aspect_ratio",
    ]
    side_effects = ["writes video file to output_path", "calls HeyGen API"]
    user_visible_verification = ["Inspect sampled frames for motion quality and prompt adherence"]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if os.environ.get("HEYGEN_API_KEY") else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        meta = HEYGEN_PROVIDERS.get(inputs.get("provider_variant", "veo_3_1"), HEYGEN_PROVIDERS["veo_3_1"])
        return estimate_quality_cost(meta["quality"])

    def estimate_runtime(self, inputs: dict[str, Any]) -> float:
        meta = HEYGEN_PROVIDERS.get(inputs.get("provider_variant", "veo_3_1"), HEYGEN_PROVIDERS["veo_3_1"])
        return estimate_speed_runtime(meta["speed"])

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        provider = inputs.get("provider_variant", "veo_3_1")
        if provider not in HEYGEN_PROVIDERS:
            return ToolResult(
                success=False,
                error=(
                    f"Unknown provider_variant: {provider}. "
                    f"Available: {', '.join(sorted(HEYGEN_PROVIDERS))}"
                ),
            )
        operation = inputs.get("operation", "text_to_video")
        operation_error = validate_video_operation(operation, {"text_to_video", "image_to_video"})
        if operation_error:
            return ToolResult(success=False, error=operation_error)
        if operation == "image_to_video" and not (
            inputs.get("reference_image_url") or inputs.get("reference_image_path")
        ):
            return ToolResult(
                success=False,
                error="image_to_video requires reference_image_url or reference_image_path",
            )
        _, output_error = require_generated_video_output_path(inputs, self.name)
        if output_error:
            return output_error

        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="HeyGen video generation is unavailable. " + self.install_instructions)
        start = time.time()
        try:
            result = generate_heygen_video(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"HeyGen video generation failed: {exc}")
        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result
