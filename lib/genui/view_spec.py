"""Validate GenUI renderer view specs.

The view spec is renderer-only state. It is not a canonical Video Production Buddy
artifact and it must never encode executable canonical artifact writes.
"""

from __future__ import annotations

from typing import Any


VIEW_SPEC_FILENAME = "view_spec.json"
RENDERER_NAME = "json-render"
A2UI_RENDERER_NAME = "a2ui"
SURFACE_VIEW_CONTRACT = "genui_surface_view"
SESSION_VIEW_CONTRACT = "genui_session_view"


CATALOG_COMPONENTS = {
    "WorkspaceShell",
    "CockpitShell",
    "Section",
    "InfoCard",
    "TextInputField",
    "TextAreaField",
    "SelectField",
    "ChoiceGroupField",
    "CheckboxField",
    "NumberField",
    "UrlField",
    "FilePathField",
    "ApprovalField",
    "MediaPreviewCard",
    "ReviewGrid",
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
    "ActionBar",
}


def validate_view_spec(spec: dict[str, Any]) -> None:
    """Validate the minimal invariants needed before handing the spec to JS."""
    renderer = spec.get("renderer")
    if renderer == A2UI_RENDERER_NAME:
        _validate_a2ui_view_spec(spec)
        return
    if renderer != RENDERER_NAME:
        raise ValueError("GenUI view spec renderer must be json-render or a2ui")
    if spec.get("contract") != SURFACE_VIEW_CONTRACT and spec.get("version") != "2.0":
        raise ValueError("GenUI json-render view spec contract is invalid")
    root = spec.get("root")
    elements = spec.get("elements")
    if not isinstance(root, str) or not isinstance(elements, dict) or root not in elements:
        raise ValueError("GenUI view spec must contain a valid root element")
    for element_id, element in elements.items():
        if not isinstance(element, dict):
            raise ValueError(f"GenUI element {element_id!r} must be an object")
        element_type = element.get("type")
        if not isinstance(element_type, str):
            raise ValueError(f"GenUI element {element_id!r} must declare a type")
        if element_type not in CATALOG_COMPONENTS:
            raise ValueError(f"GenUI element {element_id!r} uses unknown json-render component {element_type!r}")
        if "props" not in element or not isinstance(element["props"], dict):
            raise ValueError(f"GenUI element {element_id!r} must declare object props")
        children = element.get("children", [])
        if children is not None and not isinstance(children, list):
            raise ValueError(f"GenUI element {element_id!r} children must be a list")


def _validate_a2ui_view_spec(spec: dict[str, Any]) -> None:
    if spec.get("contract") != SESSION_VIEW_CONTRACT and spec.get("version") != "3.0":
        raise ValueError("GenUI A2UI view spec contract is invalid")
    root = spec.get("root")
    a2ui = spec.get("a2ui")
    if not isinstance(root, str) or not isinstance(a2ui, dict):
        raise ValueError("GenUI A2UI view spec must contain root and a2ui objects")
    components = a2ui.get("components")
    operations = a2ui.get("operations")
    if not isinstance(components, list) or not isinstance(operations, list):
        raise ValueError("GenUI A2UI view spec must contain component and operation lists")
    component_ids: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            raise ValueError("GenUI A2UI components must be objects")
        component_id = component.get("id")
        component_type = component.get("type")
        if not isinstance(component_id, str) or not component_id:
            raise ValueError("GenUI A2UI components must declare string ids")
        if component_id in component_ids:
            raise ValueError(f"GenUI A2UI component id collision: {component_id!r}")
        component_ids.add(component_id)
        if not isinstance(component_type, str) or not component_type:
            raise ValueError(f"GenUI A2UI component {component_id!r} must declare a type")
        if "props" not in component or not isinstance(component["props"], dict):
            raise ValueError(f"GenUI A2UI component {component_id!r} must declare object props")
        children = component.get("children", [])
        if children is not None and not isinstance(children, list):
            raise ValueError(f"GenUI A2UI component {component_id!r} children must be a list")
    if root not in component_ids:
        raise ValueError("GenUI A2UI view spec root must reference a component id")
    operation_types = [operation.get("type") for operation in operations if isinstance(operation, dict)]
    if operation_types[:3] != ["surfaceUpdate", "dataModelUpdate", "beginRendering"]:
        raise ValueError("GenUI A2UI view spec must start with surfaceUpdate, dataModelUpdate, beginRendering")


def render_shell_html() -> str:
    """Return the static shell used by the json-render frontend bundle."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Video Production Buddy GenUI</title>
  <link rel="stylesheet" href="/assets/index.css">
</head>
<body>
  <noscript>Video Production Buddy GenUI requires JavaScript to render the browser interface.</noscript>
  <div id="root">Loading Video Production Buddy GenUI interface...</div>
  <script type="module" src="/assets/index.js"></script>
</body>
</html>
"""
