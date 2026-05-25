"""Scene fidelity validator.

Reads scene_type_registry.json and validates that every scene/cut:
  - uses a scene_type that exists in the registry (closed enum check)
  - uses a Remotion component the registry knows about
  - lists only motion_specs that the chosen component actually supports
  - includes any registry-required props, including cut-only props that are
    resolved after the asset stage (for example approved productImage paths)
  - includes props required by a declared motion primitive when the registry
    marks that primitive as prop-dependent

Used by:
  - asset-director-animated.md before any asset is generated
  - compose-director.md as Check 7 (pre-render)

Run from CLI for ad-hoc validation:
    python -m tools.validation.scene_fidelity_check \
        projects/<name>/artifacts/scene_plan.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REGISTRY_PATH_DEFAULT = (
    Path(__file__).resolve().parent.parent.parent
    / "remotion-composer"
    / "scene_type_registry.json"
)

VIDEO_CUT_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
MEDIA_CUT_EXTENSIONS = VIDEO_CUT_EXTENSIONS | {".png", ".jpg", ".jpeg", ".webp"}


def load_registry(registry_path: Path | None = None) -> dict[str, Any]:
    path = registry_path or REGISTRY_PATH_DEFAULT
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _scene_iter(plan: dict[str, Any]):
    """Yield (idx, scene_dict, kind) for either scene_plan.scenes[] or edit_decisions.cuts[]."""
    if "scenes" in plan:
        for idx, scene in enumerate(plan.get("scenes", [])):
            yield idx, scene, "scene"
    elif "cuts" in plan:
        for idx, cut in enumerate(plan.get("cuts", [])):
            yield idx, cut, "cut"


def _scene_type(scene: dict[str, Any]) -> str | None:
    return scene.get("scene_type") or scene.get("type")


def _has_prop_value(scene: dict[str, Any], prop: str) -> bool:
    value = scene.get(prop)
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return value != ""


def _is_plain_media_cut(scene: dict[str, Any], kind: str) -> bool:
    if kind != "cut" or _scene_type(scene):
        return False
    source = scene.get("source")
    if not isinstance(source, str) or not source:
        return False
    return Path(source).suffix.lower() in MEDIA_CUT_EXTENSIONS


def _check_overlapping_source_reuse(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag repeated use of the same source-video time range.

    Reusing one generated video as multiple non-overlapping trims is valid.
    Reusing overlapping source windows makes the final render visibly repeat
    footage even when the timeline itself has no gaps.
    """
    cuts = plan.get("cuts")
    if not isinstance(cuts, list):
        return []

    render_runtime = str(plan.get("render_runtime", "")).lower()
    default_source_start = 0.0 if render_runtime == "remotion" else None
    ranges_by_source: dict[str, list[tuple[float, float, str]]] = {}
    issues: list[dict[str, Any]] = []
    tolerance = 0.05

    for idx, cut in enumerate(cuts):
        if not isinstance(cut, dict):
            continue
        source = cut.get("source")
        if not isinstance(source, str) or not source:
            continue
        if source.startswith("remotion:"):
            continue
        if Path(source).suffix.lower() not in VIDEO_CUT_EXTENSIONS:
            continue

        try:
            timeline_start = float(cut["in_seconds"])
            timeline_end = float(cut["out_seconds"])
        except (KeyError, TypeError, ValueError):
            continue

        duration = timeline_end - timeline_start
        if duration <= 0:
            continue

        if "source_in_seconds" in cut:
            try:
                source_start = float(cut["source_in_seconds"])
            except (TypeError, ValueError):
                continue
        else:
            source_start = default_source_start if default_source_start is not None else timeline_start
        source_end = source_start + duration
        cut_id = str(cut.get("id", f"cut-{idx}"))

        for prev_start, prev_end, prev_id in ranges_by_source.get(source, []):
            overlap_start = max(source_start, prev_start)
            overlap_end = min(source_end, prev_end)
            if overlap_end - overlap_start > tolerance:
                issues.append(
                    {
                        "severity": "critical",
                        "scene_id": cut_id,
                        "kind": "overlapping_source_reuse",
                        "source": source,
                        "overlaps_with": prev_id,
                        "source_range_seconds": [
                            round(source_start, 3),
                            round(source_end, 3),
                        ],
                        "overlap_range_seconds": [
                            round(overlap_start, 3),
                            round(overlap_end, 3),
                        ],
                        "detail": (
                            f"Cut {cut_id!r} reuses source range "
                            f"{source_start:.2f}-{source_end:.2f}s from {source!r}, "
                            f"overlapping cut {prev_id!r}. This creates repeated "
                            "visible footage; use a non-overlapping source range, "
                            "a single longer cut, or another asset."
                        ),
                    }
                )
                break

        ranges_by_source.setdefault(source, []).append((source_start, source_end, cut_id))

    return issues


