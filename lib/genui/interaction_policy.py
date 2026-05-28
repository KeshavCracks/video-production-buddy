"""Dynamic GenUI routing policy.

The agent uses this module before substantive human interactions to decide
whether linear chat is enough or a browser GenUI round is warranted.
"""

from __future__ import annotations

from typing import Any


VISUAL_CAPABILITIES = {
    "visual_demonstration",
    "media_review",
    "side_by_side_comparison",
}
MULTI_AXIS_CAPABILITIES = {
    "multi_axis_selection",
    "matrix_review",
    "ranked_selection",
}
STRUCTURED_CAPABILITIES = {
    "structured_revision_capture",
    "multi_field_editing",
}
STATUS_CAPABILITIES = {
    "status_timeline",
    "artifact_trace",
    "budget_panel",
}
STAGE_POLICIES = {
    "ad-video.proposal_lock": {
        "mode": "gate_workspace",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "proposal_lock", "structured_revision_capture"],
        "required_ui_primitives": [
            "structured_fields",
            "approval_attestation",
            "artifact_trace",
            "durable_decision",
            "review_completion",
        ],
    },
    "ad-video.runtime_selection": {
        "mode": "gate_workspace",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "runtime_selection", "side_by_side_comparison"],
        "required_ui_primitives": [
            "side_by_side_comparison",
            "structured_fields",
            "approval_attestation",
            "artifact_trace",
            "durable_decision",
        ],
    },
    "ad-video.product_reference": {
        "mode": "media_review_room",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "product_reference", "media_review"],
        "required_ui_primitives": [
            "media_player",
            "keyframe_strip",
            "side_by_side_comparison",
            "approval_attestation",
            "artifact_trace",
        ],
    },
    "ad-video.sample_review": {
        "mode": "media_review_room",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "sample_review", "media_review", "structured_revision_capture"],
        "required_ui_primitives": [
            "media_player",
            "scene_rail",
            "timecoded_annotation",
            "frame_region_annotation",
            "issue_tracker",
            "review_completion",
        ],
    },
    "ad-video.asset_review": {
        "mode": "media_review_room",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "asset_review", "media_review"],
        "required_ui_primitives": [
            "media_player",
            "scene_rail",
            "side_by_side_comparison",
            "timecoded_annotation",
            "issue_tracker",
        ],
    },
    "ad-video.music_review": {
        "mode": "media_review_room",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "music_review", "media_review"],
        "required_ui_primitives": ["audio_player", "timecoded_annotation", "issue_tracker", "review_completion"],
    },
    "ad-video.publish_review": {
        "mode": "media_review_room",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "publish_review", "media_review"],
        "required_ui_primitives": [
            "media_player",
            "status_timeline",
            "approval_attestation",
            "issue_tracker",
            "review_completion",
        ],
    },
    "ad-video.background_status": {
        "mode": "background_status",
        "schema_strategy": "fixed",
        "reasons": ["stage_policy_required", "background_status"],
        "required_ui_primitives": ["status_timeline", "operation_timeline", "tool_operation_card"],
    },
}


def _count_items(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _capabilities(request: dict[str, Any]) -> set[str]:
    raw = request.get("capabilities_needed") or []
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw}


def _policy_key(request: dict[str, Any]) -> str | None:
    pipeline_type = str(request.get("pipeline_type") or "")
    aliases = {
        "sample": "sample_review",
        "final_review": "publish_review",
    }
    routed_tokens = [
        str(request.get("gate") or ""),
        str(request.get("interaction_kind") or ""),
    ]
    for raw_token in routed_tokens:
        if not raw_token:
            continue
        token = raw_token.lower().replace("-", "_")
        candidate = aliases.get(token, token)
        key = f"{pipeline_type}.{candidate}"
        if key in STAGE_POLICIES:
            return key
    stage = str(request.get("stage") or "").lower().replace("-", "_")
    if stage:
        key = f"{pipeline_type}.{stage}"
        if key in STAGE_POLICIES:
            return key
    return None


