"""Small safety helpers for tool status and metadata reads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tools.base_tool import ToolStatus, _coerce_tool_status, _json_safe


def safe_tool_attr(tool: object, attr: str, default: Any = None) -> Any:
    """Read a tool attribute without letting malformed metadata break callers."""
    try:
        return getattr(tool, attr)
    except Exception:
        return default


def safe_tool_status(tool: object) -> ToolStatus:
    """Return a ToolStatus, treating status backend failures as degraded."""
    try:
        raw_status = tool.get_status()  # type: ignore[attr-defined]
    except Exception:
        return ToolStatus.DEGRADED

    return _coerce_tool_status(raw_status)


def is_tool_available(tool: object) -> bool:
    """Whether a tool is available without raising on broken status hooks."""
    return safe_tool_status(tool) == ToolStatus.AVAILABLE


def safe_tool_provider(tool: object, default: str = "unknown") -> str:
    """Return a provider label without letting provider metadata raise."""
    return str(safe_tool_attr(tool, "provider", default) or default)


def safe_tool_name(tool: object) -> str:
    """Return a stable display name for a tool-like object."""
    fallback = tool.__class__.__name__
    return str(safe_tool_attr(tool, "name", fallback) or fallback)


def _safe_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return []
    try:
        return list(value)
    except Exception:
        return []


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


_LIST_INFO_FIELDS = (
    "dependencies",
    "capabilities",
    "best_for",
    "not_good_for",
    "idempotency_key_fields",
    "side_effects",
    "fallback_tools",
    "agent_skills",
    "related_skills",
    "user_visible_verification",
)

_DICT_INFO_FIELDS = (
    "input_schema",
    "output_schema",
    "artifact_schema",
    "supports",
    "provider_matrix",
)


def _normalize_info_shape(info: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(info)
    for field in _LIST_INFO_FIELDS:
        if field in normalized:
            normalized[field] = _safe_list(normalized[field])
    for field in _DICT_INFO_FIELDS:
        if field in normalized:
            normalized[field] = _safe_dict(normalized[field])
    if "progress_schema" in normalized and normalized["progress_schema"] is not None:
        normalized["progress_schema"] = _safe_dict(normalized["progress_schema"])
    return normalized


def _value_or_enum_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    return getattr(value, "value", value)


def _default_info(tool: object) -> dict[str, Any]:
    return {
        "name": safe_tool_name(tool),
        "provider": safe_tool_provider(tool),
        "capability": safe_tool_attr(tool, "capability", "generic"),
        "stability": _value_or_enum_value(
            safe_tool_attr(tool, "stability", "experimental"),
            "experimental",
        ),
        "tier": _value_or_enum_value(safe_tool_attr(tool, "tier", ""), ""),
        "runtime": _value_or_enum_value(
            safe_tool_attr(tool, "runtime", "unknown"),
            "unknown",
        ),
        "best_for": _safe_list(safe_tool_attr(tool, "best_for", [])),
        "supports": _safe_dict(safe_tool_attr(tool, "supports", {})),
        "agent_skills": _safe_list(safe_tool_attr(tool, "agent_skills", [])),
        "usage_location": None,
    }


def safe_tool_info(tool: object) -> dict[str, Any]:
    """Return JSON-safe tool info, falling back to direct safe metadata reads."""
    try:
        info = tool.get_info()  # type: ignore[attr-defined]
        if isinstance(info, dict):
            defaults = _default_info(tool)
            defaults.update(info)
            return _json_safe(_normalize_info_shape(defaults))
    except Exception:
        pass

    return _json_safe(_normalize_info_shape(_default_info(tool)))
