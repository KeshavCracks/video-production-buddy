"""Reference-video analyzer regression tests."""

from __future__ import annotations

from pathlib import Path

from tools.base_tool import ToolResult
from tools.analysis.video_analyzer import VideoAnalyzer


def test_video_analyzer_schema_requires_output_dir() -> None:
    assert "output_dir" in VideoAnalyzer.input_schema["required"]


def test_local_video_transcript_only_uses_video_path_for_whisper_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    video_path = tmp_path / "reference.mp4"
    video_path.write_bytes(b"fixture")
    monkeypatch.chdir(tmp_path)
    output_dir = Path("projects/demo/artifacts/analysis")
    transcribed_inputs = []

    class StubTranscriber:
        def execute(self, inputs):
            transcribed_inputs.append(inputs)
            return ToolResult(
                success=True,
                data={
                    "segments": [{"start": 0, "end": 1, "text": "Local speech"}],
                    "language": "en",
                    "duration_seconds": 1,
                },
            )

    monkeypatch.setattr(
        "tools.analysis.transcriber.Transcriber",
        StubTranscriber,
    )

    analyzer = VideoAnalyzer()
    monkeypatch.setattr(analyzer, "_get_duration", lambda _path: 1.0)

    result = analyzer.execute(
        {
            "source": str(video_path),
            "analysis_depth": "transcript_only",
            "output_dir": str(output_dir),
        }
    )

    assert result.success
    assert transcribed_inputs
    assert transcribed_inputs[0]["input_path"] == str(video_path)
    assert result.data["narration_transcript"]["full_text"] == "Local speech"


def test_video_analyzer_rejects_non_project_output_dir_before_setup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    video_path = tmp_path / "reference.mp4"
    video_path.write_bytes(b"fixture")
    duration_calls = []
    forbidden_dir = tmp_path / "analysis"

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
            "output_dir": str(forbidden_dir),
        }
    )

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "projects/<project-name>/artifacts/" in (result.error or "")
    assert duration_calls == []
    assert not forbidden_dir.exists()


def test_video_analyzer_rejects_file_shaped_output_dir_before_setup(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    video_path = tmp_path / "reference.mp4"
    video_path.write_bytes(b"fixture")
    output_dir = Path("projects/demo/artifacts/reference_analysis.json")
    duration_calls = []

    class StubTranscriber:
        def execute(self, inputs):
            return ToolResult(
                success=True,
                data={
                    "segments": [{"start": 0, "end": 1, "text": "Local speech"}],
                    "language": "en",
                    "duration_seconds": 1,
                },
            )

    analyzer = VideoAnalyzer()
    monkeypatch.setattr(
        analyzer,
        "_get_duration",
        lambda path: duration_calls.append(path) or 1.0,
    )
    monkeypatch.setattr("tools.analysis.transcriber.Transcriber", StubTranscriber)

    result = analyzer.execute(
        {
            "source": str(video_path),
            "analysis_depth": "transcript_only",
            "output_dir": str(output_dir),
        }
    )

    assert result.success is False
    assert "output_dir" in (result.error or "")
    assert "must be a directory path" in (result.error or "")
    assert duration_calls == []
    assert not output_dir.exists()


def test_url_analysis_routes_artifacts_and_media_to_project_subdirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    analysis_dir = Path("projects/demo/artifacts/reference_analysis")
    captured: dict[str, dict[str, object]] = {}

    class StubDownloader:
        def execute(self, inputs):
            captured["download"] = dict(inputs)
            return ToolResult(
                success=True,
                data={
                    "video_path": "projects/demo/reference_assets/reference_analysis/reference_video.mp4",
                    "audio_path": "projects/demo/reference_assets/reference_analysis/reference_audio.wav",
                    "metadata": {
                        "title": "Reference",
                        "duration": 8.0,
                        "resolution": "1280x720",
                    },
                    "platform": "other_url",
                },
            )

    class StubTranscriber:
        def execute(self, inputs):
            captured["transcriber"] = dict(inputs)
            return ToolResult(
                success=True,
                data={
                    "segments": [{"start": 0, "end": 1, "text": "Local speech"}],
                    "language": "en",
                    "duration_seconds": 1,
                },
            )

    class StubSceneDetect:
        def execute(self, inputs):
            captured["scene_detect"] = dict(inputs)
            return ToolResult(
                success=True,
                data={
                    "scenes": [
                        {"index": 0, "start_seconds": 0.0, "end_seconds": 4.0}
                    ]
                },
            )

    class StubFrameSampler:
        def execute(self, inputs):
            captured["frame_sampler"] = dict(inputs)
            return ToolResult(
                success=True,
                data={
                    "frames": [
                        {
                            "timestamp_seconds": 1.0,
                            "path": "projects/demo/assets/keyframes/reference_analysis/frame_0001.jpg",
                        }
                    ]
                },
            )

    class StubAudioEnergy:
        def execute(self, inputs):
            captured["audio_energy"] = dict(inputs)
            return ToolResult(
                success=True,
                data={"recommended_offset_seconds": 0.0},
            )

    monkeypatch.setattr("tools.analysis.video_downloader.VideoDownloader", StubDownloader)
    monkeypatch.setattr("tools.analysis.transcriber.Transcriber", StubTranscriber)
    monkeypatch.setattr("tools.analysis.scene_detect.SceneDetect", StubSceneDetect)
    monkeypatch.setattr("tools.analysis.frame_sampler.FrameSampler", StubFrameSampler)
    monkeypatch.setattr("tools.analysis.audio_energy.AudioEnergy", StubAudioEnergy)
    monkeypatch.setattr(VideoAnalyzer, "_classify_scene_motion", lambda self, path, scenes: [])

    result = VideoAnalyzer().execute(
        {
            "source": "https://example.com/reference.mp4",
            "analysis_depth": "standard",
            "output_dir": str(analysis_dir),
        }
    )

    assert result.success
    assert captured["download"]["output_dir"] == (
        "projects/demo/reference_assets/reference_analysis"
    )
    assert captured["transcriber"]["output_dir"] == (
        "projects/demo/artifacts/reference_analysis/transcripts"
    )
    assert captured["scene_detect"]["output_path"] == (
        "projects/demo/artifacts/reference_analysis/scenes.json"
    )
    assert captured["frame_sampler"]["output_dir"] == (
        "projects/demo/assets/keyframes/reference_analysis"
    )
    assert (tmp_path / analysis_dir / "video_analysis_brief.json").exists()
