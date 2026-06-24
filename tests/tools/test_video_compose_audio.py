import shutil
from pathlib import Path

import pytest

from tools.base_tool import ToolResult
from tools.video.video_compose import VideoCompose


@pytest.fixture
def project_renders_dir(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    project_dir = repo_root / "projects" / f"pytest-video-compose-audio-{tmp_path.name}"
    shutil.rmtree(project_dir, ignore_errors=True)
    renders_dir = project_dir / "renders"
    yield renders_dir
    shutil.rmtree(project_dir, ignore_errors=True)


def test_video_compose_external_audio_is_encoded_stereo(
    tmp_path,
    monkeypatch,
    project_renders_dir,
):
    source = tmp_path / "source.mp4"
    audio = tmp_path / "mix.wav"
    output = project_renders_dir / "final.mp4"
    source.write_bytes(b"video")
    audio.write_bytes(b"audio")

    composer = VideoCompose()
    monkeypatch.setattr(composer, "_has_audio_stream", lambda _path: False)

    commands: list[list[str]] = []

    def capture_command(cmd):
        commands.append(list(cmd))
        return ToolResult(success=True, data={})

    monkeypatch.setattr(composer, "run_command", capture_command)

    result = composer._compose(
        {
            "edit_decisions": {
                "version": "1.0",
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": str(source),
                        "in_seconds": 0,
                        "out_seconds": 1,
                    }
                ],
            },
            "audio_path": str(audio),
            "output_path": str(output),
            "profile": "tiktok",
        }
    )

    assert result.success
    final_cmd = commands[-1]
    assert final_cmd[0] == "ffmpeg"
    assert final_cmd[final_cmd.index("-c:a") + 1] == "aac"
    assert final_cmd[final_cmd.index("-ac") + 1] == "2"
