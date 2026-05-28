"""GenUI interaction journal.

The journal is agent-owned product state. Browser sessions may produce
ui_session_response, but they never update this journal directly.
"""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schemas.artifacts import validate_artifact


GENUI_CONTRACT = "genui"
JOURNAL_CONTRACT = "genui_interaction_journal"
LEGACY_PRODUCT_VERSION_KEY = "genui" + "_product" + "_version"
LEGACY_SESSION_VERSION_KEY = "session" + "_version"
LEGACY_SURFACE_VERSION_KEY = "surface" + "_version"
JOURNAL_FILENAME = "interaction_journal.json"

_VISUAL_PRIMITIVES_BY_REASON = {
    "media_review": ["media_player", "keyframe_strip", "timecoded_annotation", "issue_tracker"],
    "visual_demonstration": ["artifact_trace"],
    "side_by_side_comparison": ["side_by_side_comparison"],
    "multi_axis_selection": ["structured_fields"],
    "structured_revision_capture": ["structured_fields", "approval_attestation"],
    "project_state_overview": ["status_timeline", "artifact_trace", "budget_panel"],
    "background_status": ["status_timeline"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _reject_non_finite_json(value: Any, *, context: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"GenUI journal contains non-finite JSON number at {context}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite_json(item, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite_json(item, context=f"{context}[{index}]")


def _slug(value: Any, *, fallback: str) -> str:
    raw = str(value or fallback)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-_.")
    if not slug:
        slug = fallback
    if not slug[0].isalnum():
        slug = f"interaction-{slug}"
    return slug[:128]


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _dedupe_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(str(item) for item in values if str(item)))


def required_ui_primitives_from_decision(decision: dict[str, Any]) -> list[str]:
    primitives: list[str] = []
    for reason in _dedupe_strings(decision.get("reasons")):
        primitives.extend(_VISUAL_PRIMITIVES_BY_REASON.get(reason, []))
    if not primitives and decision.get("recommended_mode") not in {None, "cli"}:
        primitives.append("structured_fields")
    return list(dict.fromkeys(primitives))


def interaction_journal_path(project_dir: Path | str) -> Path:
    return Path(project_dir).resolve() / "artifacts" / "ui" / JOURNAL_FILENAME


def build_interaction_journal(
    *,
    project_id: str,
    pipeline_type: str,
    entries: list[dict[str, Any]] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build and validate a GenUI interaction journal payload."""
    now = _now_iso()
    normalized_entries = [_normalize_entry(entry) for entry in entries or []]
    journal = {
        "contract": JOURNAL_CONTRACT,
        "project_id": project_id,
        "pipeline_type": pipeline_type,
        "created_at": created_at or now,
        "updated_at": now,
        "interactions": normalized_entries,
        "metadata": {
            "genui_contract": GENUI_CONTRACT,
            "canonical_writes": False,
            "browser_writes": ["ui_session_response", "ui_surface_response"],
        },
    }
    validate_interaction_journal(journal)
    return journal


def validate_interaction_journal(journal: dict[str, Any]) -> None:
    normalized = _normalize_journal_contract(journal)
    _reject_non_finite_json(normalized, context="ui_interaction_journal")
    validate_artifact("ui_interaction_journal", normalized)


def _normalize_journal_contract(journal: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(journal)
    normalized.pop("version", None)
    normalized["contract"] = JOURNAL_CONTRACT
    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop(LEGACY_PRODUCT_VERSION_KEY, None)
        metadata["genui_contract"] = metadata.get("genui_contract") or GENUI_CONTRACT
    normalized["interactions"] = [_normalize_entry(entry) for entry in normalized.get("interactions") or []]
    return normalized


def read_interaction_journal(project_dir: Path | str, *, project_id: str, pipeline_type: str) -> dict[str, Any]:
    path = interaction_journal_path(project_dir)
    if not path.exists():
        return build_interaction_journal(project_id=project_id, pipeline_type=pipeline_type)
    with open(path) as f:
        journal = json.load(f)
    journal = _normalize_journal_contract(journal)
    validate_interaction_journal(journal)
    if journal["project_id"] != project_id or journal["pipeline_type"] != pipeline_type:
        raise ValueError("GenUI journal project_id/pipeline_type does not match the current interaction")
    return journal


def write_interaction_journal(project_dir: Path | str, journal: dict[str, Any]) -> Path:
    journal = _normalize_journal_contract(journal)
    validate_interaction_journal(journal)
    path = interaction_journal_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(journal, f, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    return path


def routing_decision_id(request_or_session_id: Any) -> str:
    return _slug(f"route-{request_or_session_id}", fallback="route-genui")


def entry_from_request_decision(
    request: dict[str, Any],
    decision: dict[str, Any],
    *,
    status: str,
    session_data: dict[str, Any] | None = None,
    fallback_reason: str | None = None,
    validation_status: str | None = None,
) -> dict[str, Any]:
    request_id = _slug(request.get("request_id"), fallback="genui-interaction")
    mode = str(decision.get("recommended_mode") or "cli")
    session_data = session_data or {}
    is_cli = mode == "cli"
    validation = {
        "status": validation_status or ("not_required" if is_cli else "pending"),
        "errors": [],
    }
    entry = {
        "interaction_id": request_id,
        "routing_decision_id": routing_decision_id(request_id),
        "request_id": request_id,
        "project_id": str(request["project_id"]),
        "pipeline_type": str(request["pipeline_type"]),
        "stage": str(request["stage"]),
        "gate": str(request["gate"]),
        "interaction_kind": str(decision.get("interaction_kind") or request.get("interaction_kind") or "dynamic_genui"),
        "mode": mode,
        "recommended_tool": decision.get("recommended_tool") if decision.get("recommended_tool") != "genui_interaction" else "genui_session",
        "linear_chat_sufficient": bool(decision.get("linear_chat_sufficient")),
        "reasons": _dedupe_strings(decision.get("reasons")),
        "required_ui_primitives": required_ui_primitives_from_decision(decision),
        "status": status,
        "session_id": session_data.get("session_id"),
        "decision_id": session_data.get("decision_id"),
        "stage_policy_id": decision.get("stage_policy_id") or session_data.get("stage_policy_id"),
        "schema_strategy": decision.get("schema_strategy") or session_data.get("schema_strategy"),
        "session_contract": session_data.get("session_contract"),
        "surface_contract": session_data.get("surface_contract"),
        "renderer": session_data.get("renderer"),
        "framework": session_data.get("framework"),
        "framework_renderer": session_data.get("framework_renderer"),
        "protocol": session_data.get("protocol"),
        "config_path": session_data.get("config_path"),
        "view_spec_path": session_data.get("view_spec_path"),
        "response_path": session_data.get("response_path"),
        "events_path": session_data.get("events_path"),
        "state_path": session_data.get("state_path"),
        "url": session_data.get("url"),
        "browser_url": session_data.get("browser_url"),
        "session_url": session_data.get("session_url"),
        "replay_path": session_data.get("replay_path") or session_data.get("html_path"),
        "replay_url": session_data.get("replay_url"),
        "status_url": session_data.get("status_url"),
        "fallback_reason": fallback_reason,
        "operation_event_summary": session_data.get("operation_event_summary"),
        "pending_response": session_data.get("pending_response"),
        "stale_session": session_data.get("stale_session"),
        "validation": validation,
    }
    return _normalize_entry(entry)


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    now = _now_iso()
    normalized = deepcopy(entry)
    normalized["interaction_id"] = _slug(normalized.get("interaction_id"), fallback="genui-interaction")
    normalized["routing_decision_id"] = _slug(
        normalized.get("routing_decision_id") or f"route-{normalized['interaction_id']}",
        fallback="route-genui",
    )
    normalized["request_id"] = str(normalized.get("request_id") or normalized["interaction_id"])
    normalized["mode"] = str(normalized.get("mode") or "cli")
    normalized["recommended_tool"] = normalized.get("recommended_tool")
    normalized["linear_chat_sufficient"] = bool(normalized.get("linear_chat_sufficient"))
    normalized["reasons"] = _dedupe_strings(normalized.get("reasons"))
    normalized["required_ui_primitives"] = _dedupe_strings(normalized.get("required_ui_primitives"))
    normalized.pop(LEGACY_PRODUCT_VERSION_KEY, None)
    if normalized.get(LEGACY_SESSION_VERSION_KEY):
        normalized["session_contract"] = "genui_session"
        normalized.pop(LEGACY_SESSION_VERSION_KEY, None)
    if normalized.get(LEGACY_SURFACE_VERSION_KEY):
        normalized["surface_contract"] = "genui_surface"
        normalized.pop(LEGACY_SURFACE_VERSION_KEY, None)
    normalized["created_at"] = str(normalized.get("created_at") or now)
    normalized["updated_at"] = str(normalized.get("updated_at") or now)
    validation = normalized.get("validation")
    if not isinstance(validation, dict):
        validation = {}
    normalized["validation"] = {
        "status": str(validation.get("status") or "pending"),
        "errors": _dedupe_strings(validation.get("errors")),
    }
    return _without_none(normalized)


def upsert_interaction_entry(project_dir: Path | str, entry: dict[str, Any]) -> Path:
    normalized = _normalize_entry(entry)
    journal = read_interaction_journal(
        project_dir,
        project_id=str(normalized["project_id"]),
        pipeline_type=str(normalized["pipeline_type"]),
    )
    interactions = journal["interactions"]
    for index, existing in enumerate(interactions):
        if existing["interaction_id"] == normalized["interaction_id"]:
            preserved_created = existing.get("created_at")
            interactions[index] = {
                **existing,
                **normalized,
                "created_at": preserved_created or normalized["created_at"],
                "updated_at": _now_iso(),
            }
            break
    else:
        interactions.append(normalized)
    journal["updated_at"] = _now_iso()
    return write_interaction_journal(project_dir, journal)


def update_interaction_entry(
    project_dir: Path | str,
    *,
    project_id: str,
    pipeline_type: str,
    interaction_id: str | None = None,
    session_id: str | None = None,
    updates: dict[str, Any],
) -> Path:
    journal = read_interaction_journal(project_dir, project_id=project_id, pipeline_type=pipeline_type)
    for entry in journal["interactions"]:
        if (interaction_id and entry["interaction_id"] == interaction_id) or (
            session_id and entry.get("session_id") == session_id
        ):
            entry.update(_without_none(updates))
            entry["updated_at"] = _now_iso()
            break
    else:
        return write_interaction_journal(project_dir, journal)
    journal["updated_at"] = _now_iso()
    return write_interaction_journal(project_dir, journal)
