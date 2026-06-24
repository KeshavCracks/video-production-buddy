# Voice and Subtitles

## Mandarin Male Voice

Last verified: 2026-06-18.

- `qwen3-tts-instruct-flash` through DashScope / `cosyvoice_tts` has voices
  Dylan, Ethan, and Kai documented as male, but they rendered feminine in
  Mandarin in prior checks, with and without `instructions`. Do not use them as
  the default male Mandarin narrator.
- CosyVoice system male voices such as `longxiaocheng` and `longanyang` returned
  HTTP 400 / parse errors in this Bailian account because the models were not
  enabled. See `provider_findings.md`.
- Reliable Mandarin male voice path: `minimax_tts`, model `speech-2.8-hd`.
- Known usable MiniMax male voice IDs:
  - `male-qn-badao` - deep/powerful
  - `presenter_male` - anchor/presenter
  - `male-qn-jingying` - elite/business
  - `male-qn-daxuesheng` - young
  - `male-qn-qingse` - clear youth
- Voice IDs observed not to exist on this account: `audiobook_man_1`,
  `male-qn-baobao`, `news_anchor_1`.

## Voice Provider Routing

- `schemas/artifacts/production_proposal.schema.json` `audio_contract` allows
  `voice_provider = "minimax"` with `voice_model = "speech-2.8-hd"` and the
  MiniMax male voice IDs above when `voice_gender = male`.
- `skills/pipelines/ad-video/asset-director.md` has a MiniMax branch that calls
  `MinimaxTTS`.
- MiniMax delivery control is voice + pitch + speed. It is not a
  free-form-instruction-capable voice path.
- Narration assets should record `source_tool = "minimax_tts"` when this route
  is used.

## CJK Subtitle Rendering

Last verified: 2026-06-18.

- The base environment had no CJK fonts; ffmpeg/libass fell back to DejaVu Sans
  and Chinese subtitles rendered as tofu / missing glyphs.
- A CJK font is bundled at `projects/<project-id>/fonts/NotoSansSC.ttf`
  (Noto Sans SC, variable, about 18MB). It was also copied to `~/.fonts/` and
  registered with `fc-cache`.
- Always burn Chinese subtitles with font name `Noto Sans SC` and a bold weight
  when available.
- For a heavier display weight on brand endcards, prefer Noto Sans SC Bold/Black
  or HarmonyOS Sans when available.

## Verification Commands

```bash
fc-match "Noto Sans SC"
```

If the result resolves to DejaVu or another non-CJK font:

```bash
fc-cache -f ~/.fonts
fc-match "Noto Sans SC"
```

Before a fresh production run, also verify the selected TTS provider through
the registry and, for paid/API voices, a short sample render.
