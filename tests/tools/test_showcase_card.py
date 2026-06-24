from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import jsonschema
import pytest

from tools.video.showcase_card import ShowcaseCard


def test_showcase_card_idempotency_key_includes_output_and_render_parameters():
    tool = ShowcaseCard()
    base = {
        "input_path": "clip.mp4",
        "output_path": "out-a.mp4",
        "title": "Demo",
        "subtitle": "Short description",
        "output_width": 1080,
        "output_height": 1920,
        "background_color": "0x0A0F1A",
        "title_font": "segoeuib.ttf",
        "title_font_size": 52,
        "subtitle_font_size": 28,
        "title_color": "white",
        "watermark": "Brand",
    }
    variants = [
        {"output_path": "out-b.mp4"},
        {"output_width": 720},
        {"output_height": 1280},
        {"background_color": "0xFFFFFF"},
        {"title_font": "arial.ttf"},
        {"title_font_size": 60},
        {"subtitle_font_size": 32},
        {"title_color": "yellow"},
        {"watermark": "Other"},
    ]

    base_key = tool.idempotency_key(base)

    for variant in variants:
        assert tool.idempotency_key({**base, **variant}) != base_key


def test_showcase_card_success_payload_includes_output_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"clip")
    output_path = "projects/demo/renders/showcase-card.mp4"

    def fake_run_command(self: ShowcaseCard, cmd: list[str]) -> SimpleNamespace:
        if cmd[0] == "ffprobe":
            return SimpleNamespace(stdout="640,360\n")
        assert cmd[0] == "ffmpeg"
        Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1]).write_bytes(b"card")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(ShowcaseCard, "run_command", fake_run_command)

    result = ShowcaseCard().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "title": "Demo",
            "subtitle": "Clip",
        }
    )

    assert result.success is True
    assert result.data["output_path"] == output_path
    assert result.artifacts == [output_path]
    assert (tmp_path / output_path).exists()
    assert {
        "output",
        "output_path",
        "source_resolution",
        "output_resolution",
        "title",
        "subtitle",
        "letterbox_y_offset",
    } <= set(ShowcaseCard.output_schema["properties"])
    jsonschema.validate(instance=result.data, schema=ShowcaseCard.output_schema)


@pytest.mark.parametrize("output_path", ["card.mp4", "/tmp/card.mp4"])
def test_showcase_card_requires_project_output_path_before_ffmpeg(
    output_path: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"clip")
    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def fake_run_command(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="640,360\n")

    monkeypatch.setattr(ShowcaseCard, "run_command", fake_run_command)

    result = ShowcaseCard().execute(
        {
            "input_path": str(input_path),
            "output_path": output_path,
            "title": "Demo",
        }
    )

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert calls == []
