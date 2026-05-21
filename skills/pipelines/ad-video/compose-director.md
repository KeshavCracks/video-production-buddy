# Compose Director — Ad Video Pipeline

## When to Use

You receive `edit_decisions`, `asset_manifest`, and `EP_STATE` and render the final video outputs. You render the primary 16:9 video first, then all opted-in derivative variants as separate output files.

## CRITICAL Pre-Render Checks

**Before any render begins, run ALL of these checks. Do not skip any.**

### Check -1: Planning chain freshness

Load `production_bible`, `script`, and `scene_plan` from the required project
artifacts, then run `ad_video_planning_chain_check` before render.
Do not treat missing planning artifacts as permission to skip this gate. If any input is
missing, stale, schema-invalid, or the gate fails, **ABORT** and return to the
stale or unthreaded planning stage. Do not render an ad whose selected
`trend_alignment` never reached script refs or scene trend refs.

```python
from tools.validation.ad_video_planning_chain_check import AdVideoPlanningChainCheck

planning_gate = AdVideoPlanningChainCheck().execute({
    "production_bible": production_bible,
    "script": script,
    "scene_plan": scene_plan,
})
if not planning_gate.success:
    raise RuntimeError(f"Planning chain gate failed: {planning_gate.error}")
```

### Check 0: Remotion profile (aspect ratio)

The `Explainer` composition in `Root.tsx` defaults to **1920×1080** regardless of any `width`/`height` fields in the props JSON. To get the correct output resolution you MUST pass `"profile"` to the `video_compose` call:

| `EP_STATE.aspect_ratio_primary` | `profile` value |
|---|---|
| `"9:16"` (TikTok / Reels / Shorts) | `"tiktok"` |
| `"16:9"` (YouTube landscape) | `"youtube_landscape"` |
| `"1:1"` (Instagram feed) | `"instagram_feed"` |

If you omit `profile`, Remotion silently renders 1920×1080 regardless of what the scene plan says. Always set it.

### Check 1: render_runtime verification
```
EP_STATE.style_mode == "animated" → render_runtime ∈ {remotion, hyperframes}
EP_STATE.style_mode == "cinematic" → render_runtime == ffmpeg
```

The user's choice (Remotion vs. HyperFrames for animated mode) was locked at the proposal stage via the `render_runtime_selection` decision in `decision_log`. Compose MUST route by `render_runtime` — do NOT fall back to the tool's legacy default, do NOT silently pick Remotion, do NOT treat HyperFrames as "basically Remotion." Each engine has a distinct renderer invocation (see Primary Render section).

If `EP_STATE.render_runtime` is unset or does not match the `style_mode` constraint above, OR if `production_proposal.render_runtime` does not match `EP_STATE.render_runtime`: **ABORT. Alert EP. Do not render.** A runtime mismatch is a CRITICAL failure — this is the silent runtime swap prevention.

### Check 2: Asset file existence
For every asset reference in `edit_decisions.cuts[]` and `edit_decisions.audio.narration.segments[]`:
- `cuts[].source` resolves to an asset_manifest ID, file path, or `remotion:<component>`
- `audio.narration.segments[].asset_id` resolves to an audio file in `asset_manifest`
If any file missing: **ABORT. Alert EP with missing file list.**

### Check 3: Derivative readiness
If `derivative_variants` is non-empty:
- Every scene in `edit_decisions` has `crop_regions` in `scene_plan`
- `edit_decisions.derivative_specs` is present
If any scene is missing crop_regions: **ABORT. Send back to scene_plan director.**

### Check 4a: Scene fidelity (closed-enum + motion vocabulary)

Before any render, validate that every cut in `edit_decisions.cuts[]` uses a `type` registered in `remotion-composer/scene_type_registry.json` and that any declared `motion_specs` are supported by the chosen component:

```python
from tools.validation.scene_fidelity_check import check_plan, load_registry
registry = load_registry()
report = check_plan(edit_decisions, registry)
if not report["ok"]:
    raise RuntimeError(f"Scene fidelity failed: {report['issues']}")
```

