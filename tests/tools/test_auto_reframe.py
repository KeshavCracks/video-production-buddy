from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest

from tools.base_tool import ToolResult
from tools.video.auto_reframe import AutoReframe


def _project_output(name: str) -> str:
    return f"projects/test-auto-reframe/renders/{name}"


def test_auto_reframe_rejects_unknown_target_aspect(monkeypatch, tmp_path: Path):
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    tool = AutoReframe()
    monkeypatch.setattr(tool, "_get_video_info", lambda _path: (1920, 1080, 30.0))
    monkeypatch.setattr(tool, "_get_face_data", lambda *args, **kwargs: [])

    def fake_render(*args, **kwargs):
        return ToolResult(success=True)

    monkeypatch.setattr(tool, "_render_static_crop", fake_render)

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": _project_output("out.mp4"),
            "target_aspect": "not-a-real-aspect",
        }
    )

    assert not result.success
    assert "Unknown target_aspect" in (result.error or "")


def test_auto_reframe_matching_aspect_writes_requested_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"already-portrait")
    output_path = tmp_path / _project_output("out.mp4")
    tool = AutoReframe()
    monkeypatch.setattr(tool, "_get_video_info", lambda _path: (1080, 1920, 30.0))

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": _project_output("out.mp4"),
            "target_aspect": "portrait",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == _project_output("out.mp4")
    assert result.artifacts == [_project_output("out.mp4")]
    assert output_path.read_bytes() == b"already-portrait"
    assert {
        "message",
        "input",
        "output",
        "output_path",
        "source_resolution",
        "crop_resolution",
        "output_resolution",
        "method",
        "target_aspect",
    } <= set(AutoReframe.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=AutoReframe.output_schema)


def test_auto_reframe_render_success_payload_includes_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"landscape-video")
    tool = AutoReframe()

    monkeypatch.setattr(tool, "_get_video_info", lambda _path: (1920, 1080, 30.0))
    monkeypatch.setattr(tool, "_get_face_data", lambda *args, **kwargs: [])

    def fake_render_static_crop(
        input_path: Path,
        output_path: Path,
        *args,
        **kwargs,
    ) -> ToolResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"reframed")
        return ToolResult(success=True)

    monkeypatch.setattr(tool, "_render_static_crop", fake_render_static_crop)

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": _project_output("rendered.mp4"),
            "target_aspect": "portrait",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == _project_output("rendered.mp4")
    assert result.artifacts == [_project_output("rendered.mp4")]
    assert (tmp_path / _project_output("rendered.mp4")).read_bytes() == b"reframed"
    jsonschema.validate(instance=result.data, schema=AutoReframe.output_schema)


def test_auto_reframe_idempotency_key_includes_output_and_render_parameters():
    tool = AutoReframe()
    base = {
        "input_path": "input.mp4",
        "output_path": "out-a.mp4",
        "target_aspect": "portrait",
        "target_width": 1080,
        "target_height": 1920,
        "face_tracking_json": "faces-a.json",
        "smoothing_window": 15,
        "face_padding": 0.4,
        "sample_fps": 5,
        "codec": "libx264",
        "crf": 18,
    }
    variants = [
        {"output_path": "out-b.mp4"},
        {"face_tracking_json": "faces-b.json"},
        {"sample_fps": 10},
        {"codec": "libx265"},
        {"crf": 23},
    ]

    base_key = tool.idempotency_key(base)

    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key


def test_auto_reframe_precomputed_face_tracking_rejects_non_strict_json(tmp_path: Path):
    tracking_path = tmp_path / "faces.json"
    tracking_path.write_text(
        '{"faces":[{"timestamp_seconds":0,"bbox":{"x":NaN,"y":0.2,"width":0.1,"height":0.1}}]}\n',
        encoding="utf-8",
    )
    tool = AutoReframe()

    with pytest.raises(ValueError, match="strict JSON"):
        tool._get_face_data(
            {"face_tracking_json": str(tracking_path)},
            tmp_path / "input.mp4",
            30.0,
        )


@pytest.mark.parametrize("output_kind", ["missing", "relative", "absolute"])
def test_auto_reframe_requires_project_output_path_before_tracking_or_render(
    output_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    tool = AutoReframe()
    face_calls: list[Path] = []
    render_calls: list[Path] = []

    monkeypatch.setattr(tool, "_get_video_info", lambda _path: (1920, 1080, 30.0))

    def fake_get_face_data(inputs, path, fps):
        face_calls.append(path)
        return []

    def fake_render_static_crop(
        input_path: Path,
        output_path: Path,
        *args,
        **kwargs,
    ) -> ToolResult:
        render_calls.append(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"rendered")
        return ToolResult(success=True)

    monkeypatch.setattr(tool, "_get_face_data", fake_get_face_data)
    monkeypatch.setattr(tool, "_render_static_crop", fake_render_static_crop)
    inputs: dict[str, object] = {
        "input_path": str(input_path),
        "target_aspect": "portrait",
    }
    if output_kind == "relative":
        inputs["output_path"] = "reframed.mp4"
        forbidden_output = tmp_path / "reframed.mp4"
    elif output_kind == "absolute":
        forbidden_output = tmp_path / "reframed.mp4"
        inputs["output_path"] = str(forbidden_output)
    else:
        forbidden_output = tmp_path / "input_portrait.mp4"

    result = tool.execute(inputs)

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert face_calls == []
    assert render_calls == []
    assert not forbidden_output.exists()


def test_auto_reframe_schema_requires_output_path() -> None:
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"input_path": "input.mp4"},
            schema=AutoReframe.input_schema,
        )


def test_auto_reframe_dynamic_crop_escapes_single_quotes_in_sendcmd_path(tmp_path: Path):
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = tmp_path / "work'space" / "out.mp4"
    tool = AutoReframe()
    captured: dict[str, str] = {}

    def fake_run_command(cmd, *args, **kwargs):
        captured["vf"] = cmd[cmd.index("-vf") + 1]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"reframed")

    tool.run_command = fake_run_command  # type: ignore[method-assign]

    result = tool._render_dynamic_crop(
        input_path,
        output_path,
        crop_xs=[10, 20, 30],
        crop_ys=[5, 15, 25],
        crop_w=100,
        crop_h=100,
        out_w=200,
        out_h=200,
        fps=30.0,
        codec="libx264",
        crf=18,
    )

    assert result.success, result.error
    assert "work\\'space" in captured["vf"]
