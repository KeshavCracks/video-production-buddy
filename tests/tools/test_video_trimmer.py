from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest

from tools.video.video_trimmer import VideoTrimmer


class _RecordingVideoTrimmer(VideoTrimmer):
    def __init__(self) -> None:
        super().__init__()
        self.concat_list_body: str | None = None
        self.commands: list[list[str]] = []

    def run_command(self, cmd, *args, **kwargs):
        self.commands.append(list(cmd))
        if "-f" in cmd and "concat" in cmd:
            list_path = Path(cmd[cmd.index("-i") + 1])
            self.concat_list_body = list_path.read_text(encoding="utf-8")

        class _Result:
            stdout = "{}"
            stderr = ""

        return _Result()


class _WritingVideoTrimmer(_RecordingVideoTrimmer):
    def run_command(self, cmd, *args, **kwargs):
        result = super().run_command(cmd, *args, **kwargs)
        output_path = Path(cmd[-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"video")
        return result


def _project_output(name: str) -> str:
    return f"projects/test-video-trimmer/assets/video/{name}"


def test_video_trimmer_concat_missing_segment_reports_missing_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    tool = VideoTrimmer()
    missing = tmp_path / "missing.mp4"

    result = tool.execute(
        {
            "operation": "concat",
            "segments": [{"input_path": str(missing)}],
            "output_path": _project_output("out.mp4"),
        }
    )

    assert not result.success
    assert f"Segment input not found: {missing}" in (result.error or "")


def test_video_trimmer_concat_escapes_single_quotes_in_file_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    clip = tmp_path / "clip's intro.mp4"
    clip.write_bytes(b"placeholder")
    other = tmp_path / "other.mp4"
    other.write_bytes(b"placeholder")
    tool = _RecordingVideoTrimmer()

    result = tool.execute(
        {
            "operation": "concat",
            "segments": [
                {"input_path": str(clip)},
                {"input_path": str(other)},
            ],
            "output_path": _project_output("out.mp4"),
        }
    )

    assert result.success
    assert tool.concat_list_body is not None
    assert "clip'\\''s intro.mp4" in tool.concat_list_body


def test_video_trimmer_idempotency_key_includes_outputs_and_operation_parameters():
    tool = VideoTrimmer()
    base = {
        "operation": "cut",
        "input_path": "input.mp4",
        "output_path": "out-a.mp4",
        "start_seconds": 1,
        "end_seconds": 3,
        "speed_factor": 1.0,
        "codec": "copy",
        "segments": [{"input_path": "a.mp4"}, {"input_path": "b.mp4"}],
    }
    variants = [
        {"output_path": "out-b.mp4"},
        {"codec": "libx264"},
        {"segments": [{"input_path": "b.mp4"}, {"input_path": "a.mp4"}]},
    ]

    base_key = tool.idempotency_key(base)

    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key


@pytest.mark.parametrize("operation", ["cut", "speed", "concat"])
@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_video_trimmer_requires_project_output_path_before_render(
    operation: str,
    output_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    clip_a.write_bytes(b"a")
    clip_b.write_bytes(b"b")
    tool = _RecordingVideoTrimmer()

    if operation == "cut":
        inputs: dict[str, object] = {
            "operation": "cut",
            "input_path": str(clip_a),
            "start_seconds": 0,
            "end_seconds": 1,
        }
        default_output = tmp_path / "a_cut.mp4"
    elif operation == "speed":
        inputs = {
            "operation": "speed",
            "input_path": str(clip_a),
            "speed_factor": 1.5,
        }
        default_output = tmp_path / "a_speed.mp4"
    else:
        inputs = {
            "operation": "concat",
            "segments": [
                {"input_path": str(clip_a)},
                {"input_path": str(clip_b)},
            ],
        }
        default_output = tmp_path / "concat_output.mp4"

    if output_kind == "relative":
        inputs["output_path"] = f"{operation}.mp4"
        forbidden_output = tmp_path / f"{operation}.mp4"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / f"{operation}.mp4"
        inputs["output_path"] = str(forbidden_output)
    else:
        forbidden_output = default_output

    result = tool.execute(inputs)

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert tool.commands == []
    assert not forbidden_output.exists()


@pytest.mark.parametrize(
    "instance",
    [
        {"operation": "cut", "input_path": "input.mp4"},
        {"operation": "speed", "input_path": "input.mp4"},
        {"operation": "concat", "segments": [{"input_path": "input.mp4"}]},
    ],
)
def test_video_trimmer_schema_requires_output_path_for_write_operations(
    instance: dict[str, object],
) -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=instance, schema=VideoTrimmer.input_schema)


@pytest.mark.parametrize("operation", ["cut", "speed", "concat"])
def test_video_trimmer_success_payload_includes_output_path(
    operation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    clip_a.write_bytes(b"a")
    clip_b.write_bytes(b"b")
    output_path = _project_output(f"{operation}.mp4")

    if operation == "cut":
        inputs: dict[str, object] = {
            "operation": "cut",
            "input_path": str(clip_a),
            "start_seconds": 0.25,
            "end_seconds": 1.0,
        }
    elif operation == "speed":
        inputs = {
            "operation": "speed",
            "input_path": str(clip_a),
            "speed_factor": 1.5,
        }
    else:
        inputs = {
            "operation": "concat",
            "segments": [
                {"input_path": str(clip_a)},
                {"input_path": str(clip_b)},
            ],
        }

    result = _WritingVideoTrimmer().execute({**inputs, "output_path": output_path})

    assert result.success is True
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()
    assert {
        "operation",
        "input",
        "output",
        "output_path",
        "start_seconds",
        "end_seconds",
        "speed_factor",
        "segment_count",
    } <= set(VideoTrimmer.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=VideoTrimmer.output_schema)
