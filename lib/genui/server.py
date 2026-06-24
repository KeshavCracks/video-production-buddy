"""Local GenUI browser session server.

This module intentionally uses only the Python standard library. The server is
project-scoped and writes only ui_session_response or explicit ui_surface_response;
canonical artifact writes remain an agent responsibility.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
import re
import signal
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from lib.genui import render_shell_html
from lib.genui.view_spec import VIEW_SPEC_FILENAME, validate_view_spec


STATIC_RENDERER_DIR = Path(__file__).resolve().parent / "static" / "renderer"
MAX_SUBMISSION_BYTES = 64 * 1024
PASSIVE_MEDIA_TYPES = {
    ".apng": "image/apng",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".flac": "audio/flac",
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".m4a": "audio/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".mp4": "video/mp4",
    ".oga": "audio/ogg",
    ".ogg": "audio/ogg",
    ".ogv": "video/ogg",
    ".png": "image/png",
    ".txt": "text/plain",
    ".vtt": "text/vtt",
    ".wav": "audio/wav",
    ".webm": "video/webm",
    ".webp": "image/webp",
}
PROJECT_MEDIA_DIRS = {"assets", "media", "outputs", "reference_assets", "renders"}
SAFE_MEDIA_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$")
CSP_VALUE = (
    "default-src 'self'; connect-src 'self'; img-src 'self'; "
    "media-src 'self'; script-src 'self'; style-src 'self'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)
SESSION_CONTRACT = "genui_session"
SURFACE_CONTRACT = "genui_surface"


class GenUIRequestHandler(BaseHTTPRequestHandler):
    config: dict[str, Any]
    project_root: Path
    response_path: Path
    events_path: Path
    view_spec_path: Path
    draft_path: Path
    submit_nonce: str

    def _request_path(self) -> str:
        return urlparse(self.path).path

    def _request_query(self) -> dict[str, list[str]]:
        return parse_qs(urlparse(self.path).query, keep_blank_values=False)

    def _json_body(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, allow_nan=False)

    def _is_allowed_origin(self, origin: str | None) -> bool:
        if origin is None:
            return True
        if origin == "null":
            return False

        parsed = urlparse(origin)
        if parsed.scheme != "http":
            return False
        try:
            hostname = parsed.hostname
            origin_port = parsed.port or 80
        except ValueError:
            return False
        if hostname not in {"127.0.0.1", "localhost", "::1"}:
            return False
        return origin_port == self.server.server_address[1]

    def _is_allowed_submit_origin(self, origin: str | None) -> bool:
        return origin is not None and self._is_allowed_origin(origin)

    def _cors_headers(self) -> dict[str, str]:
        origin = self.headers.get("Origin")
        if origin is None or not self._is_allowed_origin(origin):
            return {}

        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Vary": "Origin",
        }

    def _send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP_VALUE)
        for header, value in self._cors_headers().items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(encoded)

    def _send_bytes(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", CSP_VALUE)
        for header, value in self._cors_headers().items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_event_stream(self, events: list[dict[str, Any]], *, event_cursor: str | None = None) -> None:
        chunks = []
        for event in events:
            event_type = str(event.get("type", "message"))
            if event.get("cursor"):
                chunks.append(f"id: {event['cursor']}\n")
            chunks.append(f"event: {event_type}\n")
            chunks.append(f"data: {json.dumps(event, ensure_ascii=False, allow_nan=False)}\n\n")
        body = "".join(chunks).encode("utf-8")
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if event_cursor:
            self.send_header("X-GenUI-Event-Cursor", event_cursor)
        for header, value in self._cors_headers().items():
            self.send_header(header, value)
        self.end_headers()
        self.wfile.write(body)

    def _load_spec_state(self) -> dict[str, Any]:
        spec = _load_view_spec(self.view_spec_path)
        return spec.get("state") or {}

    def _is_session_config(self) -> bool:
        return self.config.get("contract") == SESSION_CONTRACT or self.config.get("version") == "3.0"

    def _contract_payload_value(self) -> str | None:
        contract = self.config.get("contract")
        if isinstance(contract, str):
            return contract
        if self.config.get("version") == "3.0":
            return SESSION_CONTRACT
        if self.config.get("version") == "2.0":
            return SURFACE_CONTRACT
        return None

    def _genui_contract_payload_value(self) -> str | None:
        metadata = self.config.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("genui_contract"), str):
            return metadata["genui_contract"]
        contract = self.config.get("genui_contract")
        if isinstance(contract, str):
            return contract
        return "genui"

    def _session_events(self) -> list[dict[str, Any]]:
        state = self._load_spec_state()
        if self._is_session_config():
            from lib.genui.session import ensure_session_events

            return ensure_session_events(self.events_path, self.config, state)
        from lib.genui.surface import build_ag_ui_events

        events = build_ag_ui_events(self.config, state)
        if not self.events_path.exists():
            try:
                event_lines = [
                    json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n"
                    for event in events
                ]
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"GenUI event log must be strict JSON serializable: {exc}"
                ) from exc
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.events_path, "w", encoding="utf-8") as f:
                f.writelines(event_lines)
        return events

    def _session_status_payload(self) -> dict[str, Any]:
        events = self._session_events()
        last_event = events[-1] if events else {}
        return {
            "ok": True,
            "session_id": self.config.get("session_id") or self.config.get("surface_id") or self.config.get("config_id"),
            "genui_contract": self._genui_contract_payload_value(),
            "contract": self._contract_payload_value(),
            "server_state": "submitted" if self.response_path.exists() else "running",
            "response_exists": self.response_path.exists(),
            "response_path": str(self.response_path),
            "draft_exists": self.draft_path.exists(),
            "draft_path": str(self.draft_path),
            "events_path": str(self.events_path),
            "event_count": len(events),
            "event_cursor": last_event.get("cursor"),
        }

    def do_GET(self) -> None:
        request_path = self._request_path()
        if request_path in {"/", "/form"}:
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            self._send(
                HTTPStatus.OK,
                render_shell_html(),
                "text/html; charset=utf-8",
            )
            return
        if request_path == "/spec.json":
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            try:
                spec = _load_view_spec(self.view_spec_path)
                body = json.dumps(spec, indent=2, allow_nan=False)
            except OSError as exc:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    self._json_body({"ok": False, "error": str(exc)}),
                    "application/json; charset=utf-8",
                )
                return
            except Exception as exc:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    self._json_body({"ok": False, "error": str(exc)}),
                    "application/json; charset=utf-8",
                )
                return
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
            return
        if request_path == "/draft":
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            if not self.draft_path.exists():
                self._send(HTTPStatus.OK, self._json_body({"ok": True, "draft": None}), "application/json; charset=utf-8")
                return
            try:
                draft = _loads_strict_json(self.draft_path.read_text())
                body = json.dumps({"ok": True, "draft": draft}, indent=2, ensure_ascii=False, allow_nan=False)
            except Exception as exc:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    self._json_body({"ok": False, "error": str(exc)}),
                    "application/json; charset=utf-8",
                )
                return
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
            return
        if request_path == "/events":
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            try:
                events = self._session_events()
                after = (self._request_query().get("after") or [None])[0]
                if self._is_session_config():
                    from lib.genui.session import filter_session_events_after

                    visible_events = filter_session_events_after(events, after)
                else:
                    visible_events = events
                last_event = events[-1] if events else {}
            except Exception as exc:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    self._json_body({"ok": False, "error": str(exc)}),
                    "application/json; charset=utf-8",
                )
                return
            self._send_event_stream(visible_events, event_cursor=last_event.get("cursor"))
            return
        if request_path == "/session.json":
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            try:
                body = json.dumps(self._session_status_payload(), indent=2, ensure_ascii=False, allow_nan=False)
            except Exception as exc:
                self._send(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    self._json_body({"ok": False, "error": str(exc)}),
                    "application/json; charset=utf-8",
                )
                return
            self._send(HTTPStatus.OK, body, "application/json; charset=utf-8")
            return
        if request_path.startswith("/assets/"):
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            try:
                asset_path = (STATIC_RENDERER_DIR / request_path.lstrip("/")).resolve()
                asset_path.relative_to(STATIC_RENDERER_DIR.resolve())
            except ValueError:
                self._send(HTTPStatus.FORBIDDEN, "Forbidden asset path", "text/plain; charset=utf-8")
                return
            if not asset_path.is_file():
                self._send(HTTPStatus.NOT_FOUND, "Renderer asset not found", "text/plain; charset=utf-8")
                return
            content_type = mimetypes.guess_type(asset_path.name)[0] or "application/octet-stream"
            self._send_bytes(HTTPStatus.OK, asset_path.read_bytes(), content_type)
            return
        if request_path.startswith("/media/"):
            if not self._is_allowed_origin(self.headers.get("Origin")):
                self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
                return
            try:
                media_path = _validate_media_request_path(request_path, self.project_root)
            except ValueError:
                self._send(HTTPStatus.FORBIDDEN, "Forbidden media path", "text/plain; charset=utf-8")
                return
            if not media_path.is_file():
                self._send(HTTPStatus.NOT_FOUND, "Media not found", "text/plain; charset=utf-8")
                return
            content_type = PASSIVE_MEDIA_TYPES.get(media_path.suffix.lower())
            if content_type is None:
                self._send(HTTPStatus.FORBIDDEN, "Forbidden media type", "text/plain; charset=utf-8")
                return
            self._send_bytes(HTTPStatus.OK, media_path.read_bytes(), content_type)
            return
        if request_path not in {"/", "/form"}:
            self._send(HTTPStatus.NOT_FOUND, "Not found", "text/plain; charset=utf-8")
            return

    def do_OPTIONS(self) -> None:
        if self._request_path() not in {"/submit", "/draft"}:
            self._send(HTTPStatus.NOT_FOUND, "Not found", "text/plain; charset=utf-8")
            return
        if not self._is_allowed_submit_origin(self.headers.get("Origin")):
            self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
            return
        self._send(HTTPStatus.NO_CONTENT, "", "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        request_path = self._request_path()
        if request_path not in {"/submit", "/draft"}:
            self._send(HTTPStatus.NOT_FOUND, "Not found", "text/plain; charset=utf-8")
            return
        if not self._is_allowed_submit_origin(self.headers.get("Origin")):
            self._send(HTTPStatus.FORBIDDEN, "Forbidden origin", "text/plain; charset=utf-8")
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self._send(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type must be application/json", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_SUBMISSION_BYTES:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "GenUI submission is too large", "text/plain; charset=utf-8")
                return
            raw = self.rfile.read(length)
            submission = _loads_strict_json(raw.decode("utf-8"))
            if submission.get("nonce") != self.submit_nonce:
                raise ValueError("Invalid GenUI submit nonce")
            if request_path == "/draft":
                draft_payload = {
                    "version": "1.0",
                    "session_id": self.config.get("session_id") or self.config.get("config_id"),
                    "saved_at": submission.get("saved_at"),
                    "model": submission.get("model") if isinstance(submission.get("model"), dict) else {},
                    "browser_events": submission.get("browser_events") if isinstance(submission.get("browser_events"), list) else [],
                }
                self.draft_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.draft_path, "w") as f:
                    json.dump(draft_payload, f, indent=2, ensure_ascii=False, allow_nan=False)
                    f.write("\n")
                if self._is_session_config():
                    from lib.genui.session import append_session_event

                    self._session_events()
                    append_session_event(
                        self.events_path,
                        self.config,
                        {
                            "type": "GENUI_DRAFT_SAVED",
                            "threadId": self.config["transport"]["thread_id"],
                            "runId": self.config["transport"]["run_id"],
                            "draftPath": str(self.draft_path),
                        },
                    )
                self._send(
                    HTTPStatus.OK,
                    self._json_body({"ok": True, "draft_path": str(self.draft_path)}),
                    "application/json; charset=utf-8",
                )
                return
            if self._is_session_config():
                from lib.genui.session import (
                    session_response_payload_from_submission,
                    write_session_response,
                )

                response = session_response_payload_from_submission(self.config, submission, project_dir=self.project_root)
                write_session_response(self.response_path, response)
                from lib.genui.session import append_session_event

                self._session_events()
                append_session_event(
                    self.events_path,
                    self.config,
                    {
                        "type": "GENUI_RESPONSE_SUBMITTED",
                        "threadId": self.config["transport"]["thread_id"],
                        "runId": self.config["transport"]["run_id"],
                        "action": response["action"],
                        "responseId": response["response_id"],
                    },
                )
            else:
                from lib.genui.surface import (
                    surface_response_payload_from_submission,
                    write_surface_response,
                )

                response = surface_response_payload_from_submission(self.config, submission)
                write_surface_response(self.response_path, response)
        except Exception as exc:
            self._send(
                HTTPStatus.BAD_REQUEST,
                self._json_body({"ok": False, "error": str(exc)}),
                "application/json; charset=utf-8",
            )
            return
        self._send(
            HTTPStatus.OK,
            self._json_body({"ok": True, "response_path": str(self.response_path)}),
            "application/json; charset=utf-8",
        )
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format: str, *args: Any) -> None:
        return


def _validate_server_paths(config_path: Path, response_path: Path, view_spec_path: Path) -> Path:
    config_file = config_path.resolve()
    response_file = response_path.resolve()
    view_spec_file = view_spec_path.resolve()
    bundle_dir = config_file.parent

    if config_file.name != "config.json":
        raise ValueError("GenUI config path must end with config.json")
    if response_file != bundle_dir / "response.json":
        raise ValueError("GenUI response path must be artifacts/ui/<config_id>/response.json")
    if view_spec_file != bundle_dir / VIEW_SPEC_FILENAME:
        raise ValueError(f"GenUI view spec path must be artifacts/ui/<config_id>/{VIEW_SPEC_FILENAME}")
    if bundle_dir.parent.name != "ui" or bundle_dir.parent.parent.name != "artifacts":
        raise ValueError("GenUI server paths must live under <project>/artifacts/ui/<config_id>")
    project_root = bundle_dir.parent.parent.parent
    if project_root == project_root.parent:
        raise ValueError("GenUI server paths must include a project directory before artifacts/ui")
    return project_root


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid non-standard JSON constant {value!r}")


def _loads_strict_json(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_json_constant)


def _load_view_spec(path: Path) -> dict[str, Any]:
    spec = _loads_strict_json(path.read_text())
    if not isinstance(spec, dict):
        raise ValueError("GenUI view spec must contain a JSON object")
    validate_view_spec(spec)
    return spec


def _validate_bundle_config(config: dict[str, Any], config_path: Path) -> None:
    config_id = config.get("config_id") or config.get("surface_id") or config.get("session_id")
    if not isinstance(config_id, str) or not config_id:
        raise ValueError("GenUI config must declare config_id, surface_id, or session_id")
    if config_path.resolve().parent.name != config_id:
        raise ValueError("GenUI config_id or surface_id must match the artifacts/ui/<id> bundle directory")


def _validate_media_request_path(request_path: str, project_root: Path) -> Path:
    """Resolve a /media/ request and enforce schema-equivalent safe segments."""
    relative_media_path = request_path.removeprefix("/media/")
    if (
        not relative_media_path
        or relative_media_path.startswith("/")
        or "%" in relative_media_path
        or "\\" in relative_media_path
    ):
        raise ValueError("Invalid media path")
    decoded = unquote(relative_media_path)
    if decoded != relative_media_path:
        raise ValueError("Invalid media path")
    parts = Path(decoded).parts
    if not parts or any(not SAFE_MEDIA_SEGMENT.fullmatch(part) for part in parts):
        raise ValueError("Invalid media path")
    if parts[0] in PROJECT_MEDIA_DIRS:
        media_root = (project_root / parts[0]).resolve()
        media_path = media_root.joinpath(*parts[1:]).resolve()
    else:
        media_root = (project_root / "media").resolve()
        media_path = media_root.joinpath(*parts).resolve()
    media_path.relative_to(media_root)
    return media_path


def _validate_loopback_host(host: str) -> None:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return
    try:
        if ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise ValueError("GenUI server host must be loopback-only")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--response-path", required=True)
    parser.add_argument("--view-spec-path", required=True)
    parser.add_argument("--submit-nonce", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    with open(args.config_path) as f:
        config = _loads_strict_json(f.read())

    response_path = Path(args.response_path)
    view_spec_path = Path(args.view_spec_path)
    config_path = Path(args.config_path)
    project_root = _validate_server_paths(config_path, response_path, view_spec_path)
    _validate_bundle_config(config, config_path)
    _validate_loopback_host(args.host)

    handler = type(
        "BoundGenUIRequestHandler",
        (GenUIRequestHandler,),
        {
            "config": config,
            "project_root": project_root,
            "response_path": response_path,
            "events_path": response_path.with_name("events.jsonl"),
            "draft_path": response_path.with_name("draft.json"),
            "view_spec_path": view_spec_path,
            "submit_nonce": args.submit_nonce,
        },
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)

    shutdown_requested = threading.Event()

    def _handle_signal(signum: int, frame: Any) -> None:
        shutdown_requested.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    pid_path = response_path.parent / "server.pid"
    pid_path.write_text(str(os.getpid()))

    try:
        server.serve_forever()
    finally:
        server.server_close()
        try:
            pid_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    main()
