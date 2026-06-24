"""Music generation tool via ElevenLabs Music API.

Generates background music and sound effects for video production.
Reports unavailable when no API key is configured.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
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
from tools.output_paths import require_explicit_output_path


class MusicGen(BaseTool):
    # NOTE: Routes exclusively to ElevenLabs Music API (ELEVENLABS_API_KEY).
    # For MiniMax music use `minimax_music`; for Suno use `suno_music`.
    # The generic name is kept for backward compatibility.
    name = "music_gen"
    version = "0.1.0"
    tier = ToolTier.GENERATE
    capability = "music_generation"
    provider = "elevenlabs"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.STOCHASTIC
    runtime = ToolRuntime.API

    dependencies = ["env:ELEVENLABS_API_KEY"]
    install_instructions = (
        "Set the ELEVENLABS_API_KEY environment variable:\n"
        "  export ELEVENLABS_API_KEY=your_key_here\n"
        "Get a key at https://elevenlabs.io"
    )

    agent_skills = ["music", "sound-effects", "elevenlabs"]

    capabilities = [
        "generate_background_music",
        "generate_sfx",
    ]
    best_for = [
        "Generating custom background music through ElevenLabs Music",
        "Creating ad, explainer, or trailer music beds when no library track is approved",
    ]

    input_schema = {
        "type": "object",
        "required": ["prompt", "output_path"],
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Music description (mood, genre, instruments, tempo)",
            },
            "duration_seconds": {
                "type": "number",
                "minimum": 3,
                "maximum": 600,
                "description": (
                    "Target duration in seconds (API supports 3-600s). "
                    "Should match the target video duration from the script/proposal. "
                    "Omitting this defaults to 60s which may not match your video."
                ),
            },
            "output_path": {"type": "string"},
        },
    }
    output_schema = {
        "type": "object",
        "required": [
            "provider",
            "prompt",
            "duration_seconds",
            "format",
            "output",
            "output_path",
        ],
        "properties": {
            "provider": {"type": "string", "const": "elevenlabs"},
            "prompt": {"type": "string"},
            "duration_seconds": {"type": "number", "minimum": 0},
            "format": {"type": "string", "const": "mp3"},
            "output": {"type": "string"},
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=256, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["rate_limit", "timeout"])
    idempotency_key_fields = ["prompt", "output_path", "duration_seconds"]
    side_effects = ["writes audio file to output_path", "calls ElevenLabs API"]
    user_visible_verification = [
        "Inspect audio metadata, duration, tags, and waveform metrics for mood and quality fit",
    ]

    _AUTH_FAILED_KEY_PREFIXES: set[str] = set()

    def get_status(self) -> ToolStatus:
        key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not key:
            return ToolStatus.UNAVAILABLE
        if key[:8] in self.__class__._AUTH_FAILED_KEY_PREFIXES:
            return ToolStatus.UNAVAILABLE
        return ToolStatus.AVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        # ElevenLabs music generation pricing is per generation
        duration = inputs.get("duration_seconds")
        if duration is None:
            raise ValueError(
                "music_gen.estimate_cost: duration_seconds is required. "
                "Derive it from the approved target runtime in the script/proposal. "
                "Silent defaults are not permitted."
            )
        # Approximate: ~$0.05 per 30 seconds
        return round(duration / 30 * 0.05, 4)

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        duration = inputs.get("duration_seconds")
        if duration is None:
            return ToolResult(
                success=False,
                error=(
                    "music_gen: duration_seconds is required. "
                    "Derive it from the approved target runtime in the script/proposal. "
                    "Silent defaults to 60s are not permitted — the generated music "
                    "must match the actual video duration."
                ),
            )

        output_path, output_error = require_explicit_output_path(
            inputs, self.name, artifact_label="generated music audio"
        )
        if output_error:
            return output_error
        assert output_path is not None

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            return ToolResult(
                success=False,
                error="No ElevenLabs API key. " + self.install_instructions,
            )

        start = time.time()

        try:
            result = self._generate(inputs, api_key, output_path)
        except Exception as e:
            return ToolResult(success=False, error=f"Music generation failed: {e}")

        result.duration_seconds = round(time.time() - start, 2)
        if not result.success:
            return result
        result.cost_usd = self.estimate_cost(inputs)
        result.data.setdefault("output_path", str(output_path))
        return result

    def _generate(
        self,
        inputs: dict[str, Any],
        api_key: str,
        output_path: Path,
    ) -> ToolResult:
        import logging
        import requests

        logger = logging.getLogger(__name__)

        prompt = inputs["prompt"]
        duration = inputs.get("duration_seconds")

        url = "https://api.elevenlabs.io/v1/music"

        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "prompt": prompt,
            "music_length_ms": int(duration * 1000),
        }

        response = requests.post(
            url, headers=headers, json=payload, timeout=180
        )
        if response.status_code == 401:
            self.__class__._AUTH_FAILED_KEY_PREFIXES.add(api_key[:8])
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return ToolResult(
            success=True,
            data={
                "provider": "elevenlabs",
                "prompt": prompt,
                "duration_seconds": duration,
                "output": str(output_path),
                "format": "mp3",
            },
            artifacts=[str(output_path)],
        )
