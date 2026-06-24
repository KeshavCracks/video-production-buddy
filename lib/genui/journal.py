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

from schemas.artifacts import load_strict_json_object, validate_artifact


GENUI_CONTRACT = "genui"
JOURNAL_CONTRACT = "genui_interaction_journal"
LEGACY_PRODUCT_VERSION_KEY = "genui" + "_product" + "_version"
LEGACY_SESSION_VERSION_KEY = "session" + "_version"
LEGACY_SURFACE_VERSION_KEY = "surface" + "_version"
JOURNAL_FILENAME = "interaction_journal.json"
GENUI_RESPONSE_ARTIFACTS = {
    "genui_session_response": "ui_session_response",
    "genui_surface_response": "ui_surface_response",
}
_GENUI_FALLBACK_REASON_TOKENS = (
    "genui_interaction",
    "genui_session",
    "genui_surface",
    "browser",
    "localhost",
    "serve",
    "server",
    "unavailable",
    "failed",
    "failure",
    "declined",
)
_NATIVE_AGENT_UI_TOKENS = (
    "askuserquestion",
    "request_user_input",
    "native question",
    "native form",
    "agent-native",
)

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
    journal = load_strict_json_object(path, context="GenUI interaction journal")
    journal = _normalize_journal_contract(journal)
    validate_interaction_journal(journal)
    if journal["project_id"] != project_id or journal["pipeline_type"] != pipeline_type:
        raise ValueError("GenUI journal project_id/pipeline_type does not match the current interaction")
    return journal


def genui_required_gate_evidence_report(
    project_dir: Path | str,
    *,
    project_id: str,
    pipeline_type: str,
    required_gates: list[dict[str, Any] | str],
) -> dict[str, Any]:
    """Report whether GenUI-required gates have response or fallback evidence.

    A required gate is satisfied only when the interaction journal has a
    matching entry with a schema-valid GenUI response artifact, or an explicit
    fallback reason documenting a GenUI route failure/unavailable browser path
    or user-declined browser path. Agent-native question widgets alone are not
    accepted as evidence.
    """
    gates = [_normalize_required_gate_spec(gate) for gate in required_gates]
    journal = read_interaction_journal(
        project_dir,
        project_id=project_id,
        pipeline_type=pipeline_type,
    )
    interactions = journal.get("interactions") or []
    issues: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    for gate in gates:
        matches = [
            entry
            for entry in interactions
            if entry.get("stage") == gate["stage"] and entry.get("gate") == gate["gate"]
        ]
        if not matches:
            issues.append(
                {
                    **gate,
                    "code": "missing_journal_entry",
                    "message": (
                        "GenUI-required gate has no matching ui_interaction_journal entry."
                    ),
                }
            )
            continue

        evaluations = [
            _evaluate_required_gate_entry(project_dir, entry)
            for entry in reversed(matches)
        ]
        accepted = next((item for item in evaluations if item["ok"]), None)
        if accepted is not None:
            evidence.append({**gate, **accepted})
            continue

        issues.append(
            {
                **gate,
                "code": "missing_genui_gate_evidence",
                "message": (
                    "GenUI-required gate must have a valid ui_session_response/"
                    "ui_surface_response or an explicit GenUI fallback reason."
                ),
                "entry_evaluations": evaluations,
            }
        )

    return {
        "ok": not issues,
        "project_id": project_id,
        "pipeline_type": pipeline_type,
        "required_gates": gates,
        "evidence": evidence,
        "issues": issues,
    }


def _normalize_required_gate_spec(gate: dict[str, Any] | str) -> dict[str, str]:
    if isinstance(gate, str):
        separator = ":" if ":" in gate else "."
        parts = gate.split(separator, 1)
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError("GenUI required gate strings must use 'stage:gate' or 'stage.gate'")
        return {"stage": parts[0].strip(), "gate": parts[1].strip()}
    stage = str(gate.get("stage") or "").strip()
    gate_name = str(gate.get("gate") or "").strip()
    if not stage or not gate_name:
        raise ValueError("GenUI required gate specs must include stage and gate")
    return {"stage": stage, "gate": gate_name}


def _evaluate_required_gate_entry(project_dir: Path | str, entry: dict[str, Any]) -> dict[str, Any]:
    base = {
        "interaction_id": entry.get("interaction_id"),
        "status": entry.get("status"),
        "mode": entry.get("mode"),
        "recommended_tool": entry.get("recommended_tool"),
        "response_path": entry.get("response_path"),
    }
    response = _response_evidence(project_dir, entry)
    if response["ok"]:
        return {
            **base,
            "ok": True,
            "evidence_type": "genui_response",
            "response_contract": response["contract"],
            "resolved_response_path": response["path"],
        }

    fallback_reason = str(entry.get("fallback_reason") or "").strip()
    if _fallback_reason_documents_genui_attempt(fallback_reason):
        return {
            **base,
            "ok": True,
            "evidence_type": "genui_fallback",
            "fallback_reason": fallback_reason,
            "response_error": response["error"],
        }

    errors = [response["error"]]
    if fallback_reason:
        errors.append(
            "fallback_reason does not document a GenUI route failure, "
            "unavailable browser path, or user-declined browser path."
        )
    else:
        errors.append("missing fallback_reason")
    return {**base, "ok": False, "errors": errors}


def _response_evidence(project_dir: Path | str, entry: dict[str, Any]) -> dict[str, Any]:
    response_path = entry.get("response_path")
    if not isinstance(response_path, str) or not response_path.strip():
        return {"ok": False, "error": "missing response_path"}

    resolved = _resolve_existing_response_path(project_dir, response_path)
    if resolved is None:
        return {"ok": False, "error": f"response_path does not exist: {response_path}"}

    try:
        response = load_strict_json_object(resolved, context=f"GenUI response {resolved}")
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    contract = response.get("contract")
    artifact_name = GENUI_RESPONSE_ARTIFACTS.get(str(contract))
    if artifact_name is None:
        return {"ok": False, "error": f"unsupported GenUI response contract: {contract!r}"}
    try:
        validate_artifact(artifact_name, response)
    except Exception as exc:
        return {"ok": False, "error": f"{artifact_name} validation failed: {exc}"}

    for field in ("project_id", "pipeline_type", "stage", "gate"):
        if response.get(field) != entry.get(field):
            return {
                "ok": False,
                "error": (
                    f"response {field} {response.get(field)!r} does not match "
                    f"journal entry {entry.get(field)!r}"
                ),
            }
    return {"ok": True, "contract": contract, "path": str(resolved)}


def _resolve_existing_response_path(
    project_dir: Path | str,
    response_path: str,
) -> Path | None:
    path = Path(response_path)
    candidates = (
        [path]
        if path.is_absolute()
        else [Path(project_dir).resolve() / path, Path.cwd() / path]
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return None


def _fallback_reason_documents_genui_attempt(reason: str) -> bool:
    normalized = reason.strip().lower()
    if not normalized:
        return False
    if any(token in normalized for token in _NATIVE_AGENT_UI_TOKENS):
        return False
    return any(token in normalized for token in _GENUI_FALLBACK_REASON_TOKENS)


def write_interaction_journal(project_dir: Path | str, journal: dict[str, Any]) -> Path:
    journal = _normalize_journal_contract(journal)
    validate_interaction_journal(journal)
    try:
        serialized = json.dumps(journal, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"GenUI interaction journal must be strict JSON serializable: {exc}"
        ) from exc
    path = interaction_journal_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(serialized)
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
