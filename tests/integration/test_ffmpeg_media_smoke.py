from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.qa, pytest.mark.ffmpeg]


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg/ffprobe are required for the media smoke test")


def test_ffmpeg_smoke_creates_probeable_video(tmp_path: Path) -> None:
    _require_ffmpeg()
    output = tmp_path / "smoke.mp4"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=24:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height",
            "-of",
            "default=nw=1",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert "codec_name=" in probe.stdout
    assert "width=320" in probe.stdout
    assert "height=180" in probe.stdout
