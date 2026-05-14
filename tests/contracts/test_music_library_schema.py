"""Music-library timing sidecar schema contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[2]
TRACK_TIMING_SCHEMA = REPO / "schemas" / "music_library" / "track_timing.schema.json"


@pytest.fixture(scope="module")
def track_timing_schema() -> dict:
    return json.loads(TRACK_TIMING_SCHEMA.read_text())


def _valid_timing_sidecar() -> dict:
    return {
        "version": "1.0",
        "track_file": "cinematic_build.wav",
        "duration_seconds": 62.4,
        "bpm": 124,
        "drop_seconds": [18.2, 42.0],
        "downbeats": [0.0, 1.94, 3.87],
        "arc_shape": "rising",
        "genre_tags": ["cinematic", "electronic"],
        "license": "commercial-use",
    }


def test_track_timing_schema_is_valid_jsonschema(track_timing_schema: dict) -> None:
    jsonschema.Draft202012Validator.check_schema(track_timing_schema)


def test_track_timing_sidecar_accepts_declared_drop_seconds(
    track_timing_schema: dict,
) -> None:
    jsonschema.validate(instance=_valid_timing_sidecar(), schema=track_timing_schema)


@pytest.mark.parametrize(
    "track_file",
    [
        "../outside.mp3",
        "nested/../../outside.wav",
        "/tmp/outside.mp3",
        "C:/Music/outside.mp3",
        "\\\\server\\share\\outside.mp3",
        "\\\\?\\C:\\Music\\outside.mp3",
    ],
)
def test_track_timing_sidecar_requires_track_file_inside_music_library(
    track_timing_schema: dict,
    track_file: str,
) -> None:
    sidecar = _valid_timing_sidecar()
    sidecar["track_file"] = track_file

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=sidecar, schema=track_timing_schema)


@pytest.mark.parametrize("drop_seconds", [None, []])
def test_track_timing_sidecar_requires_non_empty_drop_seconds_for_library_locked_sync(
    track_timing_schema: dict,
    drop_seconds: list[float] | None,
) -> None:
    sidecar = _valid_timing_sidecar()
    if drop_seconds is None:
        sidecar.pop("drop_seconds")
    else:
        sidecar["drop_seconds"] = drop_seconds

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=sidecar, schema=track_timing_schema)
