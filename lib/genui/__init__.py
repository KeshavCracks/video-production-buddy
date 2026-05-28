"""GenUI local interaction helpers.

GenUI is an interaction layer: it collects user choices visually, writes only
browser response artifacts, and leaves canonical artifact updates to the agent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.genui.view_spec import (
    RENDERER_NAME,
    VIEW_SPEC_FILENAME,
    render_shell_html,
)


SURFACE_DIRNAME = "ui"


def is_wsl2() -> bool:
    """Detect whether the current process is running under WSL2."""
    try:
        release = Path("/proc/version").read_text().lower()
        return "microsoft" in release and "wsl" in release
    except OSError:
        return False


def get_browser_url(url: str) -> str:
    """Adjust a localhost URL for the host browser."""
    if is_wsl2():
        return url.replace("127.0.0.1", "localhost", 1)
    return url


def _pid_cmdline(pid: int) -> list[str]:
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return []
    return [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]


def _pid_matches_genui_server(pid: int, state_path: Path) -> bool:
    cmdline = _pid_cmdline(pid)
    if not cmdline:
        return False
    if "-m" not in cmdline or "lib.genui.server" not in cmdline:
        return False

    expected = {
        "--config-path": (state_path.parent / "config.json").resolve(),
        "--response-path": (state_path.parent / "response.json").resolve(),
        "--view-spec-path": (state_path.parent / VIEW_SPEC_FILENAME).resolve(),
    }
    for flag, expected_path in expected.items():
        try:
            value = cmdline[cmdline.index(flag) + 1]
        except (ValueError, IndexError):
            return False
        try:
            if Path(value).resolve() != expected_path:
                return False
        except OSError:
            return False
    return True


def cleanup_server(state_path: Path | str) -> bool:
    """Kill an orphaned GenUI server process based on its state file or PID file."""
    import os
    import signal

    path = Path(state_path)
    pid: int | None = None
    pid_path = path.parent / "server.pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
        except (ValueError, OSError):
            pid = None

    if pid is None and path.exists():
        try:
            state = json.loads(path.read_text())
            pid = state.get("pid")
        except (json.JSONDecodeError, OSError):
            return False

    if not pid:
        return False
    if not _pid_matches_genui_server(pid, path):
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass

    for marker in (path, pid_path):
        try:
            marker.unlink()
        except OSError:
            pass
    return True


def cleanup_orphaned_servers(project_dir: Path | str) -> int:
    """Find and kill orphaned GenUI server processes for a project."""
    project_root = Path(project_dir)
    ui_dir = project_root / "artifacts" / SURFACE_DIRNAME
    if not ui_dir.exists():
        return 0
    count = 0
    for state_path in ui_dir.rglob("server.json"):
        if cleanup_server(state_path):
            count += 1
    return count


def wait_for_response(
    response_path: Path | str,
    *,
    timeout_seconds: float = 300.0,
    poll_interval: float = 2.0,
) -> dict[str, Any] | None:
    """Poll for a GenUI browser response file to appear."""
    import time

    from lib.genui.session import validate_session_response

    path = Path(response_path)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                if data.get("contract") == "genui_session_response" or data.get("version") == "3.0":
                    validate_session_response(data)
                else:
                    validate_surface_response(data)
                if data.get("action"):
                    return data
            except (Exception, json.JSONDecodeError, OSError):
                pass
        time.sleep(poll_interval)
    return None


def check_availability() -> dict[str, Any]:
    """Return a summary of GenUI browser availability for agent decisions."""
    from tools.tool_registry import registry

    registry.discover()
    session_tool = registry.get("genui_session")
    surface_tool = registry.get("genui_surface")
    session_available = session_tool is not None and session_tool.get_info().get("status") == "available"
    surface_available = surface_tool is not None and surface_tool.get_info().get("status") == "available"
    return {
        "available": session_available or surface_available,
        "default_tool": "genui_session" if session_available else "genui_surface" if surface_available else None,
        "session_available": session_available,
        "surface_available": surface_available,
        "wsl2": is_wsl2(),
        "browser_url_note": (
            "Running on WSL2 - use localhost instead of 127.0.0.1 in browser."
            if is_wsl2()
            else "Use the returned URL directly in a local browser."
        ),
    }


from lib.genui.session import (  # noqa: E402
    SessionBundle,
    build_dynamic_session_config,
    build_project_cockpit_session_config,
    compile_session_view_spec,
    review_session_response,
    session_response_payload_from_submission,
    validate_session_config,
    validate_session_response,
    write_session_bundle,
    write_session_response,
    write_session_view_spec,
)
from lib.genui.surface import (  # noqa: E402
    SurfaceBundle,
    build_dynamic_surface_config,
    compile_surface_view_spec,
    surface_response_payload_from_submission,
    validate_surface_config,
    validate_surface_response,
    write_surface_bundle,
    write_surface_response,
    write_surface_view_spec,
)


__all__ = [
    "SurfaceBundle",
    "SessionBundle",
    "build_dynamic_session_config",
    "build_project_cockpit_session_config",
    "build_dynamic_surface_config",
    "check_availability",
    "cleanup_orphaned_servers",
    "cleanup_server",
    "compile_session_view_spec",
    "compile_surface_view_spec",
    "review_session_response",
    "get_browser_url",
    "is_wsl2",
    "RENDERER_NAME",
    "render_shell_html",
    "session_response_payload_from_submission",
    "surface_response_payload_from_submission",
    "SURFACE_DIRNAME",
    "validate_session_config",
    "validate_session_response",
    "validate_surface_config",
    "validate_surface_response",
    "wait_for_response",
    "write_session_bundle",
    "write_session_response",
    "write_session_view_spec",
    "write_surface_bundle",
    "write_surface_response",
    "write_surface_view_spec",
]
