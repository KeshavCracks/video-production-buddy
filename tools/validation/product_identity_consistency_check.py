"""Product identity reference consistency validator.

This deterministic check runs before product-visible generated video clips are
accepted into the ad-video asset manifest. It verifies that every scene declared
as product-visible has either:

* an approved product_identity_reference used by generated visual assets, or
* an explicit user-approved risk waiver with text_only_waived conditioning.

CLI usage:
    python -m tools.validation.product_identity_consistency_check projects/<name>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


VISUAL_ASSET_TYPES = {"image", "video", "animation"}
REFERENCE_SOURCE_TYPES = {"user_provided", "generated", "external_url"}
PRODUCT_VISIBLE_VALUES = {"background", "partial", "hero", "detail", "packshot"}


def _load_artifact(project_dir: Path, name: str) -> dict[str, Any]:
    path = project_dir / "artifacts" / name
    if not path.exists():
        raise FileNotFoundError(f"missing artifact: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _reference_path(reference: dict[str, Any]) -> str | None:
    return reference.get("selected_reference_image_path") or reference.get("selected_reference_url")


def _approval_is_present(reference: dict[str, Any]) -> bool:
    approval = reference.get("user_approval") or {}
    return (
        reference.get("approval_status") == "approved"
        and approval.get("approved") is True
        and bool(approval.get("approved_by"))
        and bool(approval.get("approved_at"))
    )


def _risk_waiver_is_approved(reference: dict[str, Any]) -> bool:
    waiver = reference.get("risk_waiver") or {}
    return (
        reference.get("source_type") == "risk_accepted"
        and reference.get("approval_status") == "approved"
        and waiver.get("user_approved") is True
        and bool(waiver.get("approved_by"))
        and bool(waiver.get("approved_at"))
    )


def _reference_is_approved(reference: dict[str, Any]) -> bool:
    source_type = reference.get("source_type")
    if source_type in REFERENCE_SOURCE_TYPES:
        return _approval_is_present(reference) and bool(_reference_path(reference))
    if source_type == "risk_accepted":
        return _risk_waiver_is_approved(reference)
    if source_type == "not_applicable":
        return reference.get("approval_status") == "not_required"
    return False


def _product_visible_scenes(scene_plan: dict[str, Any]) -> list[dict[str, Any]]:
    visible = []
    for scene in scene_plan.get("scenes", []) or []:
        product_visibility = scene.get("product_visibility", "none")
        reference_required = scene.get("product_reference_required") is True
        if reference_required or product_visibility in PRODUCT_VISIBLE_VALUES:
            visible.append(scene)
    return visible


def _visual_assets_for_scene(
    asset_manifest: dict[str, Any],
    scene_id: str,
) -> list[dict[str, Any]]:
    return [
        asset
        for asset in asset_manifest.get("assets", []) or []
        if asset.get("scene_id") == scene_id and asset.get("type") in VISUAL_ASSET_TYPES
    ]


def _conditioning_issue_for_reference(
    asset: dict[str, Any],
    reference: dict[str, Any],
) -> str | None:
    conditioning = asset.get("product_identity_conditioning")
    asset_id = asset.get("id", "<unknown>")
    if not conditioning:
        return (
            f"Asset {asset_id} belongs to a product-visible scene but has no "
            "product_identity_conditioning metadata."
        )

    mode = conditioning.get("conditioning_mode")
    source_type = reference.get("source_type")
    if source_type == "risk_accepted":
        if mode != "text_only_waived":
            return (
                f"Asset {asset_id} uses conditioning_mode={mode!r} but the "
                "product_identity_reference is a risk_accepted waiver; record "
                "text_only_waived with waiver_decision_id."
            )
        if not conditioning.get("waiver_decision_id"):
            return (
                f"Asset {asset_id} records text_only_waived without "
                "waiver_decision_id."
            )
        return None

    if mode == "text_only_waived":
        return (
            f"Asset {asset_id} is text_only_waived even though an approved product "
            "identity reference exists."
        )

    reference_id = reference.get("reference_id")
    if conditioning.get("approved_reference_id") != reference_id:
        return (
            f"Asset {asset_id} records approved_reference_id="
            f"{conditioning.get('approved_reference_id')!r}, expected {reference_id!r}."
        )

    expected_path = _reference_path(reference)
    if conditioning.get("approved_reference_path") != expected_path:
        return (
            f"Asset {asset_id} records approved_reference_path="
            f"{conditioning.get('approved_reference_path')!r}, expected {expected_path!r}."
        )

    return None


def check_product_identity_consistency(
    product_identity_reference: dict[str, Any],
    scene_plan: dict[str, Any],
    asset_manifest: dict[str, Any],
    decision_log: dict[str, Any] | None = None,
    generated_scene_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Validate product-visible scene conditioning against an approved reference.

    The optional decision_log is accepted for caller convenience; the executable
    gate uses the canonical product_identity_reference artifact as the source of
    truth for approval metadata.

    When generated_scene_ids is provided, missing-asset checks are scoped to
    those selected/generated scene ids. This is used by the sample approval gate,
    where asset_manifest intentionally contains only sample assets while
    scene_plan still contains the full ad.
    """
    del decision_log

    issues: list[str] = []
    warnings: list[str] = []
    product_visible_scenes = _product_visible_scenes(scene_plan)
    asset_required_scenes = product_visible_scenes
    asset_scope = "full"
    if generated_scene_ids is not None:
        asset_scope = "generated_scene_ids"
        generated_scene_id_set = set(generated_scene_ids)
        scene_ids_in_plan = {
            scene.get("id")
            for scene in scene_plan.get("scenes", []) or []
            if scene.get("id")
        }
        missing_scene_ids = sorted(generated_scene_id_set - scene_ids_in_plan)
        for scene_id in missing_scene_ids:
            issues.append(
                f"Generated scene id {scene_id!r} was not found in scene_plan.scenes[]."
            )
        asset_required_scenes = [
            scene
            for scene in product_visible_scenes
            if scene.get("id") in generated_scene_id_set
        ]
    conditioned_assets_checked = 0

    if not product_visible_scenes:
        if product_identity_reference.get("source_type") == "not_applicable":
            return {
                "status": "FAIL" if issues else "PASS",
                "issues": issues,
                "warnings": [],
                "summary": {
                    "product_visible_scenes": 0,
                    "asset_required_product_visible_scenes": 0,
                    "conditioned_assets_checked": 0,
                    "asset_scope": asset_scope,
                },
            }
        warnings.append(
            "No product-visible scenes were declared, but product_identity_reference "
            f"source_type={product_identity_reference.get('source_type')!r}. Verify the "
            "scene_plan product_visibility annotations are intentional."
        )
        return {
            "status": "FAIL" if issues else "WARN",
            "issues": issues,
            "warnings": warnings,
            "summary": {
                "product_visible_scenes": 0,
                "asset_required_product_visible_scenes": 0,
                "conditioned_assets_checked": 0,
                "asset_scope": asset_scope,
            },
        }

    source_type = product_identity_reference.get("source_type")
    if source_type == "not_applicable":
        issues.append(
            "Product-visible scenes require an approved product identity reference "
            "or explicit user-approved risk waiver; source_type is not_applicable."
        )
    elif source_type == "risk_accepted":
        if not _risk_waiver_is_approved(product_identity_reference):
            issues.append(
                "Product-visible scenes use a risk_accepted strategy, but the risk "
                "waiver is not explicitly user-approved."
            )
    elif source_type in REFERENCE_SOURCE_TYPES:
        if not _reference_is_approved(product_identity_reference):
            issues.append(
                "Product-visible scenes require an approved product identity reference "
                "with selected reference path/URL and user_approval metadata."
            )
    else:
        issues.append(f"Unknown product_identity_reference.source_type={source_type!r}.")

    for scene in asset_required_scenes:
        scene_id = scene.get("id", "<unknown>")
        visual_assets = _visual_assets_for_scene(asset_manifest, scene_id)
        if not visual_assets:
            issues.append(
                f"Product-visible scene {scene_id} has no generated visual asset in "
                "asset_manifest.assets[]."
            )
            continue

        for asset in visual_assets:
            conditioned_assets_checked += 1
            issue = _conditioning_issue_for_reference(asset, product_identity_reference)
            if issue:
                issues.append(issue)
                continue

            conditioning = asset.get("product_identity_conditioning") or {}
            verdict = conditioning.get("fidelity_verdict")
            asset_id = asset.get("id", "<unknown>")
            if verdict == "FLAG":
                issues.append(
                    f"Asset {asset_id} has fidelity_verdict=FLAG against the approved "
                    "product identity reference."
                )
            elif verdict in {"WARN", "NOT_CHECKED"}:
                warnings.append(
                    f"Asset {asset_id} has fidelity_verdict={verdict}; asset review "
                    "must inspect product consistency before compose."
                )

    status = "FAIL" if issues else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "summary": {
            "product_visible_scenes": len(product_visible_scenes),
            "asset_required_product_visible_scenes": len(asset_required_scenes),
            "conditioned_assets_checked": conditioned_assets_checked,
            "asset_scope": asset_scope,
        },
    }


def check_project(
    project_dir: Path,
    generated_scene_ids: list[str] | None = None,
) -> dict[str, Any]:
    reference = _load_artifact(project_dir, "product_identity_reference.json")
    scene_plan = _load_artifact(project_dir, "scene_plan.json")
    asset_manifest = _load_artifact(project_dir, "asset_manifest.json")
    decision_log_path = project_dir / "decision_log.json"
    decision_log = None
    if decision_log_path.exists():
        with open(decision_log_path, encoding="utf-8") as f:
            decision_log = json.load(f)
    return check_product_identity_consistency(
        reference,
        scene_plan,
        asset_manifest,
        decision_log,
        generated_scene_ids=generated_scene_ids,
    )


def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: python -m tools.validation.product_identity_consistency_check "
            "<project-dir> [generated_scene_id ...]",
            file=sys.stderr,
        )
        return 2
    project_dir = Path(argv[1]).resolve()
    if not project_dir.exists():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 2
    generated_scene_ids = argv[2:] or None
    verdict = check_project(project_dir, generated_scene_ids)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