If this fails, ABORT. Send the issues back to scene-director — do NOT silently degrade by rendering unrecognized cuts as text_cards.

### Check 4b: KVM coverage (when production_bible defines KVMs)

```python
from tools.validation.scene_fidelity_check import check_kvm_coverage
kvm_report = check_kvm_coverage(production_bible, scene_plan)
if not kvm_report["ok"]:
    raise RuntimeError(f"Uncovered KVMs: {kvm_report['issues']}")
```

If a mandatory KVM is not fulfilled by any scene, ABORT. The emotional climax of the ad cannot be silently dropped.

### Check 4: Subtitle file (opt-in)
- Read `edit_decisions.subtitles.enabled`. If `false` (the default): subtitles are NOT burnt in — skip this check and omit `subtitle_path` from the `video_compose` call.
- If `true`: verify `asset_manifest` contains a subtitle file path and that file exists on disk. If missing: **ABORT. Alert EP.**

## Primary Render (at `EP_STATE.aspect_ratio_primary`)

The primary render resolution is determined by `EP_STATE.aspect_ratio_primary` (locked at proposal):
- `"16:9"` → output 1920×1080
- `"9:16"` → output 1080×1920

Use the `video_compose` and `audio_mixer` tools from the tool registry. Do NOT construct raw ffmpeg or npx commands directly — the tool handles normalization, concat, encoding, and runtime governance internally.

### Pre-Mix Validation (mandatory before Step 1)

Before calling `audio_mixer`, verify three things. These checks catch the class of bug where a corrupt TTS file or a broken sidechaincompress silently truncates narration — and the render proceeds with no visible error.

**1. TTS format check.** For each narration segment file, run:

```bash
ffprobe -v quiet -print_format json -show_streams <file>
```

Verify `streams[0].codec_name` is `"mp3"` (not `"pcm_s16le"`, `"wav"`, or empty). If WAV content is detected in a `.mp3` file, call `cosyvoice_tts` again with `"format": "mp3"` — the tool's `_ensure_audio_format` helper will transcode on output. Do **not** pass a WAV-content `.mp3` file to `audio_mixer`; the sidechaincompress filter will produce corrupt or truncated audio.

**2. total_duration_seconds present.** Verify `edit_decisions.total_duration_seconds` is set to a positive number. If absent, compute it as:

```python
total_duration = max(cut["out_seconds"] for cut in edit_decisions["cuts"])
```

Log a warning and set it explicitly. This field is required for the post-mix duration assertion below and for the `_run_final_review` audio truncation check in `video_compose`.

**3. Post-mix duration assertion.** After `audio_mixer.execute(...)` returns, read `result.data["duration_seconds"]`. Assert it is within ±5% of `edit_decisions.total_duration_seconds`:

```python
target = edit_decisions["total_duration_seconds"]
actual = result.data.get("duration_seconds")
if actual and abs(actual - target) / target > 0.05:
    raise RuntimeError(
        f"Mix duration {actual:.2f}s is more than 5% off target {target:.2f}s "
        f"({abs(actual - target) / target:.0%} drift). "
        "Check for truncated TTS segments or broken filter graph."
    )
```

If the assertion fails: surface a structured blocker. Alert EP with the gap. Do **not** proceed to `video_compose`.

### Step 1: Pre-mix audio via audio_mixer

Before calling `video_compose`, produce a single pre-mixed audio track (narration + ducked music):

