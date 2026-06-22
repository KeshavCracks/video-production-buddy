from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest

from tools.base_tool import ToolResult
from tools.output_paths import (
    require_explicit_output_path,
    require_explicit_project_corpus_destination,
    require_explicit_project_media_destination,
    require_explicit_project_sidecar_destination,
    require_explicit_project_sidecar_path,
    require_explicit_project_source_media_destination,
    require_optional_project_artifact_destination,
    require_optional_project_media_directory_destination,
    require_optional_project_media_destination,
    require_optional_project_sidecar_path,
)

PathHelper = Callable[..., tuple[Path | None, ToolResult | None]]


@pytest.mark.parametrize(
    ("helper", "field_name"),
    [
        (require_explicit_output_path, "output_path"),
        (require_optional_project_sidecar_path, "sidecar_path"),
        (require_optional_project_artifact_destination, "artifact_dir"),
        (require_optional_project_media_destination, "media_dir"),
        (require_optional_project_media_directory_destination, "media_dir"),
        (require_explicit_project_sidecar_destination, "sidecar_dir"),
        (require_explicit_project_media_destination, "media_dir"),
        (require_explicit_project_source_media_destination, "source_dir"),
        (require_explicit_project_corpus_destination, "corpus_dir"),
        (require_explicit_project_sidecar_path, "sidecar_path"),
    ],
)
@pytest.mark.parametrize("raw_path", [[], {}, 123])
def test_project_path_helpers_reject_non_string_values(
    helper: PathHelper,
    field_name: str,
    raw_path: object,
) -> None:
    path, error = _call_path_helper(helper, field_name, raw_path)

    assert path is None
    assert error is not None
    assert f"{field_name} for demo artifact must be a string path" in (
        error.error or ""
    )


def test_generated_media_output_path_accepts_pathlike_value() -> None:
    path, error = require_explicit_output_path(
        {"output_path": Path("projects/demo/assets/audio/voice.mp3")},
        "demo_tool",
        artifact_label="demo artifact",
    )

    assert error is None
    assert path == Path("projects/demo/assets/audio/voice.mp3")


@pytest.mark.parametrize(
    "raw_path",
    [
        " projects/demo/assets/audio/voice.mp3",
        "projects/demo/assets/audio/voice.mp3 ",
    ],
)
def test_generated_media_output_path_rejects_padded_project_paths(
    raw_path: str,
) -> None:
    path, error = require_explicit_output_path(
        {"output_path": raw_path},
        "demo_tool",
        artifact_label="demo artifact",
    )

    assert path is None
    assert error is not None
    assert "projects/<project-name>/" in (error.error or "")


@pytest.mark.parametrize(
    ("helper", "field_name"),
    [
        (require_optional_project_sidecar_path, "sidecar_path"),
        (require_explicit_project_sidecar_path, "sidecar_path"),
    ],
)
def test_project_sidecar_path_helpers_require_file_paths(
    helper: PathHelper,
    field_name: str,
) -> None:
    path, error = _call_path_helper(
        helper,
        field_name,
        "projects/demo/artifacts/transcript",
    )

    assert path is None
    assert error is not None
    assert "must be a file path" in (error.error or "")


def test_project_sidecar_destination_accepts_directory_path() -> None:
    path, error = require_explicit_project_sidecar_destination(
        {"sidecar_dir": "projects/demo/artifacts/transcripts"},
        "sidecar_dir",
        "demo_tool",
        artifact_label="demo artifact",
    )

    assert error is None
    assert path == Path("projects/demo/artifacts/transcripts")


def test_project_sidecar_destination_rejects_file_paths() -> None:
    path, error = require_explicit_project_sidecar_destination(
        {"sidecar_dir": "projects/demo/artifacts/transcript.json"},
        "sidecar_dir",
        "demo_tool",
        artifact_label="demo artifact",
    )

    assert path is None
    assert error is not None
    assert "sidecar_dir for demo artifact must be a directory path" in (
        error.error or ""
    )
    assert "projects/<project-name>/artifacts/" in (error.error or "")


@pytest.mark.parametrize(
    ("helper", "field_name", "raw_path"),
    [
        (
            require_optional_project_artifact_destination,
            "artifact_path",
            "projects/demo/artifacts/character_design.json",
        ),
        (
            require_optional_project_media_destination,
            "media_path",
            "projects/demo/renders/preview.mp4",
        ),
    ],
)
def test_flexible_destination_helpers_accept_file_paths(
    helper: PathHelper,
    field_name: str,
    raw_path: str,
) -> None:
    path, error = _call_path_helper(helper, field_name, raw_path)

    assert error is None
    assert path == Path(raw_path)


def test_optional_media_directory_destination_rejects_file_paths() -> None:
    path, error = require_optional_project_media_directory_destination(
        {"media_dir": "projects/demo/renders/hyperframes.json"},
        "media_dir",
        "demo_tool",
        artifact_label="demo workspace",
    )

    assert path is None
    assert error is not None
    assert "media_dir for demo workspace must be a directory path" in (
        error.error or ""
    )


@pytest.mark.parametrize(
    ("helper", "field_name", "raw_path", "expected_hint"),
    [
        (
            require_explicit_project_source_media_destination,
            "source_dir",
            "projects/demo/assets/video/raw.mp4",
            "projects/<project-name>/reference_assets/",
        ),
        (
            require_explicit_project_corpus_destination,
            "corpus_dir",
            "projects/demo/corpus/index.jsonl",
            "projects/<project-name>/corpus/",
        ),
    ],
)
def test_project_directory_destination_helpers_reject_file_paths(
    helper: PathHelper,
    field_name: str,
    raw_path: str,
    expected_hint: str,
) -> None:
    path, error = _call_path_helper(helper, field_name, raw_path)

    assert path is None
    assert error is not None
    assert f"{field_name} for demo artifact must be a directory path" in (
        error.error or ""
    )
    assert expected_hint in (error.error or "")


def _call_path_helper(
    helper: PathHelper,
    field_name: str,
    raw_path: Any,
) -> tuple[Path | None, ToolResult | None]:
    if helper is require_explicit_output_path:
        return helper(
            {"output_path": raw_path},
            "demo_tool",
            artifact_label="demo artifact",
        )
    return helper(
        {field_name: raw_path},
        field_name,
        "demo_tool",
        artifact_label="demo artifact",
    )
