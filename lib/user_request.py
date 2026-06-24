"""User-request capture for project workspaces.

The verbatim user instruction that started a project is the canonical
source of intent — every downstream artifact (intake_brief, brief,
research_brief, ...) is an interpretation of it. This module writes that
record at project init, before any stage runs.

Two outputs per project:

- ``projects/<project_id>/artifacts/user_request.json`` — schema-validated
  canonical record (see ``schemas/artifacts/user_request.schema.json``).
- ``projects/<project_id>/USER_PROMPT.md`` — human-readable mirror surfaced
  at the project root for casual browsing and audit.

Append-only by design: revisions to the user's intent during intake become
new ``prompt_turns`` entries. The original ``prompt`` is never rewritten.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from schemas.artifacts import validate_artifact

ARTIFACT_FILENAME = "user_request.json"
MIRROR_FILENAME = "USER_PROMPT.md"
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Reference:
    """A concrete material the user pointed to (URL, file, library track)."""

    kind: str  # "url" | "file" | "music_library" | "other"
    value: str
    role: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "value": self.value}
        if self.role is not None:
            out["role"] = self.role
        if self.note is not None:
            out["note"] = self.note
        return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _artifact_path(project_dir: Path) -> Path:
    return project_dir / "artifacts" / ARTIFACT_FILENAME


def _mirror_path(project_dir: Path) -> Path:
    return project_dir / MIRROR_FILENAME


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant {value}")


def _validate_project_workspace_dir(project_dir: Path) -> None:
    if len(project_dir.parts) < 2 or project_dir.parts[-2] != "projects":
        raise ValueError(
            "user_request project_dir must be under projects/<project-name>"
        )


def _resolve_project_id(project_dir: Path, project_id: Optional[str]) -> str:
    resolved = project_id or project_dir.name
    if not PROJECT_ID_PATTERN.fullmatch(resolved):
        raise ValueError(
            "user_request project_id must be kebab-case "
            "(lowercase letters, numbers, and single hyphens)"
        )
    if resolved != project_dir.name:
        raise ValueError(
            "user_request project_id must match project directory name "
            f"({project_dir.name!r})"
        )
    return resolved


def _build_payload(
    *,
    project_id: str,
    prompt: str,
    references: Iterable[Reference] = (),
    pipeline_hint: Optional[str] = None,
    session_id: Optional[str] = None,
    language: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    created_at: Optional[str] = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": "1.0",
        "project_id": project_id,
        "created_at": created_at or _now_iso(),
        "prompt": prompt,
        "prompt_turns": [],
        "references": [r.to_dict() for r in references],
        "pipeline_hint": pipeline_hint,
        "session_id": session_id,
        "language": language,
        "metadata": metadata or {},
    }
    return payload


def _render_mirror(payload: dict[str, Any]) -> str:
    """Render USER_PROMPT.md from the canonical payload."""
    lines: list[str] = []
    lines.append(f"# User Request — {payload['project_id']}")
    lines.append("")
    lines.append(f"_Captured at {payload['created_at']}_")
    if payload.get("pipeline_hint"):
        lines.append(f"_Pipeline hint: `{payload['pipeline_hint']}`_")
    if payload.get("language"):
        lines.append(f"_Language: `{payload['language']}`_")
    if payload.get("session_id"):
        lines.append(f"_Session: `{payload['session_id']}`_")
    lines.append("")
    lines.append("## Original prompt")
    lines.append("")
    lines.append(payload["prompt"].rstrip())
    lines.append("")

    turns = payload.get("prompt_turns") or []
    if turns:
        lines.append("## Follow-up turns")
        lines.append("")
        for turn in turns:
            header = f"### {turn['at']}"
            if turn.get("note"):
                header += f" — {turn['note']}"
            lines.append(header)
            lines.append("")
            lines.append(turn["text"].rstrip())
            lines.append("")

    refs = payload.get("references") or []
    if refs:
        lines.append("## References mentioned")
        lines.append("")
        for ref in refs:
            bullet = f"- `{ref['kind']}` — {ref['value']}"
            if ref.get("role"):
                bullet += f" ({ref['role']})"
            if ref.get("note"):
                bullet += f" — {ref['note']}"
            lines.append(bullet)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Canonical record of user intent for this project. "
        "Do not edit; append new turns via `lib/user_request.append_turn`. "
        f"Machine-readable form: `artifacts/{ARTIFACT_FILENAME}`._"
    )
    lines.append("")
    return "\n".join(lines)


def _read_payload(project_dir: Path) -> dict[str, Any]:
    path = _artifact_path(project_dir)
    if not path.exists():
        raise FileNotFoundError(
            f"No user_request.json at {path}. "
            "Call record_user_request() first when initializing a project."
        )
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f, parse_constant=_reject_json_constant)
        json.dumps(payload, allow_nan=False)
    except ValueError as exc:
        raise ValueError(f"user_request must be strict JSON serializable: {exc}") from exc
    return payload


def _write_mirror(project_dir: Path, payload: dict[str, Any]) -> None:
    mirror_path = _mirror_path(project_dir)
    mirror_path.parent.mkdir(parents=True, exist_ok=True)
    with open(mirror_path, "w") as f:
        f.write(_render_mirror(payload))


def _write_payload(project_dir: Path, payload: dict[str, Any]) -> Path:
    _validate_project_workspace_dir(project_dir)
    validate_artifact("user_request", payload)
    try:
        serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"user_request must be strict JSON serializable: {exc}") from exc

    artifact_path = _artifact_path(project_dir)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifact_path, "w") as f:
        f.write(serialized)
        f.write("\n")

    _write_mirror(project_dir, payload)
    return artifact_path


def record_user_request(
    project_dir: Path,
    prompt: str,
    *,
    project_id: Optional[str] = None,
    references: Iterable[Reference] = (),
    pipeline_hint: Optional[str] = None,
    session_id: Optional[str] = None,
    language: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    overwrite: bool = False,
) -> Path:
    """Record the verbatim user instruction at project init.

    Idempotent by default: if ``user_request.json`` already exists, the call
    is a no-op (returns the existing path) so that re-running an intake
    flow does not silently clobber the original prompt. Pass
    ``overwrite=True`` only when a stale or test record needs replacing.

    Returns the path to the canonical JSON artifact. The Markdown mirror is
    written alongside it.
    """
    project_dir = Path(project_dir)
    if not prompt or not prompt.strip():
        raise ValueError("user_request prompt must be non-empty")

    resolved_project_id = _resolve_project_id(project_dir, project_id)
    _validate_project_workspace_dir(project_dir)
    artifact_path = _artifact_path(project_dir)
    if artifact_path.exists() and not overwrite:
        payload = _read_payload(project_dir)
        validate_artifact("user_request", payload)
        if not _mirror_path(project_dir).exists():
            _write_mirror(project_dir, payload)
        return artifact_path

    payload = _build_payload(
        project_id=resolved_project_id,
        prompt=prompt,
        references=references,
        pipeline_hint=pipeline_hint,
        session_id=session_id,
        language=language,
        metadata=metadata,
    )
    return _write_payload(project_dir, payload)


def append_turn(
    project_dir: Path,
    text: str,
    *,
    note: Optional[str] = None,
    at: Optional[str] = None,
) -> Path:
    """Append a verbatim user follow-up turn to an existing user_request.

    Use when the user materially refines the brief during intake (changed
    platform, added a reference, swapped tone). The original ``prompt``
    field is never modified.
    """
    project_dir = Path(project_dir)
    if not text or not text.strip():
        raise ValueError("prompt turn text must be non-empty")

    payload = _read_payload(project_dir)
    turn: dict[str, Any] = {
        "at": at or _now_iso(),
        "text": text,
    }
    if note is not None:
        turn["note"] = note
    payload.setdefault("prompt_turns", []).append(turn)
    return _write_payload(project_dir, payload)


def add_reference(
    project_dir: Path,
    reference: Reference,
) -> Path:
    """Append a single Reference entry to an existing user_request."""
    project_dir = Path(project_dir)
    payload = _read_payload(project_dir)
    payload.setdefault("references", []).append(reference.to_dict())
    return _write_payload(project_dir, payload)


def read_user_request(project_dir: Path) -> dict[str, Any]:
    """Read and validate the user_request payload for a project."""
    payload = _read_payload(Path(project_dir))
    validate_artifact("user_request", payload)
    return payload
