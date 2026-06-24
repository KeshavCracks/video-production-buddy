#!/usr/bin/env python3
"""QA Test 06: Video stitch, concat/crossfade/fade/spatial layouts.

Tests the VideoStitch tool with both matching and mismatched clips.
Generates fixtures via ffmpeg, no API keys needed.
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
PROJECT_OUT = os.path.join("projects", "qa-video-stitch", "renders")
OUTPUTS = [
    "stitch_cut.mp4",
    "stitch_crossfade.mp4",
    "stitch_fadeblack.mp4",
    "stitch_normalized.mp4",
    "stitch_preview.mp4",
    "stitch_side_by_side.mp4",
    "stitch_pip.mp4",
    "stitch_vstack.mp4",
]


def project_output(name: str) -> str:
    return os.path.join(PROJECT_OUT, name)


def ensure_video(
    path: str,
    duration: int = 4,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    color: str = "blue",
) -> None:
    """Generate a test video clip with ffmpeg."""
    if os.path.exists(path):
        print(f"  [fixture] Using existing: {path}")
        return
    print(f"  [fixture] Generating {duration}s {width}x{height}@{fps}fps {color}: {path}")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s={width}x{height}:d={duration}:r={fps}",
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
            str(fps),
            "-keyint_min",
            str(fps),
            "-c:a",
            "aac",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-shortest",
            path,
        ],
        capture_output=True,
        check=True,
    )


def _prepare_fixtures() -> tuple[str, str, str, str]:
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PROJECT_OUT, exist_ok=True)

    clip_1 = os.path.join(OUT, "stitch_clip1.mp4")
    clip_2 = os.path.join(OUT, "stitch_clip2.mp4")
    clip_3 = os.path.join(OUT, "stitch_clip3.mp4")
    clip_mismatch = os.path.join(OUT, "stitch_clip_mismatch.mp4")

    ensure_video(clip_1, duration=4, color="darkblue")
    ensure_video(clip_2, duration=4, color="darkgreen")
    ensure_video(clip_3, duration=4, color="darkred")
    ensure_video(clip_mismatch, duration=4, width=640, height=480, fps=24, color="purple")
    return clip_1, clip_2, clip_3, clip_mismatch


def _log_validate_result(label: str, result) -> None:
    print(f"\n--- {label} ---")
    print(f"Success: {result.success}")
    if result.data:
        print(f"  Compatible: {result.data.get('compatible')}")
        print(f"  Total duration: {result.data.get('total_duration')}s")
        mismatches = result.data.get("mismatches", [])
        print(f"  Mismatches: {len(mismatches)}")
        for mismatch in mismatches:
            print(f"  Clip[{mismatch['clip_index']}]: {', '.join(mismatch['differences'])}")
    if result.error:
        print(f"Error: {result.error}")


def _log_render_result(label: str, result) -> None:
    print(f"\n--- {label} ---")
    print(f"Success: {result.success}, Duration: {result.duration_seconds:.2f}s")
    if result.data:
        details = []
        if "duration" in result.data:
            details.append(f"Duration: {result.data.get('duration')}s")
        if "method" in result.data:
            details.append(f"Method: {result.data.get('method')}")
        if "auto_normalized" in result.data:
            details.append(f"Normalized: {result.data.get('auto_normalized')}")
        if "preview_resolution" in result.data:
            details.append(f"Preview resolution: {result.data.get('preview_resolution')}")
        if "layout" in result.data:
            details.append(f"Layout: {result.data.get('layout')}")
        if details:
            print(f"  {', '.join(details)}")
    if result.error:
        print(f"Error: {result.error}")


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
            f" {video.get('codec_name', '?')}"
            f" | Audio: {audio.get('codec_name', '?')}"
            f" | Size: {os.path.getsize(path)} bytes"
        )


def _run_video_stitch_qa():
    load_env()
    from tools.video.video_stitch import VideoStitch

    clip_1, clip_2, clip_3, clip_mismatch = _prepare_fixtures()
    tool = VideoStitch()
    print(f"Tool status: {tool.get_status()}")

    r1 = tool.execute({"operation": "validate", "clips": [clip_1, clip_2, clip_3]})
    _log_validate_result("Test 1: Validate matching clips", r1)

    r2 = tool.execute({"operation": "validate", "clips": [clip_1, clip_mismatch]})
    _log_validate_result("Test 2: Validate mismatched clips", r2)

    r3 = tool.execute(
        {
            "operation": "stitch",
            "clips": [clip_1, clip_2],
            "transition": "cut",
            "output_path": project_output("stitch_cut.mp4"),
        }
    )
    _log_render_result("Test 3: Cut stitch (2 clips)", r3)

    r4 = tool.execute(
        {
            "operation": "stitch",
            "clips": [clip_1, clip_2],
            "transition": "crossfade",
            "transition_duration": 1.0,
            "output_path": project_output("stitch_crossfade.mp4"),
        }
    )
    _log_render_result("Test 4: Crossfade stitch (2 clips)", r4)

    r5 = tool.execute(
        {
            "operation": "stitch",
            "clips": [clip_1, clip_2, clip_3],
            "transition": "fade",
            "transition_duration": 0.5,
            "output_path": project_output("stitch_fadeblack.mp4"),
        }
    )
    _log_render_result("Test 5: Fade through black (3 clips)", r5)

    r6 = tool.execute(
        {
            "operation": "stitch",
            "clips": [clip_1, clip_mismatch],
            "transition": "cut",
            "auto_normalize": True,
            "output_path": project_output("stitch_normalized.mp4"),
        }
    )
    _log_render_result("Test 6: Stitch mismatched clips (auto_normalize)", r6)

    r7 = tool.execute(
        {
            "operation": "preview_stitch",
            "clips": [clip_1, clip_2, clip_3],
            "transition": "cut",
            "output_path": project_output("stitch_preview.mp4"),
        }
    )
    _log_render_result("Test 7: Preview stitch", r7)

    r8 = tool.execute(
        {
            "operation": "spatial",
            "clips": [clip_1, clip_2],
            "layout": "side_by_side",
            "output_path": project_output("stitch_side_by_side.mp4"),
        }
    )
    _log_render_result("Test 8: Spatial side-by-side", r8)

    r9 = tool.execute(
        {
            "operation": "spatial",
            "clips": [clip_1, clip_2],
            "layout": "picture_in_picture",
            "pip_position": "bottom_right",
            "pip_scale": 0.3,
            "pip_margin": 20,
            "output_path": project_output("stitch_pip.mp4"),
        }
    )
    _log_render_result("Test 9: Spatial PIP (bottom-right)", r9)

    r10 = tool.execute(
        {
            "operation": "spatial",
            "clips": [clip_1, clip_2],
            "layout": "vertical_stack",
            "output_path": project_output("stitch_vstack.mp4"),
        }
    )
    _log_render_result("Test 10: Spatial vertical stack", r10)

    _probe_outputs(OUTPUTS)
    print("\n=== VIDEO STITCH TEST COMPLETE ===")
    return [r1, r2, r3, r4, r5, r6, r7, r8, r9, r10], OUTPUTS


def test_video_stitch_qa_script_succeeded() -> None:
    results, outputs = _run_video_stitch_qa()
    assert all(result.success for result in results), [
        result.error for result in results if not result.success
    ]
    for name in outputs:
        assert os.path.exists(project_output(name)), f"missing QA output: {name}"
