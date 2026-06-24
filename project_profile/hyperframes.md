# HyperFrames Runtime Findings

Provider/runtime behavior can drift. Treat this file as dated project-side
evidence and re-check the live tool/runtime before promising HyperFrames in a
new production run.

## Last Verified

- Date: 2026-06-18
- Scope: local `hyperframes_compose` scaffolding, the `projects/zhiying`
  HyperFrames beta handoff, and current Layer 2 HyperFrames guidance.

## CJK Text Rendering

- HyperFrames/browser capture did not reliably resolve CJK fonts from system
  fallback in this environment. Chinese text rendered correctly only after the
  workspace explicitly packaged Noto Sans SC and declared it with `@font-face`.
- Any HyperFrames workspace containing Chinese/CJK text must package
  `NotoSansSC.ttf` or an equivalent subset under `workspace/assets/` and include
  an `@font-face` rule for `Noto Sans SC` in `index.html`.
- `hyperframes_compose` now detects CJK text in `edit_decisions`, searches for
  `projects/<project-id>/fonts/NotoSansSC.ttf`, workspace-local font assets, or
  `~/.fonts/NotoSansSC.ttf`, copies the font to `workspace/assets/`, and injects
  the `@font-face` rule during scaffold.
- If a hand-authored HyperFrames workspace bypasses `hyperframes_compose`, the
  agent must perform the same font packaging before lint/validate/render. Do not
  rely on browser/system fallback for Chinese typography.
- If CJK text is present and no local Noto Sans SC font can be found, scaffold
  should fail rather than silently producing tofu/missing glyphs.

## Video-Heavy Rendering

- Default parallel capture can overwhelm headless Chrome when a composition
  loads many video elements.
- For compositions with more than five video cuts/background videos, use
  `hyperframes render --workers 1`.
- `hyperframes_compose` automatically passes `--workers 1` for this video-heavy
  case when the caller has not supplied an explicit worker count.
- Sparse source keyframes can cause render timeouts or frozen frames.
  `hyperframes_compose` checks staged video assets with `ffprobe`; when the max
  keyframe interval exceeds five seconds, it creates a `.dense.mp4` workspace
  copy using `ffmpeg -c:v libx264 -r 30 -g 30 -keyint_min 30 -sc_threshold 0
  -movflags +faststart` and points the generated HTML at that prepared copy.

## Verification Commands

```bash
rg -n "@font-face|Noto Sans SC|NotoSansSC" projects/<project-id>/hyperframes projects/<project-id>/hf_beta
```

```bash
pytest tests/tools/test_hyperframes_compose.py -k "cjk_font or video_heavy"
```

```bash
pytest tests/tools/test_hyperframes_compose.py -k "sparse_keyframe"
```