def check_plan(plan: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    """Validate a scene_plan or edit_decisions dict against the registry."""
    types = registry.get("scene_types", {})
    issues: list[dict[str, Any]] = []
    failing_ids: set[str] = set()
    checked = 0

    for idx, scene, kind in _scene_iter(plan):
        checked += 1
        scene_id = scene.get("id", f"{kind}-{idx}")
        st = _scene_type(scene)

        if not st:
            if _is_plain_media_cut(scene, kind):
                continue
            issues.append(
                {
                    "severity": "critical",
                    "scene_id": scene_id,
                    "kind": "missing_scene_type",
                    "detail": "scene/cut has no `scene_type` or `type` field",
                }
            )
            failing_ids.add(scene_id)
            continue

        type_def = types.get(st)
        if type_def is None:
            issues.append(
                {
                    "severity": "critical",
                    "scene_id": scene_id,
                    "kind": "unknown_scene_type",
                    "detail": (
                        f"scene_type {st!r} is not in the registry. "
                        f"Valid types: {sorted(types.keys())}. "
                        "Either pick a registered type, or request a new component before continuing."
                    ),
                }
            )
            failing_ids.add(scene_id)
            continue

        requested = scene.get("motion_specs") or []
        supported = set(type_def.get("motion_primitives", []))
        unsupported = [m for m in requested if m not in supported]
        if unsupported:
            issues.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "kind": "unsupported_motion_spec",
                    "detail": (
                        f"scene_type {st!r} (component {type_def.get('component')!r}) does not support "
                        f"motion primitives: {unsupported}. Supported: {sorted(supported)}. "
                        "Either pick another scene_type or request a new component."
                    ),
                }
            )
            failing_ids.add(scene_id)

        required = list(type_def.get("required_props", []) or [])
        if kind == "cut":
            required.extend(type_def.get("required_cut_props", []) or [])
        missing = [p for p in required if not _has_prop_value(scene, p)]
        if missing:
            issues.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "kind": "missing_required_props",
                    "detail": (
                        f"scene_type {st!r} requires props {missing} but none were provided."
                    ),
                }
            )
            failing_ids.add(scene_id)

        motion_required_props = dict(type_def.get("motion_required_props", {}) or {})
        if kind == "cut":
            motion_required_props.update(
                type_def.get("motion_required_cut_props", {}) or {}
            )
        for primitive in requested:
            requirement = motion_required_props.get(primitive)
            if not isinstance(requirement, dict):
                continue

            all_of = requirement.get("all_of", []) or []
            missing_all = [p for p in all_of if not _has_prop_value(scene, p)]
            any_of = requirement.get("any_of", []) or []
            missing_any = bool(any_of) and not any(
                _has_prop_value(scene, p) for p in any_of
            )
            if not missing_all and not missing_any:
                continue

            issues.append(
                {
                    "severity": "major",
                    "scene_id": scene_id,
                    "kind": "missing_motion_required_props",
                    "motion_spec": primitive,
                    "required_props": missing_all,
                    "required_any_props": any_of if missing_any else [],
                    "detail": (
                        f"scene_type {st!r} declares motion primitive {primitive!r}, "
                        "but the props required to render that motion were not provided."
                    ),
                }
            )
            failing_ids.add(scene_id)

    for issue in _check_overlapping_source_reuse(plan):
        issues.append(issue)
        failing_ids.add(str(issue.get("scene_id", "unknown")))

    return {
        "ok": len(failing_ids) == 0,
        "issues": issues,
        "summary": {
            "scenes_checked": checked,
            "scenes_failing": len(failing_ids),
        },
    }