def assess_interaction_need(request: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic CLI-vs-GenUI recommendation for one interaction.

    The result is advisory: the agent still communicates the decision and owns
    canonical artifact updates after any submitted `ui_session_response`.
    """
    capabilities = _capabilities(request)
    if request.get("user_declined_browser"):
        return {
            "recommended_mode": "cli",
            "recommended_tool": None,
            "linear_chat_sufficient": True,
            "interaction_kind": request.get("interaction_kind") or "clarification",
            "reasons": ["user_declined_browser"],
            "confidence": 0.95,
            "cli_fallback_allowed": True,
        }
    if request.get("browser_available") is False and not request.get("force_genui"):
        return {
            "recommended_mode": "cli",
            "recommended_tool": None,
            "linear_chat_sufficient": True,
            "interaction_kind": request.get("interaction_kind") or "clarification",
            "reasons": ["browser_unavailable"],
            "confidence": 0.9,
            "cli_fallback_allowed": True,
        }
    if request.get("previous_genui_failed") and not request.get("force_genui"):
        return {
            "recommended_mode": "cli",
            "recommended_tool": None,
            "linear_chat_sufficient": True,
            "interaction_kind": request.get("interaction_kind") or "clarification",
            "reasons": ["previous_genui_failed"],
            "confidence": 0.85,
            "cli_fallback_allowed": True,
        }
    policy_id = _policy_key(request)
    policy = STAGE_POLICIES.get(policy_id or "")
    reasons: list[str] = []
    interaction_kind = request.get("interaction_kind")

    if policy:
        reasons.extend(policy["reasons"])
    if request.get("force_genui"):
        reasons.append("explicit_genui_request")
    if interaction_kind == "media_review":
        reasons.append("media_review")
    if interaction_kind == "option_comparison":
        reasons.append("side_by_side_comparison")
    if interaction_kind == "multi_axis_selection":
        reasons.append("multi_axis_selection")
    if interaction_kind == "structured_revision":
        reasons.append("structured_revision_capture")
    if interaction_kind == "project_cockpit":
        reasons.append("project_state_overview")
    if interaction_kind == "background_status":
        reasons.append("background_status")
    if interaction_kind == "dynamic_genui":
        reasons.append("dynamic_genui")
    if request.get("requires_visual_demonstration") or capabilities & VISUAL_CAPABILITIES:
        reasons.append("visual_demonstration")
    if request.get("requires_multi_axis_selection") or capabilities & MULTI_AXIS_CAPABILITIES:
        reasons.append("multi_axis_selection")
    if request.get("requires_structured_revision_capture") or capabilities & STRUCTURED_CAPABILITIES:
        reasons.append("structured_revision_capture")
    if capabilities & STATUS_CAPABILITIES:
        reasons.append("project_state_overview")
    if _count_items(request.get("media_items")) > 0:
        reasons.append("media_review")
    if _count_items(request.get("review_items")) >= 2:
        reasons.append("side_by_side_comparison")
    if _count_items(request.get("choices")) >= 3:
        reasons.append("many_options")
    if _count_items(request.get("fields")) >= 3:
        reasons.append("many_structured_fields")

    # Preserve order while removing duplicates from overlapping triggers.
    deduped_reasons = list(dict.fromkeys(reasons))
    use_genui = bool(deduped_reasons)

    recommended_mode = "cli"
    if policy:
        recommended_mode = str(policy["mode"])
    elif use_genui:
        if interaction_kind == "project_cockpit" or request.get("surface_mode") == "project_cockpit":
            recommended_mode = "project_cockpit"
        elif interaction_kind == "background_status" or request.get("surface_mode") == "background_status":
            recommended_mode = "background_status"
        elif "media_review" in deduped_reasons:
            recommended_mode = "media_review_room"
        else:
            recommended_mode = "gate_workspace"

    required_primitives = list(policy["required_ui_primitives"]) if policy else []
    result = {
        "recommended_mode": recommended_mode,
        "recommended_tool": "genui_interaction" if use_genui else None,
        "linear_chat_sufficient": not use_genui,
        "interaction_kind": request.get("interaction_kind") or ("dynamic_genui" if use_genui else "clarification"),
        "reasons": deduped_reasons,
        "confidence": 0.95 if policy else 0.9 if use_genui else 0.75,
        "cli_fallback_allowed": True,
    }
    if policy_id:
        result["stage_policy_id"] = policy_id
    if policy:
        result["schema_strategy"] = str(policy["schema_strategy"])
        result["required_ui_primitives"] = required_primitives
    return result
