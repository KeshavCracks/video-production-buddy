"""Phase 2 side-by-side comparison: Phase 1 vs Phase 2 enhanced output.

Runs the talking-head compose handler twice — once with enhance=False
(Phase 1 baseline) and once with enhance=True (Phase 2 enhanced) —
then asserts both outputs exist and reports file size / duration for
manual comparison.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _make_synthetic_footage(path: Path, duration: int = 5) -> Path:
    """Generate a synthetic talking-head-like video with ffmpeg."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=darkblue:s=1280x720:d={duration}:r=30",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:v", "libx264", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(path),
        ],
        capture_output=True, check=True,
    )
    return path


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return float(data.get("format", {}).get("duration", 0))


def _get_file_size_mb(path: str) -> float:
    return Path(path).stat().st_size / (1024 * 1024)


def _project_render_path(filename: str) -> str:
    return f"projects/phase2-comparison/renders/{filename}"


def _absolute_from_workspace(workspace: Path, path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(workspace / candidate)


@pytest.fixture(scope="module")
def comparison_outputs(tmp_path_factory):
    """Run compose handler twice: baseline and enhanced."""
    if not _has_ffmpeg():
        pytest.skip("FFmpeg not available")
    tmp = tmp_path_factory.mktemp("comparison")
    footage = _make_synthetic_footage(tmp / "source_footage.mp4")
    old_cwd = Path.cwd()
    os.chdir(tmp)

    try:
        from tools.video.video_compose import VideoCompose
        from tools.enhancement.face_enhance import FaceEnhance
        from tools.enhancement.color_grade import ColorGrade
        from tools.audio.audio_enhance import AudioEnhance

        results = {}

        # Phase 1 baseline: just encode
        composer = VideoCompose()
        baseline_path = _project_render_path("phase1_baseline.mp4")
        r = composer.execute({
            "operation": "encode",
            "input_path": str(footage),
            "output_path": baseline_path,
            "codec": "libx264",
            "crf": 20,
        })
        assert r.success, f"Baseline encode failed: {r.error}"
        results["baseline"] = _absolute_from_workspace(tmp, baseline_path)

        # Phase 2 enhanced: face -> color -> audio
        current = str(footage)
        enhancements = []

        face = FaceEnhance()
        face_out = _project_render_path("step_face.mp4")
        r = face.execute({
            "input_path": current,
            "output_path": face_out,
            "presets": ["talking_head_standard"],
        })
        if r.success:
            current = _absolute_from_workspace(tmp, r.data["output"])
            enhancements.append("face_enhance:talking_head_standard")

        color = ColorGrade()
        color_out = _project_render_path("step_color.mp4")
        r = color.execute({
            "input_path": current,
            "output_path": color_out,
            "profile": "cinematic_warm",
            "intensity": 0.85,
        })
        if r.success:
            current = _absolute_from_workspace(tmp, r.data["output"])
            enhancements.append("color_grade:cinematic_warm@0.85")

        audio = AudioEnhance()
        audio_out = _project_render_path("step_audio.mp4")
        r = audio.execute({
            "input_path": current,
            "output_path": audio_out,
            "preset": "clean_speech",
        })
        if r.success:
            current = _absolute_from_workspace(tmp, r.data["output"])
            enhancements.append("audio_enhance:clean_speech")

        # Final encode
        enhanced_path = _project_render_path("phase2_enhanced.mp4")
        r = composer.execute({
            "operation": "encode",
            "input_path": current,
            "output_path": enhanced_path,
            "codec": "libx264",
            "crf": 20,
        })
        assert r.success, f"Enhanced encode failed: {r.error}"
        results["enhanced"] = _absolute_from_workspace(tmp, enhanced_path)
        results["enhancements"] = enhancements

        return results
    finally:
        os.chdir(old_cwd)


class TestPhase2Comparison:
    def test_baseline_exists(self, comparison_outputs):
        assert Path(comparison_outputs["baseline"]).exists()

    def test_enhanced_exists(self, comparison_outputs):
        assert Path(comparison_outputs["enhanced"]).exists()

    def test_both_have_valid_duration(self, comparison_outputs):
        base_dur = _get_duration(comparison_outputs["baseline"])
        enh_dur = _get_duration(comparison_outputs["enhanced"])
        assert base_dur > 0
        assert enh_dur > 0
        # Durations should be within 1 second of each other
        assert abs(base_dur - enh_dur) < 1.0, (
            f"Duration mismatch: baseline={base_dur:.1f}s, enhanced={enh_dur:.1f}s"
        )

    def test_enhancements_were_applied(self, comparison_outputs):
        enhancements = comparison_outputs["enhancements"]
        assert len(enhancements) > 0, "No enhancements were applied"

    def test_report(self, comparison_outputs):
        """Print comparison report for manual review."""
        baseline = comparison_outputs["baseline"]
        enhanced = comparison_outputs["enhanced"]

        base_size = _get_file_size_mb(baseline)
        enh_size = _get_file_size_mb(enhanced)
        base_dur = _get_duration(baseline)
        enh_dur = _get_duration(enhanced)
        enhancements = comparison_outputs["enhancements"]

        report = (
            f"\n{'='*60}\n"
            f"  Phase 1 vs Phase 2 Comparison\n"
            f"{'='*60}\n"
            f"  Baseline:  {base_size:.2f} MB, {base_dur:.1f}s\n"
            f"  Enhanced:  {enh_size:.2f} MB, {enh_dur:.1f}s\n"
            f"  Enhancements: {', '.join(enhancements)}\n"
            f"  Baseline path:  {baseline}\n"
            f"  Enhanced path:  {enhanced}\n"
            f"{'='*60}\n"
        )
        print(report)
        # Always passes — this test is for reporting
        assert True
