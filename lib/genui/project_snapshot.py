"""Read-only project cockpit snapshots for GenUI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lib.pipeline_loader import get_stage_order, load_pipeline
from lib.genui.surface import SURFACE_CONTRACT, validate_surface_config


MEDIA_EXTENSIONS = {
    ".apng": "image",
    ".gif": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".m4a": "audio",
    ".mov": "video",
    ".mp3": "audio",
    ".mp4": "video",
    ".ogg": "audio",
    ".png": "image",
    ".wav": "audio",
    ".webm": "video",
    ".webp": "image",
}


def _safe_id(value: Any, *, fallback: str) -> str:
    raw = str(value or fallback)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-_.")
    if not slug:
        slug = fallback
    if not slug[0].isalnum():
        slug = f"cockpit-{slug}"
    return slug[:64]


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.relative_to(project_root).as_posix()
    except ValueError:
        return str(path)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _safe_json_summary(path: Path, project_root: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {
            "id": _safe_id(path.stem, fallback="artifact"),
            "artifact": path.stem,
            "path": _relative_path(path, project_root),
            "status": "unreadable",
        }
    if isinstance(data, dict):
        keys = sorted(str(key) for key in data.keys())[:12]
    else:
        keys = []
    rel = _relative_path(path, project_root)
    return {
        "id": _safe_id(Path(rel).with_suffix("").as_posix(), fallback=path.stem),
        "artifact": path.stem,
        "path": rel,
        "status": "present",
        "keys": keys,
    }


def _load_pipeline_manifest(pipeline_type: str) -> dict[str, Any] | None:
    try:
        return load_pipeline(pipeline_type)
    except Exception:
        return None


def _stage_order(pipeline_type: str, active_stage: str | None) -> list[str]:
    manifest = _load_pipeline_manifest(pipeline_type)
    if manifest is None:
        return [active_stage or "current"]
    return get_stage_order(manifest)


def _active_stage_parts(active_stage: str | None) -> tuple[str | None, str | None]:
    if not active_stage:
        return None, None
    top_level_stage, separator, sub_stage = active_stage.partition(".")
    if not separator:
        return active_stage, None
    return top_level_stage, sub_stage


def _checkpoint_map(project_root: Path) -> dict[str, dict[str, Any]]:
    checkpoints: dict[str, dict[str, Any]] = {}
    for path in sorted(project_root.glob("checkpoint_*.json")):
        data = _load_json(path)
        stage = path.stem.removeprefix("checkpoint_")
        if isinstance(data, dict):
            stage = str(data.get("stage") or stage)
        checkpoints[stage] = {
            "path": path,
            "data": data if isinstance(data, dict) else {},
        }
    return checkpoints


def _checkpoint_status(data: dict[str, Any], *, active: bool) -> str:
    status = data.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    if data.get("approved") is True:
        return "approved"
    if data.get("approved") is False:
        return "awaiting_human" if active else "pending"
    return "active" if active else "pending"


def _timeline_items(pipeline_type: str, active_stage: str | None) -> list[dict[str, Any]]:
    stages = _stage_order(pipeline_type, active_stage)
    active_top_level_stage, active_sub_stage = _active_stage_parts(active_stage)
    items: list[dict[str, Any]] = []
    for stage in stages:
        active = stage == active_top_level_stage or stage == active_stage
        item = {
            "id": stage,
            "label": stage.replace("_", " ").title(),
            "status": "active" if active else "pending",
        }
        if active and active_sub_stage:
            item.update(
                {
                    "active_stage": active_stage,
                    "active_sub_stage": active_sub_stage,
                    "active_sub_stage_label": active_sub_stage.replace("_", " ").title(),
                }
            )
        items.append(item)
    return items


def _timeline_items_with_checkpoints(
    project_root: Path,
    pipeline_type: str,
    active_stage: str | None,
) -> list[dict[str, Any]]:
    checkpoints = _checkpoint_map(project_root)
    items: list[dict[str, Any]] = []
    for item in _timeline_items(pipeline_type, active_stage):
        stage = item["id"]
        checkpoint = checkpoints.get(item.get("active_stage") or stage) or checkpoints.get(stage)
        if checkpoint:
            data = checkpoint["data"]
            active = item.get("status") == "active" or item.get("active_stage") == active_stage
            item = {
                **item,
                "status": _checkpoint_status(data, active=active),
                "checkpoint": checkpoint["path"].name,
            }
            if data.get("approved") is not None:
                item["approved"] = bool(data["approved"])
        items.append(item)
    return items


def _artifact_summaries(project_root: Path) -> list[dict[str, Any]]:
    artifact_dir = project_root / "artifacts"
    if not artifact_dir.exists():
        return []
    return [
        _safe_json_summary(path, project_root)
        for path in sorted(artifact_dir.rglob("*.json"))
        if path.is_file() and "ui" not in path.relative_to(artifact_dir).parts
    ][:200]


def _artifact_ref_path(artifact: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", artifact).strip("_")
    return token or "artifact"


def _decision_items(project_root: Path) -> list[dict[str, Any]]:
    data = _load_json(project_root / "artifacts" / "decision_log.json")
    if isinstance(data, dict):
        entries = data.get("decisions") or data.get("entries") or data.get("decision_log") or []
    elif isinstance(data, list):
        entries = data
    else:
        entries = []
    items: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        category = entry.get("category") or entry.get("type") or entry.get("decision") or "decision"
        item = {
            "id": _safe_id(entry.get("id") or f"decision-{index + 1}", fallback="decision"),
            "category": str(category),
        }
        for key in ["stage", "selected", "status", "timestamp", "approved", "reason"]:
            if key in entry:
                item[key] = entry[key]
        items.append(item)
    return items[:50]


def _first_number(data: Any, names: set[str]) -> int | float | None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in names and isinstance(value, (int, float)) and not isinstance(value, bool):
                return value
        for value in data.values():
            found = _first_number(value, names)
            if found is not None:
                return found
    if isinstance(data, list):
        for value in data:
            found = _first_number(value, names)
            if found is not None:
                return found
    return None


def _budget_cost_items(project_root: Path) -> list[dict[str, Any]]:
    artifact_dir = project_root / "artifacts"
    if not artifact_dir.exists():
        return []
    paths = sorted(path for path in artifact_dir.rglob("*.json") if path.is_file())
    paths.sort(key=lambda path: path.name != "production_proposal.json")
    items: list[dict[str, Any]] = []
    for path in paths:
        data = _load_json(path)
        if data is None:
            continue
        approved_budget = _first_number(
            data,
            {"approved_budget_usd", "budget_usd", "total_budget_usd", "max_budget_usd"},
        )
        estimated_cost = _first_number(
            data,
            {"estimated_cost_usd", "total_usd", "cost_usd", "actual_cost_usd"},
        )
        if approved_budget is None and estimated_cost is None:
            continue
        item: dict[str, Any] = {
            "id": _safe_id(path.stem, fallback="budget"),
            "artifact": path.stem,
            "path": _relative_path(path, project_root),
        }
        if approved_budget is not None:
            item["approved_budget_usd"] = approved_budget
        if estimated_cost is not None:
            item["estimated_cost_usd"] = estimated_cost
        items.append(item)
    return items[:25]


def _media_refs(project_root: Path) -> list[dict[str, Any]]:
    roots = [
        project_root / "renders",
        project_root / "assets",
        project_root / "reference_assets",
        project_root / "media",
        project_root / "outputs",
    ]
    refs: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            kind = MEDIA_EXTENSIONS.get(path.suffix.lower())
            if not kind:
                continue
            rel = path.relative_to(project_root).as_posix()
            refs.append(
                {
                    "id": _safe_id(Path(rel).with_suffix("").as_posix(), fallback="media"),
                    "kind": kind,
                    "title": path.name,
                    "path": f"/media/{rel}",
                    "alt": rel,
                }
            )
            if len(refs) >= 100:
                return refs
    return refs


def _pending_responses(project_root: Path) -> list[dict[str, Any]]:
    ui_root = project_root / "artifacts" / "ui"
    if not ui_root.exists():
        return []
    pending: list[dict[str, Any]] = []
    for config_path in sorted(ui_root.glob("*/config.json")):
        bundle_dir = config_path.parent
        if (bundle_dir / "response.json").exists():
            continue
        data = _load_json(config_path)
        session_id = bundle_dir.name
        if isinstance(data, dict):
            session_id = str(data.get("session_id") or data.get("config_id") or session_id)
        pending.append(
            {
                "session_id": session_id,
                "config_path": _relative_path(config_path, project_root),
                "response_path": _relative_path(bundle_dir / "response.json", project_root),
            }
        )
    return pending[:100]


def _stale_sessions(project_root: Path) -> list[dict[str, Any]]:
    ui_root = project_root / "artifacts" / "ui"
    if not ui_root.exists():
        return []
    stale: list[dict[str, Any]] = []
    for state_path in sorted(ui_root.glob("*/server.json")):
        data = _load_json(state_path)
        if not isinstance(data, dict):
            continue
        response_path = Path(str(data.get("response_path") or state_path.with_name("response.json")))
        if not response_path.is_absolute():
            response_path = project_root / response_path
        if data.get("server_state") == "running" and not response_path.exists():
            stale.append(
                {
                    "session_id": str(data.get("session_id") or state_path.parent.name),
                    "state_path": _relative_path(state_path, project_root),
                    "url": data.get("url"),
                    "response_path": _relative_path(response_path, project_root),
                }
            )
    return stale[:100]


def _journal_items(project_root: Path) -> list[dict[str, Any]]:
    journal = _load_json(project_root / "artifacts" / "ui" / "interaction_journal.json")
    if not isinstance(journal, dict):
        return []
    entries = journal.get("interactions") or []
    items: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        validation = entry.get("validation") if isinstance(entry.get("validation"), dict) else {}
        items.append(
            {
                "interaction_id": str(entry.get("interaction_id") or entry.get("request_id") or "interaction"),
                "mode": entry.get("mode"),
                "status": entry.get("status"),
                "stage": entry.get("stage"),
                "gate": entry.get("gate"),
                "validation_status": validation.get("status"),
            }
        )
    return items[-100:]


def _validation_blockers(project_root: Path) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for item in _journal_items(project_root):
        if item.get("validation_status") in {"blocked", "invalid"}:
            blockers.append(item)
    return blockers


def build_project_cockpit_snapshot(
    project_dir: Path | str,
    *,
    pipeline_type: str,
    active_stage: str | None = None,
) -> dict[str, Any]:
    """Return project cockpit facts independent of the renderer version."""
    project_root = Path(project_dir)
    artifact_items = _artifact_summaries(project_root)
    decision_items = _decision_items(project_root)
    budget_cost_items = _budget_cost_items(project_root)
    media_refs = _media_refs(project_root)
    pending_responses = _pending_responses(project_root)
    stale_sessions = _stale_sessions(project_root)
    validation_blockers = _validation_blockers(project_root)
    journal_items = _journal_items(project_root)
    return {
        "timeline_items": _timeline_items_with_checkpoints(project_root, pipeline_type, active_stage),
        "artifact_items": artifact_items,
        "decision_items": decision_items,
        "budget_cost_items": budget_cost_items,
        "media_refs": media_refs,
        "pending_responses": pending_responses,
        "stale_sessions": stale_sessions,
        "validation_blockers": validation_blockers,
        "journal_items": journal_items,
        "artifact_count": len(artifact_items),
        "decision_count": len(decision_items),
        "budget_cost_count": len(budget_cost_items),
        "media_count": len(media_refs),
        "pending_response_count": len(pending_responses),
        "stale_session_count": len(stale_sessions),
        "validation_blocker_count": len(validation_blockers),
    }


def build_project_cockpit_config(
    project_dir: Path | str,
    *,
    project_id: str,
    pipeline_type: str,
    active_stage: str | None = None,
) -> dict[str, Any]:
    """Build a read-only compatibility project cockpit config from local project artifacts."""
    project_root = Path(project_dir)
    snapshot = build_project_cockpit_snapshot(
        project_root,
        pipeline_type=pipeline_type,
        active_stage=active_stage,
    )
    artifact_items = snapshot["artifact_items"]
    decision_items = snapshot["decision_items"]
    budget_cost_items = snapshot["budget_cost_items"]
    media_refs = snapshot["media_refs"]
    blocks = [
        {
            "id": "timeline",
            "type": "CockpitTimeline",
            "title": "Pipeline timeline",
            "items": snapshot["timeline_items"],
        },
        {
            "id": "artifacts",
            "type": "CockpitArtifactGallery",
            "title": "Artifacts",
            "items": artifact_items,
            "artifact_ref_ids": [item["id"] for item in artifact_items],
        },
    ]
    if decision_items:
        blocks.append(
            {
                "id": "decision_history",
                "type": "CockpitArtifactGallery",
                "title": "Decision history",
                "items": decision_items,
            }
        )
    if budget_cost_items:
        blocks.append(
            {
                "id": "budget_cost",
                "type": "CockpitArtifactGallery",
                "title": "Budget and cost",
                "items": budget_cost_items,
            }
        )
    if media_refs:
        blocks.append(
            {
                "id": "media_outputs",
                "type": "CockpitArtifactGallery",
                "title": "Media outputs",
                "media_ids": [item["id"] for item in media_refs],
            }
        )
    blocks.append(
        {
            "id": "trace",
            "type": "ArtifactTracePanel",
            "title": "Cockpit boundaries",
            "trace_ref_ids": ["read-only-boundary"],
        }
    )
    config = {
        "contract": SURFACE_CONTRACT,
        "surface_id": "project-cockpit",
        "config_id": "project-cockpit",
        "project_id": project_id,
        "pipeline_type": pipeline_type,
        "stage": active_stage or "project",
        "gate": "cockpit",
        "mode": "project_cockpit",
        "title": "Project Cockpit",
        "description": "Read-only GenUI overview of pipeline progress, artifacts, and pending human gates.",
        "ag_ui": {
            "thread_id": project_id,
            "run_id": "project-cockpit",
        },
        "media_refs": media_refs,
        "artifact_refs": [
            {
                "id": item["id"],
                "artifact": item["artifact"],
                "path": _artifact_ref_path(item["artifact"]),
                "label": item["artifact"].replace("_", " ").title(),
                "summary": item.get("status"),
            }
            for item in artifact_items
        ],
        "trace_refs": [
            {
                "id": "read-only-boundary",
                "label": "Read-only cockpit",
                "source": "AGENT_GUIDE.md",
                "summary": "The cockpit observes project state and opens gates; it does not advance pipeline stages.",
            }
        ],
        "blocks": blocks,
        "actions": [],
        "metadata": {
            "genui_contract": "genui",
            "project_cockpit": True,
            "read_only": True,
            "protocol": "ag-ui",
        },
    }
    validate_surface_config(config)
    return config
