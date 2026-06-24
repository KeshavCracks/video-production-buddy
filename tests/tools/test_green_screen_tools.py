from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap

import jsonschema
import numpy as np
import pytest
from PIL import Image

from tools.video.green_screen_composite import GreenScreenComposite
from tools.video.green_screen_processor import GreenScreenProcessor


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_green_screen_composite_imports_without_optional_pixel_dependencies():
    script = textwrap.dedent(
        """
        import importlib.abc
        import sys

        class OptionalDependencyBlocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "numpy" or fullname.startswith("numpy."):
                    raise ImportError(f"blocked optional dependency: {fullname}")
                if fullname == "PIL" or fullname.startswith("PIL."):
                    raise ImportError(f"blocked optional dependency: {fullname}")
                return None

        sys.meta_path.insert(0, OptionalDependencyBlocker())

        from tools.video.green_screen_composite import GreenScreenComposite

        print(GreenScreenComposite().name)
        """
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "green_screen_composite"


def test_green_screen_processor_rejects_unknown_method(monkeypatch, tmp_path: Path):
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    monkeypatch.chdir(tmp_path)
    output_path = Path("projects/test-green/renders/out.mp4")
    tool = GreenScreenProcessor()
    monkeypatch.setattr(
        tool,
        "_probe_video",
        lambda _path: {"duration": 1.0, "width": 640, "height": 360, "fps": 30.0},
    )
    monkeypatch.setattr(tool, "_extract_frames", lambda *args, **kwargs: 1)
    monkeypatch.setattr(tool, "_process_rembg", lambda *args, **kwargs: True)
    monkeypatch.setattr(tool, "_reconstruct_video", lambda *args, **kwargs: output_path.write_bytes(b"out"))

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": str(output_path),
            "method": "not-a-real-method",
        }
    )

    assert not result.success
    assert "Unknown method" in (result.error or "")


def test_green_screen_processor_idempotency_key_includes_output_path():
    tool = GreenScreenProcessor()
    base = {
        "input_path": "input.mp4",
        "output_path": "out-a.mp4",
        "method": "chromakey",
        "fps": 15,
        "bg_color": "#0E172A",
        "max_frames": 0,
    }

    assert tool.idempotency_key(base) != tool.idempotency_key({**base, "output_path": "out-b.mp4"})


def test_green_screen_processor_success_payload_matches_output_schema(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    output_path = "projects/test-green/renders/keyed.mp4"
    tool = GreenScreenProcessor()

    monkeypatch.setattr(
        tool,
        "_probe_video",
        lambda _path: {"duration": 1.0, "width": 640, "height": 360, "fps": 30.0},
    )
    monkeypatch.setattr(tool, "_auto_detect_method", lambda *args, **kwargs: "chromakey")
    monkeypatch.setattr(tool, "_extract_frames", lambda *args, **kwargs: 2)
    monkeypatch.setattr(tool, "_process_chromakey", lambda *args, **kwargs: True)
    monkeypatch.setattr(tool, "_reconstruct_video", lambda *args, **kwargs: (tmp_path / output_path).write_bytes(b"keyed"))

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "method": "auto",
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).read_bytes() == b"keyed"
    assert {
        "method_used",
        "frame_count",
        "duration",
        "output_path",
        "resolution",
        "fps",
        "bg_color",
    } <= set(GreenScreenProcessor.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=GreenScreenProcessor.output_schema)


@pytest.mark.parametrize("output_path", ["out.mp4", "/tmp/out.mp4"])
def test_green_screen_processor_requires_project_output_path_before_probe(
    output_path, monkeypatch, tmp_path: Path
):
    input_path = tmp_path / "input.mp4"
    input_path.write_bytes(b"stub-video")
    calls = []
    tool = GreenScreenProcessor()

    def fake_probe(*args, **kwargs):
        calls.append((args, kwargs))
        return {"duration": 1.0, "width": 640, "height": 360, "fps": 30.0}

    monkeypatch.setattr(tool, "_probe_video", fake_probe)

    result = tool.execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "method": "chromakey",
        }
    )

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert calls == []


