"""GenUI compatibility product surfaces.

GenUI compatibility keeps Video Production Buddy's existing safety model: the local browser collects
human review input and writes only a response artifact. The agent remains the
only writer of canonical production artifacts, decision logs, and checkpoints.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from schemas.artifacts import validate_artifact
from lib.genui.view_spec import (
    RENDERER_NAME,
    VIEW_SPEC_FILENAME,
    render_shell_html,
    validate_view_spec,
)


SURFACE_CONTRACT = "genui_surface"
SURFACE_RESPONSE_CONTRACT = "genui_surface_response"
SURFACE_VIEW_CONTRACT = "genui_surface_view"
SURFACE_DIRNAME = "ui"
MAX_SURFACE_VALUE_LENGTH = 10000
MAX_SURFACE_LIST_ITEMS = 500


SURFACE_COMPONENTS = {
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
}


FIELD_TYPES = {
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
}


@dataclass(frozen=True)
class SurfaceBundle:
    """Materialized compatibility surface files for one project interaction."""

    config: dict[str, Any]
    config_path: Path
    html_path: Path
    view_spec_path: Path
    response_path: Path
    state_path: Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    _reject_non_finite_json(payload, context=str(path))
    try:
        serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    except (TypeError, ValueError) as exc:
        raise ValueError(f"GenUI compatibility payload must be strict JSON serializable: {exc}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(serialized)


def _reject_non_finite_json(value: Any, *, context: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"GenUI compatibility payload contains non-finite JSON number at {context}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite_json(item, context=f"{context}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite_json(item, context=f"{context}[{index}]")


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
        slug = f"surface-{slug}"
    return slug[:64]


def _without_none(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


def _surface_id(config: dict[str, Any]) -> str:
    surface_id = config.get("surface_id") or config.get("config_id")
    if not isinstance(surface_id, str) or not surface_id:
        raise ValueError("GenUI compatibility surface config must declare surface_id")
    return surface_id


def _iter_blocks(config: dict[str, Any]) -> list[dict[str, Any]]:
    return list(config.get("blocks") or [])


def _iter_configured_fields(config: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for block in _iter_blocks(config):
        block_id = block["id"]
        if block.get("options"):
            field_type = "multiselect" if block.get("multiple") else "radio"
            fields.append(
                {
                    "id": f"{block_id}.selection",
                    "_block_id": block_id,
                    "_local_id": "selection",
                    "_kind": "selection",
                    "_binding": block.get("binding"),
                    "type": field_type,
                    "required": True,
                    "choices": block["options"],
                    "default": (
                        _recommended_option_values(block["options"])
                        if field_type == "multiselect"
                        else _recommended_option_value(block["options"])
                    ),
                }
            )
        for field in block.get("fields") or []:
            fields.append(
                {
                    **field,
                    "id": f"{block_id}.{field['id']}",
                    "_block_id": block_id,
                    "_local_id": field["id"],
                    "_kind": "field",
                    "_binding": field.get("binding"),
                }
            )
        for field in block.get("annotation_fields") or []:
            fields.append(
                {
                    **field,
                    "id": f"{block_id}.{field['id']}",
                    "_block_id": block_id,
                    "_local_id": field["id"],
                    "_kind": "annotation",
                    "_binding": field.get("binding"),
                    "_target_ref": _annotation_target_ref(block, field),
                }
            )
        if block["type"] == "ApprovalChecklist":
            for item in block.get("items") or []:
                item_id = _slug(item.get("id") or item.get("label"), fallback="approval")
                fields.append(
                    {
                        "id": f"{block_id}.{item_id}",
                        "_block_id": block_id,
                        "_local_id": item_id,
                        "_kind": "approval",
                        "_label": str(item.get("label") or item_id),
                        "type": "approval",
                        "required": bool(item.get("required", True)),
                        "default": bool(item.get("approved", False)),
                    }
                )
    return fields


def _recommended_option_value(options: list[dict[str, Any]]) -> str:
    for option in options:
        if option.get("recommended"):
            return _option_value(option)
    if options:
        return _option_value(options[0])
    return ""


def _recommended_option_values(options: list[dict[str, Any]]) -> list[str]:
    values = [
        _option_value(option)
        for option in options
        if option.get("recommended")
    ]
    if values:
        return values
    if options:
        return [_option_value(options[0])]
    return []


def _option_value(option: dict[str, Any], *, fallback: Any = "") -> str:
    return str(option.get("value") or option.get("id") or option.get("label") or fallback)


def _annotation_target_ref(block: dict[str, Any], field: dict[str, Any]) -> str:
    explicit = field.get("target_ref") or field.get("targetRef")
    if isinstance(explicit, str) and explicit:
        return explicit
    media_ids = [media_id for media_id in block.get("media_ids") or [] if isinstance(media_id, str)]
    if len(media_ids) == 1:
        return media_ids[0]
    return block["id"]


def _field_default(field: dict[str, Any]) -> Any:
    if "default" in field:
        return field["default"]
    field_type = field.get("type")
    choices = field.get("choices") or []
    if field_type in {"checkbox", "approval"}:
        return False
    if field_type == "multiselect":
        return _recommended_option_values(choices)
    if field_type in {"radio", "select"}:
        return _recommended_option_value(choices)
    return ""


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, bool):
        return value is False
    return False


def _coerce_field_value(field: dict[str, Any], value: Any) -> Any:
    field_id = field["id"]
    field_type = field["type"]
    if field_type == "multiselect":
        if not isinstance(value, list):
            raise ValueError(f"GenUI compatibility field {field_id!r} must be a list")
        if len(value) > MAX_SURFACE_LIST_ITEMS:
            raise ValueError(f"GenUI compatibility field {field_id!r} has too many selections")
        if not all(isinstance(item, str) for item in value):
            raise ValueError(f"GenUI compatibility field {field_id!r} selections must be strings")
        return value
    if field_type in {"checkbox", "approval"}:
        if not isinstance(value, bool):
            raise ValueError(f"GenUI compatibility field {field_id!r} must be boolean")
        return value
    if field_type == "number":
        if value is None or (isinstance(value, str) and not value.strip()):
            return value
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"GenUI compatibility field {field_id!r} must be numeric") from exc
        if not math.isfinite(number):
            raise ValueError(f"GenUI compatibility field {field_id!r} must be finite")
        return number
    if not isinstance(value, str):
        raise ValueError(f"GenUI compatibility field {field_id!r} must be a string")
    if len(value) > MAX_SURFACE_VALUE_LENGTH:
        raise ValueError(f"GenUI compatibility field {field_id!r} is too long")
    return value


def _resolve_visible_field_id(field: dict[str, Any], configured_field_ids: set[str]) -> str:
    visible_if = field.get("visible_if")
    if not visible_if:
        return ""
    reference = str(visible_if["field"])
    if reference in configured_field_ids:
        return reference

    same_block = f"{field.get('_block_id')}.{reference}"
    if field.get("_block_id") and same_block in configured_field_ids:
        return same_block

    suffix_matches = sorted(
        field_id for field_id in configured_field_ids if field_id.endswith(f".{reference}")
    )
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    if len(suffix_matches) > 1:
        raise ValueError(
            f"GenUI compatibility field {field['id']!r} has ambiguous visible_if field "
            f"{reference!r}: {suffix_matches}"
        )
    raise ValueError(
        f"GenUI compatibility field {field['id']!r} has visible_if referencing unknown field {reference!r}"
    )


def _visibility_values(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
    configured_field_ids: set[str],
) -> dict[str, Any]:
    visibility_values: dict[str, Any] = {}
    for field in fields:
        field_id = field["id"]
        raw_value = values[field_id] if field_id in values else _field_default(field)
        try:
            visibility_values[field_id] = _coerce_field_value(field, raw_value)
        except ValueError:
            visibility_values[field_id] = raw_value
        if field.get("visible_if"):
            _resolve_visible_field_id(field, configured_field_ids)
    return visibility_values


def _field_is_visible(
    field: dict[str, Any],
    visibility_values: dict[str, Any],
    configured_field_ids: set[str],
) -> bool:
    visible_if = field.get("visible_if")
    if not visible_if:
        return True

    reference_id = _resolve_visible_field_id(field, configured_field_ids)
    value = visibility_values.get(reference_id)
    operator = visible_if["operator"]
    if operator == "not_empty":
        return not _is_empty(value)
    if operator == "empty":
        return _is_empty(value)
    if operator == "equals":
        return value == visible_if.get("value")
    if operator == "not_equals":
        return value != visible_if.get("value")
    return True


def _normalize_surface_config_contract(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized.pop("version", None)
    normalized["contract"] = SURFACE_CONTRACT
    metadata = dict(normalized.get("metadata") or {})
    for key in list(metadata):
        if re.fullmatch(r"genui_v\d+(?:_compatible)?", key):
            metadata.pop(key, None)
    metadata["genui_contract"] = "genui"
    normalized["metadata"] = metadata
    return normalized


def _normalize_surface_response_contract(response: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(response)
    normalized.pop("version", None)
    normalized["contract"] = SURFACE_RESPONSE_CONTRACT
    return normalized


def validate_surface_config(config: dict[str, Any]) -> None:
    """Validate a compatibility surface config and Video Production Buddy invariants."""
    normalized = _normalize_surface_config_contract(config)
    validate_artifact("ui_surface_config", normalized)
    _reject_non_finite_json(normalized, context="ui_surface_config")
    surface_id = _surface_id(normalized)
    if normalized.get("config_id") and normalized["config_id"] != surface_id:
        raise ValueError("GenUI compatibility config_id must match surface_id when provided")
    if normalized.get("mode") == "project_cockpit" and normalized.get("actions"):
        raise ValueError("GenUI compatibility project cockpit does not accept submissions")
    block_ids: set[str] = set()
    action_ids: set[str] = set()
    for block in _iter_blocks(normalized):
        block_id = block["id"]
        if block_id in block_ids:
            raise ValueError(f"GenUI compatibility config contains duplicate block id {block_id!r}")
        block_ids.add(block_id)
        if block["type"] not in SURFACE_COMPONENTS:
            raise ValueError(f"GenUI compatibility config uses unknown block type {block['type']!r}")
    for action in normalized.get("actions") or []:
        action_id = action["id"]
        if action_id in action_ids:
            raise ValueError(f"GenUI compatibility config contains duplicate action id {action_id!r}")
        action_ids.add(action_id)
    fields = _iter_configured_fields(normalized)
    field_ids = {field["id"] for field in fields}
    if len(field_ids) != len(fields):
        raise ValueError("GenUI compatibility config contains duplicate field ids")
    for field in fields:
        if field.get("visible_if"):
            _resolve_visible_field_id(field, field_ids)


def validate_surface_response(response: dict[str, Any]) -> None:
    """Validate a compatibility surface response artifact."""
    normalized = _normalize_surface_response_contract(response)
    validate_artifact("ui_surface_response", normalized)
    _reject_non_finite_json(normalized, context="ui_surface_response")


def _refs_for_block(config: dict[str, Any], block: dict[str, Any]) -> dict[str, Any]:
    media_refs = {item["id"]: item for item in config.get("media_refs") or []}
    artifact_refs = {item["id"]: item for item in config.get("artifact_refs") or []}
    trace_refs = {item["id"]: item for item in config.get("trace_refs") or []}
    return {
        "mediaRefs": [
            media_refs[media_id]
            for media_id in block.get("media_ids") or []
            if media_id in media_refs
        ],
        "artifactRefs": [
            artifact_refs[ref_id]
            for ref_id in block.get("artifact_ref_ids") or []
            if ref_id in artifact_refs
        ],
        "traceRefs": [
            trace_refs[ref_id]
            for ref_id in block.get("trace_ref_ids") or []
            if ref_id in trace_refs
        ],
    }


def _block_props(config: dict[str, Any], block: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    block_id = block["id"]
    value_field_ids: list[str] = []
    props = {
        "blockId": block_id,
        "title": block["title"],
        "description": block.get("description"),
        "binding": block.get("binding"),
        "items": block.get("items") or [],
        "options": block.get("options") or [],
        "fields": block.get("fields") or [],
        "annotationFields": block.get("annotation_fields") or [],
        **_refs_for_block(config, block),
    }
    state_values: dict[str, Any] = {}
    if block.get("options"):
        field_id = f"{block_id}.selection"
        value_field_ids.append(field_id)
        state_values[field_id] = (
            _recommended_option_values(block["options"])
            if block.get("multiple")
            else _recommended_option_value(block["options"])
        )
        props["valueFieldId"] = field_id
        props["value"] = {"$bindState": f"/values/{field_id}"}
        props["multiple"] = bool(block.get("multiple"))
    for field in [*(block.get("fields") or []), *(block.get("annotation_fields") or [])]:
        field_id = f"{block_id}.{field['id']}"
        value_field_ids.append(field_id)
        state_values[field_id] = _field_default(field)
    if block["type"] == "ApprovalChecklist":
        for item in block.get("items") or []:
            item_id = _slug(item.get("id") or item.get("label"), fallback="approval")
            field_id = f"{block_id}.{item_id}"
            value_field_ids.append(field_id)
            state_values[field_id] = bool(item.get("approved", False))
    if value_field_ids:
        props["valueFieldIds"] = value_field_ids
    return _without_none(props), state_values


def compile_surface_view_spec(
    config: dict[str, Any],
    *,
    submit_url: str | None = None,
    submit_nonce: str | None = None,
    preview_only: bool = False,
) -> dict[str, Any]:
    """Compile a compatibility surface config into a json-render view spec."""
    config = _normalize_surface_config_contract(config)
    validate_surface_config(config)
    surface_id = _surface_id(config)
    elements: dict[str, Any] = {}
    child_ids: list[str] = []
    values: dict[str, Any] = {}

    def add_element(element_id: str, element: dict[str, Any]) -> None:
        if element_id in elements:
            raise ValueError(f"GenUI compatibility view spec element id collision: {element_id!r}")
        elements[element_id] = element

    for block in config["blocks"]:
        element_id = f"block-{block['id']}"
        props, block_values = _block_props(config, block)
        values.update(block_values)
        add_element(
            element_id,
            {
                "type": block["type"],
                "props": props,
                "children": [],
            },
        )
        child_ids.append(element_id)

    if config.get("actions"):
        action_id = "genui-actions"
        add_element(
            action_id,
            {
                "type": "ActionBar",
                "props": {
                    "actions": config["actions"],
                    "submitUrl": submit_url,
                    "previewOnly": preview_only or submit_url is None,
                },
                "children": [],
            },
        )
        child_ids.append(action_id)

    root_id = "genui-root"
    root_type = "CockpitShell" if config["mode"] == "project_cockpit" else "WorkspaceShell"
    add_element(
        root_id,
        {
            "type": root_type,
            "props": {
                "title": config["title"],
                "description": config.get("description"),
                "surfaceId": surface_id,
                "projectId": config["project_id"],
                "pipelineType": config["pipeline_type"],
                "stage": config["stage"],
                "gate": config["gate"],
                "mode": config["mode"],
                "mediaRefs": config.get("media_refs") or [],
                "artifactRefs": config.get("artifact_refs") or [],
                "traceRefs": config.get("trace_refs") or [],
            },
            "children": child_ids,
        },
    )

    spec = {
        "contract": SURFACE_VIEW_CONTRACT,
        "renderer": RENDERER_NAME,
        "root": root_id,
        "elements": elements,
        "state": {
            "values": values,
            "annotations": [],
            "selected_refs": [],
            "revision_patches": [],
            "approval_attestations": [],
            "status": {
                "message": (
                    "Preview only. Start GenUI compatibility in serve mode to submit this surface."
                    if submit_url is None
                    else ""
                )
            },
        },
        "metadata": {
            "surface_id": surface_id,
            "config_id": surface_id,
            "project_id": config["project_id"],
            "pipeline_type": config["pipeline_type"],
            "stage": config["stage"],
            "gate": config["gate"],
            "mode": config["mode"],
            "submit_url": submit_url,
            "submit_nonce": submit_nonce,
            "preview_only": preview_only or submit_url is None,
            "ag_ui": config.get("ag_ui") or {"thread_id": config["project_id"], "run_id": surface_id},
        },
    }
    validate_view_spec(spec)
    return spec


def write_surface_view_spec(
    path: Path | str,
    config: dict[str, Any],
    *,
    submit_url: str | None = None,
    submit_nonce: str | None = None,
    preview_only: bool = False,
) -> Path:
    spec = compile_surface_view_spec(
        config,
        submit_url=submit_url,
        submit_nonce=submit_nonce,
        preview_only=preview_only,
    )
    target = Path(path)
    _dump_json(target, spec)
    return target


def write_surface_bundle(project_dir: Path | str, config: dict[str, Any]) -> SurfaceBundle:
    """Validate and materialize a GenUI compatibility surface bundle."""
    config = _normalize_surface_config_contract(config)
    validate_surface_config(config)
    project_root = Path(project_dir)
    surface_id = _surface_id(config)
    base = _resolve_project_path(project_root, Path("artifacts") / SURFACE_DIRNAME / surface_id)
    config_path = base / "config.json"
    html_path = base / "form.html"
    view_spec_path = base / VIEW_SPEC_FILENAME
    response_path = base / "response.json"
    state_path = base / "server.json"

    if response_path.exists():
        response_path.unlink()
    if state_path.exists():
        state_path.unlink()

    stored_config = _normalize_surface_config_contract({**config, "config_id": surface_id})
    _dump_json(config_path, stored_config)
    write_surface_view_spec(view_spec_path, stored_config, preview_only=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w") as f:
        f.write(render_shell_html())

    return SurfaceBundle(
        config=stored_config,
        config_path=config_path,
        html_path=html_path,
        view_spec_path=view_spec_path,
        response_path=response_path,
        state_path=state_path,
    )


def _configured_values(config: dict[str, Any], submitted_values: Any, *, action: str) -> dict[str, Any]:
    if submitted_values is None:
        submitted_values = {}
    if not isinstance(submitted_values, dict):
        raise ValueError("GenUI compatibility submission values must be an object")
    fields = _iter_configured_fields(config)
    configured_field_ids = {field["id"] for field in fields}
    unconfigured = sorted(set(submitted_values) - configured_field_ids)
    if unconfigured:
        raise ValueError(f"GenUI compatibility submission contains unconfigured values: {unconfigured}")

    normalized: dict[str, Any] = {}
    visibility_values = _visibility_values(fields, submitted_values, configured_field_ids)
    for field in fields:
        if not _field_is_visible(field, visibility_values, configured_field_ids):
            continue
        raw = submitted_values.get(field["id"], _field_default(field))
        value = _coerce_field_value(field, raw)
        if action != "abort" and field.get("required") and _is_empty(value):
            raise ValueError(f"Required GenUI compatibility field {field['id']!r} is missing")
        choices = field.get("choices") or []
        if choices and not _is_empty(value):
            allowed = {_option_value(choice) for choice in choices}
            if field["type"] == "multiselect":
                invalid = [item for item in value if item not in allowed]
                if invalid:
                    raise ValueError(f"GenUI compatibility field {field['id']!r} has invalid choices: {invalid}")
            elif str(value) not in allowed:
                raise ValueError(f"GenUI compatibility field {field['id']!r} has invalid choice: {value!r}")
        if field["type"] == "number" and not _is_empty(value):
            if "min" in field and value < field["min"]:
                raise ValueError(f"GenUI compatibility field {field['id']!r} is below minimum {field['min']}")
            if "max" in field and value > field["max"]:
                raise ValueError(f"GenUI compatibility field {field['id']!r} is above maximum {field['max']}")
        normalized[field["id"]] = value
    return normalized


def _visible_configured_fields(config: dict[str, Any], submitted_values: dict[str, Any]) -> list[dict[str, Any]]:
    fields = _iter_configured_fields(config)
    configured_field_ids = {field["id"] for field in fields}
    visibility_values = _visibility_values(fields, submitted_values, configured_field_ids)
    return [
        field
        for field in fields
        if _field_is_visible(field, visibility_values, configured_field_ids)
    ]


def _has_patch_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return len(value) > 0
    return True


def _configured_selected_refs(config: dict[str, Any], fields: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    refs.update(str(item["id"]) for item in config.get("media_refs") or [])
    refs.update(str(item["id"]) for item in config.get("artifact_refs") or [])
    refs.update(str(item["id"]) for item in config.get("trace_refs") or [])
    refs.update(str(block["id"]) for block in _iter_blocks(config))
    for field in fields:
        if field.get("_kind") != "selection":
            continue
        refs.update(_option_value(choice) for choice in field.get("choices") or [])
    return refs


def _configured_annotations(fields: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(field["_block_id"]), str(field.get("_target_ref") or field["_block_id"]))
        for field in fields
        if field.get("_kind") == "annotation"
    }


def _configured_revision_values(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
) -> dict[tuple[str, str], list[Any]]:
    allowed: dict[tuple[str, str], list[Any]] = {}
    for field in fields:
        binding = field.get("_binding") or field.get("binding")
        if not isinstance(binding, dict):
            continue
        artifact = binding.get("artifact")
        path = binding.get("path")
        if not isinstance(artifact, str) or not isinstance(path, str):
            continue
        value = values.get(field["id"])
        if not _has_patch_value(value):
            continue
        allowed.setdefault((artifact, path), []).append(value)
    return allowed


def _configured_approval_attestations(
    fields: list[dict[str, Any]],
    values: dict[str, Any],
) -> dict[str, tuple[str, bool]]:
    allowed: dict[str, tuple[str, bool]] = {}
    for field in fields:
        if field.get("_kind") != "approval":
            continue
        approval_id = str(field.get("_local_id") or field["id"])
        label = str(field.get("_label") or approval_id)
        allowed[approval_id] = (label, values.get(field["id"]) is True)
    return allowed


def _validate_semantic_submission_items(
    config: dict[str, Any],
    submitted_values: dict[str, Any],
    values: dict[str, Any],
    *,
    annotations: list[Any],
    selected_refs: list[Any],
    revision_patches: list[Any],
    approval_attestations: list[Any],
) -> None:
    fields = _visible_configured_fields(config, submitted_values)

    allowed_annotations = _configured_annotations(fields)
    for item in annotations:
        if not isinstance(item, dict):
            raise ValueError("GenUI compatibility annotations must contain objects")
        key = (str(item.get("block_id") or ""), str(item.get("target_ref") or ""))
        if key not in allowed_annotations:
            raise ValueError(f"GenUI compatibility annotation is not configured for block/target {key!r}")

    allowed_selected_refs = _configured_selected_refs(config, fields)
    invalid_selected_refs = [item for item in selected_refs if not isinstance(item, str) or item not in allowed_selected_refs]
    if invalid_selected_refs:
        raise ValueError(f"GenUI compatibility selected_refs contains unconfigured refs: {invalid_selected_refs}")

    allowed_revision_values = _configured_revision_values(fields, values)
    for item in revision_patches:
        if not isinstance(item, dict):
            raise ValueError("GenUI compatibility revision_patches must contain objects")
        artifact = item.get("artifact")
        path = item.get("path")
        key = (artifact, path)
        if not isinstance(artifact, str) or not isinstance(path, str) or key not in allowed_revision_values:
            raise ValueError(f"GenUI compatibility revision patch is not configured for {key!r}")
        if not any(item.get("value") == allowed for allowed in allowed_revision_values[key]):
            raise ValueError(f"GenUI compatibility revision patch value does not match submitted field {key!r}")

    allowed_attestations = _configured_approval_attestations(fields, values)
    for item in approval_attestations:
        if not isinstance(item, dict):
            raise ValueError("GenUI compatibility approval_attestations must contain objects")
        approval_id = item.get("id")
        if not isinstance(approval_id, str) or approval_id not in allowed_attestations:
            raise ValueError(f"GenUI compatibility approval attestation is not configured for {approval_id!r}")
        label, approved = allowed_attestations[approval_id]
        if item.get("label") != label or item.get("approved") is not approved:
            raise ValueError(f"GenUI compatibility approval attestation does not match configured value for {approval_id!r}")


def _bounded_list(value: Any, *, field_name: str, max_items: int = MAX_SURFACE_LIST_ITEMS) -> list[Any]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError(f"GenUI compatibility {field_name} must be a list")
    if len(value) > max_items:
        raise ValueError(f"GenUI compatibility {field_name} has too many items")
    return value


def surface_response_payload_from_submission(
    config: dict[str, Any],
    submission: dict[str, Any],
    *,
    response_id: str | None = None,
) -> dict[str, Any]:
    """Build a ui_surface_response payload from browser-submitted state."""
    validate_surface_config(config)
    configured_actions = {action["kind"] for action in config.get("actions") or []}
    action = submission.get("action", "submit")
    if config.get("mode") == "project_cockpit":
        raise ValueError("GenUI compatibility project cockpit does not accept submissions")
    if configured_actions and action not in configured_actions:
        raise ValueError(f"Submit action {action!r} is not configured for {_surface_id(config)}")

    submitted_values = submission.get("values")
    values = _configured_values(config, submitted_values, action=action)
    if submitted_values is None:
        submitted_values = {}
    if not isinstance(submitted_values, dict):
        raise ValueError("GenUI compatibility submission values must be an object")
    browser_events = _bounded_list(submission.get("browser_events"), field_name="browser_events", max_items=50)
    annotations = _bounded_list(submission.get("annotations"), field_name="annotations")
    selected_refs = _bounded_list(submission.get("selected_refs"), field_name="selected_refs")
    revision_patches = _bounded_list(submission.get("revision_patches"), field_name="revision_patches", max_items=200)
    approval_attestations = _bounded_list(
        submission.get("approval_attestations"),
        field_name="approval_attestations",
        max_items=200,
    )
    _reject_non_finite_json(
        {
            "annotations": annotations,
            "selected_refs": selected_refs,
            "revision_patches": revision_patches,
            "approval_attestations": approval_attestations,
            "browser_events": browser_events,
        },
        context="ui_surface_submission",
    )
    _validate_semantic_submission_items(
        config,
        submitted_values,
        values,
        annotations=annotations,
        selected_refs=selected_refs,
        revision_patches=revision_patches,
        approval_attestations=approval_attestations,
    )
    last_event_type = None
    if browser_events and isinstance(browser_events[-1], dict):
        last_event_type = browser_events[-1].get("type")
    surface_id = _surface_id(config)
    response = {
        "contract": SURFACE_RESPONSE_CONTRACT,
        "response_id": response_id or f"resp-{surface_id}-{int(datetime.now(timezone.utc).timestamp())}",
        "surface_id": surface_id,
        "config_id": surface_id,
        "project_id": config["project_id"],
        "pipeline_type": config["pipeline_type"],
        "stage": config["stage"],
        "gate": config["gate"],
        "submitted_at": _now_iso(),
        "action": action,
        "values": values,
        "annotations": annotations,
        "selected_refs": selected_refs,
        "revision_patches": revision_patches,
        "approval_attestations": approval_attestations,
        "event_summary": _without_none(
            {
                "event_count": len(browser_events),
                "last_event_type": last_event_type,
            }
        ),
        "browser_events": browser_events,
        "validation": {"status": "pending", "errors": []},
    }
    validate_surface_response(response)
    return response


def write_surface_response(response_path: Path | str, response: dict[str, Any]) -> Path:
    response = _normalize_surface_response_contract(response)
    validate_surface_response(response)
    path = Path(response_path)
    _dump_json(path, response)
    return path


def _default_actions() -> list[dict[str, Any]]:
    return [
        {"id": "approve", "label": "Approve", "kind": "approve", "recommended": True},
        {"id": "revise", "label": "Request revisions", "kind": "revise"},
        {"id": "abort", "label": "Abort", "kind": "abort"},
    ]


def _options_from_choices(choices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        _without_none(
            {
                "id": _option_value(choice, fallback=idx),
                "value": _option_value(choice, fallback=idx),
                "label": choice.get("label") or _option_value(choice, fallback=idx),
                "summary": choice.get("description") or choice.get("summary"),
                "description": choice.get("description"),
                "tradeoff": choice.get("tradeoff"),
                "recommended": choice.get("recommended"),
                "preview": choice.get("preview"),
            }
        )
        for idx, choice in enumerate(choices)
    ]


def build_dynamic_surface_config(
    request: dict[str, Any],
    *,
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compatibility gate workspace from an interaction request."""
    from lib.genui.dynamic import validate_interaction_request
    from lib.genui.interaction_policy import assess_interaction_need

    validate_interaction_request(request)
    decision = decision or assess_interaction_need(request)
    surface_id = _slug(request.get("config_id") or request.get("request_id"), fallback="genui-surface")
    media_refs = [
        _without_none(
            {
                "id": _slug(item.get("id") or item.get("title"), fallback="media"),
                "kind": item.get("kind", "path"),
                "title": item.get("title") or item.get("id") or "Media",
                "path": item.get("path"),
                "text": item.get("text"),
                "alt": item.get("alt") or item.get("title"),
            }
        )
        for item in request.get("media_items") or []
        if item.get("path") or item.get("kind") == "text"
    ]
    artifact_refs = []
    for field in request.get("fields") or []:
        binding = field.get("binding")
        if binding:
            artifact_refs.append(
                {
                    "id": _slug(f"{field['id']}-binding", fallback="artifact"),
                    "artifact": binding["artifact"],
                    "path": binding["path"],
                    "label": field.get("label", field["id"]),
                }
            )
    trace_refs = [
        {
            "id": "agent-review-boundary",
            "label": "Agent review boundary",
            "source": "AGENT_GUIDE.md",
            "summary": "GenUI collects choices only; the agent validates the response before canonical writes.",
        }
    ]
    blocks: list[dict[str, Any]] = [
        {
            "id": "context",
            "type": "BriefWorksheet",
            "title": request["title"],
            "description": request.get("prompt"),
            "items": [{"label": "Interaction kind", "value": request.get("interaction_kind")}],
        }
    ]
    if media_refs:
        blocks.append(
            {
                "id": "media",
                "type": "MediaCompare",
                "title": request.get("review_title") or "Media review",
                "media_ids": [item["id"] for item in media_refs],
                "annotation_fields": [
                    {"id": "notes", "label": "Review notes", "type": "textarea"},
                    {"id": "approved", "label": "Media approved", "type": "approval"},
                ],
            }
        )
    choices = _options_from_choices(request.get("choices") or [])
    review_items = request.get("review_items") or []
    if choices or review_items:
        blocks.append(
            _without_none({
                "id": "comparison",
                "type": "ConceptComparison",
                "title": request.get("selection_label") or "Option comparison",
                "description": request.get("description"),
                "options": choices,
                "multiple": bool(request.get("allow_multiple")),
                "items": review_items,
                "binding": request.get("selection_binding"),
            })
        )
    fields = request.get("fields") or []
    if fields:
        blocks.append(
            {
                "id": "revisions",
                "type": "RevisionPatch",
                "title": "Structured revisions",
                "fields": fields,
                "artifact_ref_ids": [ref["id"] for ref in artifact_refs],
            }
        )
    blocks.append(
        {
            "id": "approval",
            "type": "ApprovalChecklist",
            "title": "Approval contract",
            "items": [
                {
                    "id": "reviewed",
                    "label": "I reviewed the visible evidence and choices in this workspace.",
                    "required": True,
                }
            ],
        }
    )
    blocks.append(
        {
            "id": "trace",
            "type": "ArtifactTracePanel",
            "title": "Traceability",
            "artifact_ref_ids": [ref["id"] for ref in artifact_refs],
            "trace_ref_ids": [ref["id"] for ref in trace_refs],
        }
    )
    config = _without_none(
        {
            "contract": SURFACE_CONTRACT,
            "surface_id": surface_id,
            "config_id": surface_id,
            "project_id": str(request["project_id"]),
            "pipeline_type": str(request["pipeline_type"]),
            "stage": str(request["stage"]),
            "gate": str(request["gate"]),
            "mode": "gate_workspace",
            "title": str(request["title"]),
            "description": request.get("description"),
            "ag_ui": {
                "thread_id": str(request["project_id"]),
                "run_id": surface_id,
            },
            "media_refs": media_refs,
            "artifact_refs": artifact_refs,
            "trace_refs": trace_refs,
            "blocks": blocks,
            "actions": request.get("submit_actions") or _default_actions(),
            "metadata": {
                "genui_contract": "genui",
                "dynamic_interaction": True,
                "interaction_kind": decision.get("interaction_kind"),
                "linear_chat_insufficient": decision.get("linear_chat_sufficient") is False,
                "decision_reasons": decision.get("reasons", []),
                "source_request_id": request.get("request_id"),
                "protocol": "ag-ui",
            },
        }
    )
    validate_surface_config(config)
    return config


def build_ag_ui_events(config: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a small AG-UI-compatible event snapshot for the local surface."""
    validate_surface_config(config)
    try:
        from ag_ui.core import EventType
    except Exception:
        EventType = None  # type: ignore[assignment]

    def event_type(name: str) -> str:
        if EventType is None:
            return name
        value = getattr(EventType, name)
        return str(getattr(value, "value", value))

    surface_id = _surface_id(config)
    ag_ui = config.get("ag_ui") or {"thread_id": config["project_id"], "run_id": surface_id}
    common = {
        "threadId": ag_ui["thread_id"],
        "runId": ag_ui["run_id"],
    }
    return [
        {"type": event_type("RUN_STARTED"), **common},
        {"type": event_type("STATE_SNAPSHOT"), **common, "snapshot": state},
        {
            "type": event_type("ACTIVITY_SNAPSHOT"),
            **common,
            "activity": {
                "surfaceId": surface_id,
                "mode": config["mode"],
                "blocks": [block["id"] for block in config.get("blocks") or []],
            },
        },
        {"type": event_type("RUN_FINISHED"), **common},
    ]
