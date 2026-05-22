"""Local GenUI form materialization and serving tool."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from lib.genui import (
    cleanup_orphaned_servers,
    get_browser_url,
    is_wsl2,
    render_form_html,
    write_form_bundle,
)
from tools.base_tool import BaseTool, ToolResult, ToolRuntime, ToolStability, ToolTier


class GenUIForm(BaseTool):
    """Materialize a project-scoped visual form and optionally serve it locally."""

    name = "genui_form"
    version = "0.1.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    runtime = ToolRuntime.LOCAL
    capability = "interaction"
    provider = "openmontage"
    capabilities = ["visual_form", "questionnaire", "approval_gate"]
    supports = {
        "modes": ["prepare", "serve"],
        "localhost_only": True,
        "canonical_writes": False,
        "components": [
            "text",
            "textarea",
            "select",
            "radio",
            "multiselect",
            "checkbox",
            "number",
            "file_path",
            "url",
            "approval",
            "info_card",
        ],
    }
    best_for = [
        "collecting dense requirements visually",
        "approval gates with many options",
        "reducing long CLI questionnaire fatigue",
    ]
    not_good_for = [
        "canonical artifact mutation without agent review",
        "public web hosting",
    ]
    side_effects = [
        "writes projects/<project>/artifacts/ui/<config_id>/config.json",
        "writes projects/<project>/artifacts/ui/<config_id>/form.html",
        "may start a localhost-only Python HTTP server in serve mode",
    ]
    input_schema = {
        "type": "object",
        "required": ["project_dir", "config"],
        "properties": {
            "project_dir": {"type": "string"},
            "config": {"type": "object"},
            "mode": {"type": "string", "enum": ["prepare", "serve"], "default": "serve"},
            "host": {"type": "string", "default": "127.0.0.1"},
            "port": {"type": "integer", "minimum": 0, "maximum": 65535, "default": 0},
        },
    }
    output_schema = {
        "type": "object",
        "required": ["config_id", "config_path", "html_path", "response_path", "server_state"],
        "properties": {
            "config_id": {"type": "string"},
            "config_path": {"type": "string"},
            "html_path": {"type": "string"},
            "response_path": {"type": "string"},
            "server_state": {"type": "string"},
            "url": {"type": ["string", "null"]},
            "browser_url": {"type": ["string", "null"]},
            "pid": {"type": ["integer", "null"]},
            "wsl2": {"type": "boolean"},
            "browser_opened": {"type": "boolean"},
            "instructions": {"type": "string"},
        },
    }
    artifact_schema = {
        "produces": ["ui_form_config"],
        "expects_response": "ui_response",
    }
    user_visible_verification = [
        "Open the returned localhost URL and submit the form.",
        "Confirm projects/<project>/artifacts/ui/<config_id>/response.json exists before mapping to canonical artifacts.",
    ]

    def _try_open_browser(self, url: str) -> bool:
        """Attempt to open the form URL in the user's default browser.

        Returns True if a browser was opened, False otherwise.
        On WSL2, tries Windows browser via cmd.exe; otherwise tries webbrowser.
        """
        import webbrowser

        if is_wsl2():
            try:
                windows_url = url.replace("127.0.0.1", "localhost", 1)
                subprocess.run(
                    ["cmd.exe", "/c", "start", windows_url],
                    check=False,
                    capture_output=True,
                    timeout=5,
                )
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return False
        return webbrowser.open(url)

    def _choose_port(self, host: str) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])

    def _start_server(self, bundle: Any, host: str, port: int) -> subprocess.Popen:
        cmd = [
            sys.executable,
            "-m",
            "lib.genui.server",
            "--config-path",
            str(bundle.config_path),
            "--response-path",
            str(bundle.response_path),
            "--host",
            host,
            "--port",
            str(port),
        ]
        return subprocess.Popen(
            cmd,
            cwd=Path(__file__).resolve().parent.parent.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    def _wait_until_ready(
        self,
        process: subprocess.Popen,
        host: str,
        port: int,
        *,
        timeout_seconds: float = 3.0,
    ) -> None:
        deadline = time.monotonic() + timeout_seconds
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(
                    "genui_form server did not become ready "
                    f"(process exited with code {process.returncode})"
                )
            try:
                with urllib.request.urlopen(f"http://{host}:{port}/", timeout=0.25) as response:
                    if response.status == 200:
                        return
            except Exception as exc:
                if process.poll() is not None:
                    raise RuntimeError(
                        "genui_form server did not become ready "
                        f"(process exited with code {process.returncode})"
                    ) from exc
                last_error = exc
                try:
                    with socket.create_connection((host, port), timeout=0.25):
                        pass
                except OSError:
                    pass
                time.sleep(0.05)
            else:
                if process.poll() is None:
                    return
        raise RuntimeError(
            "genui_form server did not become ready "
            f"on {host}:{port}: {last_error}"
        )

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        try:
            project_dir = Path(inputs["project_dir"])
            config = inputs["config"]
            mode = inputs.get("mode", "serve")
            host = inputs.get("host", "127.0.0.1")
            if host not in {"127.0.0.1", "localhost"}:
                raise ValueError("genui_form only serves localhost-bound forms")
            if mode not in {"prepare", "serve"}:
                raise ValueError("mode must be 'prepare' or 'serve'")

            cleanup_orphaned_servers(project_dir)
            bundle = write_form_bundle(project_dir, config)
            data: dict[str, Any] = {
                "config_id": config["config_id"],
                "config_path": str(bundle.config_path),
                "html_path": str(bundle.html_path),
                "response_path": str(bundle.response_path),
                "server_state": "prepared",
                "url": None,
                "browser_url": None,
                "pid": None,
                "wsl2": is_wsl2(),
                "instructions": (
                    f"Preview prepared at {bundle.html_path}. Run genui_form in serve mode "
                    f"to get a localhost URL, then wait while {bundle.response_path} is validated."
                ),
            }

            artifacts = [str(bundle.config_path), str(bundle.html_path)]
            if mode == "serve":
                port = int(inputs.get("port") or 0)
                if port == 0:
                    port = self._choose_port(host)
                submit_url = f"http://{host}:{port}/submit"
                with open(bundle.html_path, "w") as f:
                    f.write(render_form_html(config, submit_url=submit_url))
                process = self._start_server(bundle, host, port)
                try:
                    self._wait_until_ready(process, host, port)
                except Exception:
                    if process.poll() is None:
                        process.terminate()
                    raise
                localhost_url = f"http://{host}:{port}/"
                browser_url = get_browser_url(localhost_url)
                browser_opened = self._try_open_browser(browser_url)
                data.update(
                    {
                        "server_state": "running",
                        "url": localhost_url,
                        "browser_url": browser_url,
                        "pid": process.pid,
                        "browser_opened": browser_opened,
                        "instructions": (
                            f"Open {browser_url} in a local browser, submit the form, "
                            f"then wait while {bundle.response_path} is validated before any "
                            "canonical artifacts are updated."
                            + (" (Browser should have opened automatically.)" if browser_opened else "")
                        ),
                    }
                )
                bundle.state_path.parent.mkdir(parents=True, exist_ok=True)
                with open(bundle.state_path, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                artifacts.append(str(bundle.state_path))

            return ToolResult(success=True, data=data, artifacts=artifacts)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
