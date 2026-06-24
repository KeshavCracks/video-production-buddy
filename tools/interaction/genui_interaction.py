"""Dynamic GenUI interaction router.

This tool lets the agent decide per interaction round whether linear CLI/chat is
enough or whether to synthesize and serve a browser GenUI surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.genui.dynamic import (
    INTERACTION_REQUEST_SCHEMA,
    validate_interaction_request,
)
from lib.genui.interaction_policy import assess_interaction_need
from lib.genui.journal import (
    GENUI_CONTRACT,
    entry_from_request_decision,
    interaction_journal_path,
    upsert_interaction_entry,
)
from lib.genui.review_assets import enrich_interaction_request_with_review_assets
from lib.genui.session import SESSION_CONTRACT, build_dynamic_session_config
from lib.genui.surface import SURFACE_CONTRACT, build_dynamic_surface_config
from tools.base_tool import BaseTool, ToolResult, ToolRuntime, ToolStability, ToolTier
from tools.interaction.genui_session import GenUISession
from tools.interaction.genui_surface import GenUISurface


GENUI_BROWSER_MODES = {"gate_workspace", "media_review_room", "project_cockpit", "background_status", "genui"}


class GenUIInteraction(BaseTool):
    """Assess an interaction and materialize a dynamic GenUI round when needed."""

    name = "genui_interaction"
    version = "0.2.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    runtime = ToolRuntime.LOCAL
    capability = "interaction"
    provider = "video_production_buddy"
    capabilities = [
        "genui_session",
        "genui_framework_backed",
        "genui_compatibility_surface",
        "dynamic_genui",
        "interaction_journal",
        "interaction_routing",
        "visual_demonstration",
        "multi_axis_selection",
        "structured_revision_capture",
        "project_cockpit",
        "media_review_room",
        "a2ui_framework",
        "ag_ui_events",
    ]
    supports = {
        "modes": ["prepare", "serve"],
        "recommended_renderer": "a2ui",
        "framework": "a2ui",
        "framework_renderer": "@copilotkit/a2ui-renderer",
        "protocol": "ag-ui",
        "delegates_to": "genui_session",
        "compatibility_surface_tool": "genui_surface",
        "canonical_writes": False,
        "dynamic_per_round_decision": True,
        "genui_contract": GENUI_CONTRACT,
        "session_contract": SESSION_CONTRACT,
        "surface_contract": SURFACE_CONTRACT,
        "visual_blocks": [
            "MediaReviewRoom",
            "IssueTracker",
            "MediaCompare",
            "ConceptComparison",
            "RuntimeComparison",
            "RevisionPatch",
            "ApprovalChecklist",
            "ArtifactTracePanel",
            "OperationTimeline",
            "ReviewCompletionPanel",
            "DurableDecisionPanel",
        ],
    }
    best_for = [
        "deciding when linear chat is insufficient",
        "dynamic visual comparison and media review rounds",
        "multi-axis option selection with structured revision capture",
        "materializing framework-backed GenUI A2UI sessions from interaction context",
        "materializing ad-hoc GenUI compatibility surfaces only for explicit compatibility fallback",
    ]
    not_good_for = [
        "single yes/no clarifications",
        "canonical artifact mutation without agent review",
    ]
    side_effects = [
        "may write projects/<project>/artifacts/ui/<session_id>/config.json",
        "may write projects/<project>/artifacts/ui/<session_id>/view_spec.json",
        "may write projects/<project>/artifacts/ui/interaction_journal.json",
        "may start the localhost-only GenUI browser server in serve mode",
        "may open a local browser only when open_browser is true",
        "may write compatibility projects/<project>/artifacts/ui/<surface_id>/ files only for explicit compatibility fallback",
    ]
    input_schema = {
        "type": "object",
        "required": ["project_dir", "interaction_request"],
        "properties": {
            "project_dir": {"type": "string"},
            "interaction_request": INTERACTION_REQUEST_SCHEMA,
            "mode": {"type": "string", "enum": ["prepare", "serve"], "default": "serve"},
            "host": {"type": "string", "default": "127.0.0.1"},
            "port": {"type": "integer", "minimum": 0, "maximum": 65535, "default": 0},
            "force_genui": {"type": "boolean", "default": False},
            "compatibility_mode": {"type": "string", "enum": ["standard", "surface"], "default": "standard"},
            "open_browser": {"type": "boolean", "default": False},
        },
    }
    output_schema = {
        "type": "object",
        "required": ["decision", "recommended_mode", "dynamic_interaction"],
        "properties": {
            "decision": {"type": "object"},
            "recommended_mode": {
                "type": "string",
                "enum": ["cli", "gate_workspace", "media_review_room", "project_cockpit", "background_status", "genui"],
            },
            "dynamic_interaction": {"type": "boolean"},
            "genui_contract": {"type": ["string", "null"]},
            "renderer": {"type": ["string", "null"]},
            "surface_contract": {"type": ["string", "null"]},
            "session_contract": {"type": ["string", "null"]},
            "delegated_tool": {"type": ["string", "null"]},
            "config_path": {"type": ["string", "null"]},
            "view_spec_path": {"type": ["string", "null"]},
            "response_path": {"type": ["string", "null"]},
            "events_path": {"type": ["string", "null"]},
            "journal_path": {"type": ["string", "null"]},
            "routing_decision_path": {"type": ["string", "null"]},
            "server_state": {"type": ["string", "null"]},
            "url": {"type": ["string", "null"]},
            "browser_url": {"type": ["string", "null"]},
            "session_url": {"type": ["string", "null"]},
            "status_url": {"type": ["string", "null"]},
            "instructions": {"type": "string"},
        },
    }
    artifact_schema = {
        "produces": ["ui_session_config", "ui_surface_config"],
        "produces_journal": "ui_interaction_journal",
        "expects_response": "ui_session_response",
        "delegates_to": "genui_session",
        "compatibility_surface": "genui_surface",
    }
    idempotency_key_fields = [
        "project_dir",
        "interaction_request",
        "mode",
        "host",
        "port",
        "force_genui",
        "compatibility_mode",
        "open_browser",
    ]
    user_visible_verification = [
        "For GenUI mode, use the returned localhost URL only when an interactive decision is needed.",
        "For CLI mode, ask the compact question directly and record why linear chat was sufficient.",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            project_dir = Path(inputs["project_dir"])
            request = dict(inputs["interaction_request"])
            if inputs.get("force_genui"):
                request["force_genui"] = True
            enrichment = enrich_interaction_request_with_review_assets(project_dir, request)
            request = enrichment.request
            validate_interaction_request(request)
            decision = assess_interaction_need(request)
            journal_path = interaction_journal_path(project_dir)
            if decision["recommended_mode"] not in GENUI_BROWSER_MODES:
                upsert_interaction_entry(
                    project_dir,
                    entry_from_request_decision(
                        request,
                        decision,
                        status="cli_recommended",
                        fallback_reason="linear_chat_sufficient",
                        validation_status="not_required",
                    ),
                )
                return ToolResult(
                    success=True,
                    data={
                        "decision": decision,
                        "recommended_mode": "cli",
                        "dynamic_interaction": False,
                        "genui_contract": GENUI_CONTRACT,
                        "renderer": None,
                        "session_contract": None,
                        "surface_contract": None,
                        "config_path": None,
                        "view_spec_path": None,
                        "response_path": None,
                        "journal_path": str(journal_path),
                        "routing_decision_path": str(journal_path),
                        "server_state": None,
                        "url": None,
                        "browser_url": None,
                        "instructions": (
                            "Linear chat is sufficient for this interaction. Ask the compact "
                            "question in the CLI and record the response in the appropriate "
                            "agent-owned artifact or decision log."
                        ),
                    },
                )

            if inputs.get("compatibility_mode", "standard") != "surface":
                config = build_dynamic_session_config(request, decision=decision)
                metadata = config.setdefault("metadata", {})
                metadata["review_assets_auto_populated"] = enrichment.auto_populated
                metadata["review_asset_issues"] = enrichment.issues
                session_result = GenUISession().execute(
                    {
                        "project_dir": str(project_dir),
                        "config": config,
                        "mode": inputs.get("mode", "serve"),
                        "host": inputs.get("host", "127.0.0.1"),
                        "port": inputs.get("port", 0),
                        "record_journal": False,
                        "open_browser": inputs.get("open_browser") is True,
                    }
                )
                if not session_result.success:
                    return ToolResult(success=False, error=session_result.error)
                data = {
                    **session_result.data,
                    "decision": decision,
                    "recommended_mode": decision["recommended_mode"],
                    "dynamic_interaction": True,
                    "genui_contract": GENUI_CONTRACT,
                    "session_contract": SESSION_CONTRACT,
                    "surface_contract": None,
                    "delegated_tool": "genui_session",
                    "journal_path": str(journal_path),
                    "routing_decision_path": str(journal_path),
                }
                upsert_interaction_entry(
                    project_dir,
                    entry_from_request_decision(
                        request,
                        decision,
                        status="running" if data.get("server_state") == "running" else "prepared",
                        session_data=data,
                    ),
                )
                return ToolResult(
                    success=True,
                    data=data,
                    artifacts=session_result.artifacts,
                    cost_usd=session_result.cost_usd,
                    duration_seconds=session_result.duration_seconds,
                )

            config = build_dynamic_surface_config(request, decision=decision)
            surface_result = GenUISurface().execute(
                {
                    "project_dir": str(project_dir),
                    "config": config,
                    "mode": inputs.get("mode", "serve"),
                    "host": inputs.get("host", "127.0.0.1"),
                    "port": inputs.get("port", 0),
                    "open_browser": inputs.get("open_browser") is True,
                }
            )
            if not surface_result.success:
                return ToolResult(success=False, error=surface_result.error)

            data = {
                **surface_result.data,
                "decision": decision,
                "recommended_mode": decision["recommended_mode"],
                "dynamic_interaction": True,
                "genui_contract": GENUI_CONTRACT,
                "session_contract": None,
                "surface_contract": SURFACE_CONTRACT,
                "delegated_tool": "genui_surface",
                "journal_path": str(journal_path),
                "routing_decision_path": str(journal_path),
            }
            fallback_decision = {**decision, "recommended_tool": "genui_surface"}
            upsert_interaction_entry(
                project_dir,
                entry_from_request_decision(
                    request,
                    fallback_decision,
                    status="fallback",
                    session_data=data,
                    fallback_reason="explicit_compatibility_surface",
                ),
            )
            return ToolResult(
                success=True,
                data=data,
                artifacts=surface_result.artifacts,
                cost_usd=surface_result.cost_usd,
                duration_seconds=surface_result.duration_seconds,
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
