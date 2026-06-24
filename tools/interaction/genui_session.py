"""Local GenUI session materialization and serving tool."""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from lib.genui import (
    cleanup_orphaned_servers,
    get_browser_url,
    is_wsl2,
)
from lib.genui.journal import (
    GENUI_CONTRACT,
    entry_from_request_decision,
    interaction_journal_path,
    update_interaction_entry,
    upsert_interaction_entry,
)
from lib.genui.interaction_policy import assess_interaction_need
from lib.genui.review_assets import enrich_interaction_request_with_review_assets
from lib.genui.session import (
    SESSION_CONTRACT,
    build_dynamic_session_config,
    read_session_events,
    review_session_response,
    session_event_summary,
    validate_session_response,
    with_source_artifact_hashes,
    write_session_bundle,
    write_session_view_spec,
)
from schemas.artifacts import load_strict_json_object
from tools.base_tool import BaseTool, ToolResult, ToolRuntime, ToolStability, ToolTier
from tools.interaction.genui_runtime import LocalGenUIServerRuntime


class GenUISession(LocalGenUIServerRuntime, BaseTool):
    """Materialize and optionally serve a GenUI A2UI session."""

    name = "genui_session"
    version = "0.1.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    runtime = ToolRuntime.LOCAL
    capability = "interaction"
    provider = "video_production_buddy"
    capabilities = [
        "genui_session",
        "genui_framework_backed",
        "interaction_journal",
        "session_replay",
        "session_status",
        "response_validation",
        "a2ui_framework",
        "copilotkit_a2ui_renderer",
        "ag_ui_events",
        "media_review_room",
        "issue_lifecycle",
        "timecoded_annotation",
        "project_cockpit",
        "structured_revision_capture",
        "draft_autosave",
        "conflict_safe_resume",
    ]
    supports = {
        "modes": ["prepare", "serve", "status", "replay", "validate_response", "summarize"],
        "localhost_only": True,
        "canonical_writes": False,
        "renderer": "a2ui",
        "framework": "a2ui",
        "framework_renderer": "@copilotkit/a2ui-renderer",
        "protocol": "ag-ui",
        "genui_contract": GENUI_CONTRACT,
        "session_contract": SESSION_CONTRACT,
        "surface_modes": ["gate_workspace", "media_review_room", "project_cockpit", "background_status"],
        "components": [
            "MediaReviewRoom",
            "IssueTracker",
            "GateWorkspace",
            "ProjectCockpit",
            "BackgroundStatus",
            "MediaTimeline",
            "MediaComparison",
            "RegionAnnotation",
            "IssueBoard",
            "ArtifactTrace",
            "RevisionPatchPreview",
            "LiveStatusPanel",
            "InteractionJournalPanel",
            "OperationTimeline",
            "ReviewCompletionPanel",
            "DurableDecisionPanel",
        ],
    }
    best_for = [
        "framework-backed GenUI sessions",
        "media-native review with timecoded annotations and issue IDs",
        "dynamic per-round browser workspaces when linear chat is insufficient",
        "read-only project cockpit sessions",
    ]
    not_good_for = [
        "single yes/no clarifications",
        "canonical artifact mutation without agent review",
        "public web hosting",
    ]
    side_effects = [
        "writes projects/<project>/artifacts/ui/<session_id>/config.json",
        "writes projects/<project>/artifacts/ui/<session_id>/form.html",
        "writes projects/<project>/artifacts/ui/<session_id>/view_spec.json",
        "writes projects/<project>/artifacts/ui/<session_id>/events.jsonl after event stream materialization",
        "may write response-only projects/<project>/artifacts/ui/<session_id>/draft.json during browser autosave",
        "writes projects/<project>/artifacts/ui/interaction_journal.json",
        "may start a localhost-only Python HTTP server in serve mode",
        "may open a local browser only when open_browser is true",
    ]
    input_schema = {
        "type": "object",
        "required": ["project_dir"],
        "properties": {
            "project_dir": {"type": "string"},
            "interaction_request": {"type": "object"},
            "config": {"type": "object"},
            "session_id": {"type": "string"},
            "mode": {
                "type": "string",
                "enum": ["prepare", "serve", "status", "replay", "validate_response", "summarize"],
                "default": "serve",
            },
            "host": {"type": "string", "default": "127.0.0.1"},
            "port": {"type": "integer", "minimum": 0, "maximum": 65535, "default": 0},
            "record_journal": {"type": "boolean", "default": True},
            "open_browser": {"type": "boolean", "default": False},
        },
    }
    output_schema = {
        "type": "object",
        "required": [
            "session_id",
            "genui_contract",
            "session_contract",
            "config_path",
            "html_path",
            "view_spec_path",
            "response_path",
            "events_path",
            "server_state",
            "renderer",
            "framework",
        ],
        "properties": {
            "session_id": {"type": "string"},
            "genui_contract": {"type": "string"},
            "session_contract": {"type": "string"},
            "config_id": {"type": "string"},
            "config_path": {"type": "string"},
            "html_path": {"type": "string"},
            "view_spec_path": {"type": "string"},
            "response_path": {"type": "string"},
            "events_path": {"type": "string"},
            "draft_path": {"type": "string"},
            "draft_exists": {"type": "boolean"},
            "server_state": {"type": "string"},
            "renderer": {"type": "string"},
            "framework": {"type": "string"},
            "framework_renderer": {"type": "string"},
            "protocol": {"type": "string"},
            "journal_path": {"type": "string"},
            "state_path": {"type": "string"},
            "status_url": {"type": ["string", "null"]},
            "session_url": {"type": ["string", "null"]},
            "event_count": {"type": "integer"},
            "event_cursor": {"type": ["string", "null"]},
            "operation_event_summary": {"type": "object"},
            "replay_url": {"type": ["string", "null"]},
            "replay_path": {"type": ["string", "null"]},
            "response_exists": {"type": "boolean"},
            "review": {"type": "object"},
            "validation": {"type": "object"},
            "summary": {"type": "string"},
            "patch_plan": {"type": "array"},
            "url": {"type": ["string", "null"]},
            "browser_url": {"type": ["string", "null"]},
            "pid": {"type": ["integer", "null"]},
            "wsl2": {"type": "boolean"},
            "browser_opened": {"type": "boolean"},
            "instructions": {"type": "string"},
        },
    }
    artifact_schema = {
        "produces": ["ui_session_config", "ui_interaction_journal"],
        "expects_response": "ui_session_response",
    }
    idempotency_key_fields = [
        "project_dir",
        "interaction_request",
        "config",
        "session_id",
        "mode",
        "host",
        "port",
        "open_browser",
    ]
    user_visible_verification = [
        "Use the returned localhost URL for the GenUI session when an interactive decision is needed.",
        "Confirm projects/<project>/artifacts/ui/<session_id>/response.json exists before mapping to canonical artifacts.",
        "Validate ui_session_response and review the patch plan before canonical artifacts are updated.",
    ]

    def _config_from_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        config = inputs.get("config")
        if isinstance(config, dict):
            return config
        request = inputs.get("interaction_request")
        if isinstance(request, dict):
            enrichment = enrich_interaction_request_with_review_assets(Path(inputs["project_dir"]), request)
            config = build_dynamic_session_config(enrichment.request)
            metadata = config.setdefault("metadata", {})
            metadata["review_assets_auto_populated"] = enrichment.auto_populated
            metadata["review_asset_issues"] = enrichment.issues
            return config
        raise ValueError("genui_session requires a GenUI session config or interaction_request")

    def _bundle_paths(self, project_dir: Path, session_id: str) -> dict[str, Path]:
        base = project_dir.resolve() / "artifacts" / "ui" / session_id
        return {
            "config_path": base / "config.json",
            "html_path": base / "form.html",
            "view_spec_path": base / "view_spec.json",
            "response_path": base / "response.json",
            "state_path": base / "server.json",
            "events_path": base / "events.jsonl",
            "draft_path": base / "draft.json",
        }

    def _config_for_session_id(self, project_dir: Path, session_id: str) -> dict[str, Any]:
        paths = self._bundle_paths(project_dir, session_id)
        if not paths["config_path"].exists():
            raise ValueError(f"GenUI session config not found for {session_id!r}")
        return load_strict_json_object(
            paths["config_path"],
            context=f"GenUI session config {session_id}",
        )

    def _status_data(self, project_dir: Path, session_id: str, config: dict[str, Any]) -> dict[str, Any]:
        paths = self._bundle_paths(project_dir, session_id)
        state: dict[str, Any] = {}
        if paths["state_path"].exists():
            state = load_strict_json_object(
                paths["state_path"],
                context=f"GenUI session server state {session_id}",
            )
        response_exists = paths["response_path"].exists()
        server_state = "submitted" if response_exists else str(state.get("server_state") or "prepared")
        events = read_session_events(paths["events_path"])
        event_summary = session_event_summary(events)
        url = state.get("url")
        status_url = f"{str(url).rstrip('/')}/events" if isinstance(url, str) and url else None
        session_url = f"{str(url).rstrip('/')}/session.json" if isinstance(url, str) and url else None
        return {
            "session_id": session_id,
            "genui_contract": GENUI_CONTRACT,
            "session_contract": SESSION_CONTRACT,
            "config_id": session_id,
            "config_path": str(paths["config_path"]),
            "html_path": str(paths["html_path"]),
            "view_spec_path": str(paths["view_spec_path"]),
            "response_path": str(paths["response_path"]),
            "events_path": str(paths["events_path"]),
            "draft_path": str(paths["draft_path"]),
            "state_path": str(paths["state_path"]),
            "journal_path": str(interaction_journal_path(project_dir)),
            "server_state": server_state,
            "renderer": "a2ui",
            "framework": "a2ui",
            "framework_renderer": "@copilotkit/a2ui-renderer",
            "protocol": "ag-ui",
            "url": url,
            "browser_url": state.get("browser_url"),
            "status_url": status_url,
            "session_url": session_url,
            "event_count": event_summary.get("event_count", 0),
            "event_cursor": event_summary.get("event_cursor"),
            "operation_event_summary": event_summary,
            "replay_url": None,
            "replay_path": str(paths["html_path"]),
            "pid": state.get("pid"),
            "wsl2": is_wsl2(),
            "browser_opened": bool(state.get("browser_opened", False)),
            "response_exists": response_exists,
            "draft_exists": paths["draft_path"].exists(),
            "instructions": (
                f"GenUI session {session_id} is {server_state}. "
                "Use validate_response after response.json exists; canonical artifacts remain agent-owned."
            ),
        }

    def _execute_existing_session_mode(self, inputs: dict[str, Any], mode: str) -> ToolResult:
        project_dir = Path(inputs["project_dir"])
        session_id = inputs.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError(f"genui_session mode {mode!r} requires session_id")
        config = self._config_for_session_id(project_dir, session_id)
        data = self._status_data(project_dir, session_id, config)
        paths = self._bundle_paths(project_dir, session_id)
        record_journal = inputs.get("record_journal", True) is not False

        if mode == "status":
            if record_journal and data["response_exists"]:
                update_interaction_entry(
                    project_dir,
                    project_id=config["project_id"],
                    pipeline_type=config["pipeline_type"],
                    session_id=session_id,
                    updates={"status": "submitted"},
                )
            return ToolResult(success=True, data=data, artifacts=[str(paths["config_path"])])

        if mode == "replay":
            write_session_view_spec(paths["view_spec_path"], config, preview_only=True)
            replay_data = {
                **data,
                "server_state": "replay_prepared",
                "replay_path": str(paths["html_path"]),
                "instructions": (
                    f"Replay prepared at {paths['html_path']} with renderer state at {paths['view_spec_path']}. "
                    "Use serve mode for an interactive localhost browser session."
                ),
            }
            if record_journal:
                update_interaction_entry(
                    project_dir,
                    project_id=config["project_id"],
                    pipeline_type=config["pipeline_type"],
                    session_id=session_id,
                    updates={"status": "replay_prepared", "replay_path": str(paths["html_path"])},
                )
            return ToolResult(success=True, data=replay_data, artifacts=[str(paths["view_spec_path"])])

        if not paths["response_path"].exists():
            raise ValueError(f"GenUI response not found at {paths['response_path']}")
        response = load_strict_json_object(
            paths["response_path"],
            context=f"GenUI session response {session_id}",
        )
        validate_session_response(response)
        review = review_session_response(config, response)
        validation = review["validation"]
        patch_plan = review["patch_plan"]
        blocking_issue_ids = review["blocking_issue_ids"]

        if mode == "validate_response":
            next_status = "blocked" if validation.get("status") == "blocked" else "validated"
            if record_journal:
                update_interaction_entry(
                    project_dir,
                    project_id=config["project_id"],
                    pipeline_type=config["pipeline_type"],
                    session_id=session_id,
                    updates={
                        "status": next_status,
                        "validation": validation,
                        "patch_plan_count": len(patch_plan),
                        "blocking_issue_ids": blocking_issue_ids,
                    },
                )
            return ToolResult(
                success=True,
                data={
                    **data,
                    "server_state": next_status,
                    "review": review,
                    "validation": validation,
                    "patch_plan": patch_plan,
                    "instructions": (
                        "Response blocked; resolve validation errors before canonical artifacts are updated."
                        if next_status == "blocked"
                        else "Response validated for agent review. No canonical artifacts were written."
                    ),
                },
                artifacts=[str(paths["response_path"])],
            )

        summary_parts = [
            f"Action: {response['action']}",
            f"Values: {', '.join(response.get('values') or {}) or 'none'}",
            f"Issues: {len(response.get('issues') or [])}",
            f"Patches pending agent review: {len(patch_plan)}",
        ]
        for patch in patch_plan[:3]:
            value = patch.get("value")
            if isinstance(value, str) and value:
                summary_parts.append(value)
        summary = " | ".join(summary_parts)
        next_status = "blocked" if validation.get("status") == "blocked" else "summarized"
        if record_journal:
            update_interaction_entry(
                project_dir,
                project_id=config["project_id"],
                pipeline_type=config["pipeline_type"],
                session_id=session_id,
                updates={
                    "status": next_status,
                    "validation": validation,
                    "patch_plan_count": len(patch_plan),
                    "blocking_issue_ids": blocking_issue_ids,
                },
            )
        return ToolResult(
            success=True,
            data={
                **data,
                "server_state": next_status,
                "review": review,
                "validation": validation,
                "summary": summary,
                "patch_plan": patch_plan,
                "instructions": (
                    "Response blocked; summary is informational only until validation errors are resolved."
                    if next_status == "blocked"
                    else "Summary prepared from the validated GenUI response. No canonical artifacts were written."
                ),
            },
            artifacts=[str(paths["response_path"])],
        )

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            project_dir = Path(inputs["project_dir"])
            mode = inputs.get("mode", "serve")
            host = inputs.get("host", "127.0.0.1")
            if mode in {"status", "replay", "validate_response", "summarize"}:
                return self._execute_existing_session_mode(inputs, mode)

            config = self._config_from_inputs(inputs)
            config = with_source_artifact_hashes(config, project_dir)
            if host not in {"127.0.0.1", "localhost"}:
                raise ValueError("genui_session only serves localhost-bound sessions")
            if mode not in {"prepare", "serve"}:
                raise ValueError("mode must be 'prepare', 'serve', 'status', 'replay', 'validate_response', or 'summarize'")

            cleanup_orphaned_servers(project_dir)
            bundle = write_session_bundle(project_dir, config)
            session_id = bundle.config["session_id"]
            data: dict[str, Any] = {
                "session_id": session_id,
                "genui_contract": GENUI_CONTRACT,
                "session_contract": SESSION_CONTRACT,
                "config_id": session_id,
                "config_path": str(bundle.config_path),
                "html_path": str(bundle.html_path),
                "view_spec_path": str(bundle.view_spec_path),
                "response_path": str(bundle.response_path),
                "events_path": str(bundle.events_path),
                "draft_path": str(bundle.draft_path),
                "state_path": str(bundle.state_path),
                "journal_path": str(interaction_journal_path(project_dir)),
                "server_state": "prepared",
                "renderer": "a2ui",
                "framework": "a2ui",
                "framework_renderer": "@copilotkit/a2ui-renderer",
                "protocol": "ag-ui",
                "url": None,
                "browser_url": None,
                "status_url": None,
                "session_url": None,
                "event_count": 0,
                "event_cursor": None,
                "operation_event_summary": {"event_count": 0},
                "replay_url": None,
                "replay_path": str(bundle.html_path),
                "pid": None,
                "wsl2": is_wsl2(),
                "browser_opened": False,
                "response_exists": False,
                "draft_exists": False,
                "instructions": (
                    f"GenUI files prepared at {bundle.html_path} and {bundle.view_spec_path}. "
                    "Run genui_session in serve mode to render the A2UI/CopilotKit session, then wait while "
                    f"{bundle.response_path} is validated before canonical artifacts are updated."
                ),
            }

            request = inputs.get("interaction_request")
            if inputs.get("record_journal", True) is not False:
                if isinstance(request, dict):
                    decision = assess_interaction_need(request)
                    upsert_interaction_entry(
                        project_dir,
                        entry_from_request_decision(
                            request,
                            decision,
                            status="prepared",
                            session_data=data,
                        ),
                    )
                else:
                    synthetic_request = {
                        "request_id": session_id,
                        "project_id": bundle.config["project_id"],
                        "pipeline_type": bundle.config["pipeline_type"],
                        "stage": bundle.config["stage"],
                        "gate": bundle.config["gate"],
                        "interaction_kind": bundle.config.get("visual_need_assessment", {}).get("interaction_kind", "dynamic_genui"),
                    }
                    synthetic_decision = {
                        "recommended_mode": bundle.config["mode"],
                        "recommended_tool": "genui_session",
                        "linear_chat_sufficient": False,
                        "interaction_kind": synthetic_request["interaction_kind"],
                        "reasons": bundle.config.get("visual_need_assessment", {}).get("reasons") or [],
                    }
                    upsert_interaction_entry(
                        project_dir,
                        entry_from_request_decision(
                            synthetic_request,
                            synthetic_decision,
                            status="prepared",
                            session_data=data,
                        ),
                    )

            artifacts = [str(bundle.config_path), str(bundle.html_path), str(bundle.view_spec_path)]
            if mode == "serve":
                port = int(inputs.get("port") or 0)
                if port == 0:
                    port = self._choose_port(host)
                submit_url = f"http://{host}:{port}/submit"
                submit_nonce = secrets.token_urlsafe(32)
                write_session_view_spec(
                    bundle.view_spec_path,
                    bundle.config,
                    submit_url=submit_url,
                    submit_nonce=submit_nonce,
                )
                from lib.genui.view_spec import render_shell_html

                with open(bundle.html_path, "w") as f:
                    f.write(render_shell_html())
                process = self._start_server(bundle, host, port, submit_nonce)
                try:
                    self._wait_until_ready(process, host, port)
                except Exception:
                    if process.poll() is None:
                        process.terminate()
                    raise
                time.sleep(0.02)
                localhost_url = f"http://{host}:{port}/"
                browser_url = get_browser_url(localhost_url)
                browser_opened = (
                    self._try_open_browser(browser_url)
                    if inputs.get("open_browser") is True
                    else False
                )
                data.update(
                    {
                        "server_state": "running",
                        "url": localhost_url,
                        "browser_url": browser_url,
                        "status_url": f"{localhost_url.rstrip('/')}/events",
                        "session_url": f"{localhost_url.rstrip('/')}/session.json",
                        "replay_url": localhost_url,
                        "pid": process.pid,
                        "browser_opened": browser_opened,
                        "instructions": (
                            f"Browser URL available at {browser_url}. Review the GenUI session when needed, submit it, "
                            f"then wait while {bundle.response_path} is validated before any canonical "
                            "artifacts are updated."
                            + (" (Browser launch requested and completed.)" if browser_opened else "")
                        ),
                    }
                )
                try:
                    self._write_strict_json_file(bundle.state_path, data)
                except (TypeError, ValueError):
                    if process.poll() is None:
                        process.terminate()
                    raise
                artifacts.append(str(bundle.state_path))
                if inputs.get("record_journal", True) is not False:
                    update_interaction_entry(
                        project_dir,
                        project_id=bundle.config["project_id"],
                        pipeline_type=bundle.config["pipeline_type"],
                        session_id=session_id,
                        updates={
                            "status": "running",
                            "url": localhost_url,
                            "browser_url": browser_url,
                            "status_url": f"{localhost_url.rstrip('/')}/events",
                            "session_url": f"{localhost_url.rstrip('/')}/session.json",
                            "replay_url": localhost_url,
                            "state_path": str(bundle.state_path),
                            "events_path": str(bundle.events_path),
                        },
                    )

            return ToolResult(success=True, data=data, artifacts=artifacts)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
