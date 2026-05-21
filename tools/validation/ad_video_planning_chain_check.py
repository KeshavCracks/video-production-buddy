"""Validate ad-video planning artifacts before asset generation or render."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.knowledge_alignment import check_ad_video_planning_knowledge_alignment
from lib.trend_alignment import check_ad_video_planning_trend_alignment
from schemas.artifacts import validate_artifact
from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolTier,
)


class AdVideoPlanningChainCheck(BaseTool):
    name = "ad_video_planning_chain_check"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "validation"
    provider = "openmontage"
    stability = ToolStability.PRODUCTION
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=128, disk_mb=1, network_required=False)

    capabilities = [
        "validate_ad_video_planning_chain",
        "validate_trend_alignment_threading",
        "validate_knowledge_alignment_threading",
        "validate_pre_asset_gate",
    ]
    best_for = [
        "blocking ad-video asset generation when selected trend guidance is not threaded",
        "detecting stale planning artifacts before render",
    ]
    not_good_for = [
        "evaluating visual quality of rendered clips",
        "discovering live social trends",
    ]

    input_schema = {
        "type": "object",
        "properties": {
            "production_bible": {"type": "object"},
            "script": {"type": "object"},
            "scene_plan": {"type": "object"},
            "production_bible_path": {"type": "string"},
            "script_path": {"type": "string"},
            "scene_plan_path": {"type": "string"},
        },
        "anyOf": [
            {"required": ["production_bible", "script", "scene_plan"]},
            {"required": ["production_bible_path", "script_path", "scene_plan_path"]},
        ],
    }
    output_schema = {
        "type": "object",
        "required": ["trend_alignment", "knowledge_alignment"],
        "properties": {
            "trend_alignment": {"type": "object"},
            "knowledge_alignment": {"type": "object"},
        },
    }
    user_visible_verification = [
        "Confirm selected trend refs appear in required script sections",
        "Confirm visual/pacing trends appear in scene_plan trend refs and notes",
    ]

    def _load_artifact(self, inputs: dict[str, Any], key: str) -> dict[str, Any]:
        value = inputs.get(key)
        if isinstance(value, dict):
            return value

        path_value = inputs.get(f"{key}_path")
        if not isinstance(path_value, str) or not path_value.strip():
            raise ValueError(f"Missing {key} or {key}_path")
        with open(Path(path_value), encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict):
            raise ValueError(f"{key}_path must contain a JSON object")
        return loaded

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        started = time.time()
        try:
            production_bible = self._load_artifact(inputs, "production_bible")
            script = self._load_artifact(inputs, "script")
            scene_plan = self._load_artifact(inputs, "scene_plan")

            validate_artifact("production_bible", production_bible, pipeline_type="ad-video")
            validate_artifact("script", script, pipeline_type="ad-video")
            validate_artifact("scene_plan", scene_plan, pipeline_type="ad-video")

            report = check_ad_video_planning_trend_alignment(
                production_bible,
                script,
                scene_plan,
            )
            knowledge_report = check_ad_video_planning_knowledge_alignment(
                production_bible,
                script,
                scene_plan,
            )
            if not report["ok"] or not knowledge_report["ok"]:
                issues = []
                issues.extend(report.get("issues", []))
                issues.extend(knowledge_report.get("issues", []))
                return ToolResult(
                    success=False,
                    data={"trend_alignment": report, "knowledge_alignment": knowledge_report},
                    error=json.dumps(issues, sort_keys=True),
                    duration_seconds=time.time() - started,
                )
            return ToolResult(
                success=True,
                data={"trend_alignment": report, "knowledge_alignment": knowledge_report},
                duration_seconds=time.time() - started,
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=str(exc),
                duration_seconds=time.time() - started,
            )
