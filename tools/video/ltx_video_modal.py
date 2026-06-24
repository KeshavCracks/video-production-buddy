"""Modal-hosted LTX video generation."""

from __future__ import annotations

import os
import time

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
    generate_ltx_modal_video,
    require_generated_video_output_path,
    validate_video_operation,
)


class LTXVideoModal(BaseTool):
    name = "ltx_video_modal"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "video_generation"
    provider = "ltx-modal"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:MODAL_LTX2_ENDPOINT_URL"]
    install_instructions = (
        "Set the MODAL_LTX2_ENDPOINT_URL environment variable to your deployed LTX endpoint:\n"
        "  set MODAL_LTX2_ENDPOINT_URL=https://<your-modal-endpoint>"
    )
    fallback = "ltx_video_local"
    fallback_tools = ["ltx_video_local", "wan_video", "hunyuan_video", "cogvideo_video", "image_selector"]
    agent_skills = ["ltx2"]

    capabilities = ["text_to_video", "image_to_video"]
    supports = {
        "reference_image": True,
        "offline": False,
        "native_audio": False,
        "self_hosted_cloud": True,
    }
    best_for = ["self-hosted cloud GPU rendering for LTX without local workstation dependence"]
    not_good_for = ["zero-setup local workflows"]
    provider_matrix = {
        "ltx2-modal": {
            "tool": "ltx_video_modal",
            "name": "LTX-2 (Modal)",
            "mode": "api",
            "quality": "high",
            "speed": "medium",
        }
    }

    input_schema = {
        "type": "object",
        "required": ["prompt", "output_path"],
        "properties": {
            "prompt": {"type": "string"},
            "operation": {"type": "string", "enum": ["text_to_video", "image_to_video"], "default": "text_to_video"},
            "reference_image_url": {"type": "string"},
            "reference_image_path": {"type": "string"},
            "aspect_ratio": {"type": "string", "enum": ["16:9", "9:16", "1:1"], "default": "16:9"},
            "duration_hint": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "num_frames": {"type": "integer"},
            "num_inference_steps": {"type": "integer"},
            "seed": {"type": "integer"},
            "output_path": {"type": "string"},
        },
    }
    output_schema = {
        "type": "object",
        "required": [
            "provider",
            "provider_name",
            "mode",
            "prompt",
            "width",
            "height",
            "num_frames",
            "fps",
            "duration_seconds",
            "operation",
            "output",
            "output_path",
            "format",
        ],
        "properties": {
            "provider": {"type": "string", "const": "ltx-modal"},
            "provider_name": {"type": "string"},
            "mode": {"type": "string", "const": "modal"},
            "prompt": {"type": "string"},
            "width": {"type": "integer", "minimum": 0},
            "height": {"type": "integer", "minimum": 0},
            "num_frames": {"type": "integer", "minimum": 1},
            "fps": {"type": "integer", "minimum": 1},
            "duration_seconds": {"type": "number", "minimum": 0},
            "operation": {"type": "string", "enum": ["text_to_video", "image_to_video"]},
            "output": {"type": "string"},
            "output_path": {"type": "string"},
            "format": {"type": "string", "const": "mp4"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=512, vram_mb=0, disk_mb=500, network_required=True)
    retry_policy = RetryPolicy(max_retries=2, backoff_seconds=10.0, retryable_errors=["timeout", "server_error"])
    idempotency_key_fields = [
        "prompt",
        "output_path",
        "operation",
        "reference_image_url",
        "reference_image_path",
        "aspect_ratio",
        "duration_hint",
        "width",
        "height",
        "num_frames",
        "num_inference_steps",
        "seed",
    ]
    side_effects = ["writes video file to output_path", "calls modal endpoint"]
    user_visible_verification = ["Inspect sampled frames for motion quality and prompt adherence"]

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE if os.environ.get("MODAL_LTX2_ENDPOINT_URL") else ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, object]) -> float:
        return 0.25

    def estimate_runtime(self, inputs: dict[str, object]) -> float:
        return 180.0

    def execute(self, inputs: dict[str, object]) -> ToolResult:
        operation = inputs.get("operation", "text_to_video")
        operation_error = validate_video_operation(operation, {"text_to_video", "image_to_video"})
        if operation_error:
            return ToolResult(success=False, error=operation_error)
        if operation == "image_to_video" and not (
            inputs.get("reference_image_path") or inputs.get("reference_image_url")
        ):
            return ToolResult(
                success=False,
                error="image_to_video requires reference_image_url or reference_image_path",
            )
        _, output_error = require_generated_video_output_path(inputs, self.name)
        if output_error:
            return output_error
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(success=False, error="Modal LTX video generation is unavailable. " + self.install_instructions)
        start = time.time()
        try:
            result = generate_ltx_modal_video(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Modal LTX video generation failed: {exc}")
        result.duration_seconds = round(time.time() - start, 2)
        result.cost_usd = self.estimate_cost(inputs)
        return result