def check_kvm_coverage(
    bible: dict[str, Any], scene_plan: dict[str, Any]
) -> dict[str, Any]:
    """Verify mandatory KVM coverage and required motion primitive fulfillment."""
    visual = bible.get("visual") or {}
    kvms = (
        visual.get("key_visual_moments")
        or bible.get("kvms")
        or bible.get("key_visual_moments")
        or []
    )
    if not kvms:
        return {"ok": True, "issues": [], "summary": {"kvms_checked": 0}}

    kvm_by_id = {
        kvm_id: kvm
        for kvm in kvms
        if (kvm_id := (kvm.get("moment_id") or kvm.get("kvm_id") or kvm.get("id")))
    }
    coverage: dict[str, list[str]] = {}
    issues = []
    motion_primitive_gaps = 0
    for scene in scene_plan.get("scenes", []) or scene_plan.get("cuts", []):
        scene_id = scene.get("id", "?")
        scene_motion_specs = set(scene.get("motion_specs", []) or [])
        for kvm_id in scene.get("fulfills_kvm", []) or []:
            coverage.setdefault(kvm_id, []).append(scene_id)
            kvm = kvm_by_id.get(kvm_id)
            if not kvm:
                continue

            required_motion_primitives = [
                primitive
                for primitive in (kvm.get("required_motion_primitives") or [])
                if primitive
            ]
            missing_motion_primitives = [
                primitive
                for primitive in required_motion_primitives
                if primitive not in scene_motion_specs
            ]
            if missing_motion_primitives:
                motion_primitive_gaps += 1
                issues.append(
                    {
                        "severity": "critical",
                        "scene_id": scene_id,
                        "kvm_id": kvm_id,
                        "kind": "missing_required_motion_primitives",
                        "required_motion_primitives": required_motion_primitives,
                        "missing_motion_primitives": missing_motion_primitives,
                        "detail": (
                            f"Scene {scene_id!r} fulfills KVM {kvm_id!r} but omits "
                            f"required motion primitives {missing_motion_primitives} "
                            "from `motion_specs`."
                        ),
                    }
                )

    uncovered = 0
    for kvm in kvms:
        kvm_id = kvm.get("moment_id") or kvm.get("kvm_id") or kvm.get("id")
        mandatory = kvm.get("mandatory", True)
        if mandatory and kvm_id not in coverage:
            uncovered += 1
            issues.append(
                {
                    "severity": "critical",
                    "kvm_id": kvm_id,
                    "kind": "uncovered_kvm",
                    "detail": (
                        f"Mandatory KVM {kvm_id!r} ({kvm.get('description', '')[:80]!r}) "
                        "is not fulfilled by any scene. Add `fulfills_kvm: ["
                        f'"{kvm_id}"]` to the relevant scene.'
                    ),
                }
            )

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "summary": {
            "kvms_checked": len(kvms),
            "kvms_uncovered": uncovered,
            "kvm_motion_primitive_gaps": motion_primitive_gaps,
            "coverage": coverage,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: scene_fidelity_check.py <scene_plan.json> [<production_bible.json>]")
        return 2

    plan_path = Path(argv[1])
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)

    registry = load_registry()
    report = check_plan(plan, registry)

    if len(argv) >= 3:
        with open(argv[2], encoding="utf-8") as f:
            bible = json.load(f)
        kvm_report = check_kvm_coverage(bible, plan)
        report["kvm_coverage"] = kvm_report
        report["ok"] = report["ok"] and kvm_report["ok"]

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
