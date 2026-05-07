"""Beat / drop detector for music tracks.

Used by:
  - asset-director.md `library_locked` workflow — verify declared drop_seconds
    against what the audio actually contains
  - asset-director.md `search_align` workflow — find the bass drop in a stock
    music track so it can be aligned to production_bible.narrative.tension_peak_at_seconds
  - CLI ad-hoc:
        python -m lib.beat_detector path/to/track.mp3

Two paths exist:

1. **Full analysis (BPM + downbeats + drops):** requires `librosa` and `numpy`.
   Install with `pip install librosa`. Lazy-imported — module loads even
   without librosa.

2. **Loudness-peak fallback (drops only, no tempo):** uses ffmpeg `astats`
   to find the loudest moments in the track. Works without librosa but
   produces no BPM or downbeat data.

When librosa is unavailable, `detect_bpm` and `detect_downbeats` return None /
empty list with a documented reason; `detect_drops` falls back to ffmpeg.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _try_import_librosa():
    """Lazy import. Returns (librosa, numpy) or (None, None) when missing."""
    try:
        import librosa  # type: ignore[import-not-found]
        import numpy as np  # type: ignore[import-not-found]
        return librosa, np
    except ImportError:
        return None, None


def detect_bpm(audio_path: str | Path) -> float | None:
    """Estimate BPM using librosa.beat.beat_track.

    Returns None when librosa is unavailable or the track is too short to
    produce a confident estimate.
    """
    librosa, np = _try_import_librosa()
    if librosa is None:
        return None
    path = str(audio_path)
    try:
        y, sr = librosa.load(path, sr=None, mono=True)
    except Exception:
        return None
    if y.size == 0:
        return None
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    except Exception:
        return None
    # tempo may be ndarray of shape (1,) or scalar; coerce to float
    return float(tempo)


def detect_downbeats(
    audio_path: str | Path, bpm: float | None = None
) -> list[float]:
    """Return beat-onset timestamps (seconds) using librosa.

    Returns an empty list when librosa is unavailable or no beats are found.
    The optional `bpm` hint is accepted for API symmetry but currently
    ignored — librosa.beat.beat_track derives its own tempo internally.
    """
    librosa, np = _try_import_librosa()
    if librosa is None:
        return []
    path = str(audio_path)
    try:
        y, sr = librosa.load(path, sr=None, mono=True)
        _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        if beat_frames is None or len(beat_frames) == 0:
            return []
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        return [float(t) for t in beat_times]
    except Exception:
        return []


def _ffmpeg_loudness_peaks(audio_path: str | Path, top_k: int = 3) -> list[float]:
    """Find the loudest moments via ffmpeg `astats` over fixed windows.

    Walks the track in 1-second windows, measures each window's RMS energy,
    returns the top-k window center times. Coarse but ffmpeg-only.

    Returns an empty list when ffmpeg is unavailable or fails.
    """
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        return []
    path = str(audio_path)

    # Probe duration
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, check=True, timeout=30,
        )
        duration = float(proc.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
        return []
    if duration <= 0:
        return []

    # Run astats with metadata on 1-second windows
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-af", "astats=metadata=1:reset=1,ametadata=mode=print:key=lavfi.astats.Overall.RMS_level",
             "-f", "null", "-"],
            capture_output=True, text=True, check=True, timeout=120,
        )
        text = proc.stderr
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    # Parse the ametadata-print log. Lines look like:
    #   "[Parsed_ametadata_N @ 0xADDR] frame:K  pts:T  pts_time:S.MS"
    #   "[Parsed_ametadata_N @ 0xADDR] lavfi.astats.Overall.RMS_level=-12.34"
    # Bucket per-frame RMS into 1-second windows, take max RMS per window,
    # then pick the loudest windows separated by at least 2 seconds.
    rms_per_window: dict[int, float] = {}
    last_t: float | None = None

    def _strip_prefix(line: str) -> str:
        # Drop the leading "[Parsed_ametadata_N @ 0xADDR] " bracket if present
        if line.startswith("[") and "] " in line:
            return line.split("] ", 1)[1]
        return line

    for raw in text.splitlines():
        line = _strip_prefix(raw.strip())
        if line.startswith("frame:") and "pts_time:" in line:
            try:
                last_t = float(line.split("pts_time:")[1].split()[0])
            except (IndexError, ValueError):
                last_t = None
        elif line.startswith("lavfi.astats.Overall.RMS_level=") and last_t is not None:
            try:
                rms = float(line.split("=", 1)[1])
                bucket = int(last_t)
                if bucket not in rms_per_window or rms > rms_per_window[bucket]:
                    rms_per_window[bucket] = rms
            except (IndexError, ValueError):
                continue

    if not rms_per_window:
        return []

    # Pick top-k loudest windows, enforcing min 2s separation.
    ranked = sorted(rms_per_window.items(), key=lambda kv: kv[1], reverse=True)
    picked: list[float] = []
    for t_int, _rms in ranked:
        if all(abs(t_int - p) >= 2 for p in picked):
            picked.append(float(t_int))
        if len(picked) >= max(1, top_k):
            break
    return [round(t, 3) for t in picked]


def detect_drops(audio_path: str | Path, top_k: int = 3) -> list[float]:
    """Locate bass-drop / climactic-loudness candidate timestamps (seconds).

    Prefers a librosa-based approach (onset_strength + RMS energy peaks) when
    available; falls back to ffmpeg `astats` window scan when librosa is not
    installed.

    Returns an ordered list (loudest first), empty if detection fails.
    """
    librosa, np = _try_import_librosa()
    if librosa is None or np is None:
        return _ffmpeg_loudness_peaks(audio_path, top_k=top_k)

    path = str(audio_path)
    try:
        y, sr = librosa.load(path, sr=None, mono=True)
    except Exception:
        return _ffmpeg_loudness_peaks(audio_path, top_k=top_k)
    if y.size == 0:
        return []

    # RMS envelope at hop_length=2048 (~46ms at 44.1kHz)
    try:
        rms = librosa.feature.rms(y=y, frame_length=4096, hop_length=2048)[0]
        times = librosa.frames_to_time(
            np.arange(len(rms)), sr=sr, hop_length=2048
        )
        # Smooth RMS to focus on sustained loud segments (not single transients)
        kernel = max(1, int(sr / 2048))  # ~1 second smoothing
        if kernel > 1 and len(rms) >= kernel:
            smoothed = np.convolve(rms, np.ones(kernel) / kernel, mode="same")
        else:
            smoothed = rms
        # Peak picking: pre/post window 1.5s, threshold = mean + 1*std
        threshold = float(smoothed.mean() + smoothed.std())
        peak_idx = librosa.util.peak_pick(
            smoothed,
            pre_max=int(1.5 * sr / 2048),
            post_max=int(1.5 * sr / 2048),
            pre_avg=int(1.5 * sr / 2048),
            post_avg=int(1.5 * sr / 2048),
            delta=max(threshold * 0.1, 1e-6),
            wait=int(2 * sr / 2048),  # min 2s between peaks
        )
        if len(peak_idx) == 0:
            return _ffmpeg_loudness_peaks(audio_path, top_k=top_k)
        # Rank by smoothed RMS at the peak, take top-k
        ranked = sorted(peak_idx, key=lambda i: smoothed[i], reverse=True)[: max(1, top_k)]
        return [round(float(times[i]), 3) for i in ranked]
    except Exception:
        return _ffmpeg_loudness_peaks(audio_path, top_k=top_k)


def analyze(audio_path: str | Path, top_k_drops: int = 3) -> dict[str, Any]:
    """Combined report: BPM + downbeats + drops + provenance flags."""
    librosa, _ = _try_import_librosa()
    backend = "librosa" if librosa is not None else "ffmpeg-fallback"
    return {
        "audio_path": str(audio_path),
        "backend": backend,
        "bpm": detect_bpm(audio_path),
        "downbeats": detect_downbeats(audio_path) if librosa is not None else [],
        "drop_seconds": detect_drops(audio_path, top_k=top_k_drops),
        "notes": [
            "BPM and downbeats require librosa (pip install librosa)."
            if librosa is None
            else "Full analysis (librosa) — BPM, downbeats, drops detected.",
            "drop_seconds are loudness peaks; for explicit musical drops, "
            "compare to a sidecar timing file or use a beat-aware drop detector.",
        ],
    }


def _cli(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python -m lib.beat_detector <audio-path>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"error: audio file not found: {path}", file=sys.stderr)
        return 2
    report = analyze(path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