def test_green_screen_composite_rejects_unknown_layout():
    speaker = Image.new("RGB", (32, 32), (0, 0, 0))
    background = Image.new("RGB", (32, 32), (255, 255, 255))

    with pytest.raises(ValueError, match="Unknown layout"):
        GreenScreenComposite()._composite_frame(
            speaker,
            background,
            np.array([0, 0, 0]),
            layout="not-a-real-layout",
            speaker_scale=0.65,
            bg_shift_up=0,
            out_w=32,
            out_h=32,
        )


def test_green_screen_composite_idempotency_key_includes_output_and_audio_source():
    tool = GreenScreenComposite()
    base = {
        "speaker_path": "speaker.mp4",
        "background_path": "background.mp4",
        "output_path": "out-a.mp4",
        "original_audio_path": "audio-a.mp4",
        "layout": "news_anchor",
        "speaker_scale": 0.65,
        "bg_shift_up": 300,
        "bg_color_hex": "#0E172A",
    }
    variants = [
        {"output_path": "out-b.mp4"},
        {"original_audio_path": "audio-b.mp4"},
    ]

    base_key = tool.idempotency_key(base)

    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key


def test_green_screen_composite_success_payload_includes_output_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    speaker_path = tmp_path / "speaker.mp4"
    background_path = tmp_path / "background.mp4"
    speaker_path.write_bytes(b"speaker")
    background_path.write_bytes(b"background")
    output_path = "projects/test-green/renders/composite.mp4"
    tool = GreenScreenComposite()

    monkeypatch.setattr(
        tool,
        "_probe_video",
        lambda _path: {"fps": 15.0, "duration": 1.0, "width": 64, "height": 36},
    )

    def fake_extract_frames(_video_path: Path, frames_dir: Path, _fps: float) -> None:
        frames_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (64, 36), (0, 0, 0)).save(frames_dir / "frame_000001.png")

    def fake_composite_frame(*args, **kwargs) -> Image.Image:
        return Image.new("RGB", (64, 36), (255, 255, 255))

    def fake_encode_frames(
        _frames_dir: Path,
        encoded_output_path: Path,
        *_args,
        **_kwargs,
    ) -> None:
        encoded_output_path.parent.mkdir(parents=True, exist_ok=True)
        encoded_output_path.write_bytes(b"composite")

    monkeypatch.setattr(tool, "_extract_frames", fake_extract_frames)
    monkeypatch.setattr(tool, "_composite_frame", fake_composite_frame)
    monkeypatch.setattr(tool, "_encode_frames", fake_encode_frames)

    result = tool.execute(
        {
            "speaker_path": str(speaker_path),
            "background_path": str(background_path),
            "output_path": output_path,
        }
    )

    assert result.success, result.error
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).read_bytes() == b"composite"
    assert {
        "output",
        "output_path",
        "layout",
        "fps",
        "frame_count",
        "duration",
        "dimensions",
        "speaker_scale",
        "has_audio",
    } <= set(GreenScreenComposite.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=GreenScreenComposite.output_schema)


@pytest.mark.parametrize("output_path", ["out.mp4", "/tmp/out.mp4"])
def test_green_screen_composite_requires_project_output_path_before_probe(
    output_path, monkeypatch, tmp_path: Path
):
    speaker_path = tmp_path / "speaker.mp4"
    background_path = tmp_path / "background.mp4"
    speaker_path.write_bytes(b"speaker")
    background_path.write_bytes(b"background")
    calls = []
    tool = GreenScreenComposite()

    def fake_probe(*args, **kwargs):
        calls.append((args, kwargs))
        return {"fps": 15.0, "duration": 1.0, "width": 640, "height": 360}

    monkeypatch.setattr(tool, "_probe_video", fake_probe)

    result = tool.execute(
        {
            "speaker_path": str(speaker_path),
            "background_path": str(background_path),
            "output_path": output_path,
        }
    )

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert calls == []
