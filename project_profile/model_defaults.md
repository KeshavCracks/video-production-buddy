# Model Defaults

These are dated observations about configured model defaults in this checkout.
They are not permanent claims about provider state. Re-check provider docs,
account access, and tool defaults before saying a model is current, latest, or
strongest.

## Last Verified

- Date: 2026-06-17 / 2026-06-18
- Scope: local tool defaults and known configured options in this repo state.

## Observed Defaults

- `wan_video_api` -> `happyhorse-1.0-t2v`
  - Notes: Wan flagship path observed at the time; native audio+video. Mute
    native audio under this project's final mix when appropriate.
  - Alternate noted: `wan2.7-t2v`.
- `minimax_video` -> `MiniMax-Hailuo-2.3`
  - Notes: good fit for human/performance scenes; supports `[command]` camera
    syntax.
- `wanx_image` -> `wan2.7-image-pro`
- `minimax_tts` -> `speech-2.8-hd`
- `minimax_music` -> `music-2.6`
- `cosyvoice_tts` strongest observed Qwen3 path:
  `qwen3-tts-instruct-flash`

At the time of the audit, no project-code change was needed for model strength;
defaults already pointed at the strongest known configured options.

## Verification Commands

Use live code inspection plus registry preflight before relying on this list:

```bash
rg -n "model|default|happyhorse|Hailuo|speech-2.8|music-2.6|wan2.7|qwen3" tools schemas skills project_profile
```

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.provider_menu_summary(), indent=2, ensure_ascii=False))"
```

When a tool exposes `get_info()` or a dry-run/sample mode, prefer that over
static text inspection for current account/runtime availability.
