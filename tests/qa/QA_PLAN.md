# Quality Validation Plan — Phase 3.5 + G3.11

## Purpose

Run every tool with real API keys, inspect outputs with terminal/headless checks, find gaps, fix them. This is the gate before calling Phase 3.5 "Verified."

## Current QA Scripts

| Script | Tools Tested | API Keys Used | Est. Cost |
|--------|-------------|---------------|-----------|
| `test_04_audio_mix.py` | `audio_mixer` | None (ffmpeg only) | $0 |
| `test_05_video_compose.py` | `video_compose` | None (ffmpeg only) | $0 |
| `test_06_video_stitch.py` | `video_stitch` | None (ffmpeg only) | $0 |
| `test_07_playbook_intelligence.py` | `playbook_loader.py` functions | None (pure Python) | $0 |
| `test_08_end_to_end.py` | Full animated-explainer pipeline | None (ffmpeg fixtures) | $0 |
| `test_09_hyperframes_compose.py` | HyperFrames scaffold/lint/validate/render | None (local CLI; opt-in) | $0 |
| `test_phase2_comparison.py` | Phase 1 vs Phase 2 media comparison | None (ffmpeg fixtures) | $0 |

## Inspection Protocol

For each output:
1. **Audio files**: Use `ffprobe` for format/duration/channels, waveform/loudness analysis for clipping and mix balance, and Whisper/transcript checks to verify content matches prompt.
2. **Image files**: Use `ffprobe` or image metadata for dimensions, OCR where text is expected, and generated thumbnails/contact sheets for composition, text readability, and style match.
3. **Video files**: Use `ffprobe` for resolution/fps/duration/codec, extracted frame contact sheets for visual checks, subtitle/timestamp comparison for timing, and audio-stream analysis for A/V alignment.
4. **Design intelligence**: Run against all 3 playbooks, verify contrast ratios match manual calculation, check CVD warnings are accurate

## Known Risk Areas

| Area | Risk | How to Validate |
|------|------|-----------------|
| TTS voice selection | Default voice may not match playbook mood | Test with multiple voice IDs, compare against playbook `voice_style` |
| Image gen consistency | DALL-E/FLUX outputs vary wildly per prompt | Test with playbook `image_prompt_prefix` prepended |
| Music duration alignment | Music may not match narration duration | Compare `music.duration` vs `tts.duration`, check padding/looping |
| Audio ducking timing | Ducking may cut music too aggressively | Inspect waveform: music should duck ~6dB under speech, recover smoothly |
| Video stitch transitions | Crossfade may flicker with mismatched codecs | Test with both matching and mismatched clips, check `auto_normalize` |
| Subtitle burn-in | Font size/position may clip on mobile formats | Test with 9:16 (TikTok) and 16:9 (YouTube) profiles |
| Remotion render | Components may fail with real data | Build a test composition with all 8 components, render at 1080p |
| Playbook contrast | Edge cases in dark-on-dark or light-on-light themes | Test with all 3 playbooks + a deliberately low-contrast custom one |

## Run Order

```bash
cd /path/to/video-production-buddy
export VPB_ALLOW_BROWSER_OPEN=0
export PYTHONDONTWRITEBYTECODE=1

# Phase 1: Composition fixtures and inspectable outputs
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_04_audio_mix.py -v
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_05_video_compose.py -v
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_06_video_stitch.py -v
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_phase2_comparison.py -v

# Phase 2: Intelligence validation (no API calls)
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_07_playbook_intelligence.py -v

# Phase 3: Full pipeline
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_08_end_to_end.py -v

# Optional HyperFrames runtime QA
HYPERFRAMES_QA=1 VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/qa/test_09_hyperframes_compose.py -v
```

## Success Criteria

- [ ] Generated narration fixtures: clear speech, correct content, no artifacts, ≥44.1kHz
- [ ] Generated image fixtures: match prompt intent, correct dimensions, no watermarks, good composition
- [ ] Music fixtures: match mood prompt, correct duration (±2s), no abrupt cuts
- [ ] Audio mix: speech clearly above music, ducking smooth, no clipping
- [ ] Video compose: A/V sync within 50ms, correct resolution, ffprobe-readable output with representative extracted frames
- [ ] Video stitch: smooth transitions, no frame drops, PIP correctly positioned
- [ ] Playbook intelligence: all 3 playbooks pass a11y, contrast ratios within 0.1 of manual calc
- [ ] End-to-end: 60-second explainer renders without errors, all stages checkpoint correctly