```python
from styles.playbook_loader import load_playbook
from tools.audio.audio_mixer import AudioMixer

loaded_playbook = load_playbook(EP_STATE["playbook"])
music_vol = loaded_playbook["audio"]["music_volume"]  # e.g. 0.30 for ad-brand

# Build tracks list: one speech track per narration segment (with start offset),
# plus one music track. AudioMixer.full_mix handles ducking internally.
tracks = []
for seg in edit_decisions["audio"]["narration"]["segments"]:
    tracks.append({
        "path": asset_manifest_lookup(seg["asset_id"]),  # resolve asset_id → file path
        "role": "speech",
        "start_seconds": seg["start_seconds"],
        "volume": 1.0,
    })
tracks.append({
    "path": asset_manifest_lookup("m01"),  # music asset
    "role": "music",
    "volume": music_vol,
})

mixer = AudioMixer()
# audio_contract is locked at proposal stage in production_proposal.json /
# production_bible.json. Always pass target_lufs and target_total_duration_seconds
# explicitly — do not rely on legacy defaults.
audio_contract = (
    EP_STATE.get("audio_contract")
    or production_bible.get("audio_contract")
    or {}
)
target_lufs = audio_contract.get("target_lufs", -14)  # TikTok/Reels/Shorts default
result = mixer.execute({
    "operation": "full_mix",
    "tracks": tracks,
    "music_volume_schedule": (
        edit_decisions.get("audio", {}).get("music", {}).get("volume_schedule", [])
    ),
    "ducking": {
        "enabled": True,
        "music_volume_during_speech": music_vol * 0.126,
        "attack_ms": 8,
        "release_ms": 300,
    },
    "target_lufs": target_lufs,
    "target_total_duration_seconds": edit_decisions["total_duration_seconds"],
    "output_path": "assets/audio/mixed_audio.mp3",
})
if result.error:
    raise RuntimeError(f"audio_mixer failed: {result.error}")
```

### Step 2: Render primary 16:9 via video_compose

`video_compose(operation="render")` handles: per-clip normalization (scale/fps/yuv420p), concat, optional subtitle burn, profile scaling, and runtime governance (it aborts on any render_runtime mismatch — no silent swap).

```python
import json
from pathlib import Path
from tools.video.video_compose import VideoCompose

def load_json(path: str) -> dict:
    with open(Path(path), encoding="utf-8") as f:
        return json.load(f)

edit_decisions = load_json("projects/<name>/artifacts/edit_decisions.json")
asset_manifest = load_json("projects/<name>/artifacts/asset_manifest.json")

composer = VideoCompose()
result = composer.execute({
    "operation": "render",
    "render_runtime": EP_STATE["render_runtime"],  # "ffmpeg" for cinematic; "remotion"/"hyperframes" for animated
    "edit_decisions": edit_decisions,
    "asset_manifest": asset_manifest,
    "audio_path": "assets/audio/mixed_audio.aac",
    # Include subtitle_path only if edit_decisions.subtitles.enabled == True:
    "subtitle_path": "assets/subtitles.srt",
    "options": {
        "subtitle_burn": EP_STATE.get("subtitle_burn", False),
        # ── IMPORTANT: Use ASS format subtitles, not SRT ────────────────────
        # When using ffmpeg's subtitles= filter, ALL font sizes and margins
        # are interpreted relative to PlayResX/PlayResY in the ASS header.
        # SRT files do NOT carry PlayRes, so libass falls back to its internal
        # default (~384x288), causing all sizes to be scaled up massively and
        # margins to be placed in completely wrong positions.
        #
        # ALWAYS generate an ASS file (not SRT) with explicit PlayResX/PlayResY
        # matching the video resolution. Then Fontsize and MarginV are in
        # actual pixels of the video frame.
        #
        # ASS template for 16:9 (1920x1080): Fontsize=24, MarginV=20
        # ASS template for 9:16 (1080x1920): Fontsize=28, MarginV=160
        # Alignment=2 = bottom-center (ASS numpad value).
        # BorderStyle=1 = outline+shadow only, no background box.
        #
        # See asset-director.md Step 3 for how to generate the ASS file.
    },
    "output_path": "renders/output_16x9.mp4",
})
if result.error:
    raise RuntimeError(f"video_compose primary render failed: {result.error}")
```

**HyperFrames note:** when `render_runtime == "hyperframes"`, `video_compose` routes internally to the HyperFrames engine (HTML/GSAP motion primitives). Do NOT attempt to construct a separate HyperFrames invocation — pass `render_runtime="hyperframes"` and let the tool route correctly.

### Post-primary probe

