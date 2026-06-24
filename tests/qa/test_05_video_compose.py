#!/usr/bin/env python3
"""QA Test 05: Video composition, image + mixed audio to video.

Creates a video from static images with audio and optional subtitles.
Uses ffmpeg-generated fixtures if prior test outputs do not exist.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from lib.env_loader import load_env


OUT = os.path.join(os.path.dirname(__file__), "output")
PROJECT_OUT = os.path.join("projects", "qa-video-compose", "renders")
OUTPUTS = [
    "compose_basic.mp4",
    "compose_subtitled.mp4",
    "compose_burn_subs.mp4",
    "compose_encoded.mp4",
    "compose_overlay.mp4",
]


def project_output(name: str) -> str:
    return os.path.join(PROJECT_OUT, name)


def ensure_image(path: str, width: int = 1280, height: int = 720, color: str = "blue") -> None:
    """Generate a test image with ffmpeg if it does not already exist."""
    if os.path.exists(path):
        print(f"  [fixture] Using existing: {path}")
        return
    print(f"  [fixture] Generating {color} image: {path}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d=1",
            "-frames:v",
            "1",
            path,
        ],
        capture_output=True,
        check=True,
    )


def ensure_video(
    path: str,
    duration: int = 5,
    width: int = 1280,
    height: int = 720,
    color: str = "blue",
) -> None:
    """Generate a test video clip with ffmpeg if it does not already exist."""
    if os.path.exists(path):
        print(f"  [fixture] Using existing: {path}")
        return
    print(f"  [fixture] Generating {duration}s {color} video: {path}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d={duration}:r=30",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "30",
            "-keyint_min",
            "30",
            "-c:a",
            "aac",
            "-shortest",
            path,
        ],
        capture_output=True,
        check=True,
    )


def ensure_audio(path: str, duration: int = 5) -> None:
    """Generate a test audio file if it does not already exist."""
    if os.path.exists(path):
        print(f"  [fixture] Using existing: {path}")
        return
    print(f"  [fixture] Generating {duration}s audio: {path}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={duration}",
            "-ar",
            "44100",
            "-ac",
            "2",
            path,
        ],
        capture_output=True,
        check=True,
    )


def ensure_subtitle(path: str) -> None:
    """Write a minimal SRT subtitle file."""
    if os.path.exists(path):
        print(f"  [fixture] Using existing: {path}")
        return
    print(f"  [fixture] Generating subtitle: {path}")
    with open(path, "w", encoding="utf-8") as file:
        file.write("1\n00:00:00,000 --> 00:00:03,000\nWelcome to Video Production Buddy\n\n")
        file.write("2\n00:00:03,000 --> 00:00:06,000\nBuilding amazing videos with AI\n\n")
        file.write("3\n00:00:06,000 --> 00:00:10,000\nLet's see what we can create\n\n")


def _prepare_fixtures() -> tuple[str, str, str, str]:
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PROJECT_OUT, exist_ok=True)

    clip_a = os.path.join(OUT, "compose_clip_a.mp4")
    clip_b = os.path.join(OUT, "compose_clip_b.mp4")
    audio_mix = os.path.join(OUT, "compose_audio.wav")
    subtitle = os.path.join(OUT, "compose_subs.srt")

    # Use 10s clips so -c copy has keyframe headroom.
    ensure_video(clip_a, duration=10, color="darkblue")
    ensure_video(clip_b, duration=10, color="darkgreen")
    ensure_audio(audio_mix, duration=10)
    ensure_subtitle(subtitle)
    return clip_a, clip_b, audio_mix, subtitle


def _log_result(label: str, result) -> None:
    print(f"\n--- {label} ---")
    print(f"Success: {result.success}, Duration: {result.duration_seconds:.2f}s")
    if result.error:
        print(f"Error: {result.error}")
    if result.artifacts:
        print(f"Artifacts: {result.artifacts}")


def _probe_outputs(outputs: list[str]) -> None:
    print("\n--- Output inspection ---")
    for name in outputs:
        path = project_output(name)
        if not os.path.exists(path):
            print(f"\n[{name}] FILE NOT FOUND")
            continue
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
        )
        info = json.loads(probe.stdout)
        fmt = info.get("format", {})
        video = {}
        audio = {}
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video" and not video:
                video = stream
            elif stream.get("codec_type") == "audio" and not audio:
                audio = stream
        print(
            f"\n[{name}]"
            f" Duration: {fmt.get('duration', '?')}s"
            f" | Video: {video.get('width', '?')}x{video.get('height', '?')}"
            f" {video.get('codec_name', '?')}@{video.get('r_frame_rate', '?')}fps"
            f" | Audio: {audio.get('codec_name', '?')}"
            f" {audio.get('sample_rate', '?')}Hz"
            f" {audio.get('channels', '?')}ch"
            f" | Size: {os.path.getsize(path)} bytes"
        )


def _run_video_compose_qa():
    load_env()
    from tools.video.video_compose import VideoCompose

    clip_a, clip_b, audio_mix, subtitle = _prepare_fixtures()
    tool = VideoCompose()
    print(f"Tool status: {tool.get_status()}")

    r1 = tool.execute(
        {
            "operation": "compose",
            "edit_decisions": {
                "cuts": [
                    {"source": clip_a, "in_seconds": 0, "out_seconds": 5},
                    {"source": clip_b, "in_seconds": 0, "out_seconds": 5},
                ],
            },
            "audio_path": audio_mix,
            "output_path": project_output("compose_basic.mp4"),
        }
    )
    _log_result("Test 1: Compose from edit_decisions", r1)

    r2 = tool.execute(
        {
            "operation": "compose",
            "edit_decisions": {
                "cuts": [
                    {"source": clip_a, "in_seconds": 0, "out_seconds": 5},
                    {"source": clip_b, "in_seconds": 0, "out_seconds": 5},
                ],
            },
            "audio_path": audio_mix,
            "subtitle_path": subtitle,
            "subtitle_style": {
                "font": "Arial",
                "font_size": 24,
                "primary_color": "&HFFFFFF",
                "outline_color": "&H000000",
                "outline_width": 2,
                "margin_v": 40,
            },
            "output_path": project_output("compose_subtitled.mp4"),
        }
    )
    _log_result("Test 2: Compose with subtitles", r2)

    r3 = tool.execute(
        {
            "operation": "burn_subtitles",
            "input_path": clip_a,
            "subtitle_path": subtitle,
            "subtitle_style": {
                "font": "Arial",
                "font_size": 20,
                "bold": True,
            },
            "output_path": project_output("compose_burn_subs.mp4"),
        }
    )
    _log_result("Test 3: Burn subtitles standalone", r3)

    r4 = tool.execute(
        {
            "operation": "encode",
            "input_path": clip_a,
            "profile": "youtube_landscape",
            "crf": 20,
            "preset": "fast",
            "output_path": project_output("compose_encoded.mp4"),
        }
    )
    _log_result("Test 4: Re-encode with profile", r4)

    overlay_image = os.path.join(OUT, "compose_overlay.png")
    ensure_image(overlay_image, width=200, height=200, color="red")
    r5 = tool.execute(
        {
            "operation": "overlay",
            "input_path": clip_a,
            "overlays": [
                {
                    "asset_path": overlay_image,
                    "x": 50,
                    "y": 50,
                    "width": 150,
                    "height": 150,
                    "start_seconds": 1,
                    "end_seconds": 4,
                    "opacity": 0.8,
                },
            ],
            "output_path": project_output("compose_overlay.mp4"),
        }
    )
    _log_result("Test 5: Overlay image on video", r5)

    _probe_outputs(OUTPUTS)
    print("\n=== VIDEO COMPOSE TEST COMPLETE ===")
    return [r1, r2, r3, r4, r5], OUTPUTS


def test_video_compose_qa_script_succeeded() -> None:
    results, outputs = _run_video_compose_qa()
    assert all(result.success for result in results), [
        result.error for result in results if not result.success
    ]
    for name in outputs:
        assert os.path.exists(project_output(name)), f"missing QA output: {name}"
