from __future__ import annotations

import math
from pathlib import Path

import jsonschema
import pytest

from tools.base_tool import ToolResult
from tools.video.silence_cutter import SilenceCutter


class _RecordingSilenceCutter(SilenceCutter):
    def __init__(self) -> None:
        super().__init__()
        self.concat_list_bodies: list[str] = []

    def run_command(self, cmd, *args, **kwargs):
        if "-f" in cmd and "concat" in cmd:
            list_path = Path(cmd[cmd.index("-i") + 1])
            self.concat_list_bodies.append(list_path.read_text(encoding="utf-8"))
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"stub-output")

        class _Result:
            stdout = "{}"
            stderr = ""

        return _Result()


class _ExecuteRecordingSilenceCutter(SilenceCutter):
    def __init__(self) -> None:
        super().__init__()
        self.render_calls: list[Path] = []

    def _render_jump_cut(
        self,
        input_path: Path,
        output_path: Path,
        speech_segments: list[dict],
        codec: str,
        crf: int,
    ) -> ToolResult:
        self.render_calls.append(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered")
        return ToolResult(success=True)

    def _render_speed_up(
        self,
        input_path: Path,
        output_path: Path,
        silences: list[dict],
        speech_segments: list[dict],
        total_duration: float,
        speed_factor: float,
        codec: str,
        crf: int,
    ) -> ToolResult:
        self.render_calls.append(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered")
        return ToolResult(success=True)


def _project_video_output(name: str) -> str:
    return f"projects/test-silence-cutter/assets/video/{name}"


def _project_metadata_output(name: str) -> str:
    return f"projects/test-silence-cutter/artifacts/{name}"


def test_jump_cut_escapes_single_quotes_in_concat_list(tmp_path: Path):
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = tmp_path / "work'space" / "out.mp4"
    tool = _RecordingSilenceCutter()

    result = tool._render_jump_cut(
        input_path,
        output_path,
        [{"start": 0.0, "end": 1.0}],
        "libx264",
        18,
    )

    assert result.success, result.error
    assert "work'\\''space" in tool.concat_list_bodies[0]


def test_speed_up_escapes_single_quotes_in_concat_list(tmp_path: Path):
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = tmp_path / "work'space" / "out.mp4"
    tool = _RecordingSilenceCutter()

    result = tool._render_speed_up(
        input_path,
        output_path,
        silences=[{"start": 1.0, "end": 2.0}],
        speech_segments=[{"start": 0.0, "end": 1.0}],
        total_duration=2.0,
        speed_factor=6.0,
        codec="libx264",
        crf=18,
    )

    assert result.success, result.error
    assert "work'\\''space" in tool.concat_list_bodies[0]


def test_silence_cutter_idempotency_key_includes_output_and_render_parameters():
    tool = SilenceCutter()
    base = {
        "input_path": "talking-head.mp4",
        "output_path": "out-a.mp4",
        "mode": "speed_up",
        "silence_threshold_db": -35,
        "min_silence_duration": 0.5,
        "padding_seconds": 0.08,
        "silence_speed_factor": 6.0,
        "codec": "libx264",
        "crf": 18,
    }
    variants = [
        {"output_path": "out-b.mp4"},
        {"silence_speed_factor": 8.0},
        {"codec": "libx265"},
        {"crf": 23},
    ]

    base_key = tool.idempotency_key(base)

    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key


def test_silence_cutter_mark_rejects_non_finite_metadata_before_writing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = Path(_project_metadata_output("silence.json"))
    monkeypatch.setattr(
        SilenceCutter,
        "_detect_silence",
        lambda self, input_path, threshold_db, min_duration: [
            {"start": 1.0, "end": 2.0, "duration": math.nan}
        ],
    )
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)

    result = SilenceCutter().execute(
        {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "mode": "mark",
        }
    )

    assert result.success is False
    assert "strict JSON" in (result.error or "")
    assert not output_path.exists()


def test_silence_cutter_no_silence_writes_requested_video_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"unchanged-video")
    output_path = _project_video_output("unchanged.mp4")
    monkeypatch.setattr(SilenceCutter, "_detect_silence", lambda *args, **kwargs: [])

    result = SilenceCutter().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "mode": "remove",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).read_bytes() == b"unchanged-video"
    assert {
        "message",
        "mode",
        "silence_segments",
        "speech_segments",
        "silence_duration_seconds",
        "speech_duration_seconds",
        "input",
        "output",
        "output_path",
        "input_duration",
        "output_duration",
        "silence_removed_seconds",
        "time_saved_percent",
    } <= set(SilenceCutter.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=SilenceCutter.output_schema)


