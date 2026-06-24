"""Analysis tool contract regressions."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jsonschema
import pytest

from tools.analysis.audio_energy import AudioEnergy
from tools.analysis.audio_probe import AudioProbe
from tools.analysis.ad_knowledge_retriever import AdKnowledgeRetriever
from tools.analysis.composition_validator import CompositionValidator
from tools.analysis.face_tracker import FaceTracker
from tools.analysis.frame_sampler import FrameSampler
from tools.analysis.qwen_vl import QwenVL
from tools.analysis.scene_detect import SceneDetect
from tools.analysis.transcriber import Transcriber
from tools.analysis.transcript_fetcher import TranscriptFetcher
from tools.analysis.video_analyzer import VideoAnalyzer
from tools.analysis.video_downloader import VideoDownloader
from tools.analysis.video_understand import VideoUnderstand
from tools.analysis.visual_qa import VisualQA
from tools.base_tool import ToolStatus


def _project_analysis_output(name: str) -> str:
    return f"projects/test-analysis/artifacts/{name}"


@pytest.mark.parametrize(
    ("tool", "base", "variant"),
    [
        (AudioEnergy(), {"input_path": "music.wav"}, {"energy_threshold_lufs": -30}),
        (AudioEnergy(), {"input_path": "music.wav"}, {"video_duration_seconds": 30}),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "timestamps"},
            {"timestamps": [1.0, 2.0]},
        ),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "scene_guided"},
            {"scene_boundaries": [{"start_seconds": 0, "end_seconds": 4}]},
        ),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "scene_guided"},
            {"max_frames": 3},
        ),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "count", "count": 5},
            {"format": "png"},
        ),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "count", "count": 5},
            {"quality": 10},
        ),
        (
            FrameSampler(),
            {"input_path": "clip.mp4", "strategy": "count", "count": 5},
            {"output_dir": "frames-a"},
        ),
        (
            FaceTracker(),
            {"input_path": "clip.mp4", "sample_fps": 5},
            {"output_path": "faces-a.json"},
        ),
        (
            SceneDetect(),
            {"input_path": "clip.mp4", "method": "content", "threshold": 0.3},
            {"min_scene_length_seconds": 3},
        ),
        (
            SceneDetect(),
            {"input_path": "clip.mp4", "method": "content", "threshold": 0.3},
            {"output_path": "scenes-a.json"},
        ),
        (
            Transcriber(),
            {"input_path": "voice.wav", "model_size": "base"},
            {"diarize": True},
        ),
        (
            Transcriber(),
            {"input_path": "voice.wav", "model_size": "base"},
            {"output_dir": "transcripts-a"},
        ),
        (
            TranscriptFetcher(),
            {"url_or_video_id": "abcdefghijk", "languages": ["en"]},
            {"include_auto_generated": False},
        ),
        (
            VideoAnalyzer(),
            {"source": "clip.mp4", "analysis_depth": "standard"},
            {"max_keyframes": 5},
        ),
        (
            VideoAnalyzer(),
            {"source": "clip.mp4", "analysis_depth": "standard"},
            {"output_dir": "analysis-a"},
        ),
        (
            VideoDownloader(),
            {
                "url": "https://example.com/video",
                "format": "video",
                "max_resolution": "720p",
            },
            {"max_duration_seconds": 10},
        ),
        (
            VideoDownloader(),
            {
                "url": "https://example.com/video",
                "format": "video",
                "max_resolution": "720p",
            },
            {"output_dir": "downloads-a"},
        ),
        (
            VideoUnderstand(),
            {"input_path": "clip.mp4", "mode": "quality", "model": "clip"},
            {"frame_indices": [1, 5]},
        ),
        (
            VideoUnderstand(),
            {"input_path": "clip.mp4", "mode": "quality", "model": "clip"},
            {"max_frames": 1},
        ),
        (
            VisualQA(),
            {"operation": "probe", "input_path": "render.mp4"},
            {"expected": {"width": 1920}},
        ),
        (
            VisualQA(),
            {"operation": "review", "input_path": "render.mp4", "timestamps": [1.0]},
            {"output_dir": "qa-a"},
        ),
    ],
)
def test_analysis_idempotency_keys_include_output_shaping_inputs(
    tool: Any,
    base: dict[str, object],
    variant: dict[str, object],
) -> None:
    assert tool.idempotency_key(base) != tool.idempotency_key({**base, **variant})


@pytest.mark.parametrize(
    "tool",
    [AudioEnergy(), FrameSampler(), SceneDetect(), VideoAnalyzer()],
)
def test_ffprobe_callers_declare_ffprobe_dependency(tool: Any) -> None:
    assert any(str(dep).endswith(":ffprobe") for dep in tool.dependencies)


def test_frame_sampler_rejects_unknown_format_before_extraction(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")

    monkeypatch.setattr(
        FrameSampler,
        "_extract_count",
        lambda self, *args, **kwargs: [{"path": "frame.gif", "timestamp_seconds": 0}],
    )

    result = FrameSampler().execute(
        {
            "input_path": str(input_path),
            "strategy": "count",
            "count": 1,
            "format": "gif",
        }
    )

    assert result.success is False
    assert "Unknown format" in (result.error or "")


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_frame_sampler_requires_project_output_dir_before_extraction(
    output_kind: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    extraction_calls: list[str] = []
    monkeypatch.setattr(
        FrameSampler,
        "_extract_count",
        lambda self, *args, **kwargs: extraction_calls.append("count") or [],
    )

    inputs: dict[str, object] = {
        "input_path": str(input_path),
        "strategy": "count",
        "count": 1,
    }
    if output_kind == "relative":
        inputs["output_dir"] = "frames"
        forbidden_dir = tmp_path / "frames"
    elif output_kind == "absolute":
        forbidden_dir = tmp_path / "frames"
        inputs["output_dir"] = str(forbidden_dir)
    else:
        forbidden_dir = input_path.parent / "frames"

    result = FrameSampler().execute(inputs)

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert extraction_calls == []
    assert not forbidden_dir.exists()


def test_frame_sampler_rejects_file_shaped_output_dir_before_extraction(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_dir = Path("projects/demo/assets/review/frame.jpg")
    extraction_calls: list[str] = []
    monkeypatch.setattr(
        FrameSampler,
        "_extract_count",
        lambda self, *args, **kwargs: extraction_calls.append("count") or [],
    )

    result = FrameSampler().execute(
        {
            "input_path": str(input_path),
            "strategy": "count",
            "count": 1,
            "output_dir": str(output_dir),
        }
    )

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "must be a directory path" in (result.error or "")
    assert extraction_calls == []
    assert not output_dir.exists()


def test_frame_sampler_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_dir = "projects/test-analysis/assets/frames"
    frame_path = f"{output_dir}/frame_0000.jpg"

    monkeypatch.setattr(
        FrameSampler,
        "_extract_count",
        lambda self, *args, **kwargs: [
            {"path": frame_path, "timestamp_seconds": 0.0, "index": 0}
        ],
    )

    output_properties = FrameSampler.output_schema["properties"]
    assert {"strategy", "frame_count", "frames", "output_dir"} <= set(output_properties)

    result = FrameSampler().execute(
        {
            "input_path": str(input_path),
            "strategy": "count",
            "count": 1,
            "output_dir": output_dir,
        }
    )

    assert result.success is True
    assert result.data == {
        "strategy": "count",
        "frame_count": 1,
        "frames": [{"path": frame_path, "timestamp_seconds": 0.0, "index": 0}],
        "output_dir": output_dir,
    }
    assert result.artifacts == [output_dir]
    jsonschema.validate(instance=result.data, schema=FrameSampler.output_schema)


def test_scene_detect_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_path = "projects/test-analysis/artifacts/scenes.json"
    scenes = [
        {
            "index": 0,
            "start_seconds": 0.0,
            "end_seconds": 2.5,
            "duration_seconds": 2.5,
        }
    ]

    monkeypatch.setattr(SceneDetect, "_has_pyscenedetect", lambda self: False)
    monkeypatch.setattr(SceneDetect, "_detect_ffmpeg", lambda self, inputs: scenes)

    output_properties = SceneDetect.output_schema["properties"]
    assert {"scene_count", "scenes", "method", "output", "output_path"} <= set(
        output_properties
    )
    assert {"scene_count", "scenes", "method", "output", "output_path"} <= set(
        SceneDetect.output_schema["required"]
    )

    result = SceneDetect().execute(
        {
            "input_path": str(input_path),
            "method": "content",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data == {
        "scene_count": 1,
        "scenes": scenes,
        "method": "ffmpeg",
        "output": output_path,
        "output_path": output_path,
    }
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()
    jsonschema.validate(instance=result.data, schema=SceneDetect.output_schema)


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_visual_qa_review_requires_project_output_dir_before_extraction(
    output_kind: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "render.mp4"
    input_path.write_bytes(b"video")
    duration_calls: list[str] = []
    command_calls: list[list[str]] = []

    monkeypatch.setattr(
        VisualQA,
        "_get_duration",
        lambda self, path: duration_calls.append(path) or 8.0,
    )
    monkeypatch.setattr(
        VisualQA,
        "run_command",
        lambda self, cmd, *args, **kwargs: command_calls.append(cmd),
    )

    inputs: dict[str, object] = {
        "operation": "review",
        "input_path": str(input_path),
    }
    forbidden_dir = tmp_path / "review_frames"
    if output_kind == "relative":
        inputs["output_dir"] = "review_frames"
    elif output_kind == "absolute":
        inputs["output_dir"] = str(forbidden_dir)

    result = VisualQA().execute(inputs)

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert duration_calls == []
    assert command_calls == []
    assert not forbidden_dir.exists()


def test_visual_qa_review_rejects_file_shaped_output_dir_before_extraction(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "render.mp4"
    input_path.write_bytes(b"video")
    output_dir = Path("projects/demo/assets/review/frame.jpg")
    duration_calls: list[str] = []
    command_calls: list[list[str]] = []

    monkeypatch.setattr(
        VisualQA,
        "_get_duration",
        lambda self, path: duration_calls.append(path) or 8.0,
    )
    monkeypatch.setattr(
        VisualQA,
        "run_command",
        lambda self, cmd, *args, **kwargs: command_calls.append(cmd),
    )

    result = VisualQA().execute(
        {
            "operation": "review",
            "input_path": str(input_path),
            "timestamps": [1.0],
            "output_dir": str(output_dir),
        }
    )

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "must be a directory path" in (result.error or "")
    assert duration_calls == []
    assert command_calls == []
    assert not output_dir.exists()


def test_visual_qa_schema_requires_output_dir_for_review_only() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"operation": "review", "input_path": "render.mp4"},
            schema=VisualQA.input_schema,
        )

    jsonschema.validate(
        instance={"operation": "probe", "input_path": "render.mp4"},
        schema=VisualQA.input_schema,
    )
    jsonschema.validate(
        instance={"operation": "audio_levels", "input_path": "render.mp4"},
        schema=VisualQA.input_schema,
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "review", "input": "render.mp4"},
        {"operation": "probe", "input": "render.mp4"},
        {"operation": "audio_levels", "input": "render.mp4"},
    ],
)
def test_visual_qa_output_schema_requires_operation_payload_fields(
    payload: dict[str, str],
) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=VisualQA.output_schema)


def test_visual_qa_review_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "render.mp4"
    input_path.write_bytes(b"video")
    output_dir = "projects/test-analysis/assets/review"
    frame_path = f"{output_dir}/frame_1_0s.jpg"

    def fake_run_command(self, cmd, *args, **kwargs):
        Path(cmd[-1]).write_bytes(b"jpg")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(VisualQA, "run_command", fake_run_command)

    output_properties = VisualQA.output_schema["properties"]
    assert {"operation", "input", "output_dir", "frame_count", "frames"} <= set(
        output_properties
    )

    result = VisualQA().execute(
        {
            "operation": "review",
            "input_path": str(input_path),
            "timestamps": [1.0],
            "output_dir": output_dir,
        }
    )

    assert result.success is True
    assert result.data == {
        "operation": "review",
        "input": str(input_path),
        "output_dir": output_dir,
        "frame_count": 1,
        "frames": [{"timestamp": 1.0, "path": frame_path}],
    }
    assert result.artifacts == [frame_path]
    jsonschema.validate(instance=result.data, schema=VisualQA.output_schema)


def test_visual_qa_probe_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "render.mp4"
    input_path.write_bytes(b"video")
    probe_stdout = """
    {
      "format": {"duration": "5.5", "size": "2097152"},
      "streams": [
        {
          "codec_type": "video",
          "width": 1920,
          "height": 1080,
          "pix_fmt": "yuv420p",
          "codec_name": "h264",
          "r_frame_rate": "30/1"
        },
        {
          "codec_type": "audio",
          "codec_name": "aac",
          "sample_rate": "48000",
          "channels": 2
        }
      ]
    }
    """

    monkeypatch.setattr(
        VisualQA,
        "run_command",
        lambda self, cmd, *args, **kwargs: SimpleNamespace(stdout=probe_stdout, stderr=""),
    )

    output_properties = VisualQA.output_schema["properties"]
    assert {
        "operation",
        "input",
        "duration",
        "file_size_mb",
        "has_audio",
        "validation_passed",
        "validation_issues",
    } <= set(output_properties)

    result = VisualQA().execute(
        {
            "operation": "probe",
            "input_path": str(input_path),
            "expected": {"width": 1920, "height": 1080, "has_audio": True},
        }
    )

    assert result.success is True
    assert result.data["operation"] == "probe"
    assert result.data["input"] == str(input_path)
    assert result.data["duration"] == 5.5
    assert result.data["file_size_mb"] == 2.0
    assert result.data["has_audio"] is True
    assert result.data["validation_passed"] is True
    assert result.data["validation_issues"] == []
    jsonschema.validate(instance=result.data, schema=VisualQA.output_schema)


def test_visual_qa_audio_levels_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "render.mp4"
    input_path.write_bytes(b"video")
    volumedetect_stderr = """
    [Parsed_volumedetect_0 @ 0x1] mean_volume: -18.4 dB
    [Parsed_volumedetect_0 @ 0x1] max_volume: -3.2 dB
    """

    monkeypatch.setattr(
        VisualQA,
        "run_command",
        lambda self, cmd, *args, **kwargs: SimpleNamespace(
            stdout="",
            stderr=volumedetect_stderr,
        ),
    )

    output_properties = VisualQA.output_schema["properties"]
    assert {"operation", "input", "levels"} <= set(output_properties)

    result = VisualQA().execute(
        {
            "operation": "audio_levels",
            "input_path": str(input_path),
            "timestamps": [1.0],
        }
    )

    assert result.success is True
    assert result.data == {
        "operation": "audio_levels",
        "input": str(input_path),
        "levels": [
            {
                "timestamp": 1.0,
                "mean_volume_db": -18.4,
                "max_volume_db": -3.2,
            }
        ],
    }
    jsonschema.validate(instance=result.data, schema=VisualQA.output_schema)


def test_face_tracker_rejects_non_finite_tracks_before_writing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_path = Path(_project_analysis_output("faces.json"))
    monkeypatch.setattr(FaceTracker, "_has_opencv", lambda self: True)
    monkeypatch.setattr(FaceTracker, "_has_mediapipe", lambda self: False)
    monkeypatch.setattr(
        FaceTracker,
        "_track_opencv",
        lambda self, input_path, sample_fps: {
            "video_width": 1920,
            "video_height": 1080,
            "fps": 30.0,
            "duration_seconds": math.nan,
            "frame_count": 1,
            "face_detected_count": 1,
            "faces": [
                {
                    "frame_index": 0,
                    "timestamp_seconds": math.nan,
                    "confidence": 0.0,
                    "bbox": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
                }
            ],
        },
    )

    result = FaceTracker().execute(
        {
            "input_path": str(input_path),
            "output_path": str(output_path),
        }
    )

    assert result.success is False
    assert "strict JSON" in (result.error or "")
    assert not output_path.exists()


def test_scene_detect_rejects_unknown_method_before_detector(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    monkeypatch.setattr(SceneDetect, "_has_pyscenedetect", lambda self: False)
    monkeypatch.setattr(SceneDetect, "_detect_ffmpeg", lambda self, inputs: [])

    result = SceneDetect().execute(
        {
            "input_path": str(input_path),
            "method": "not-a-real-method",
            "output_path": _project_analysis_output("scenes.json"),
        }
    )

    assert result.success is False
    assert "Unknown method" in (result.error or "")


def test_scene_detect_rejects_non_finite_scenes_before_writing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_path = Path(_project_analysis_output("scenes.json"))
    monkeypatch.setattr(SceneDetect, "_has_pyscenedetect", lambda self: False)
    monkeypatch.setattr(
        SceneDetect,
        "_detect_ffmpeg",
        lambda self, inputs: [
            {"start_seconds": 0.0, "end_seconds": math.nan, "duration_seconds": math.nan}
        ],
    )

    result = SceneDetect().execute(
        {
            "input_path": str(input_path),
            "output_path": str(output_path),
        }
    )

    assert result.success is False
    assert "strict JSON" in (result.error or "")
    assert not output_path.exists()


@pytest.mark.parametrize("tool_cls", [FaceTracker, SceneDetect])
@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_analysis_sidecar_tools_require_project_output_path_before_detection(
    tool_cls: type[FaceTracker] | type[SceneDetect],
    output_kind: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    detector_calls: list[str] = []

    if tool_cls is FaceTracker:
        monkeypatch.setattr(FaceTracker, "_has_opencv", lambda self: True)
        monkeypatch.setattr(FaceTracker, "_has_mediapipe", lambda self: False)

        def fake_track(self, input_path, sample_fps):
            detector_calls.append("face")
            return {
                "video_width": 1920,
                "video_height": 1080,
                "fps": 30.0,
                "duration_seconds": 1.0,
                "frame_count": 1,
                "face_detected_count": 0,
                "faces": [],
            }

        monkeypatch.setattr(FaceTracker, "_track_opencv", fake_track)
        default_output = input_path.with_suffix(".faces.json")
    else:
        monkeypatch.setattr(SceneDetect, "_has_pyscenedetect", lambda self: False)
        monkeypatch.setattr(
            SceneDetect,
            "_detect_ffmpeg",
            lambda self, inputs: detector_calls.append("scene") or [],
        )
        default_output = input_path.with_suffix(".scenes.json")

    inputs: dict[str, object] = {"input_path": str(input_path)}
    if output_kind == "relative":
        inputs["output_path"] = "analysis.json"
        forbidden_output = tmp_path / "analysis.json"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / "analysis.json"
        inputs["output_path"] = str(forbidden_output)
    else:
        forbidden_output = default_output

    result = tool_cls().execute(inputs)

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert detector_calls == []
    assert not forbidden_output.exists()


@pytest.mark.parametrize("tool_cls", [FaceTracker, SceneDetect])
def test_analysis_sidecar_schemas_require_output_path(
    tool_cls: type[FaceTracker] | type[SceneDetect],
) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"input_path": "clip.mp4"},
            schema=tool_cls.input_schema,
        )


@pytest.mark.parametrize("tool_cls", [FaceTracker, SceneDetect])
def test_analysis_sidecar_success_payload_includes_output_path(
    tool_cls: type[FaceTracker] | type[SceneDetect],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")

    if tool_cls is FaceTracker:
        output_path = _project_analysis_output("faces.json")
        monkeypatch.setattr(FaceTracker, "_has_opencv", lambda self: True)
        monkeypatch.setattr(FaceTracker, "_has_mediapipe", lambda self: False)
        monkeypatch.setattr(
            FaceTracker,
            "_track_opencv",
            lambda self, input_path, sample_fps: {
                "video_width": 1920,
                "video_height": 1080,
                "fps": 30.0,
                "duration_seconds": 1.0,
                "frame_count": 1,
                "face_detected_count": 0,
                "faces": [],
            },
        )
    else:
        output_path = _project_analysis_output("scenes.json")
        monkeypatch.setattr(SceneDetect, "_has_pyscenedetect", lambda self: False)
        monkeypatch.setattr(
            SceneDetect,
            "_detect_ffmpeg",
            lambda self, inputs: [
                {
                    "start_seconds": 0.0,
                    "end_seconds": 1.0,
                    "duration_seconds": 1.0,
                }
            ],
        )

    result = tool_cls().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()


def test_face_tracker_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_path = _project_analysis_output("faces.json")

    monkeypatch.setattr(FaceTracker, "_has_opencv", lambda self: True)
    monkeypatch.setattr(FaceTracker, "_has_mediapipe", lambda self: False)
    monkeypatch.setattr(
        FaceTracker,
        "_track_opencv",
        lambda self, input_path, sample_fps: {
            "video_width": 1920,
            "video_height": 1080,
            "fps": 30.0,
            "duration_seconds": 1.25,
            "frame_count": 5,
            "face_detected_count": 3,
            "faces": [
                {
                    "frame_index": 0,
                    "timestamp_seconds": 0.0,
                    "confidence": 0.0,
                    "bbox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
                }
            ],
        },
    )

    output_properties = FaceTracker.output_schema["properties"]
    assert {
        "output",
        "output_path",
        "video_width",
        "video_height",
        "fps",
        "duration_seconds",
        "frames_sampled",
        "faces_detected",
        "method",
    } <= set(output_properties)

    result = FaceTracker().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "sample_fps": 5,
        }
    )

    assert result.success is True
    assert result.data == {
        "output": output_path,
        "output_path": output_path,
        "video_width": 1920,
        "video_height": 1080,
        "fps": 30.0,
        "duration_seconds": 1.25,
        "frames_sampled": 5,
        "faces_detected": 3,
        "method": "opencv_haar",
    }
    assert result.artifacts == [output_path]
    jsonschema.validate(instance=result.data, schema=FaceTracker.output_schema)

    sidecar = json.loads((tmp_path / output_path).read_text(encoding="utf-8"))
    assert sidecar["face_detected_count"] == 3
    assert sidecar["faces"][0]["bbox"]["x"] == 0.1


def test_transcriber_rejects_unknown_model_size_before_loading_model(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")

    class FakeWhisperModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def transcribe(self, *args: Any, **kwargs: Any):
            return [], SimpleNamespace(language="en", duration=0.0)

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )

    result = Transcriber().execute(
        {
            "input_path": str(input_path),
            "model_size": "not-a-real-model",
            "output_dir": str(tmp_path),
        }
    )

    assert result.success is False
    assert "Unknown model_size" in (result.error or "")


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_transcriber_requires_project_output_dir_before_model_loading(
    output_kind: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    model_loads: list[tuple[object, ...]] = []

    class FakeWhisperModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            model_loads.append(args)

        def transcribe(self, *args: Any, **kwargs: Any):
            return [], SimpleNamespace(language="en", duration=0.0)

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )

    inputs: dict[str, object] = {
        "input_path": str(input_path),
        "model_size": "base",
    }
    if output_kind == "relative":
        inputs["output_dir"] = "transcripts"
        forbidden_output = tmp_path / "transcripts" / "voice_transcript.json"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / "transcripts" / "voice_transcript.json"
        inputs["output_dir"] = str(forbidden_output.parent)
    else:
        forbidden_output = input_path.parent / "voice_transcript.json"

    result = Transcriber().execute(inputs)

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert model_loads == []
    assert not forbidden_output.exists()


def test_transcriber_schema_requires_output_dir() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"input_path": "voice.wav"},
            schema=Transcriber.input_schema,
        )


def test_transcriber_success_payload_includes_output_dir_and_transcript_path(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    output_dir = "projects/test-analysis/artifacts/transcripts"
    transcript_path = f"{output_dir}/voice_transcript.json"

    class FakeWhisperModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def transcribe(self, *args: Any, **kwargs: Any):
            return [], SimpleNamespace(language="en", duration=1.25)

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )

    output_properties = Transcriber.output_schema["properties"]
    assert "output_dir" in output_properties
    assert "transcript_path" in output_properties

    result = Transcriber().execute(
        {
            "input_path": str(input_path),
            "model_size": "base",
            "output_dir": output_dir,
        }
    )

    assert result.success is True
    assert result.data["output_dir"] == output_dir
    assert result.data["transcript_path"] == transcript_path
    assert result.artifacts == [transcript_path]
    assert (tmp_path / transcript_path).exists()


def test_transcriber_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    output_dir = "projects/test-analysis/artifacts/transcripts"
    transcript_path = f"{output_dir}/voice_transcript.json"

    class FakeWhisperModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def transcribe(self, *args: Any, **kwargs: Any):
            word = SimpleNamespace(word="hello", start=0.1234, end=0.5678, probability=0.9876)
            segment = SimpleNamespace(
                id=7,
                start=0.1234,
                end=1.2345,
                text=" hello ",
                words=[word],
            )
            return [segment], SimpleNamespace(language="en", duration=1.2345)

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )

    output_schema = Transcriber.output_schema
    output_properties = output_schema["properties"]
    segment_properties = output_properties["segments"]["items"]["properties"]
    word_properties = output_properties["word_timestamps"]["items"]["properties"]
    assert {
        "output_dir",
        "transcript_path",
        "segments",
        "word_timestamps",
        "language",
        "duration_seconds",
        "model_size",
        "device",
    } <= set(output_schema["required"])
    assert {"id", "start", "end", "text", "words"} <= set(segment_properties)
    assert {"word", "start", "end", "probability"} <= set(word_properties)

    result = Transcriber().execute(
        {
            "input_path": str(input_path),
            "model_size": "base",
            "output_dir": output_dir,
        }
    )

    assert result.success is True
    assert result.data == {
        "output_dir": output_dir,
        "transcript_path": transcript_path,
        "segments": [
            {
                "id": 7,
                "start": 0.123,
                "end": 1.234,
                "text": "hello",
                "words": [
                    {
                        "word": "hello",
                        "start": 0.123,
                        "end": 0.568,
                        "probability": 0.988,
                    }
                ],
            }
        ],
        "word_timestamps": [
            {
                "word": "hello",
                "start": 0.123,
                "end": 0.568,
                "probability": 0.988,
            }
        ],
        "language": "en",
        "duration_seconds": 1.234,
        "model_size": "base",
        "device": "cpu",
    }
    assert result.artifacts == [transcript_path]
    jsonschema.validate(instance=result.data, schema=Transcriber.output_schema)


def test_transcriber_rejects_non_finite_transcript_before_writing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    output_dir = Path("projects/test-analysis/artifacts/transcripts")

    class FakeWhisperModel:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def transcribe(self, *args: Any, **kwargs: Any):
            return [], SimpleNamespace(language="en", duration=math.nan)

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)),
    )

    result = Transcriber().execute(
        {
            "input_path": str(input_path),
            "model_size": "base",
            "output_dir": str(output_dir),
        }
    )

    assert result.success is False
    assert "strict JSON" in (result.error or "")
    assert not (output_dir / "voice_transcript.json").exists()


def test_video_analyzer_rejects_unknown_analysis_depth_before_subtools(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(VideoAnalyzer, "_save_brief", lambda self, brief, output_dir: None)

    result = VideoAnalyzer().execute(
        {
            "source": "https://example.com/video",
            "analysis_depth": "not-a-real-depth",
            "output_dir": str(tmp_path / "analysis"),
        }
    )

    assert result.success is False
    assert "Unknown analysis_depth" in (result.error or "")


def test_video_analyzer_requires_project_output_dir_before_setup(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    video_path = tmp_path / "reference.mp4"
    video_path.write_bytes(b"fixture")
    duration_calls: list[Path] = []

    analyzer = VideoAnalyzer()
    monkeypatch.setattr(
        analyzer,
        "_get_duration",
        lambda path: duration_calls.append(path) or 1.0,
    )

    result = analyzer.execute(
        {
            "source": str(video_path),
            "analysis_depth": "transcript_only",
        }
    )

    assert result.success is False
    assert "output_dir is required" in (result.error or "")
    assert "projects/<project-name>/artifacts/" in (result.error or "")
    assert duration_calls == []
    assert not (tmp_path / "projects").exists()


def test_video_analyzer_save_brief_rejects_non_finite_values_before_writing(
    tmp_path,
) -> None:
    output_dir = tmp_path / "analysis"
    output_dir.mkdir()
    brief = {
        "version": "1.0",
        "source": {
            "type": "local_file",
            "local_path": "clip.mp4",
            "duration_seconds": math.nan,
        },
        "content_analysis": {
            "summary": "",
            "topics": [],
            "target_audience": "general",
        },
        "structure_analysis": {
            "total_scenes": 0,
            "scenes": [],
            "pacing_profile": {},
        },
    }

    with pytest.raises(ValueError, match="strict JSON"):
        VideoAnalyzer()._save_brief(brief, output_dir)

    assert not (output_dir / "video_analysis_brief.json").exists()


def test_video_analyzer_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"video")
    output_dir = "projects/test-analysis/artifacts/analysis_local"
    frame_path = "projects/test-analysis/assets/keyframes/analysis_local/frame_0000.jpg"

    monkeypatch.setattr(VideoAnalyzer, "_get_duration", lambda self, path: 6.0)
    monkeypatch.setattr(
        VideoAnalyzer,
        "_classify_scene_motion",
        lambda self, video_path, scenes: [
            {"motion_type": "motion_clip", "flow_variance": 2.5}
        ],
    )
    monkeypatch.setattr(
        Transcriber,
        "execute",
        lambda self, inputs: SimpleNamespace(
            success=True,
            data={
                "segments": [{"start": 0.0, "end": 1.5, "text": "hello world"}],
                "language": "en",
            },
        ),
    )
    monkeypatch.setattr(
        SceneDetect,
        "execute",
        lambda self, inputs: SimpleNamespace(
            success=True,
            data={
                "scenes": [
                    {
                        "index": 0,
                        "start_seconds": 0.0,
                        "end_seconds": 3.0,
                    }
                ]
            },
        ),
    )

    def fake_sample_frames(self, inputs):
        Path(inputs["output_dir"]).mkdir(parents=True, exist_ok=True)
        return SimpleNamespace(
            success=True,
            data={
                "frames": [
                    {
                        "path": frame_path,
                        "timestamp_seconds": 0.1,
                        "index": 0,
                    }
                ]
            },
        )

    monkeypatch.setattr(FrameSampler, "execute", fake_sample_frames)
    monkeypatch.setattr(
        AudioEnergy,
        "execute",
        lambda self, inputs: SimpleNamespace(
            success=True,
            data={"recommended_offset_seconds": 0.25},
        ),
    )

    output_properties = VideoAnalyzer.output_schema["properties"]
    assert {
        "version",
        "source",
        "content_analysis",
        "structure_analysis",
        "narration_transcript",
        "keyframes",
        "style_profile",
        "replication_guidance",
        "_analysis_meta",
        "output_dir",
    } <= set(output_properties)

    result = VideoAnalyzer().execute(
        {
            "source": str(input_path),
            "analysis_depth": "standard",
            "max_keyframes": 1,
            "output_dir": output_dir,
        }
    )

    assert result.success is True
    assert result.data["source"]["type"] == "local_file"
    assert result.data["output_dir"] == output_dir
    assert result.data["source"]["duration_seconds"] == 6.0
    assert result.data["structure_analysis"]["total_scenes"] == 1
    assert result.data["keyframes"] == [
        {
            "timestamp": 0.1,
            "scene_index": 0,
            "path": frame_path,
            "description": "",
        }
    ]
    assert result.data["_analysis_meta"]["depth"] == "standard"
    assert result.artifacts == [
        f"{output_dir}/video_analysis_brief.json",
        "projects/test-analysis/assets/keyframes/analysis_local",
    ]
    assert (tmp_path / output_dir / "video_analysis_brief.json").exists()
    jsonschema.validate(instance=result.data, schema=VideoAnalyzer.output_schema)


def test_video_downloader_rejects_unknown_format_before_download(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(VideoDownloader, "_extract_metadata", lambda self, url: {"duration": 0})

    result = VideoDownloader().execute(
        {
            "url": "https://example.com/video",
            "output_dir": str(tmp_path),
            "format": "not-a-real-format",
        }
    )

    assert result.success is False
    assert "Unknown format" in (result.error or "")


def test_video_downloader_rejects_unknown_max_resolution_before_download(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(VideoDownloader, "_extract_metadata", lambda self, url: {"duration": 0})
    monkeypatch.setattr(
        VideoDownloader,
        "_download_video",
        lambda self, url, output_dir, max_res: (str(output_dir / "reference_video.mp4"), None),
    )

    result = VideoDownloader().execute(
        {
            "url": "https://example.com/video",
            "output_dir": str(tmp_path),
            "format": "video",
            "max_resolution": "1440p",
        }
    )

    assert result.success is False
    assert "Unknown max_resolution" in (result.error or "")


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_video_downloader_requires_project_output_dir_before_metadata(
    output_kind: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    metadata_calls: list[str] = []
    download_calls: list[str] = []
    monkeypatch.setattr(
        VideoDownloader,
        "_extract_metadata",
        lambda self, url: metadata_calls.append(url) or {"duration": 0},
    )
    monkeypatch.setattr(
        VideoDownloader,
        "_download_video",
        lambda self, url, output_dir, max_res: download_calls.append(str(output_dir))
        or (str(output_dir / "reference_video.mp4"), None),
    )

    inputs: dict[str, object] = {
        "url": "https://example.com/video",
        "format": "video",
        "max_resolution": "720p",
    }
    forbidden_dir = tmp_path / "downloads"
    if output_kind == "relative":
        inputs["output_dir"] = "downloads"
    elif output_kind == "absolute":
        inputs["output_dir"] = str(forbidden_dir)

    result = VideoDownloader().execute(inputs)

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert "reference_assets" in (result.error or "")
    assert metadata_calls == []
    assert download_calls == []
    assert not forbidden_dir.exists()


def test_video_downloader_metadata_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_dir = "projects/test-analysis/reference_assets/reference_video"
    metadata = {
        "title": "Reference clip",
        "duration": 12.5,
        "uploader": "Producer",
        "upload_date": "20260621",
        "description": "Short reference",
        "view_count": 123,
        "like_count": 45,
        "resolution": "1920x1080",
        "fps": 29.97,
    }
    monkeypatch.setattr(
        VideoDownloader,
        "_extract_metadata",
        lambda self, url: metadata,
    )

    output_properties = VideoDownloader.output_schema["properties"]
    metadata_properties = output_properties["metadata"]["properties"]
    assert {
        "video_path",
        "audio_path",
        "subtitle_path",
        "metadata",
        "platform",
        "output_dir",
    } <= set(output_properties)
    assert {
        "video_path",
        "audio_path",
        "subtitle_path",
        "metadata",
        "platform",
        "output_dir",
    } <= set(VideoDownloader.output_schema["required"])
    assert {
        "title",
        "duration",
        "uploader",
        "upload_date",
        "description",
        "view_count",
        "like_count",
        "resolution",
        "fps",
    } <= set(metadata_properties)

    result = VideoDownloader().execute(
        {
            "url": "https://www.youtube.com/watch?v=abcdefghijk",
            "output_dir": output_dir,
            "format": "metadata_only",
            "max_duration_seconds": 30,
        }
    )

    assert result.success is True
    assert result.data == {
        "video_path": None,
        "audio_path": None,
        "subtitle_path": None,
        "metadata": metadata,
        "platform": "youtube",
        "output_dir": output_dir,
    }
    assert result.artifacts == []
    assert (tmp_path / output_dir).exists()
    jsonschema.validate(instance=result.data, schema=VideoDownloader.output_schema)


def test_video_understand_quality_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "frame.png"
    input_path.write_bytes(b"image")
    quality_result = {
        "frame_index": 0,
        "blur_score": 250.0,
        "brightness": 120.5,
        "contrast": 42.25,
        "quality": "good",
        "issues": [],
        "resolution": "1920x1080",
    }

    monkeypatch.setattr(
        VideoUnderstand,
        "_load_frames",
        lambda self, input_path, is_video, frame_indices, max_frames: [object()],
    )
    monkeypatch.setattr(
        VideoUnderstand,
        "_analyze_quality",
        lambda self, frames: [quality_result],
    )

    output_properties = VideoUnderstand.output_schema["properties"]
    frame_properties = output_properties["frames"]["items"]["properties"]
    assert {"frames", "summary", "mode", "model", "frame_count"} <= set(
        output_properties
    )
    assert {
        "frame_index",
        "blur_score",
        "brightness",
        "contrast",
        "quality",
        "issues",
        "resolution",
    } <= set(frame_properties)

    result = VideoUnderstand().execute(
        {
            "input_path": str(input_path),
            "mode": "quality",
            "model": "clip",
            "max_frames": 1,
        }
    )

    assert result.success is True
    assert result.data == {
        "frames": [quality_result],
        "summary": "All 1 frame(s) passed quality checks.",
        "mode": "quality",
        "model": "metrics",
        "frame_count": 1,
    }
    jsonschema.validate(instance=result.data, schema=VideoUnderstand.output_schema)


def test_qwen_vl_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_path = "projects/test-analysis/artifacts/qwen-vl.txt"
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "A clear product hero shot."}
                            ]
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 6,
                    "total_tokens": 18,
                },
            }

    def fake_post(*args: object, **kwargs: object) -> FakeResponse:
        calls.append((args, kwargs))
        return FakeResponse()

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=fake_post))

    output_properties = QwenVL.output_schema["properties"]
    assert {
        "provider",
        "model",
        "model_name",
        "text",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "output",
        "output_path",
    } <= set(output_properties)

    result = QwenVL().execute(
        {
            "prompt": "Describe the frame.",
            "image_url": "https://example.test/frame.jpg",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data == {
        "provider": "bailian",
        "model": "qwen3-vl-plus",
        "model_name": "Qwen3-VL Plus",
        "text": "A clear product hero shot.",
        "prompt_tokens": 12,
        "completion_tokens": 6,
        "total_tokens": 18,
        "output": output_path,
        "output_path": output_path,
    }
    assert (tmp_path / output_path).read_text(encoding="utf-8") == result.data["text"]
    assert result.artifacts == [output_path]
    assert len(calls) == 1
    jsonschema.validate(instance=result.data, schema=QwenVL.output_schema)


def test_qwen_vl_rejects_empty_analysis_before_writing_output(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output_path = "projects/test-analysis/artifacts/empty-qwen-vl.txt"

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": [{"type": "text", "text": ""}]}}]}

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setitem(
        sys.modules,
        "requests",
        SimpleNamespace(post=lambda *args, **kwargs: FakeResponse()),
    )

    result = QwenVL().execute(
        {
            "prompt": "Describe the frame.",
            "image_url": "https://example.test/frame.jpg",
            "output_path": output_path,
        }
    )

    assert result.success is False
    assert "No analysis" in (result.error or "")
    assert not (tmp_path / output_path).exists()


@pytest.mark.parametrize(
    "output_path",
    [
        "qwen-vl.txt",
        "projects/test-analysis/tmp/qwen-vl.txt",
        "/tmp/qwen-vl.txt",
        "projects/test-analysis/artifacts",
    ],
)
def test_qwen_vl_rejects_non_project_sidecar_output_paths_before_api_call(
    output_path: str,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_post(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        raise AssertionError("qwen_vl should reject output_path before API call")

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=fake_post))

    result = QwenVL().execute(
        {
            "prompt": "Describe the frame.",
            "image_url": "https://example.test/frame.jpg",
            "output_path": output_path,
        }
    )

    assert result.success is False
    assert calls == []
    assert not (tmp_path / output_path).exists()
    assert "projects/<project-name>/" in (result.error or "")


def test_composition_validator_success_payload_matches_output_schema(
    tmp_path,
) -> None:
    composition_path = tmp_path / "composition.json"
    composition_path.write_text(
        json.dumps(
            {
                "render_runtime": "ffmpeg",
                "cuts": [
                    {
                        "id": "intro",
                        "source": "",
                        "in_seconds": 0,
                        "out_seconds": 2.5,
                    }
                ],
                "audio": {},
            }
        ),
        encoding="utf-8",
    )

    output_properties = CompositionValidator.output_schema["properties"]
    assert {"valid", "errors", "warnings", "info", "error_count", "warning_count"} <= set(
        output_properties
    )

    result = CompositionValidator().execute({"composition_path": str(composition_path)})

    assert result.success is True
    assert result.data["valid"] is True
    assert result.data["errors"] == []
    assert result.data["warnings"] == ["No audio configured (no narration or music)"]
    assert result.data["error_count"] == 0
    assert result.data["warning_count"] == 1
    assert any("Video duration: 2.5s" in item for item in result.data["info"])
    jsonschema.validate(instance=result.data, schema=CompositionValidator.output_schema)


def test_audio_energy_status_requires_ffprobe(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        if command == "ffmpeg":
            return f"/usr/bin/{command}"
        return None

    monkeypatch.setattr("tools.analysis.audio_energy.shutil.which", fake_which)

    assert AudioEnergy().get_status() == ToolStatus.UNAVAILABLE


def test_audio_energy_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "music.wav"
    input_path.write_bytes(b"audio")
    ffprobe_payload = {"format": {"duration": "5.0"}}
    ebur128_stderr = """
    [Parsed_ebur128_0 @ 0x1] t: 0.099 TARGET:-23 LUFS    M:-50.0 S:-50.0
    [Parsed_ebur128_0 @ 0x1] t: 1.099 TARGET:-23 LUFS    M:-30.0 S:-30.0
    [Parsed_ebur128_0 @ 0x1] t: 2.099 TARGET:-23 LUFS    M:-20.0 S:-20.0
    """

    monkeypatch.setattr(
        "tools.analysis.audio_energy.shutil.which",
        lambda command: f"/usr/bin/{command}" if command in {"ffmpeg", "ffprobe"} else None,
    )

    def fake_run(cmd, *args, **kwargs):
        if cmd[0].endswith("ffprobe"):
            return SimpleNamespace(stdout=json.dumps(ffprobe_payload), stderr="")
        return SimpleNamespace(stdout="", stderr=ebur128_stderr)

    monkeypatch.setattr("tools.analysis.audio_energy.subprocess.run", fake_run)

    output_properties = AudioEnergy.output_schema["properties"]
    assert {
        "file",
        "audio_duration_seconds",
        "analysis",
        "recommended_offset_seconds",
        "offset_reason",
        "needs_loop",
        "loop_info",
        "energy_profile",
    } <= set(output_properties)

    result = AudioEnergy().execute(
        {
            "input_path": str(input_path),
            "video_duration_seconds": 2,
            "energy_threshold_lufs": -40,
        }
    )

    assert result.success is True
    assert result.data["file"] == str(input_path)
    assert result.data["audio_duration_seconds"] == 5.0
    assert result.data["analysis"] == {
        "threshold_lufs": -40,
        "total_seconds": 3,
        "active_seconds": 2,
        "quiet_intro_seconds": 1.0,
        "peak_loudness_at_seconds": 2.0,
        "peak_loudness_lufs": -20.0,
    }
    assert result.data["recommended_offset_seconds"] == 1.0
    assert result.data["offset_reason"] == "Best 2s window starts at 1s (avg loudness: -25.0 LUFS)"
    assert result.data["needs_loop"] is False
    assert result.data["loop_info"] is None
    assert result.data["energy_profile"] == [
        {"time_seconds": 0, "loudness_lufs": -50.0, "active": False},
        {"time_seconds": 1, "loudness_lufs": -30.0, "active": True},
        {"time_seconds": 2, "loudness_lufs": -20.0, "active": True},
    ]
    jsonschema.validate(instance=result.data, schema=AudioEnergy.output_schema)


def test_audio_probe_success_payload_matches_output_schema(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    input_path = tmp_path / "voice.wav"
    input_path.write_bytes(b"audio")
    probe_payload = {
        "format": {
            "duration": "3.4567",
            "format_name": "wav",
            "format_long_name": "WAV / WAVE",
            "size": "1024",
            "bit_rate": "256000",
        },
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "pcm_s16le",
                "sample_rate": "16000",
                "channels": 1,
                "channel_layout": "mono",
                "bit_rate": "256000",
            }
        ],
    }

    monkeypatch.setattr(
        "tools.analysis.audio_probe.shutil.which",
        lambda command: "/usr/bin/ffprobe" if command == "ffprobe" else None,
    )
    monkeypatch.setattr(
        "tools.analysis.audio_probe.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(probe_payload),
            stderr="",
        ),
    )

    output_properties = AudioProbe.output_schema["properties"]
    assert {
        "file",
        "duration_seconds",
        "format_name",
        "format_long_name",
        "size_bytes",
        "bit_rate",
        "stream_count",
        "audio",
    } <= set(output_properties)

    result = AudioProbe().execute({"input_path": str(input_path)})

    assert result.success is True
    assert result.data == {
        "file": str(input_path),
        "duration_seconds": 3.457,
        "format_name": "wav",
        "format_long_name": "WAV / WAVE",
        "size_bytes": 1024,
        "bit_rate": 256000,
        "stream_count": 1,
        "audio": {
            "codec": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1,
            "channel_layout": "mono",
            "bit_rate": 256000,
        },
    }
    jsonschema.validate(instance=result.data, schema=AudioProbe.output_schema)


def test_ad_knowledge_retriever_success_payload_matches_output_schema() -> None:
    output_properties = AdKnowledgeRetriever.output_schema["properties"]
    card_properties = output_properties["cards_used"]["items"]["properties"]
    recommendation_properties = output_properties["application_recommendations"]["items"][
        "properties"
    ]
    contraindication_properties = output_properties["contraindications"]["items"][
        "properties"
    ]

    assert {
        "retrieval_backend",
        "cards_used",
        "application_recommendations",
        "contraindications",
        "gaps",
        "warnings",
    } <= set(output_properties)
    assert {
        "card_id",
        "domain",
        "source_ref",
        "summary",
        "principles",
        "relevance_score",
        "why_relevant",
        "avoid_when",
        "failure_patterns",
        "execution_techniques",
    } <= set(card_properties)
    assert {"card_id", "target", "recommendation", "confidence"} <= set(
        recommendation_properties
    )
    assert {"card_id", "avoid_when", "reason"} <= set(contraindication_properties)

    result = AdKnowledgeRetriever().execute(
        {
            "product_category": "smartphone camera",
            "platform": "tiktok",
            "audience": "global photography enthusiasts",
            "objectives": ["premium launch", "visual contrast hook"],
            "validation_targets": ["hook_mechanic", "proof_logic"],
            "backend": "auto",
            "top_k": 3,
        }
    )

    assert result.success is True
    assert result.data["retrieval_backend"] == "bm25"
    assert result.data["cards_used"]
    assert result.data["application_recommendations"]
    assert result.data["contraindications"]
    jsonschema.validate(instance=result.data, schema=AdKnowledgeRetriever.output_schema)


def test_transcript_fetcher_can_exclude_auto_generated_captions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSnippet:
        text = "manual caption"
        start = 1.2
        duration = 3.4

    class FakeManualTranscript:
        is_generated = False
        language_code = "en"

        def fetch(self):
            return SimpleNamespace(
                snippets=[FakeSnippet()],
                is_generated=False,
                language="en",
            )

    class FakeTranscriptList:
        def find_manually_created_transcript(self, languages):
            assert languages == ["en"]
            return FakeManualTranscript()

    class FakeYouTubeTranscriptApi:
        def list(self, video_id):
            assert video_id == "abcdefghijk"
            return FakeTranscriptList()

        def fetch(self, video_id, languages):
            return SimpleNamespace(
                snippets=[
                    SimpleNamespace(
                        text="auto caption",
                        start=0.0,
                        duration=1.0,
                    )
                ],
                is_generated=True,
                language="en",
            )

    monkeypatch.setitem(
        sys.modules,
        "youtube_transcript_api",
        SimpleNamespace(YouTubeTranscriptApi=FakeYouTubeTranscriptApi),
    )

    result = TranscriptFetcher().execute(
        {
            "url_or_video_id": "abcdefghijk",
            "languages": ["en"],
            "include_auto_generated": False,
        }
    )

    assert result.success, result.error
    assert result.data["full_text"] == "manual caption"
    assert result.data["is_auto_generated"] is False


def test_transcript_fetcher_success_payload_matches_output_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeSnippet:
        text = "first caption"
        start = 1.2345
        duration = 2.3456

    class FakeYouTubeTranscriptApi:
        def fetch(self, video_id, languages):
            assert video_id == "abcdefghijk"
            assert languages == ["en"]
            return SimpleNamespace(
                snippets=[FakeSnippet()],
                is_generated=True,
                language="en",
            )

    monkeypatch.setitem(
        sys.modules,
        "youtube_transcript_api",
        SimpleNamespace(YouTubeTranscriptApi=FakeYouTubeTranscriptApi),
    )

    output_properties = TranscriptFetcher.output_schema["properties"]
    segment_schema = output_properties["transcript"]["items"]
    assert {
        "transcript",
        "full_text",
        "language",
        "is_auto_generated",
        "word_count",
        "source",
        "video_id",
        "segment_count",
    } <= set(output_properties)
    assert {
        "transcript",
        "full_text",
        "language",
        "is_auto_generated",
        "word_count",
        "source",
        "video_id",
        "segment_count",
    } <= set(TranscriptFetcher.output_schema["required"])
    assert {"text", "start", "duration"} <= set(segment_schema["required"])

    result = TranscriptFetcher().execute(
        {
            "url_or_video_id": "https://youtu.be/abcdefghijk",
            "languages": ["en"],
        }
    )

    assert result.success is True
    assert result.data == {
        "transcript": [
            {
                "text": "first caption",
                "start": 1.234,
                "duration": 2.346,
            }
        ],
        "full_text": "first caption",
        "language": "en",
        "is_auto_generated": True,
        "word_count": 2,
        "source": "youtube_captions",
        "video_id": "abcdefghijk",
        "segment_count": 1,
    }
    jsonschema.validate(instance=result.data, schema=TranscriptFetcher.output_schema)
