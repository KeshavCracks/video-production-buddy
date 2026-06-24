"""Review media materialization for GenUI interaction requests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from schemas.artifacts import load_strict_json


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
PROJECT_MEDIA_DIRS = {"assets", "media", "outputs", "reference_assets", "renders"}
AUTO_MATERIALIZE_GATES = {
    "asset_review",
    "final_review",
    "music_review",
    "product_reference",
    "publish_review",
    "sample_review",
    "source_media_review",
}
REQUIRED_MEDIA_GATES = AUTO_MATERIALIZE_GATES
SAFE_MEDIA_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$")


@dataclass(frozen=True)
class ReviewAssetEnrichment:
    request: dict[str, Any]
    auto_populated: bool
    issues: list[str]


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return load_strict_json(path, context=f"review asset artifact {path.name}")
    except OSError:
        return None


def _slug(value: Any, *, fallback: str) -> str:
    raw = str(value or fallback)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-_.")
    if not slug:
        slug = fallback
    if not slug[0].isalnum():
        slug = f"media-{slug}"
    return slug[:64]


def _safe_media_path(value: str) -> bool:
    if not value.startswith("/media/") or "%" in value or "\\" in value:
        return False
    parts = Path(value.removeprefix("/media/")).parts
    return bool(parts) and all(SAFE_MEDIA_SEGMENT.fullmatch(part) for part in parts)


def _project_path_from_browser_media_path(project_dir: Path, value: str) -> Path:
    parts = Path(value.removeprefix("/media/")).parts
    if parts[0] in PROJECT_MEDIA_DIRS:
        return project_dir.joinpath(*parts)
    return project_dir / "media" / Path(*parts)


def _project_relative_path(project_dir: Path, path_value: str) -> Path | None:
    if not path_value or path_value.startswith("/media/"):
        return None
    raw = Path(path_value)
    try:
        relative = raw.resolve().relative_to(project_dir.resolve()) if raw.is_absolute() else raw
    except ValueError:
        return None
    if raw.is_absolute() and str(relative).startswith(".."):
        return None
    if any(part in {"", ".", ".."} for part in relative.parts):
        return None
    if not relative.parts or relative.parts[0] not in PROJECT_MEDIA_DIRS:
        return None
    if any(not SAFE_MEDIA_SEGMENT.fullmatch(part) for part in relative.parts):
        return None
    return relative


def _browser_media_path(project_dir: Path, path_value: Any, *, require_exists: bool) -> tuple[str | None, str | None]:
    if not isinstance(path_value, str) or not path_value.strip():
        return None, "missing media path"
    path_text = path_value.strip()
    if path_text.startswith("/media/"):
        if not _safe_media_path(path_text):
            return None, f"unsafe browser media path: {path_text}"
        if require_exists and not _project_path_from_browser_media_path(project_dir, path_text).is_file():
            return None, f"review media does not exist: {path_text}"
        return path_text, None
    relative = _project_relative_path(project_dir, path_text)
    if relative is None:
        return None, f"unsupported project media path: {path_text}"
    if relative.suffix.lower() not in MEDIA_EXTENSIONS:
        return None, f"unsupported review media type: {path_text}"
    if require_exists and not (project_dir / relative).is_file():
        return None, f"review media does not exist: {path_text}"
    return f"/media/{relative.as_posix()}", None


def _kind_from_browser_path(path_value: str, fallback: str = "path") -> str:
    suffix = Path(path_value).suffix.lower()
    return MEDIA_EXTENSIONS.get(suffix, fallback)


def _normalize_explicit_media_item(project_dir: Path, item: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    kind = str(item.get("kind") or "path")
    if kind == "text":
        text = item.get("text")
        if not isinstance(text, str):
            return None, f"text media item {item.get('id')!r} is missing text"
        title = str(item.get("title") or item.get("id") or "Text note")
        return {
            "id": _slug(item.get("id") or title, fallback="media"),
            "title": title,
            "kind": "text",
            "text": text,
            **({"alt": str(item["alt"])} if item.get("alt") else {}),
        }, None
    browser_path, issue = _browser_media_path(project_dir, item.get("path"), require_exists=True)
    if browser_path is None:
        return None, issue
    title = str(item.get("title") or item.get("id") or Path(browser_path).name)
    return {
        "id": _slug(item.get("id") or title, fallback="media"),
        "title": title,
        "kind": kind if kind in {"image", "video", "audio", "path"} else _kind_from_browser_path(browser_path),
        "path": browser_path,
        "alt": str(item.get("alt") or title),
    }, None


def _append_media_item(
    items: list[dict[str, Any]],
    issues: list[str],
    seen_paths: set[str],
    *,
    project_dir: Path,
    path_value: Any,
    title: str,
    item_id: str | None = None,
    source: str,
) -> None:
    browser_path, issue = _browser_media_path(project_dir, path_value, require_exists=True)
    if browser_path is None:
        issues.append(f"{source}: {issue}")
        return
    if browser_path in seen_paths:
        return
    seen_paths.add(browser_path)
    media_id = _slug(item_id or Path(browser_path).with_suffix("").as_posix().removeprefix("/media/"), fallback="media")
    existing_ids = {item["id"] for item in items}
    base_id = media_id
    index = 2
    while media_id in existing_ids:
        media_id = f"{base_id}-{index}"[:64]
        index += 1
    items.append(
        {
            "id": media_id,
            "title": title,
            "kind": _kind_from_browser_path(browser_path),
            "path": browser_path,
            "alt": title,
        }
    )


def _artifact_path(project_dir: Path, artifact_name: str) -> Path:
    return project_dir / "artifacts" / f"{artifact_name}.json"


def _collect_asset_manifest_media(project_dir: Path, items: list[dict[str, Any]], issues: list[str], seen_paths: set[str]) -> None:
    manifest = _load_json(_artifact_path(project_dir, "asset_manifest"))
    if not isinstance(manifest, dict):
        return
    if "sample_clip" in manifest:
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=manifest.get("sample_clip"),
            title="Sample preview",
            item_id="sample-preview",
            source="asset_manifest.sample_clip",
        )
    if "music_file" in manifest:
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=manifest.get("music_file"),
            title="Background music",
            item_id="background-music",
            source="asset_manifest.music_file",
        )
    for asset in manifest.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("id") or asset.get("scene_id") or "asset")
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=asset.get("path"),
            title=str(asset.get("id") or Path(str(asset.get("path") or "asset")).name),
            item_id=asset_id,
            source=f"asset_manifest.assets[{asset_id}].path",
        )
        review = asset.get("hallucination_review")
        if isinstance(review, dict):
            for index, keyframe_path in enumerate(review.get("keyframe_paths") or []):
                _append_media_item(
                    items,
                    issues,
                    seen_paths,
                    project_dir=project_dir,
                    path_value=keyframe_path,
                    title=f"{asset_id} keyframe {index + 1}",
                    item_id=f"{asset_id}-keyframe-{index + 1}",
                    source=f"asset_manifest.assets[{asset_id}].hallucination_review.keyframe_paths[{index}]",
                )


def _collect_product_reference_media(project_dir: Path, items: list[dict[str, Any]], issues: list[str], seen_paths: set[str]) -> None:
    reference = _load_json(_artifact_path(project_dir, "product_identity_reference"))
    if not isinstance(reference, dict):
        return
    if "selected_reference_image_path" in reference:
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=reference.get("selected_reference_image_path"),
            title="Selected product reference",
            item_id="selected-product-reference",
            source="product_identity_reference.selected_reference_image_path",
        )
    for index, candidate_path in enumerate(reference.get("candidate_reference_paths") or []):
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=candidate_path,
            title=f"Product reference candidate {index + 1}",
            item_id=f"product-reference-candidate-{index + 1}",
            source=f"product_identity_reference.candidate_reference_paths[{index}]",
        )


def _collect_source_media_review_media(project_dir: Path, items: list[dict[str, Any]], issues: list[str], seen_paths: set[str]) -> None:
    review = _load_json(_artifact_path(project_dir, "source_media_review"))
    if not isinstance(review, dict):
        return
    for index, source_file in enumerate(review.get("files") or []):
        if not isinstance(source_file, dict):
            continue
        source_id = _slug(source_file.get("path") or f"source-media-{index + 1}", fallback=f"source-media-{index + 1}")
        media_type = str(source_file.get("media_type") or "source")
        _append_media_item(
            items,
            issues,
            seen_paths,
            project_dir=project_dir,
            path_value=source_file.get("path"),
            title=f"Source {media_type} {index + 1}",
            item_id=source_id,
            source=f"source_media_review.files[{index}].path",
        )
        for frame_index, frame_path in enumerate(source_file.get("representative_frames") or []):
            _append_media_item(
                items,
                issues,
                seen_paths,
                project_dir=project_dir,
                path_value=frame_path,
                title=f"Source media {index + 1} frame {frame_index + 1}",
                item_id=f"{source_id}-frame-{frame_index + 1}",
                source=f"source_media_review.files[{index}].representative_frames[{frame_index}]",
            )


def _collect_render_media(project_dir: Path, items: list[dict[str, Any]], issues: list[str], seen_paths: set[str]) -> None:
    report = _load_json(_artifact_path(project_dir, "render_report"))
    if isinstance(report, dict):
        for output in report.get("outputs") or []:
            if not isinstance(output, dict):
                continue
            label = str(output.get("variant") or output.get("platform_target") or Path(str(output.get("path") or "render")).name)
            _append_media_item(
                items,
                issues,
                seen_paths,
                project_dir=project_dir,
                path_value=output.get("path"),
                title=f"Rendered output {label}",
                item_id=f"render-output-{label}",
                source=f"render_report.outputs[{label}].path",
            )
    review = _load_json(_artifact_path(project_dir, "final_review"))
    if not isinstance(review, dict):
        return
    _append_media_item(
        items,
        issues,
        seen_paths,
        project_dir=project_dir,
        path_value=review.get("output_path"),
        title="Final reviewed output",
        item_id="final-reviewed-output",
        source="final_review.output_path",
    )
    spotcheck = review.get("checks", {}).get("visual_spotcheck") if isinstance(review.get("checks"), dict) else {}
    if isinstance(spotcheck, dict):
        for index, frame_path in enumerate(spotcheck.get("frame_paths") or []):
            _append_media_item(
                items,
                issues,
                seen_paths,
                project_dir=project_dir,
                path_value=frame_path,
                title=f"Final review frame {index + 1}",
                item_id=f"final-review-frame-{index + 1}",
                source=f"final_review.checks.visual_spotcheck.frame_paths[{index}]",
            )


def _should_materialize_review_assets(request: dict[str, Any]) -> bool:
    interaction_kind = request.get("interaction_kind")
    if interaction_kind in {"clarification", "project_cockpit", "background_status"}:
        return False
    if interaction_kind == "media_review":
        return True
    if "media_review" in (request.get("capabilities_needed") or []):
        return True
    gate = str(request.get("gate") or "").lower().replace("-", "_")
    return gate in AUTO_MATERIALIZE_GATES


def _requires_review_assets(request: dict[str, Any]) -> bool:
    interaction_kind = request.get("interaction_kind")
    if interaction_kind == "media_review":
        return True
    if "media_review" in (request.get("capabilities_needed") or []):
        return True
    gate = str(request.get("gate") or "").lower().replace("-", "_")
    return gate in REQUIRED_MEDIA_GATES


def enrich_interaction_request_with_review_assets(project_dir: Path | str, request: dict[str, Any]) -> ReviewAssetEnrichment:
    """Normalize explicit media and add canonical project review assets."""
    project_root = Path(project_dir).resolve()
    enriched = dict(request)
    issues: list[str] = []
    media_items: list[dict[str, Any]] = []
    seen_paths: set[str] = set()

    for item in enriched.get("media_items") or []:
        if not isinstance(item, dict):
            issues.append("media_items contains a non-object item")
            continue
        normalized, issue = _normalize_explicit_media_item(project_root, item)
        if normalized is None:
            raise ValueError(issue or "invalid media item")
        media_items.append(normalized)
        if normalized.get("path"):
            seen_paths.add(str(normalized["path"]))

    explicit_count = len(media_items)
    if _should_materialize_review_assets(enriched):
        _collect_asset_manifest_media(project_root, media_items, issues, seen_paths)
        _collect_product_reference_media(project_root, media_items, issues, seen_paths)
        _collect_source_media_review_media(project_root, media_items, issues, seen_paths)
        _collect_render_media(project_root, media_items, issues, seen_paths)

    if media_items or "media_items" in enriched:
        enriched["media_items"] = media_items
    auto_populated = len(media_items) > explicit_count
    if _requires_review_assets(enriched) and not media_items:
        raise ValueError("GenUI media review requires at least one browser-reviewable media item")
    return ReviewAssetEnrichment(request=enriched, auto_populated=auto_populated, issues=issues)