def test_silence_cutter_mark_no_silence_writes_requested_metadata_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"quiet-free-video")
    output_path = _project_metadata_output("no-silence.json")
    monkeypatch.setattr(SilenceCutter, "_detect_silence", lambda *args, **kwargs: [])
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)

    result = SilenceCutter().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "mode": "mark",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()
    jsonschema.validate(instance=result.data, schema=SilenceCutter.output_schema)


def test_silence_cutter_mark_success_payload_includes_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = _project_metadata_output("silence.json")
    monkeypatch.setattr(
        SilenceCutter,
        "_detect_silence",
        lambda self, input_path, threshold_db, min_duration: [
            {"start": 1.0, "end": 2.0, "duration": 1.0}
        ],
    )
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)

    result = SilenceCutter().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "mode": "mark",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()
    jsonschema.validate(instance=result.data, schema=SilenceCutter.output_schema)


@pytest.mark.parametrize("mode", ["remove", "speed_up"])
def test_silence_cutter_render_success_payload_includes_output_path(
    mode: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = _project_video_output(f"{mode}.mp4")
    tool = _ExecuteRecordingSilenceCutter()
    monkeypatch.setattr(
        SilenceCutter,
        "_detect_silence",
        lambda self, input_path, threshold_db, min_duration: [
            {"start": 1.0, "end": 2.0, "duration": 1.0}
        ],
    )
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "mode": mode,
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).read_bytes() == b"rendered"
    jsonschema.validate(instance=result.data, schema=SilenceCutter.output_schema)


@pytest.mark.parametrize("mode", ["remove", "speed_up"])
@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_silence_cutter_requires_project_video_output_path_before_render(
    mode: str,
    output_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    tool = _ExecuteRecordingSilenceCutter()
    monkeypatch.setattr(
        SilenceCutter,
        "_detect_silence",
        lambda self, input_path, threshold_db, min_duration: [
            {"start": 1.0, "end": 2.0, "duration": 1.0}
        ],
    )
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)
    inputs: dict[str, object] = {
        "input_path": str(input_path),
        "mode": mode,
    }

    if output_kind == "relative":
        inputs["output_path"] = f"{mode}.mp4"
        forbidden_output = tmp_path / f"{mode}.mp4"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / f"{mode}.mp4"
        inputs["output_path"] = str(forbidden_output)
    else:
        forbidden_output = input_path.with_stem(f"{input_path.stem}_cut")

    result = tool.execute(inputs)

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert tool.render_calls == []
    assert not forbidden_output.exists()


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_silence_cutter_mark_requires_project_sidecar_output_path_before_writing(
    output_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    monkeypatch.setattr(
        SilenceCutter,
        "_detect_silence",
        lambda self, input_path, threshold_db, min_duration: [
            {"start": 1.0, "end": 2.0, "duration": 1.0}
        ],
    )
    monkeypatch.setattr(SilenceCutter, "_get_duration", lambda self, input_path: 3.0)
    inputs: dict[str, object] = {
        "input_path": str(input_path),
        "mode": "mark",
    }

    if output_kind == "relative":
        inputs["output_path"] = "silence.json"
        forbidden_output = tmp_path / "silence.json"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / "silence.json"
        inputs["output_path"] = str(forbidden_output)
    else:
        forbidden_output = input_path.with_suffix(".silence.json")

    result = SilenceCutter().execute(inputs)

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert not forbidden_output.exists()


@pytest.mark.parametrize("mode", ["mark", "remove", "speed_up"])
def test_silence_cutter_schema_requires_output_path_for_write_modes(
    mode: str,
) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"input_path": "input.mp4", "mode": mode},
            schema=SilenceCutter.input_schema,
        )
