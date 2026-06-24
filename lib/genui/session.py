"""GenUI framework-backed sessions.

GenUI uses A2UI as the declarative UI framework contract and keeps AG-UI as
the local durable session/event transport. The browser still writes only a
response artifact; canonical Video Production Buddy artifacts remain agent-owned.
"""

from __future__ import annotations

import json
import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from schemas.artifacts import validate_artifact

from lib.genui.journal import GENUI_CONTRACT
from lib.genui.project_snapshot import build_project_cockpit_snapshot
from lib.genui.view_spec import (
    A2UI_RENDERER_NAME,
    VIEW_SPEC_FILENAME,
    render_shell_html,
    validate_view_spec,
)


SESSION_CONTRACT = "genui_session"
SESSION_RESPONSE_CONTRACT = "genui_session_response"
SESSION_VIEW_CONTRACT = "genui_session_view"
SESSION_DIRNAME = "ui"
EVENT_LOG_FILENAME = "events.jsonl"
DRAFT_FILENAME = "draft.json"
MAX_SESSION_VALUE_LENGTH = 10000
MAX_SESSION_LIST_ITEMS = 500

SESSION_FRAMEWORK = {
    "name": "a2ui",
    "renderer": "@copilotkit/a2ui-renderer",
    "packages": ["@a2ui/react", "@a2ui/web_core", "@copilotkit/a2ui-renderer"],
}
SESSION_SCHEMA_STRATEGIES = {"fixed", "dynamic"}
SESSION_SURFACE_TYPES = {
    "GateWorkspace",
    "MediaReviewRoom",
    "IssueTracker",
    "ProjectCockpit",
    "BackgroundStatus",
    "ProposalLock",
    "ScriptReviewWorkspace",
    "ScenePlanWorkspace",
    "ProductReferenceApproval",
    "SampleReview",
    "AssetReview",
    "MusicReview",
    "PublishReview",
}
ISSUE_STATUSES = {"open", "accepted", "rejected", "resolved", "needs_recheck", "waived"}
BLOCKING_STATUSES = {"open", "accepted", "needs_recheck"}
PIPELINE_WORKSPACE_TYPES = {
    "proposal": "ProposalLock",
    "runtime_selection": "GateWorkspace",
    "script": "ScriptReviewWorkspace",
    "scene_plan": "ScenePlanWorkspace",
    "product_reference": "ProductReferenceApproval",
    "sample": "SampleReview",
    "sample_review": "SampleReview",
    "asset_review": "AssetReview",
    "music_review": "MusicReview",
    "publish": "PublishReview",
    "publish_review": "PublishReview",
}
WORKSPACE_KIND_ALIASES = {
    "proposal": "proposal_lock",
    "proposal_lock": "proposal_lock",
    "runtime_selection": "runtime_selection",
    "script": "script_review",
    "script_review": "script_review",
    "scene_plan": "scene_plan_review",
    "scene_plan_review": "scene_plan_review",
    "product_reference": "product_reference",
    "sample": "sample_review",
    "sample_review": "sample_review",
    "asset_review": "asset_review",
    "music_review": "music_review",
    "publish": "publish_review",
    "publish_review": "publish_review",
}
WORKSPACE_KIND_BY_SURFACE = {
    "ProposalLock": "proposal_lock",
    "ScriptReviewWorkspace": "script_review",
    "ScenePlanWorkspace": "scene_plan_review",
    "ProductReferenceApproval": "product_reference",
    "SampleReview": "sample_review",
    "AssetReview": "asset_review",
    "MusicReview": "music_review",
    "PublishReview": "publish_review",
    "ProjectCockpit": "project_cockpit",
    "BackgroundStatus": "background_status",
    "MediaReviewRoom": "media_review",
    "GateWorkspace": "gate_workspace",
}