After `video_compose` returns, verify via `result.data`:
- `duration_seconds` within ±5% of `edit_decisions.total_duration_seconds`
- `resolution` matches `EP_STATE.aspect_ratio_primary` (1920×1080 for 16:9; 1080×1920 for 9:16)
- `audio_channels` == 2 (stereo)

### Check 5: Post-render loudness

Use `ffmpeg -af volumedetect` to measure mean dB on the final output and compare to `audio_contract.target_lufs`. Loudness must be within ±2 LUFS of target:

```python
import re, subprocess
proc = subprocess.run(
    ["ffmpeg", "-i", str(output_path), "-af", "volumedetect", "-f", "null", "/dev/null"],
    capture_output=True, text=True
)
match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", proc.stderr)
if not match:
    raise RuntimeError("Could not measure loudness on final output")
mean_db = float(match.group(1))
# Approximate LUFS ≈ mean_volume for short content with loudnorm applied
if abs(mean_db - target_lufs) > 2.5:
    raise RuntimeError(
        f"Loudness {mean_db:.1f} dB is more than 2.5 dB off target {target_lufs} LUFS. "
        "Re-mix and re-encode with the correct target_lufs."
    )
```

### Check 6: Subtitle no-overlap (when subtitles enabled)

Parse the ASS file produced by the asset-director and assert no two `Dialogue:` lines overlap in time. Two cues that overlap will display simultaneously and confuse viewers.

If any check fails: ABORT. Alert EP with the mismatch. Do not proceed to derivatives.

## Derivative Rendering Loop

For each variant in `EP_STATE.derivative_variants`:

**Before each aspect-ratio derivative render:** verify `crop_regions` for that
aspect ratio are present on every scene. If any scene is missing the required
aspect-ratio crop: ABORT. Send back to scene_plan director. Duration-only
variants (`15s`, `15s_short`) do not require crop regions unless combined with
an aspect-ratio derivative. **This check is NOT skipped for subsequent
aspect-ratio derivatives.**

Call `audio_mixer` once per variant to produce a variant-appropriate mix (15s variants use shorter music trim). Then call `video_compose` with variant-specific parameters:

**9:16 variant:** pass `crop_filter: "crop=608:1080:656:0"` in options, output to `renders/output_9x16.mp4`.

**1:1 variant:** pass `crop_filter: "crop=1080:1080:420:0"` in options, output to `renders/output_1x1.mp4`.

**15s short cut:** filter `edit_decisions.cuts` to only `core: true` scenes. Verify `sum(core_scene_durations) ≤ 15.0s` before calling. Output to `renders/output_15s.mp4`.

**Cross-product derivatives** (15s × 9:16 or 15s × 1:1): apply both the 15s scene filter and the crop filter in the same `video_compose` call. Output to `renders/output_15s_9x16.mp4` / `renders/output_15s_1x1.mp4`.

## Render Report Format

```json
{
  "version": "1.0",
  "renderer": "remotion",
  "outputs": [
    {
      "variant": "16:9",
      "path": "renders/output_16x9.mp4",
      "format": "mp4",
      "duration_seconds": 59.8,
      "resolution": "1920x1080",
      "audio_channels": 2,
      "file_size_mb": 42.3
    },
    {
      "variant": "9:16",
      "path": "renders/output_9x16.mp4",
      "format": "mp4",
      "duration_seconds": 59.8,
      "resolution": "1080x1920",
      "audio_channels": 2,
      "file_size_mb": 38.1
    }
  ],
  "probe_results": {
    "16:9": {"duration_check": "PASS", "resolution_check": "PASS", "audio_check": "PASS"},
    "9:16": {"duration_check": "PASS", "resolution_check": "PASS", "audio_check": "PASS"}
  }
}
```

## Validation Before Submitting

- [ ] All 4 pre-render checks passed
- [ ] `outputs` contains `16:9` entry
- [ ] `outputs` contains one entry per opted-in derivative (and cross-products)
- [ ] All probe results PASS
- [ ] `render_report.renderer` matches `EP_STATE.render_runtime`
