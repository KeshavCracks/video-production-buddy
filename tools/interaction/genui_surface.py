"""Local GenUI compatibility product surface materialization and serving tool."""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any

from lib.genui import (
    RENDERER_NAME,
    cleanup_orphaned_servers,
    get_browser_url,
    is_wsl2,
)
from lib.genui.project_snapshot import build_project_cockpit_config
from lib.genui.surface import (
    SURFACE_CONTRACT,
    write_surface_bundle,
    write_surface_view_spec,
)
from tools.base_tool import BaseTool, ToolResult, ToolRuntime, ToolStability, ToolTier
from tools.interaction.genui_runtime import LocalGenUIServerRuntime


class GenUISurface(LocalGenUIServerRuntime, BaseTool):
    """Materialize and optionally serve a GenUI compatibility gate workspace or cockpit."""

    name = "genui_surface"
    version = "0.1.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    runtime = ToolRuntime.LOCAL
    capability = "interaction"
    provider = "video_production_buddy"
    capabilities = [
        "genui_compatibility_surface",
        "gate_workspace",
        "project_cockpit",
        "ag_ui_events",
        "visual_review",
        "structured_revision_capture",
    ]
    supports = {
        "modes": ["prepare", "serve"],
        "localhost_only": True,
        "canonical_writes": False,
        "renderer": "json-render",
        "protocol": "ag-ui",
        "surface_contract": SURFACE_CONTRACT,
        "components": [
            "BriefWorksheet",
            "EvidenceAlignment",
            "ConceptComparison",
            "RuntimeComparison",
            "ScriptReview",
            "ScenePlanReview",
            "ProductReferencePicker",
            "MediaCompare",
            "AssetAnnotation",
            "MusicReview",
            "ApprovalChecklist",
            "RevisionPatch",
            "ArtifactTracePanel",
            "CockpitTimeline",
            "CockpitArtifactGallery",
        ],
    }
    best_for = [
        "product-level GenUI gate workspaces",
        "side-by-side media and option review",
        "read-only project cockpit over pipeline state",
        "structured annotations, selections, revision patches, and approval attestations",
    ]
    not_good_for = [
        "single yes/no clarifications",
        "canonical artifact mutation without agent review",
        "public web hosting",
    ]
    side_effects = [
        "writes projects/<project>/artifacts/ui/<surface_id>/config.json",
        "writes projects/<project>/artifacts/ui/<surface_id>/form.html",
        "writes projects/<project>/artifacts/ui/<surface_id>/view_spec.json",
        "may start a localhost-only Python HTTP server in serve mode",
        "may open a local browser only when open_browser is true",
    ]
    input_schema = {
        "type": "object",
        "required": ["project_dir"],
        "properties": {
            "project_dir": {"type": "string"},
            "config": {"type": "object"},
            "mode": {"type": "string", "enum": ["prepare", "serve"], "default": "serve"},
            "host": {"type": "string", "default": "127.0.0.1"},
            "port": {"type": "integer", "minimum": 0, "maximum": 65535, "default": 0},
            "project_id": {"type": "string"},
            "pipeline_type": {"type": "string"},
            "active_stage": {"type": "string"},
            "surface_mode": {"type": "string", "enum": ["gate_workspace", "project_cockpit"]},
            "open_browser": {"type": "boolean", "default": False},
        },
    }
    output_schema = {
        "type": "object",
        "required": [
            "surface_id",
            "surface_contract",
            "config_path",
            "html_path",
            "view_spec_path",
            "response_path",
            "server_state",
            "renderer",
        ],
        "properties": {
            "surface_id": {"type": "string"},
            "surface_contract": {"type": "string"},
            "config_id": {"type": "string"},
            "config_path": {"type": "string"},
            "html_path": {"type": "string"},
            "view_spec_path": {"type": "string"},
            "response_path": {"type": "string"},
            "server_state": {"type": "string"},
            "renderer": {"type": "string"},
            "protocol": {"type": "string"},
            "url": {"type": ["string", "null"]},
            "browser_url": {"type": ["string", "null"]},
            "pid": {"type": ["integer", "null"]},
            "wsl2": {"type": "boolean"},
            "browser_opened": {"type": "boolean"},
            "instructions": {"type": "string"},
        },
    }
    artifact_schema = {
        "produces": ["ui_surface_config"],
        "expects_response": "ui_surface_response",
    }
    idempotency_key_fields = [
        "project_dir",
        "config",
        "mode",
        "host",
        "port",
        "surface_mode",
        "open_browser",
    ]
    user_visible_verification = [
        "Use the returned localhost URL for the GenUI compatibility workspace when an interactive decision is needed.",
        "Confirm projects/<project>/artifacts/ui/<surface_id>/response.json exists before mapping to canonical artifacts.",
        "Use the project cockpit as read-only project observability; it does not advance stages.",
    ]

    def _config_from_inputs(self, inputs: dict[str, Any]) -> dict[str, Any]:
        config = inputs.get("config")
        if isinstance(config, dict):
            return config
        if inputs.get("surface_mode") == "project_cockpit":
            project_id = inputs.get("project_id") or Path(inputs["project_dir"]).name
            pipeline_type = inputs.get("pipeline_type") or "ad-video"
            return build_project_cockpit_config(
                Path(inputs["project_dir"]),
                project_id=project_id,
                pipeline_type=pipeline_type,
                active_stage=inputs.get("active_stage"),
            )
        raise ValueError("genui_surface requires a config or surface_mode='project_cockpit'")

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            project_dir = Path(inputs["project_dir"])
            config = self._config_from_inputs(inputs)
            mode = inputs.get("mode", "serve")
            host = inputs.get("host", "127.0.0.1")
            if host not in {"127.0.0.1", "localhost"}:
                raise ValueError("genui_surface only serves localhost-bound surfaces")
            if mode not in {"prepare", "serve"}:
                raise ValueError("mode must be 'prepare' or 'serve'")

            cleanup_orphaned_servers(project_dir)
            bundle = write_surface_bundle(project_dir, config)
            surface_id = bundle.config["surface_id"]
            data: dict[str, Any] = {
                "surface_id": surface_id,
                "surface_contract": SURFACE_CONTRACT,
                "config_id": surface_id,
                "config_path": str(bundle.config_path),
                "html_path": str(bundle.html_path),
                "view_spec_path": str(bundle.view_spec_path),
                "response_path": str(bundle.response_path),
                "server_state": "prepared",
                "renderer": RENDERER_NAME,
                "protocol": "ag-ui",
                "url": None,
                "browser_url": None,
                "pid": None,
                "wsl2": is_wsl2(),
                "browser_opened": False,
                "instructions": (
                    f"GenUI compatibility files prepared at {bundle.html_path} and {bundle.view_spec_path}. "
                    "Run genui_surface in serve mode to render the product workspace, then "
                    f"wait while {bundle.response_path} is validated before canonical artifacts are updated."
                ),
            }

            artifacts = [str(bundle.config_path), str(bundle.html_path), str(bundle.view_spec_path)]
            if mode == "serve":
                port = int(inputs.get("port") or 0)
                if port == 0:
                    port = self._choose_port(host)
                submit_url = f"http://{host}:{port}/submit"
                submit_nonce = secrets.token_urlsafe(32)
                write_surface_view_spec(
                    bundle.view_spec_path,
                    bundle.config,
                    submit_url=submit_url,
                    submit_nonce=submit_nonce,
                )
                with open(bundle.html_path, "w") as f:
                    from lib.genui.view_spec import render_shell_html

                    f.write(render_shell_html())
                process = self._start_server(bundle, host, port, submit_nonce)
                try:
                    self._wait_until_ready(process, host, port)
                except Exception:
                    if process.poll() is None:
                        process.terminate()
                    raise
                # Give the server a short moment to finish writing server.pid on slow filesystems.
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
                        "pid": process.pid,
                        "browser_opened": browser_opened,
                        "instructions": (
                            f"Browser URL available at {browser_url}. Review the GenUI compatibility surface when needed, submit it, "
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

            return ToolResult(success=True, data=data, artifacts=artifacts)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