@dataclass(frozen=True)
class SessionBundle:
    """Materialized GenUI session files with the session-contract wire format for one project interaction."""

    config: dict[str, Any]
    config_path: Path
    html_path: Path
    view_spec_path: Path
    response_path: Path
    state_path: Path
    events_path: Path
    draft_path: Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _expires_iso(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")


def _decision_id(session_id: str) -> str:
    return _slug(f"decision-{session_id}", fallback="decision-genui")


def _resume_token(session_id: str) -> str:
    # The browser submit nonce remains the secret. This token is a durable local
    # resume handle recorded in auditable artifacts and never authorizes writes.
    return _slug(f"resume-{session_id}-local", fallback="resume-genui")


def _reject_non_finite_json(value: Any, *, context: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"GenUI payload contains non-finite JSON number at {context}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite_json(item, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite_json(item, context=f"{context}[{index}]")


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    _reject_non_finite_json(payload, context=str(path))
    try:
        serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise ValueError(f"GenUI payload must be strict JSON serializable: {exc}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(serialized)


def _resolve_project_path(project_dir: Path | str, path: Path | str) -> Path:
    project_root = Path(project_dir).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"Path {candidate} is outside project directory {project_root}") from exc
    return candidate


def _slug(value: Any, *, fallback: str) -> str:
    raw = str(value or fallback)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-_.")
    if not slug:
        slug = fallback
    if not slug[0].isalnum():
        slug = f"session-{slug}"
    return slug[:64]


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _without_none_recursive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_none_recursive(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_without_none_recursive(item) for item in value if item is not None]
    return value


def _session_id(config: dict[str, Any]) -> str:
    session_id = config.get("session_id") or config.get("config_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("GenUI session config must declare session_id")
    return session_id


def _iter_surfaces(config: dict[str, Any]) -> list[dict[str, Any]]:
    return list(config.get("surfaces") or [])


def _bounded_list(value: Any, *, field_name: str, max_items: int = MAX_SESSION_LIST_ITEMS) -> list[Any]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"GenUI {field_name} must be a list")
    if len(value) > max_items:
        raise ValueError(f"GenUI {field_name} has too many items")
    return value


def _bounded_object(value: Any, *, field_name: str) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"GenUI {field_name} must be an object")
    return value


def _allowed_target_refs(config: dict[str, Any]) -> set[str]:
    refs = {str(item["id"]) for item in config.get("media_refs") or []}
    refs.update(str(item["id"]) for item in config.get("artifact_refs") or [])
    refs.update(str(surface["id"]) for surface in _iter_surfaces(config))
    for surface in _iter_surfaces(config):
        refs.update(str(item) for item in surface.get("media_ids") or [])
        refs.update(str(item) for item in surface.get("allowed_targets") or [])
    return refs


def _configured_patch_targets(config: dict[str, Any]) -> set[tuple[str, str]]:
    targets = {
        (str(ref["artifact"]), str(ref["path"]))
        for ref in config.get("artifact_refs") or []
        if ref.get("artifact") and ref.get("path")
    }
    for issue in config.get("issues") or []:
        artifact = issue.get("artifact")
        path = issue.get("path")
        if isinstance(artifact, str) and isinstance(path, str):
            targets.add((artifact, path))
    return targets


def _choice_values(choices: Any) -> set[str]:
    values: set[str] = set()
    if not isinstance(choices, list):
        return values
    for choice in choices:
        if isinstance(choice, dict) and isinstance(choice.get("value"), str):
            values.add(choice["value"])
    return values


def _configured_value_specs(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for surface in _iter_surfaces(config):
        selection = surface.get("selection")
        if isinstance(selection, dict) and isinstance(selection.get("fieldId"), str):
            specs[selection["fieldId"]] = {
                "kind": "selection",
                "choices": _choice_values(surface.get("choices")),
                "allow_multiple": selection.get("allowMultiple") is True,
                "binding": selection.get("binding") if isinstance(selection.get("binding"), dict) else None,
            }
        for field in surface.get("fields") or []:
            if not isinstance(field, dict) or not isinstance(field.get("id"), str):
                continue
            specs[field["id"]] = {
                "kind": str(field.get("type") or "text"),
                "choices": _choice_values(field.get("choices")),
                "allow_multiple": field.get("type") == "multiselect",
                "binding": field.get("binding") if isinstance(field.get("binding"), dict) else None,
                "required": field.get("required") is True,
                "visible_if": field.get("visible_if") if isinstance(field.get("visible_if"), dict) else None,
                "min": field.get("min"),
                "max": field.get("max"),
            }
    for ref in config.get("artifact_refs") or []:
        artifact = ref.get("artifact")
        path = ref.get("path")
        if isinstance(artifact, str) and isinstance(path, str):
            specs.setdefault(
                f"{artifact}.{path}",
                {
                    "kind": "artifact_value",
                    "choices": set(),
                    "allow_multiple": False,
                    "binding": {"artifact": artifact, "path": path},
                },
            )
    return specs


def _resolve_visible_if_key(reference: str, current_key: str, specs: dict[str, dict[str, Any]]) -> str | None:
    if reference in specs:
        return reference
    prefix = current_key.rsplit(".", 1)[0] if "." in current_key else ""
    if prefix and f"{prefix}.{reference}" in specs:
        return f"{prefix}.{reference}"
    suffix_matches = [key for key in specs if key.endswith(f".{reference}")]
    return suffix_matches[0] if len(suffix_matches) == 1 else None


def _field_visible(key: str, spec: dict[str, Any], values: dict[str, Any], specs: dict[str, dict[str, Any]]) -> bool:
    visible_if = spec.get("visible_if")
    if not isinstance(visible_if, dict):
        return True
    reference = visible_if.get("field")
    operator = visible_if.get("operator")
    if not isinstance(reference, str) or not isinstance(operator, str):
        return True
    reference_key = _resolve_visible_if_key(reference, key, specs)
    if reference_key is None:
        return True
    value = values.get(reference_key)
    if operator == "not_empty":
        return not _is_empty_submission_value(value)
    if operator == "empty":
        return _is_empty_submission_value(value)
    if operator == "equals":
        return value == visible_if.get("value")
    if operator == "not_equals":
        return value != visible_if.get("value")
    return True


def _target_value_keys(config: dict[str, Any]) -> dict[tuple[str, str], list[str]]:
    keys: dict[tuple[str, str], list[str]] = {}
    for key, spec in _configured_value_specs(config).items():
        binding = spec.get("binding")
        if not isinstance(binding, dict):
            continue
        artifact = binding.get("artifact")
        path = binding.get("path")
        if isinstance(artifact, str) and isinstance(path, str):
            keys.setdefault((artifact, path), []).append(key)
    return keys


def _allowed_selected_refs(config: dict[str, Any]) -> set[str]:
    refs = _allowed_target_refs(config)
    for spec in _configured_value_specs(config).values():
        refs.update(spec.get("choices") or set())
    return refs


def _is_empty_submission_value(value: Any) -> bool:
    return value is None or value == "" or value == []


def _validate_configured_value(key: str, value: Any, spec: dict[str, Any]) -> None:
    choices = spec.get("choices") or set()
    allow_multiple = spec.get("allow_multiple") is True
    if choices:
        if allow_multiple:
            if not isinstance(value, list) or any(item not in choices for item in value):
                raise ValueError(f"GenUI value {key!r} must contain only configured choices")
        elif value not in choices:
            raise ValueError(f"GenUI value {key!r} must be one of the configured choices")
    kind = spec.get("kind")
    if kind in {"checkbox", "approval"} and not isinstance(value, bool):
        raise ValueError(f"GenUI value {key!r} must be boolean")
    if kind == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            raise ValueError(f"GenUI value {key!r} must be a finite number")
        minimum = spec.get("min")
        maximum = spec.get("max")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise ValueError(f"GenUI value {key!r} is below the configured minimum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise ValueError(f"GenUI value {key!r} is above the configured maximum")


def _validate_submission_bindings(
    config: dict[str, Any],
    *,
    action: str,
    values: dict[str, Any],
    selected_refs: list[Any],
    revision_patches: list[Any],
) -> None:
    value_specs = _configured_value_specs(config)
    for key, value in values.items():
        spec = value_specs.get(key)
        if spec is None:
            raise ValueError(f"GenUI submission value key {key!r} is not configured")
        if not _field_visible(key, spec, values, value_specs):
            if not _is_empty_submission_value(value):
                raise ValueError(f"GenUI hidden value {key!r} must not be submitted")
            continue
        if not _is_empty_submission_value(value):
            _validate_configured_value(key, value, spec)

    if action in {"submit", "approve", "revise"}:
        for key, spec in value_specs.items():
            if spec.get("required") is not True:
                continue
            if not _field_visible(key, spec, values, value_specs):
                continue
            if _is_empty_submission_value(values.get(key)):
                raise ValueError(f"GenUI required value {key!r} is missing")

    allowed_selected = _allowed_selected_refs(config)
    for selected_ref in selected_refs:
        if not isinstance(selected_ref, str) or selected_ref not in allowed_selected:
            raise ValueError(f"GenUI selected_ref {selected_ref!r} is not configured")

    keys_by_target = _target_value_keys(config)
    specs_by_key = value_specs
    for patch in revision_patches:
        if not isinstance(patch, dict):
            continue
        artifact = patch.get("artifact")
        path = patch.get("path")
        if not isinstance(artifact, str) or not isinstance(path, str):
            continue
        target = (artifact, path)
        patch_value = patch.get("value")
        for value_key in keys_by_target.get(target, []):
            submitted = values.get(value_key)
            if value_key in values and submitted != patch_value:
                raise ValueError(
                    f"GenUI revision patch for {artifact}.{path} contradicts submitted value {value_key!r}"
                )
            spec = specs_by_key.get(value_key)
            if spec and not _is_empty_submission_value(patch_value):
                _validate_configured_value(value_key, patch_value, spec)


def _media_review_required_media(config: dict[str, Any], evidence_name: str) -> set[str]:
    required: set[str] = set()
    for surface in _iter_surfaces(config):
        if surface.get("type") != "MediaReviewRoom":
            continue
        if evidence_name in set(surface.get("required_evidence") or []):
            required.update(str(item) for item in surface.get("media_ids") or [])
    return required


def _approval_attestation_required_surfaces(config: dict[str, Any]) -> set[str]:
    required: set[str] = set()
    for surface in _iter_surfaces(config):
        if "approval_attested" in set(surface.get("required_evidence") or []):
            required.add(str(surface["id"]))
    return required


def _default_operation_events(config: dict[str, Any]) -> list[dict[str, Any]]:
    session_id = _session_id(config)
    return [
        {
            "id": f"{session_id}-prepare",
            "type": "tool_call",
            "tool": "genui_session.prepare",
            "status": "complete",
            "label": "Prepared GenUI session bundle",
        },
        {
            "id": f"{session_id}-await-response",
            "type": "tool_call",
            "tool": "genui_session.await_response",
            "status": "pending",
            "label": "Awaiting browser response",
        },
    ]


def _normalize_visual_need(decision: dict[str, Any]) -> dict[str, Any]:
    reasons = list(dict.fromkeys(str(reason) for reason in decision.get("reasons") or []))
    primitives: list[str] = [
        str(item)
        for item in decision.get("required_ui_primitives") or []
        if isinstance(item, str) and item
    ]
    if "media_review" in reasons:
        primitives.extend(["media_player", "keyframe_strip", "timecoded_annotation", "issue_tracker"])
    if "visual_demonstration" in reasons:
        primitives.append("artifact_trace")
    if "side_by_side_comparison" in reasons:
        primitives.append("side_by_side_comparison")
    if "multi_axis_selection" in reasons:
        primitives.append("structured_fields")
    if "structured_revision_capture" in reasons:
        primitives.extend(["structured_fields", "approval_attestation"])
    if "project_state_overview" in reasons:
        primitives.extend(["status_timeline", "artifact_trace", "budget_panel"])
    if "background_status" in reasons:
        primitives.append("status_timeline")
    if not primitives and decision.get("recommended_mode") != "cli":
        primitives.append("structured_fields")
    recommended_mode = decision.get("recommended_mode")
    if recommended_mode == "genui":
        if "media_review" in reasons:
            recommended_mode = "media_review_room"
        else:
            recommended_mode = "gate_workspace"
    return {
        "recommended_mode": recommended_mode or "cli",
        "recommended_tool": "genui_session" if recommended_mode != "cli" else None,
        "linear_chat_sufficient": bool(decision.get("linear_chat_sufficient")),
        "interaction_kind": str(decision.get("interaction_kind") or "dynamic_genui"),
        "reasons": reasons,
        "required_ui_primitives": list(dict.fromkeys(primitives)),
        "confidence": float(decision.get("confidence", 0.9)),
        "fallback": "cli_only_when_browser_fails_or_user_declines",
    }


def _normalize_session_config_contract(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized.pop("version", None)
    normalized.pop("genui_contract", None)
    normalized.pop("genui" + "_product" + "_version", None)
    normalized["contract"] = SESSION_CONTRACT
    metadata = dict(normalized.get("metadata") or {})
    for key in list(metadata):
        if re.fullmatch(r"genui_v\d+(?:_compatible)?", key):
            metadata.pop(key, None)
    legacy_product_key = "genui" + "_product" + "_version"
    legacy_compatible_key = "compatible" + "_product" + "_versions"
    for key in [legacy_product_key, legacy_compatible_key, "compatible_contracts"]:
        metadata.pop(key, None)
    metadata["genui_contract"] = GENUI_CONTRACT
    normalized["metadata"] = metadata
    return normalized


def _normalize_session_response_contract(response: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(response)
    normalized.pop("version", None)
    normalized["contract"] = SESSION_RESPONSE_CONTRACT
    metadata = dict(normalized.get("metadata") or {})
    metadata.pop("genui" + "_product" + "_version", None)
    metadata["genui_contract"] = GENUI_CONTRACT
    normalized["metadata"] = metadata
    return normalized


def validate_session_config(config: dict[str, Any]) -> None:
    """Validate a GenUI session config and Video Production Buddy invariants."""
    normalized = _normalize_session_config_contract(config)
    validate_artifact("ui_session_config", normalized)
    _reject_non_finite_json(normalized, context="ui_session_config")
    session_id = _session_id(normalized)
    if normalized.get("config_id") and normalized["config_id"] != session_id:
        raise ValueError("GenUI config_id must match session_id when provided")
    surface_ids: set[str] = set()
    for surface in _iter_surfaces(normalized):
        surface_id = surface["id"]
        if surface_id in surface_ids:
            raise ValueError(f"GenUI config contains duplicate surface id {surface_id!r}")
        surface_ids.add(surface_id)
        if surface["type"] not in SESSION_SURFACE_TYPES:
            raise ValueError(f"GenUI config uses unknown surface type {surface['type']!r}")
    action_ids: set[str] = set()
    for action in normalized.get("actions") or []:
        action_id = action["id"]
        if action_id in action_ids:
            raise ValueError(f"GenUI config contains duplicate action id {action_id!r}")
        action_ids.add(action_id)


def validate_session_response(response: dict[str, Any]) -> None:
    """Validate a GenUI session response artifact."""
    normalized = _normalize_session_response_contract(response)
    validate_artifact("ui_session_response", normalized)
    _reject_non_finite_json(normalized, context="ui_session_response")


def _a2ui_component_for_surface(config: dict[str, Any], surface: dict[str, Any]) -> dict[str, Any]:
    refs_by_id = {
        "media": {item["id"]: item for item in config.get("media_refs") or []},
        "artifact": {item["id"]: item for item in config.get("artifact_refs") or []},
        "trace": {item["id"]: item for item in config.get("trace_refs") or []},
    }
    media_refs = [refs_by_id["media"][ref_id] for ref_id in surface.get("media_ids") or [] if ref_id in refs_by_id["media"]]
    artifact_refs = [
        refs_by_id["artifact"][ref_id]
        for ref_id in surface.get("artifact_ref_ids") or []
        if ref_id in refs_by_id["artifact"]
    ]
    trace_refs = [refs_by_id["trace"][ref_id] for ref_id in surface.get("trace_ref_ids") or [] if ref_id in refs_by_id["trace"]]
    return {
        "id": surface["id"],
        "type": surface["type"],
        "props": _without_none(
            {
                "title": surface["title"],
                "description": surface.get("description"),
                "workspaceKind": surface.get("workspace_kind"),
                "contract": surface.get("contract"),
                "mediaRefs": media_refs,
                "artifactRefs": artifact_refs,
                "traceRefs": trace_refs,
                "fields": surface.get("fields") or [],
                "choices": surface.get("choices") or [],
                "selection": surface.get("selection"),
                "reviewItems": surface.get("review_items") or [],
                "requiredEvidence": surface.get("required_evidence") or [],
                "allowedTargets": surface.get("allowed_targets") or [],
                "allowedStatuses": surface.get("allowed_statuses") or [],
                "timelineItems": surface.get("timeline_items") or [],
                "artifactItems": surface.get("artifact_items") or [],
                "decisionItems": surface.get("decision_items") or [],
                "budgetCostItems": surface.get("budget_cost_items") or [],
                "pendingResponses": surface.get("pending_responses") or [],
                "staleSessions": surface.get("stale_sessions") or [],
                "validationBlockers": surface.get("validation_blockers") or [],
                "journalItems": surface.get("journal_items") or [],
            }
        ),
        "children": [],
    }


def _a2ui_product_components(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return product panels rendered by the A2UI catalog.

    These are still declarative component instances; the trusted React catalog
    owns the actual behavior.
    """
    media_refs = config.get("media_refs") or []
    artifact_refs = config.get("artifact_refs") or []
    trace_refs = config.get("trace_refs") or []
    review_items: list[Any] = []
    choices: list[Any] = []
    issue_surface: dict[str, Any] | None = None
    required_evidence: list[str] = []
    for surface in _iter_surfaces(config):
        review_items.extend(surface.get("review_items") or [])
        choices.extend(surface.get("choices") or [])
        required_evidence.extend(str(item) for item in surface.get("required_evidence") or [])
        if surface.get("type") == "IssueTracker":
            issue_surface = surface

    components: list[dict[str, Any]] = [
        {
            "id": "genui-durable-decision",
            "type": "DurableDecisionPanel",
            "props": {
                "title": "Durable decision",
                "description": "Pending human decision metadata for resume-safe agent continuation.",
                "decision": {
                    "decisionId": config.get("decision_id"),
                    "resumeToken": config.get("resume_token"),
                    "expiresAt": config.get("expires_at"),
                    "stagePolicyId": config.get("stage_policy_id"),
                    "schemaStrategy": config.get("schema_strategy"),
                },
            },
            "children": [],
        },
        {
            "id": "genui-operation-timeline",
            "type": "OperationTimeline",
            "props": {
                "title": "Operation timeline",
                "description": "AG-UI lifecycle and tool-operation events for this interaction.",
                "operationEvents": config.get("operation_events") or _default_operation_events(config),
            },
            "children": [],
        },
        {
            "id": "genui-review-completion",
            "type": "ReviewCompletionPanel",
            "props": {
                "title": "Review completion",
                "description": "Required evidence and blocking issue state before the agent resumes.",
                "requiredEvidence": list(dict.fromkeys(required_evidence)),
            },
            "children": [],
        },
        {
            "id": "genui-live-status",
            "type": "LiveStatusPanel",
            "props": {
                "title": "Live session status",
                "description": "AG-UI event snapshot, session lifecycle, and browser response state.",
                "session": {
                    "id": _session_id(config),
                    "mode": config["mode"],
                    "stage": config["stage"],
                    "gate": config["gate"],
                    "genui_contract": GENUI_CONTRACT,
                },
            },
            "children": [],
        },
        {
            "id": "genui-journal",
            "type": "InteractionJournalPanel",
            "props": {
                "title": "Interaction journal",
                "description": "Every CLI-vs-GenUI routing decision is recorded for agent review.",
                "routingDecisionId": config.get("metadata", {}).get("routing_decision_id"),
                "sourceRequestId": config.get("metadata", {}).get("source_request_id"),
                "journalPath": config.get("metadata", {}).get("interaction_journal_path"),
            },
            "children": [],
        },
    ]
    if media_refs:
        components.extend(
            [
                {
                    "id": "genui-media-timeline",
                    "type": "MediaTimeline",
                    "props": {
                        "title": "Media timeline",
                        "description": "Open media evidence and timeline inspection state.",
                        "mediaRefs": media_refs,
                        "requiredEvidence": list(dict.fromkeys(required_evidence)),
                    },
                    "children": [],
                },
                {
                    "id": "genui-media-comparison",
                    "type": "MediaComparison",
                    "props": {
                        "title": "Media comparison",
                        "description": "Side-by-side media and option context for the current decision.",
                        "mediaRefs": media_refs,
                        "reviewItems": review_items,
                        "choices": choices,
                    },
                    "children": [],
                },
                {
                    "id": "genui-region-annotation",
                    "type": "RegionAnnotation",
                    "props": {
                        "title": "Region annotation",
                        "description": "Normalized region and time-range annotation capture.",
                        "mediaRefs": media_refs,
                    },
                    "children": [],
                },
            ]
        )
    if artifact_refs or trace_refs:
        components.append(
            {
                "id": "genui-artifact-trace",
                "type": "ArtifactTrace",
                "props": {
                    "title": "Artifact trace",
                    "description": "Agent-owned artifacts and trace links related to this interaction.",
                    "artifactRefs": artifact_refs,
                    "traceRefs": trace_refs,
                },
                "children": [],
            }
        )
    if "approval_attested" in set(required_evidence):
        components.append(
            {
                "id": "genui-approval-attestation",
                "type": "ApprovalAttestation",
                "props": {
                    "title": "Approval attestation",
                    "description": "Human approval evidence required before the agent can apply canonical updates.",
                    "requiredEvidence": list(dict.fromkeys(required_evidence)),
                },
                "children": [],
            }
        )
    if issue_surface is not None:
        components.append(
            {
                "id": "genui-issue-board",
                "type": "IssueBoard",
                "props": {
                    "title": "Issue board",
                    "description": "Structured issue lifecycle summary for the submitted response.",
                    "allowedTargets": issue_surface.get("allowed_targets") or [],
                    "allowedStatuses": issue_surface.get("allowed_statuses") or [],
                },
                "children": [],
            }
        )
    components.append(
        {
            "id": "genui-revision-preview",
            "type": "RevisionPatchPreview",
            "props": {
                "title": "Revision patch preview",
                "description": "Pending response patches for agent validation; no canonical writes happen here.",
            },
            "children": [],
        }
    )
    return components


def compile_session_view_spec(
    config: dict[str, Any],
    *,
    submit_url: str | None = None,
    submit_nonce: str | None = None,
    preview_only: bool = False,
) -> dict[str, Any]:
    """Compile a GenUI session config into the session-contract A2UI wire spec."""
    validate_session_config(config)
    session_id = _session_id(config)
    config = _normalize_session_config_contract(config)
    root_id = "genui-session-root"
    components = [_a2ui_component_for_surface(config, surface) for surface in config["surfaces"]]
    components.extend(_a2ui_product_components(config))
    if config.get("actions"):
        components.append(
            {
                "id": "genui-session-actions",
                "type": "ActionBar",
                "props": {
                    "actions": config["actions"],
                    "submitUrl": submit_url,
                    "previewOnly": preview_only or submit_url is None,
                },
                "children": [],
            }
        )
    root_component = {
        "id": root_id,
        "type": "SessionShell",
        "props": {
            "title": config["title"],
            "description": config.get("description"),
            "sessionId": session_id,
            "projectId": config["project_id"],
            "pipelineType": config["pipeline_type"],
            "stage": config["stage"],
            "gate": config["gate"],
            "mode": config["mode"],
            "workspaceKind": config.get("workspace_kind"),
            "framework": config["framework"],
            "transport": config["transport"],
            "visualNeedAssessment": config["visual_need_assessment"],
            "decisionId": config.get("decision_id"),
            "stagePolicyId": config.get("stage_policy_id"),
            "schemaStrategy": config.get("schema_strategy"),
            "genuiContract": GENUI_CONTRACT,
        },
        "children": [component["id"] for component in components],
    }
    all_components = _without_none_recursive([root_component, *components])
    data_model = _without_none_recursive({
        "session": {
            "id": session_id,
            "mode": config["mode"],
            "title": config["title"],
            "project_id": config["project_id"],
            "pipeline_type": config["pipeline_type"],
            "stage": config["stage"],
            "gate": config["gate"],
            "genui_contract": GENUI_CONTRACT,
            "workspace_kind": config.get("workspace_kind"),
            "decision_id": config.get("decision_id"),
            "resume_token": config.get("resume_token"),
            "expires_at": config.get("expires_at"),
            "stage_policy_id": config.get("stage_policy_id"),
            "schema_strategy": config.get("schema_strategy"),
        },
        "media_refs": config.get("media_refs") or [],
        "artifact_refs": config.get("artifact_refs") or [],
        "trace_refs": config.get("trace_refs") or [],
        "issues": config.get("issues") or [],
        "values": config.get("initial_values") or {},
        "annotations": [],
        "interaction_evidence": {
            "media_opened": [],
            "timeline_inspected": [],
            "seconds_watched": 0,
        },
        "draft_state": config.get("draft_state") or {},
        "event_stream": config.get("event_stream") or {},
        "conflict_policy": config.get("conflict_policy") or {},
        "operation_events": config.get("operation_events") or _default_operation_events(config),
        "project_snapshot": config.get("metadata", {}).get("project_snapshot") or {},
    })
    operations = [
        {"type": "surfaceUpdate", "surfaceId": session_id, "components": all_components},
        {"type": "dataModelUpdate", "surfaceId": session_id, "data": data_model},
        {"type": "beginRendering", "surfaceId": session_id, "rootId": root_id},
    ]
    spec = {
        "contract": SESSION_VIEW_CONTRACT,
        "renderer": A2UI_RENDERER_NAME,
        "root": root_id,
        "a2ui": {
            "surface_id": session_id,
            "operations": operations,
            "components": all_components,
            "data_model": data_model,
        },
        "state": data_model,
        "metadata": _without_none_recursive({
            "session_id": session_id,
            "config_id": session_id,
            "project_id": config["project_id"],
            "pipeline_type": config["pipeline_type"],
            "stage": config["stage"],
            "gate": config["gate"],
            "mode": config["mode"],
            "workspace_kind": config.get("workspace_kind"),
            "framework": config["framework"],
            "transport": config["transport"],
            "submit_url": submit_url,
            "submit_nonce": submit_nonce,
            "draft_url": "/draft" if not preview_only and submit_url is not None else None,
            "preview_only": preview_only or submit_url is None,
            "genui_contract": GENUI_CONTRACT,
            "routing_decision_id": config.get("metadata", {}).get("routing_decision_id"),
            "decision_id": config.get("decision_id"),
            "stage_policy_id": config.get("stage_policy_id"),
            "schema_strategy": config.get("schema_strategy"),
        }),
    }
    validate_view_spec(spec)
    return spec


def write_session_view_spec(
    path: Path | str,
    config: dict[str, Any],
    *,
    submit_url: str | None = None,
    submit_nonce: str | None = None,
    preview_only: bool = False,
) -> Path:
    spec = compile_session_view_spec(
        config,
        submit_url=submit_url,
        submit_nonce=submit_nonce,
        preview_only=preview_only,
    )
    target = Path(path)
    _dump_json(target, spec)
    return target


def session_events_path_for_response(response_path: Path | str) -> Path:
    return Path(response_path).with_name(EVENT_LOG_FILENAME)


def event_cursor(session_id: str, sequence: int) -> str:
    return f"{session_id}:{sequence:06d}"


def _event_sequence_from_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    if cursor.isdigit():
        return int(cursor)
    match = re.search(r":(\d+)$", cursor)
    if match:
        return int(match.group(1))
    return 0


def number_session_events(
    config: dict[str, Any],
    events: list[dict[str, Any]],
    *,
    start_sequence: int = 1,
    emitted_at: str | None = None,
) -> list[dict[str, Any]]:
    """Attach stable local replay metadata to an AG-UI event batch."""
    validate_session_config(config)
    session_id = _session_id(config)
    timestamp = emitted_at or _now_iso()
    numbered: list[dict[str, Any]] = []
    for offset, event in enumerate(events):
        sequence = start_sequence + offset
        numbered.append(
            {
                **event,
                "sequence": sequence,
                "cursor": event_cursor(session_id, sequence),
                "emitted_at": timestamp,
            }
        )
    return numbered


def read_session_events(path: Path | str) -> list[dict[str, Any]]:
    event_path = Path(path)
    if not event_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in event_path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError(f"GenUI event log contains non-object event at {event_path}")
        _reject_non_finite_json(event, context=f"{event_path}.event")
        events.append(event)
    return events


def write_session_events(path: Path | str, events: list[dict[str, Any]]) -> Path:
    event_path = Path(path)
    event_lines: list[str] = []
    for event in events:
        _reject_non_finite_json(event, context=f"{event_path}.event")
        event_lines.append(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with open(event_path, "w", encoding="utf-8") as f:
        f.writelines(event_lines)
    return event_path


def append_session_event(path: Path | str, config: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    event_path = Path(path)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    events = read_session_events(event_path)
    numbered = number_session_events(config, [event], start_sequence=len(events) + 1)[0]
    _reject_non_finite_json(numbered, context=f"{event_path}.event")
    serialized = json.dumps(numbered, ensure_ascii=False, allow_nan=False)
    with open(event_path, "a", encoding="utf-8") as f:
        f.write(serialized)
        f.write("\n")
    return numbered


def filter_session_events_after(events: list[dict[str, Any]], after: str | None) -> list[dict[str, Any]]:
    sequence = _event_sequence_from_cursor(after)
    if sequence <= 0:
        return events
    return [event for event in events if int(event.get("sequence") or 0) > sequence]


def session_event_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    last_event = events[-1] if events else {}
    return _without_none(
        {
            "event_count": len(events),
            "last_event_type": last_event.get("type"),
            "event_cursor": last_event.get("cursor"),
            "tool_call_count": sum(1 for event in events if str(event.get("type", "")).startswith("TOOL_CALL")),
        }
    )


def ensure_session_events(
    path: Path | str,
    config: dict[str, Any],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    events = read_session_events(path)
    if events:
        return events
    events = build_ag_ui_session_events(config, state)
    write_session_events(path, events)
    return events


def write_session_bundle(project_dir: Path | str, config: dict[str, Any]) -> SessionBundle:
    """Validate and materialize a GenUI session bundle."""
    config = _normalize_session_config_contract(config)
    validate_session_config(config)
    project_root = Path(project_dir)
    session_id = _session_id(config)
    base = _resolve_project_path(project_root, Path("artifacts") / SESSION_DIRNAME / session_id)
    config_path = base / "config.json"
    html_path = base / "form.html"
    view_spec_path = base / VIEW_SPEC_FILENAME
    response_path = base / "response.json"
    state_path = base / "server.json"
    events_path = base / EVENT_LOG_FILENAME
    draft_path = base / DRAFT_FILENAME

    if response_path.exists():
        response_path.unlink()
    if state_path.exists():
        state_path.unlink()
    if events_path.exists():
        events_path.unlink()
    if draft_path.exists():
        draft_path.unlink()

    stored_config = _normalize_session_config_contract({**config, "config_id": session_id})
    _dump_json(config_path, stored_config)
    write_session_view_spec(view_spec_path, stored_config, preview_only=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w") as f:
        f.write(render_shell_html())

    return SessionBundle(
        config=stored_config,
        config_path=config_path,
        html_path=html_path,
        view_spec_path=view_spec_path,
        response_path=response_path,
        state_path=state_path,
        events_path=events_path,
        draft_path=draft_path,
    )


def _coerce_submission_values(values: Any) -> dict[str, Any]:
    values = _bounded_object(values, field_name="values")
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("GenUI submission values must have non-empty string keys")
        _reject_non_finite_json(value, context=f"ui_session_submission.values.{key}")
        if isinstance(value, str) and len(value) > MAX_SESSION_VALUE_LENGTH:
            raise ValueError(f"GenUI value {key!r} is too long")
    return values


def _validate_session_semantics(
    config: dict[str, Any],
    *,
    action: str,
    values: dict[str, Any],
    annotations: list[Any],
    selected_refs: list[Any],
    issues: list[Any],
    revision_patches: list[Any],
    approval_attestations: list[Any],
    interaction_evidence: dict[str, Any],
) -> None:
    allowed_refs = _allowed_target_refs(config)
    for item in annotations:
        if not isinstance(item, dict):
            raise ValueError("GenUI annotations must contain objects")
        target_ref = item.get("target_ref")
        if not isinstance(target_ref, str) or target_ref not in allowed_refs:
            raise ValueError(f"GenUI annotation target_ref {target_ref!r} is not configured")
        time_range = item.get("time_range")
        if isinstance(time_range, dict) and time_range.get("end_seconds", 0) < time_range.get("start_seconds", 0):
            raise ValueError("GenUI annotation time_range end_seconds must be >= start_seconds")

    for item in issues:
        if not isinstance(item, dict):
            raise ValueError("GenUI issues must contain objects")
        target_ref = item.get("target_ref")
        if not isinstance(target_ref, str) or target_ref not in allowed_refs:
            raise ValueError(f"GenUI issue target_ref {target_ref!r} is not configured")
        if item.get("status") not in ISSUE_STATUSES:
            raise ValueError(f"GenUI issue status {item.get('status')!r} is not supported")
        artifact = item.get("artifact")
        path = item.get("path")
        if artifact is None and path is None:
            continue
        if not isinstance(artifact, str) or not isinstance(path, str):
            raise ValueError("GenUI issue patch target must include artifact and path together")
        if (artifact, path) not in _configured_patch_targets(config):
            raise ValueError(f"GenUI issue patch target {(artifact, path)!r} is not configured")

    configured_patch_targets = _configured_patch_targets(config)
    for item in revision_patches:
        if not isinstance(item, dict):
            raise ValueError("GenUI revision_patches must contain objects")
        key = (item.get("artifact"), item.get("path"))
        if not isinstance(key[0], str) or not isinstance(key[1], str) or key not in configured_patch_targets:
            raise ValueError(f"GenUI revision patch is not configured for {key!r}")
    _validate_submission_bindings(
        config,
        action=action,
        values=values,
        selected_refs=selected_refs,
        revision_patches=revision_patches,
    )

    required_opened = _media_review_required_media(config, "media_opened")
    required_timeline = _media_review_required_media(config, "timeline_inspected")
    opened = set(str(item) for item in interaction_evidence.get("media_opened") or [])
    inspected = set(str(item) for item in interaction_evidence.get("timeline_inspected") or [])
    if action == "approve":
        required_approval_surfaces = _approval_attestation_required_surfaces(config)
        approved_surfaces = {
            str(item.get("id"))
            for item in approval_attestations
            if isinstance(item, dict) and item.get("approved") is True
        }
        missing_approval = sorted(required_approval_surfaces - approved_surfaces)
        if missing_approval:
            raise ValueError(f"GenUI approval missing approval_attested evidence for {missing_approval}")
        missing_opened = sorted(required_opened - opened)
        if missing_opened:
            raise ValueError(f"GenUI approval missing media_opened evidence for {missing_opened}")
        missing_timeline = sorted(required_timeline - inspected)
        if missing_timeline:
            raise ValueError(f"GenUI approval missing timeline_inspected evidence for {missing_timeline}")
        unresolved = [
            item["id"]
            for item in issues
            if item.get("severity") == "blocking" and item.get("status") in BLOCKING_STATUSES
        ]
        if unresolved:
            raise ValueError(f"GenUI approval has unresolved blocking issues: {unresolved}")


def _review_completion_payload(
    config: dict[str, Any],
    *,
    action: str,
    issues: list[Any],
    approval_attestations: list[Any],
    interaction_evidence: dict[str, Any],
) -> dict[str, Any]:
    if action not in {"approve", "submit", "revise"}:
        return {"status": "not_required", "missing_required_evidence": []}
    missing: list[str] = []
    required_approval_surfaces = _approval_attestation_required_surfaces(config)
    approved_surfaces = {
        str(item.get("id"))
        for item in approval_attestations
        if isinstance(item, dict) and item.get("approved") is True
    }
    for surface_id in sorted(required_approval_surfaces - approved_surfaces):
        missing.append(f"approval_attested:{surface_id}")
    opened = set(str(item) for item in interaction_evidence.get("media_opened") or [])
    inspected = set(str(item) for item in interaction_evidence.get("timeline_inspected") or [])
    for media_id in sorted(_media_review_required_media(config, "media_opened") - opened):
        missing.append(f"media_opened:{media_id}")
    for media_id in sorted(_media_review_required_media(config, "timeline_inspected") - inspected):
        missing.append(f"timeline_inspected:{media_id}")
    blocking_issue_ids = [
        str(item["id"])
        for item in issues
        if isinstance(item, dict) and item.get("severity") == "blocking" and item.get("status") in BLOCKING_STATUSES
    ]
    return {
        "status": "complete" if not missing and not blocking_issue_ids else "incomplete",
        "missing_required_evidence": missing,
        "blocking_issue_ids": blocking_issue_ids,
    }


def _resolve_source_artifact_path(project_dir: Path | str, artifact_key: str) -> Path:
    project_root = Path(project_dir).resolve()
    if artifact_key.startswith("/") or "\\" in artifact_key or "\x00" in artifact_key:
        raise ValueError(f"GenUI source artifact key {artifact_key!r} is not project-relative")
    candidate = Path(artifact_key)
    if len(candidate.parts) == 1 and candidate.suffix != ".json":
        candidate = Path("artifacts") / f"{artifact_key}.json"
    path = (project_root / candidate).resolve()
    path.relative_to(project_root)
    return path


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_conflict_status(config: dict[str, Any], project_dir: Path | str | None = None) -> dict[str, Any]:
    """Check source hashes without writing canonical artifacts."""
    hashes = config.get("source_artifact_hashes") or {}
    if not isinstance(hashes, dict) or not hashes:
        return {"status": "not_checked", "source_artifact_hashes": {}, "conflicting_artifacts": []}
    if project_dir is None:
        return {"status": "not_checked", "source_artifact_hashes": hashes, "conflicting_artifacts": []}

    conflicts: list[str] = []
    for artifact_key, expected_hash in hashes.items():
        if not isinstance(artifact_key, str) or not isinstance(expected_hash, str):
            conflicts.append(str(artifact_key))
            continue
        try:
            current_hash = _file_sha256(_resolve_source_artifact_path(project_dir, artifact_key))
        except Exception:
            current_hash = None
        if current_hash != expected_hash:
            conflicts.append(artifact_key)
    return {
        "status": "conflict" if conflicts else "clean",
        "source_artifact_hashes": hashes,
        "conflicting_artifacts": conflicts,
    }


def _bound_source_artifacts(config: dict[str, Any]) -> list[str]:
    artifacts: list[str] = []
    for ref in config.get("artifact_refs") or []:
        if isinstance(ref, dict) and isinstance(ref.get("artifact"), str):
            artifacts.append(ref["artifact"])
    for surface in config.get("surfaces") or []:
        if not isinstance(surface, dict):
            continue
        contract = surface.get("contract")
        if not isinstance(contract, dict):
            continue
        for binding in contract.get("artifact_bindings") or []:
            if isinstance(binding, dict) and isinstance(binding.get("artifact"), str):
                artifacts.append(binding["artifact"])
    return list(dict.fromkeys(artifacts))


def _hashes_cover_source_artifact(hashes: dict[str, Any], project_dir: Path | str, artifact_key: str) -> bool:
    if artifact_key in hashes:
        return True
    try:
        artifact_path = _resolve_source_artifact_path(project_dir, artifact_key)
    except Exception:
        return False
    for existing_key in hashes:
        if not isinstance(existing_key, str):
            continue
        try:
            if _resolve_source_artifact_path(project_dir, existing_key) == artifact_path:
                return True
        except Exception:
            continue
    return False


def with_source_artifact_hashes(config: dict[str, Any], project_dir: Path | str) -> dict[str, Any]:
    """Attach hashes for bound source artifacts so resume checks are automatic."""
    hashes = dict(config.get("source_artifact_hashes") or {})
    for artifact_key in _bound_source_artifacts(config):
        if _hashes_cover_source_artifact(hashes, project_dir, artifact_key):
            continue
        try:
            artifact_hash = _file_sha256(_resolve_source_artifact_path(project_dir, artifact_key))
        except Exception:
            artifact_hash = None
        if artifact_hash:
            hashes[artifact_key] = artifact_hash
    next_config = dict(config)
    next_config["source_artifact_hashes"] = hashes
    validate_session_config(next_config)
    return next_config


def session_response_payload_from_submission(
    config: dict[str, Any],
    submission: dict[str, Any],
    *,
    response_id: str | None = None,
    project_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Build a ui_session_response payload from browser-submitted state."""
    validate_session_config(config)
    configured_actions = {action["kind"] for action in config.get("actions") or []}
    action = submission.get("action", "submit")
    if not configured_actions:
        raise ValueError(f"GenUI session {_session_id(config)} does not accept browser submissions")
    if configured_actions and action not in configured_actions:
        raise ValueError(f"Submit action {action!r} is not configured for {_session_id(config)}")

    values = _coerce_submission_values(submission.get("values"))
    annotations = _bounded_list(submission.get("annotations"), field_name="annotations")
    selected_refs = _bounded_list(submission.get("selected_refs"), field_name="selected_refs")
    issues = _bounded_list(submission.get("issues"), field_name="issues")
    revision_patches = _bounded_list(submission.get("revision_patches"), field_name="revision_patches", max_items=200)
    approval_attestations = _bounded_list(
        submission.get("approval_attestations"),
        field_name="approval_attestations",
        max_items=200,
    )
    browser_events = _bounded_list(submission.get("browser_events"), field_name="browser_events", max_items=50)
    interaction_evidence = _bounded_object(submission.get("interaction_evidence"), field_name="interaction_evidence")
    interaction_evidence.setdefault("media_opened", [])
    interaction_evidence.setdefault("timeline_inspected", [])
    interaction_evidence.setdefault("seconds_watched", 0)
    _reject_non_finite_json(
        {
            "values": values,
            "annotations": annotations,
            "selected_refs": selected_refs,
            "issues": issues,
            "revision_patches": revision_patches,
            "approval_attestations": approval_attestations,
            "browser_events": browser_events,
            "interaction_evidence": interaction_evidence,
        },
        context="ui_session_submission",
    )
    _validate_session_semantics(
        config,
        action=action,
        values=values,
        annotations=annotations,
        selected_refs=selected_refs,
        issues=issues,
        revision_patches=revision_patches,
        approval_attestations=approval_attestations,
        interaction_evidence=interaction_evidence,
    )
    last_event_type = None
    if browser_events and isinstance(browser_events[-1], dict):
        last_event_type = browser_events[-1].get("type")
    session_id = _session_id(config)
    required_opened = sorted(_media_review_required_media(config, "media_opened"))
    required_timeline = sorted(_media_review_required_media(config, "timeline_inspected"))
    response = _without_none({
        "contract": SESSION_RESPONSE_CONTRACT,
        "response_id": response_id or f"resp-{session_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "session_id": session_id,
        "config_id": session_id,
        "routing_decision_id": config.get("metadata", {}).get("routing_decision_id"),
        "project_id": config["project_id"],
        "pipeline_type": config["pipeline_type"],
        "stage": config["stage"],
        "gate": config["gate"],
        "submitted_at": _now_iso(),
        "action": action,
        "values": values,
        "annotations": annotations,
        "selected_refs": selected_refs,
        "issues": issues,
        "revision_patches": revision_patches,
        "approval_attestations": approval_attestations,
        "resume_decision": (
            {
                "decision_id": config["decision_id"],
                "resume_token": config["resume_token"],
                "action": action,
            }
            if config.get("decision_id") and config.get("resume_token")
            else None
        ),
        "review_completion": _review_completion_payload(
            config,
            action=action,
            issues=issues,
            approval_attestations=approval_attestations,
            interaction_evidence=interaction_evidence,
        ),
        "conflict_status": source_conflict_status(config, project_dir),
        "interaction_evidence": interaction_evidence,
        "evidence_status": {
            "media_opened_count": len(interaction_evidence.get("media_opened") or []),
            "timeline_inspected_count": len(interaction_evidence.get("timeline_inspected") or []),
            "approval_attestation_count": len(approval_attestations),
            "required_media_opened": required_opened,
            "required_timeline_inspected": required_timeline,
        },
        "event_summary": _without_none(
            {
                "event_count": len(browser_events),
                "last_event_type": last_event_type,
            }
        ),
        "browser_events": browser_events,
        "validation": {"status": "pending", "errors": []},
        "metadata": {
            "framework": config["framework"]["name"],
            "transport": config["transport"]["name"],
            "genui_contract": GENUI_CONTRACT,
        },
    })
    validate_session_response(response)
    return response


def write_session_response(response_path: Path | str, response: dict[str, Any]) -> Path:
    response = _normalize_session_response_contract(response)
    validate_session_response(response)
    path = Path(response_path)
    _dump_json(path, response)
    return path


def review_session_response(config: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Return an agent-side review plan without mutating canonical artifacts."""
    validate_session_config(config)
    validate_session_response(response)
    conflict_status = response.get("conflict_status") if isinstance(response.get("conflict_status"), dict) else {}
    conflicts = [
        str(item)
        for item in conflict_status.get("conflicting_artifacts") or []
        if str(item)
    ]
    blocking_issue_ids = [
        issue["id"]
        for issue in response.get("issues") or []
        if issue.get("severity") == "blocking" and issue.get("status") in BLOCKING_STATUSES
    ]
    patch_plan = list(response.get("revision_patches") or [])
    for issue in response.get("issues") or []:
        artifact = issue.get("artifact")
        path = issue.get("path")
        if isinstance(artifact, str) and isinstance(path, str):
            patch = {
                "artifact": artifact,
                "path": path,
                "value": issue.get("requested_change"),
                "issue_id": issue["id"],
            }
            if patch not in patch_plan:
                patch_plan.append(patch)
    return {
        "session_id": response["session_id"],
        "action": response["action"],
        "blocking_issue_ids": blocking_issue_ids,
        "conflicting_artifacts": conflicts,
        "patch_plan": patch_plan,
        "canonical_writes": [],
        "validation": {
            "status": "blocked" if blocking_issue_ids or conflicts else "ready_for_agent_review",
            "errors": [f"Source artifact changed since GenUI session creation: {item}" for item in conflicts],
        },
    }


def _default_actions() -> list[dict[str, Any]]:
    return [
        {"id": "approve", "label": "Approve", "kind": "approve", "recommended": True},
        {"id": "revise", "label": "Request revisions", "kind": "revise"},
        {"id": "abort", "label": "Abort", "kind": "abort"},
    ]


def _normalize_media_ref_path(path: Any) -> Any:
    if not isinstance(path, str) or path.startswith("/media/"):
        return path
    parts = Path(path).parts
    if parts and parts[0] in {"assets", "media", "outputs", "reference_assets", "renders"}:
        return f"/media/{Path(*parts).as_posix()}"
    return path


def _media_refs_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in request.get("media_items") or []:
        if not item.get("path") and item.get("kind") != "text":
            continue
        refs.append(
            _without_none(
                {
                    "id": _slug(item.get("id") or item.get("title"), fallback="media"),
                    "kind": item.get("kind", "path"),
                    "title": item.get("title") or item.get("id") or "Media",
                    "path": _normalize_media_ref_path(item.get("path")),
                    "text": item.get("text"),
                    "alt": item.get("alt") or item.get("title"),
                }
            )
        )
    return refs


def _artifact_refs_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    selection_binding = request.get("selection_binding")
    if selection_binding:
        refs.append(
            {
                "id": _slug(f"{request.get('selection_field_id') or 'selection'}-binding", fallback="artifact"),
                "artifact": selection_binding["artifact"],
                "path": selection_binding["path"],
                "label": request.get("selection_label") or "Selection",
            }
        )
    for field in request.get("fields") or []:
        binding = field.get("binding")
        if not binding:
            continue
        refs.append(
            {
                "id": _slug(f"{field['id']}-binding", fallback="artifact"),
                "artifact": binding["artifact"],
                "path": binding["path"],
                "label": field.get("label", field["id"]),
            }
        )
    return refs


def _fields_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(field) for field in request.get("fields") or []]


def _choices_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(choice) for choice in request.get("choices") or []]


def _selection_config_from_request(request: dict[str, Any]) -> dict[str, Any] | None:
    choices = _choices_from_request(request)
    if not choices:
        return None
    field_id = str(request.get("selection_field_id") or "selection")
    selection = _without_none(
        {
            "fieldId": field_id,
            "label": request.get("selection_label") or "Select an option",
            "allowMultiple": bool(request.get("allow_multiple")),
            "binding": request.get("selection_binding"),
        }
    )
    return selection


def _initial_values_from_request(request: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in request.get("fields") or []:
        if "default" in field:
            values[str(field["id"])] = field["default"]
    choices = _choices_from_request(request)
    if choices:
        recommended = [choice["value"] for choice in choices if choice.get("recommended")]
        if recommended:
            field_id = str(request.get("selection_field_id") or "selection")
            values[field_id] = recommended if request.get("allow_multiple") else recommended[0]
    return values


def _choose_session_mode(request: dict[str, Any], assessment: dict[str, Any]) -> str:
    if request.get("interaction_kind") == "media_review" or request.get("media_items"):
        return "media_review_room"
    if request.get("interaction_kind") == "project_cockpit" or request.get("surface_mode") == "project_cockpit":
        return "project_cockpit"
    if request.get("interaction_kind") == "background_status" or request.get("surface_mode") == "background_status":
        return "background_status"
    recommended = assessment.get("recommended_mode")
    if recommended in {"gate_workspace", "media_review_room", "project_cockpit", "background_status"}:
        return str(recommended)
    return "gate_workspace"


def _workspace_type_for_request(request: dict[str, Any]) -> str | None:
    gate = str(request.get("gate") or "").lower().replace("-", "_")
    stage = str(request.get("stage") or "").lower().replace("-", "_")
    if gate in PIPELINE_WORKSPACE_TYPES:
        return PIPELINE_WORKSPACE_TYPES[gate]
    if stage in PIPELINE_WORKSPACE_TYPES:
        return PIPELINE_WORKSPACE_TYPES[stage]
    return None


def _workspace_kind_for_request(request: dict[str, Any], *, mode: str, workspace_type: str | None) -> str:
    for raw_token in (request.get("gate"), request.get("stage")):
        token = str(raw_token or "").lower().replace("-", "_")
        if token in WORKSPACE_KIND_ALIASES:
            return WORKSPACE_KIND_ALIASES[token]
    if workspace_type:
        return WORKSPACE_KIND_BY_SURFACE.get(workspace_type, _surface_id_for_type(workspace_type).replace("-", "_"))
    if mode == "media_review_room":
        return "media_review"
    if mode == "project_cockpit":
        return "project_cockpit"
    if mode == "background_status":
        return "background_status"
    return "gate_workspace"


def _artifact_bindings_from_fields(
    fields: list[dict[str, Any]],
    selection: dict[str, Any] | None,
) -> list[dict[str, str]]:
    bindings: list[dict[str, str]] = []
    if isinstance(selection, dict) and isinstance(selection.get("binding"), dict):
        binding = selection["binding"]
        if isinstance(binding.get("artifact"), str) and isinstance(binding.get("path"), str):
            bindings.append(
                {
                    "field_id": str(selection.get("fieldId") or "selection"),
                    "artifact": binding["artifact"],
                    "path": binding["path"],
                }
            )
    for field in fields:
        binding = field.get("binding") if isinstance(field, dict) else None
        if isinstance(binding, dict) and isinstance(binding.get("artifact"), str) and isinstance(binding.get("path"), str):
            bindings.append(
                {
                    "field_id": str(field.get("id") or f"{binding['artifact']}.{binding['path']}"),
                    "artifact": binding["artifact"],
                    "path": binding["path"],
                }
            )
    return bindings


def _workspace_contract(
    *,
    workspace_kind: str,
    allowed_actions: list[dict[str, Any]],
    required_evidence: list[str],
    fields: list[dict[str, Any]],
    selection: dict[str, Any] | None,
    issue_targets: list[str],
) -> dict[str, Any]:
    return {
        "workspace_kind": workspace_kind,
        "canonical_writes": False,
        "response_artifact": "ui_session_response",
        "allowed_actions": [str(action["kind"]) for action in allowed_actions if action.get("kind")],
        "required_evidence": list(dict.fromkeys(required_evidence)),
        "artifact_bindings": _artifact_bindings_from_fields(fields, selection),
        "issue_targets": issue_targets,
    }


def _surface_id_for_type(surface_type: str) -> str:
    return _slug(re.sub(r"(?<!^)([A-Z])", r"-\1", surface_type).lower(), fallback="workspace")


def build_dynamic_session_config(
    request: dict[str, Any],
    *,
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a framework-backed session config from an interaction request."""
    from lib.genui.dynamic import validate_interaction_request
    from lib.genui.interaction_policy import assess_interaction_need

    validate_interaction_request(request)
    decision = decision or assess_interaction_need(request)
    visual_need = _normalize_visual_need(decision)
    requires_approval_attestation = "approval_attestation" in set(visual_need.get("required_ui_primitives") or [])
    session_id = _slug(request.get("config_id") or request.get("request_id"), fallback="genui-session")
    decision_id = _decision_id(session_id)
    resume_token = _resume_token(session_id)
    stage_policy_id = str(decision["stage_policy_id"]) if decision.get("stage_policy_id") else None
    schema_strategy = str(decision.get("schema_strategy") or ("fixed" if stage_policy_id else "dynamic"))
    if schema_strategy not in SESSION_SCHEMA_STRATEGIES:
        schema_strategy = "fixed" if stage_policy_id else "dynamic"
    media_refs = _media_refs_from_request(request)
    artifact_refs = _artifact_refs_from_request(request)
    interaction_fields = _fields_from_request(request)
    interaction_choices = _choices_from_request(request)
    selection_config = _selection_config_from_request(request)
    initial_values = _initial_values_from_request(request)
    trace_refs = [
        {
            "id": "agent-review-boundary",
            "label": "Agent review boundary",
            "source": "AGENT_GUIDE.md",
            "summary": "GenUI collects choices only; the agent validates ui_session_response before canonical writes.",
        },
        {
            "id": "a2ui-framework-contract",
            "label": "A2UI framework contract",
            "source": "A2UI + CopilotKit docs",
            "summary": "A2UI sessions use declarative surfaces rendered by trusted registered components, not generated code.",
        },
    ]
    mode = _choose_session_mode(request, visual_need)
    surfaces: list[dict[str, Any]] = []
    media_ids = [item["id"] for item in media_refs]
    artifact_ref_ids = [item["id"] for item in artifact_refs]
    workspace_type = _workspace_type_for_request(request)
    workspace_kind = _workspace_kind_for_request(request, mode=mode, workspace_type=workspace_type)
    submit_actions = [] if mode in {"project_cockpit", "background_status"} else request.get("submit_actions") or _default_actions()
    base_issue_targets = list(dict.fromkeys([
        *media_ids,
        *[
            str(item.get("scene_id"))
            for item in request.get("review_items") or []
            if item.get("scene_id")
        ],
    ]))
    if mode == "project_cockpit":
        surfaces.append(
            {
                "id": "project-cockpit",
                "type": "ProjectCockpit",
                "workspace_kind": workspace_kind,
                "title": request["title"],
                "description": request.get("prompt"),
                "media_ids": media_ids,
                "artifact_ref_ids": artifact_ref_ids,
                "trace_ref_ids": [item["id"] for item in trace_refs],
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=[],
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=base_issue_targets,
                ),
            }
        )
    elif mode == "background_status":
        surfaces.append(
            {
                "id": "background-status",
                "type": "BackgroundStatus",
                "workspace_kind": workspace_kind,
                "title": request["title"],
                "description": request.get("prompt"),
                "media_ids": media_ids,
                "artifact_ref_ids": artifact_ref_ids,
                "trace_ref_ids": [item["id"] for item in trace_refs],
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=[],
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=base_issue_targets,
                ),
            }
        )
    elif workspace_type is not None:
        required_evidence = ["approval_attested"] if mode == "gate_workspace" or requires_approval_attestation else []
        surfaces.append(
            {
                "id": _surface_id_for_type(workspace_type),
                "type": workspace_type,
                "workspace_kind": workspace_kind,
                "title": request["title"],
                "description": request.get("prompt"),
                "media_ids": media_ids,
                "artifact_ref_ids": artifact_ref_ids,
                "trace_ref_ids": [item["id"] for item in trace_refs],
                "required_evidence": required_evidence,
                "fields": interaction_fields,
                "choices": interaction_choices,
                "selection": selection_config,
                "review_items": request.get("review_items") or [],
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=required_evidence,
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=base_issue_targets,
                ),
            }
        )
    if mode == "media_review_room":
        required_evidence = ["media_opened", "timeline_inspected"]
        if requires_approval_attestation and workspace_type is None:
            required_evidence.append("approval_attested")
        surfaces.append(
            {
                "id": "review-room",
                "type": "MediaReviewRoom",
                "workspace_kind": workspace_kind,
                "title": request.get("review_title") or request["title"],
                "description": request.get("prompt"),
                "media_ids": media_ids,
                "artifact_ref_ids": artifact_ref_ids,
                "trace_ref_ids": [item["id"] for item in trace_refs],
                "required_evidence": required_evidence,
                "fields": interaction_fields,
                "choices": interaction_choices,
                "selection": selection_config,
                "review_items": request.get("review_items") or [],
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=required_evidence,
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=base_issue_targets,
                ),
            }
        )
    elif mode == "gate_workspace" and workspace_type is None:
        required_evidence = ["approval_attested"]
        surfaces.append(
            {
                "id": "gate-workspace",
                "type": "GateWorkspace",
                "workspace_kind": workspace_kind,
                "title": request["title"],
                "description": request.get("prompt"),
                "media_ids": media_ids,
                "artifact_ref_ids": artifact_ref_ids,
                "trace_ref_ids": [item["id"] for item in trace_refs],
                "required_evidence": required_evidence,
                "fields": interaction_fields,
                "choices": interaction_choices,
                "selection": selection_config,
                "review_items": request.get("review_items") or [],
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=required_evidence,
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=base_issue_targets,
                ),
            }
        )
    allowed_targets = list(dict.fromkeys([
        *media_ids,
        *[
            str(item.get("scene_id"))
            for item in request.get("review_items") or []
            if item.get("scene_id")
        ],
        *[surface["id"] for surface in surfaces],
    ]))
    if mode not in {"project_cockpit", "background_status"}:
        surfaces.append(
            {
                "id": "issues",
                "type": "IssueTracker",
                "workspace_kind": workspace_kind,
                "title": "Review issues",
                "description": "Track exact user-requested changes as issue IDs before the agent updates artifacts.",
                "allowed_targets": allowed_targets,
                "allowed_statuses": sorted(ISSUE_STATUSES),
                "artifact_ref_ids": artifact_ref_ids,
                "contract": _workspace_contract(
                    workspace_kind=workspace_kind,
                    allowed_actions=submit_actions,
                    required_evidence=[],
                    fields=interaction_fields,
                    selection=selection_config,
                    issue_targets=allowed_targets,
                ),
            }
        )
    config = _without_none(
        {
            "contract": SESSION_CONTRACT,
            "session_id": session_id,
            "config_id": session_id,
            "project_id": str(request["project_id"]),
            "pipeline_type": str(request["pipeline_type"]),
            "stage": str(request["stage"]),
            "gate": str(request["gate"]),
            "mode": mode,
            "workspace_kind": workspace_kind,
            "title": str(request["title"]),
            "description": request.get("description") or request.get("prompt"),
            "decision_id": decision_id,
            "resume_token": resume_token,
            "expires_at": _expires_iso(),
            "stage_policy_id": stage_policy_id,
            "schema_strategy": schema_strategy,
            "source_artifact_hashes": request.get("source_artifact_hashes") or {},
            "event_stream": {
                "transport": "sse",
                "endpoint": "/events",
                "cursor": "sequence",
                "supports_last_event_id": True,
                "replay": True,
                "max_events": 10000,
            },
            "draft_state": {
                "path": DRAFT_FILENAME,
                "endpoint": "/draft",
                "autosave": True,
                "response_only": True,
            },
            "conflict_policy": {
                "source_hash_check": "on_submit",
                "block_canonical_writes": True,
            },
            "framework": dict(SESSION_FRAMEWORK),
            "transport": {
                "name": "ag-ui",
                "thread_id": str(request["project_id"]),
                "run_id": session_id,
            },
            "visual_need_assessment": visual_need,
            "operation_events": _default_operation_events({"session_id": session_id}),
            "media_refs": media_refs,
            "artifact_refs": artifact_refs,
            "trace_refs": trace_refs,
            "surfaces": surfaces,
            "issues": [],
            "initial_values": initial_values,
            "actions": submit_actions,
            "metadata": {
                "genui_contract": GENUI_CONTRACT,
                "workspace_kind": workspace_kind,
                "draft_path": DRAFT_FILENAME,
                "interaction_journal": True,
                "routing_decision_id": f"route-{session_id}",
                "decision_id": decision_id,
                "resume_token": resume_token,
                "expires_at": _expires_iso(),
                "stage_policy_id": stage_policy_id,
                "schema_strategy": schema_strategy,
                "dynamic_interaction": True,
                "source_request_id": request.get("request_id"),
                "framework": "a2ui",
                "framework_renderer": "@copilotkit/a2ui-renderer",
                "protocol": "ag-ui",
            },
        }
    )
    validate_session_config(config)
    return config


def build_project_cockpit_session_config(
    project_dir: Path | str,
    *,
    project_id: str,
    pipeline_type: str,
    active_stage: str | None = None,
) -> dict[str, Any]:
    """Build a read-only GenUI project cockpit session config."""
    project_root = Path(project_dir)
    session_id = _slug(f"{project_id}-cockpit", fallback="project-cockpit")
    decision_id = _decision_id(session_id)
    snapshot = build_project_cockpit_snapshot(
        project_root,
        pipeline_type=pipeline_type,
        active_stage=active_stage,
    )
    artifact_items = snapshot["artifact_items"]
    media_refs = snapshot["media_refs"]
    visual_need = {
        "recommended_mode": "project_cockpit",
        "recommended_tool": "genui_session",
        "linear_chat_sufficient": False,
        "interaction_kind": "project_cockpit",
        "reasons": ["project_state_overview"],
        "required_ui_primitives": ["status_timeline", "artifact_trace", "budget_panel"],
        "confidence": 0.9,
        "fallback": "cli_only_when_browser_fails_or_user_declines",
    }
    trace_refs = [
        {
            "id": "read-only-boundary",
            "label": "Read-only cockpit boundary",
            "source": "AGENT_GUIDE.md",
            "summary": "The cockpit can inspect project state but must not advance stages or write canonical artifacts.",
        }
    ]
    config = {
        "contract": SESSION_CONTRACT,
        "session_id": session_id,
        "config_id": session_id,
        "project_id": project_id,
        "pipeline_type": pipeline_type,
        "stage": active_stage or "project",
        "gate": "project_cockpit",
        "mode": "project_cockpit",
        "workspace_kind": "project_cockpit",
        "title": f"{project_id} Project Cockpit",
        "description": "Read-only project status, artifacts, decisions, budget, blockers, and pending GenUI gates.",
        "decision_id": decision_id,
        "resume_token": _resume_token(session_id),
        "expires_at": _expires_iso(),
        "stage_policy_id": f"{pipeline_type}.project_cockpit",
        "schema_strategy": "fixed",
        "source_artifact_hashes": {},
        "event_stream": {
            "transport": "sse",
            "endpoint": "/events",
            "cursor": "sequence",
            "supports_last_event_id": True,
            "replay": True,
            "max_events": 10000,
        },
        "draft_state": {
            "path": DRAFT_FILENAME,
            "endpoint": "/draft",
            "autosave": False,
            "response_only": True,
        },
        "conflict_policy": {
            "source_hash_check": "not_required",
            "block_canonical_writes": True,
        },
        "framework": dict(SESSION_FRAMEWORK),
        "transport": {
            "name": "ag-ui",
            "thread_id": project_id,
            "run_id": session_id,
        },
        "visual_need_assessment": visual_need,
        "operation_events": _default_operation_events({"session_id": session_id}),
        "media_refs": media_refs,
        "artifact_refs": [
            {
                "id": item["id"],
                "artifact": item["artifact"],
                "path": item["artifact"].replace("-", "_"),
                "label": item["artifact"].replace("_", " ").title(),
                "summary": item.get("status"),
            }
            for item in artifact_items
        ],
        "trace_refs": trace_refs,
        "surfaces": [
            {
                "id": "project-cockpit",
                "type": "ProjectCockpit",
                "workspace_kind": "project_cockpit",
                "title": "Production control room",
                "description": f"Project root: {project_root}",
                "media_ids": [item["id"] for item in media_refs],
                "artifact_ref_ids": [item["id"] for item in artifact_items],
                "trace_ref_ids": ["read-only-boundary"],
                "timeline_items": snapshot["timeline_items"],
                "artifact_items": artifact_items,
                "decision_items": snapshot["decision_items"],
                "budget_cost_items": snapshot["budget_cost_items"],
                "pending_responses": snapshot["pending_responses"],
                "stale_sessions": snapshot["stale_sessions"],
                "validation_blockers": snapshot["validation_blockers"],
                "journal_items": snapshot["journal_items"],
                "contract": _workspace_contract(
                    workspace_kind="project_cockpit",
                    allowed_actions=[],
                    required_evidence=[],
                    fields=[],
                    selection=None,
                    issue_targets=[],
                ),
            }
        ],
        "issues": [],
        "actions": [],
        "metadata": {
            "genui_contract": GENUI_CONTRACT,
            "workspace_kind": "project_cockpit",
            "draft_path": DRAFT_FILENAME,
            "interaction_journal": True,
            "routing_decision_id": f"route-{session_id}",
            "decision_id": decision_id,
            "stage_policy_id": f"{pipeline_type}.project_cockpit",
            "schema_strategy": "fixed",
            "project_snapshot": snapshot,
            "read_only": True,
            "framework": "a2ui",
            "framework_renderer": "@copilotkit/a2ui-renderer",
            "protocol": "ag-ui",
        },
    }
    validate_session_config(config)
    return config


def build_ag_ui_session_events(config: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a cursor-addressable AG-UI-compatible event snapshot for the local session."""
    validate_session_config(config)
    try:
        from ag_ui.core import EventType
    except Exception:
        EventType = None  # type: ignore[assignment]

    def event_type(name: str) -> str:
        if EventType is None:
            return name
        value = getattr(EventType, name, name)
        return str(getattr(value, "value", value))

    session_id = _session_id(config)
    transport = config["transport"]
    common = {
        "threadId": transport["thread_id"],
        "runId": transport["run_id"],
    }
    prepare_call_id = f"{session_id}-prepare"
    await_call_id = f"{session_id}-await-response"
    raw_events = [
        {"type": event_type("RUN_STARTED"), **common},
        {"type": event_type("STEP_STARTED"), **common, "stepName": "genui_session"},
        {
            "type": "GENUI_SESSION_READY",
            **common,
            "sessionId": session_id,
            "workspaceKind": config.get("workspace_kind"),
            "genuiContract": GENUI_CONTRACT,
        },
        {"type": event_type("STATE_SNAPSHOT"), **common, "snapshot": state},
        {
            "type": event_type("TOOL_CALL_START"),
            **common,
            "toolCallId": prepare_call_id,
            "toolCallName": "genui_session.prepare",
        },
        {
            "type": event_type("TOOL_CALL_END"),
            **common,
            "toolCallId": prepare_call_id,
            "toolCallName": "genui_session.prepare",
        },
        {
            "type": event_type("STATE_DELTA"),
            **common,
            "delta": [
                {
                    "op": "replace",
                    "path": "/session/status",
                    "value": "prepared",
                }
            ],
        },
        {
            "type": event_type("TOOL_CALL_START"),
            **common,
            "toolCallId": await_call_id,
            "toolCallName": "genui_session.await_response",
        },
        {
            "type": event_type("ACTIVITY_SNAPSHOT"),
            **common,
            "activity": {
                "sessionId": session_id,
                "mode": config["mode"],
                "framework": config["framework"]["name"],
                "surfaces": [surface["id"] for surface in config.get("surfaces") or []],
                "operationEvents": config.get("operation_events") or _default_operation_events(config),
            },
        },
        {
            "type": event_type("TOOL_CALL_END"),
            **common,
            "toolCallId": await_call_id,
            "toolCallName": "genui_session.await_response",
        },
        {"type": event_type("STEP_FINISHED"), **common, "stepName": "genui_session"},
        {"type": event_type("RUN_FINISHED"), **common},
    ]
    return number_session_events(config, raw_events)
