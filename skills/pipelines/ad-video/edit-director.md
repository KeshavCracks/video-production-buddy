# Edit Director — Ad Video Pipeline

## When to Use

You receive `scene_plan`, `asset_manifest`, and `EP_STATE` and produce `edit_decisions`: a complete timeline specifying cut points, audio layering, subtitle burn configuration, and music ducking.

## Music Ducking Requirement

**Hard rule from `ad-brand` playbook: `ducking_threshold_db: -18`**

During every narration window:
- Music volume ducked to -18 dB (approximately 12% of full volume)
- Music returns to full volume at `cta_brand` beat (when narration ends)
- Transition into/out of ducking: 0.3s ease (matches playbook `transition_duration_seconds`)

```json
"audio_ducking": [
  {
    "start_seconds": 0.5,
    "end_seconds": 29.8,
    "target_db": -18,
    "fade_in_seconds": 0.3,
    "fade_out_seconds": 0.3
  }
]
```

### Emotion-Aware Volume Schedule (Path B)

When `production_bible.narrative.intensity_curve` is present (set by bible-director
Step 2 from the beat sequence), prefer an emotion-aware duck contour over the flat
-18 dB rule. Quieter narration beats duck deeper so words land; peak beats duck
shallower so the music breathes through the climax. The flat rule remains the
fallback when the bible has no intensity_curve.

Compute the contour with the deterministic helper:

```python
from lib.intensity_curve import derive_duck_schedule

# Derive narration_windows from the timeline you are building in this stage.
# For each scene that has narration:
#   start_seconds = scene.video_in + (scene.narration_offset or 0.0)
#   end_seconds   = start_seconds + narration_duration
# Scenes without narration are window boundaries — do NOT pad through them.
# Windows whose bodies are within 2*fade_seconds of each other are auto-merged
# by the helper, so do not pre-merge; pass the natural per-scene windows.
schedule = derive_duck_schedule(
    intensity_curve=production_bible["narrative"].get("intensity_curve", []),
    narration_windows=[
        {"start_seconds": 0.5,  "end_seconds": 6.2},
        {"start_seconds": 7.0,  "end_seconds": 14.5},
        # ...
    ],
    fade_seconds=0.3,
)
```

Write the result to `audio.music.volume_schedule` (per `edit_decisions.schema.json`):

```json
"audio": {
  "music": {
    "asset_id": "music-track-1",
    "volume_schedule": [
      {"t_seconds": 0.0,  "gain_db": 0.0},
      {"t_seconds": 0.2,  "gain_db": 0.0},
      {"t_seconds": 0.5,  "gain_db": -19.6},
      {"t_seconds": 6.2,  "gain_db": -16.0},
      {"t_seconds": 6.5,  "gain_db": 0.0}
    ]
  }
}
```

Do not hand-author the schedule — the helper is deterministic and the unit
tests in `tests/contracts/test_intensity_curve.py` are the spec. If
`derive_duck_schedule` raises, the inputs are malformed; fix them before
continuing.

## Subtitle Burn Configuration

```json
"subtitles": {
  "enabled": true,
  "source": "assets/subtitles.ass",
  "style": "sentence",
  "font": "DejaVu Sans",
  "font_size": 24,
  "color": "#FFFFFF",
  "outline_color": "#000000",
  "background": "#00000000",
  "position": "bottom-center",
  "max_words_per_line": 10
}
```

**Subtitle style rules:**
- `position` must be `"bottom-center"` (maps to ASS `Alignment=2`, lower edge). Never `"center"` — that is ASS `Alignment=5` (vertical midpoint, blocks content).
- `font_size`: 12 for 16:9 (1920×1080); 16 for 9:16 (1080×1920). Keep subtitles small and non-intrusive.
- `background`: transparent (`#00000000`, no box). Use outline+shadow for legibility instead.
- `MarginV` at compose time: 40px for 16:9; 200px for 9:16 (avoids platform UI overlay at bottom of TikTok/Reels).

Note: `position: "bottom-center"` in `edit_decisions.subtitles` maps directly to `Alignment=2` in the ASS `force_style` string passed to ffmpeg's `subtitles=` filter. Do not interpolate this as a generic "center" value.

## Timeline Construction

For each scene in `scene_plan.scenes[]`:
1. Create one top-level `cuts[]` item.
2. Set `in_seconds` to the cumulative offset from scene durations.
3. Set `out_seconds` to `in_seconds + scene.duration_seconds`.
4. Set `source` to an asset ID/path from `asset_manifest`, or `remotion:<component>` for generated component scenes.
5. Preserve beat identity on the cut. Prefer `maps_to_beat = scene.get("maps_to_beat")`;
   otherwise copy `beat_id = scene.get("beat_id")` or `beat = scene.get("beat")`.
   Do not submit any ad-video cut without one of these fields.
6. Apply `production_bible.visual.editing_rhythm` to the cut timing and
   transitions: average cut duration, cut density, and `transition_style` must
   match the rhythm entry for that beat. Split or combine scene-level material
   as needed before asset generation; do not let rapid beats collapse into long
   holds.
7. Copy registry props from the scene into the cut (`text`, `subtitle`, `brandName`, `ctaText`, `productImage`, `hardwareTreatment`, `banners`, `sidebarItems`, etc.). For `creator_workflow_scene`, `productImage` must be the approved `product_identity_reference.selected_reference_image_path`; do not leave it blank and do not substitute generic laptop hardware.
8. Put narration timing under `audio.narration.segments[]` using asset IDs from `asset_manifest`.
9. Verify: each narration segment duration is ≤ its scene duration.

## Edit Decisions Artifact Format

```json
{
  "version": "1.0",
  "render_runtime": "remotion",
  "music_strategy": "generative_loose",
  "renderer_family": "product-reveal",
  "total_duration_seconds": 11.0,
  "cuts": [
    {
      "id": "scene-1",
      "source": "v01",
      "in_seconds": 0.0,
      "out_seconds": 5.0,
      "maps_to_beat": "B1",
      "type": "text_card",
      "text": "45 minutes. Gone.",
      "transition_out": "cut",
      "reason": "Hook beat"
    },
    {
      "id": "scene-2",
      "source": "remotion:stat_card",
      "in_seconds": 5.0,
      "out_seconds": 11.0,
      "maps_to_beat": "B2",
      "type": "stat_card",
      "stat": "4 HRS",
      "subtitle": "back every week",
      "transition_in": "cut",
      "transition_out": "wipe-left",
      "reason": "Payload beat"
    }
  ],
  "audio": {
    "narration": {
      "segments": [
        {"asset_id": "narr-hook", "start_seconds": 0.0, "end_seconds": 4.8},
        {"asset_id": "narr-build-1", "start_seconds": 5.0, "end_seconds": 10.9}
      ],
      "volume": 1.0
    },
    "music": {
      "asset_id": "m01",
      "volume": 0.3,
      "volume_schedule": [
        {"t_seconds": 0.0, "gain_db": 0.0},
        {"t_seconds": 0.3, "gain_db": -14.0},
        {"t_seconds": 10.7, "gain_db": -14.0},
        {"t_seconds": 11.0, "gain_db": 0.0}
      ]
    }
  },
  "subtitles": {
    "enabled": true,
    "source": "assets/subtitles.ass",
    "style": "sentence",
    "font": "DejaVu Sans",
    "font_size": 24,
    "color": "#FFFFFF",
    "outline_color": "#000000",
    "background": "#00000000",
    "position": "bottom-center",
    "max_words_per_line": 10
  }
}
```

If `production_proposal.music_strategy == "none"`, set
`edit_decisions.music_strategy = "none"` and omit `audio.music` entirely. Do not
fabricate `audio.music.volume_schedule` for a no-background-music edit; there is
no music bed to duck.

## Derivative Edit Specifications

When `derivative_variants` is non-empty, include `edit_decisions.derivative_specs`
with one entry per opted-in variant:

```json
"derivative_specs": {
  "9:16": {
    "crop_regions": "from_scene_plan",
    "subtitle_style_override": {
      "font_size": 32,
      "margin_bottom_px": 80,
      "safe_zone_margin_px": 40
    }
  },
  "1:1": {
    "crop_regions": "from_scene_plan",
    "subtitle_style_override": {
      "font_size": 30,
      "margin_bottom_px": 70
    }
  },
  "15s": {
    "include_scenes": ["scene IDs where core:true"],
    "total_duration_check": "≤15s"
  }
}
```

## Validation Before Submitting

- [ ] Timeline covers 0.0 to `total_duration_seconds` with no gaps
- [ ] All `cuts[].source` and `audio.narration.segments[].asset_id` references resolve through `asset_manifest`
- [ ] Every cut carries `maps_to_beat`, `beat_id`, or `beat` copied from the scene plan
- [ ] `cuts[]` average durations, cut density, and transitions satisfy `production_bible.visual.editing_rhythm`
- [ ] If `production_bible.narrative.intensity_curve` is **absent** (legacy briefs):
      `audio.music.ducking` covers all narration windows AND duck depth matches `audio_contract.duck_depth_db`
- [ ] If `production_bible.narrative.intensity_curve` is **present** (Path B):
      `audio.music.volume_schedule` is populated by `derive_duck_schedule` and
      covers every narration window — do NOT also emit a flat `audio_ducking` block
- [ ] If subtitles were approved: `subtitles.enabled == true` and `subtitles.source` points to the generated ASS file
- [ ] If derivative_variants non-empty: `derivative_specs` present with entries for each variant
- [ ] Every narration segment duration ≤ matching scene duration


## Compliance Self-Check (run before submitting)

Load `production_bible.compliance_manifest.checkpoints`.
Filter to `applies_to_stage == "edit"`.
Split into `structural_checks[]` (`evaluation_method="structural"`) and
`semantic_checks[]` (`evaluation_method="semantic"`).

**Structural checks** — call the `compliance_check` tool for each:

    compliance_check({
        "stage_output": <the edit_decisions artifact dict you are about to submit>,
        "checkpoint": <the checkpoint object>
    })
    → returns { pass, actual_value, deviation, failure_action }

Do NOT evaluate structural checks yourself — they require deterministic code execution.
The tool handles word count, string matching, beat ID lookup, and arithmetic.

**Semantic checks** — LLM self-assessment:
Evaluate your own output against each semantic checkpoint's `criterion`.
If UNCERTAIN → treat as FAIL.

**Decision logic:**
- Any FAIL where `failure_action == "revise"` → do NOT submit. Fix and re-check.
  If still failing after one attempt, submit with:
  `compliance_failures: [{ checkpoint_id, evaluation_method, criterion, actual_value, deviation }]`
- Any `failure_action == "flag"` → submit with:
  `compliance_warnings: [{ checkpoint_id, criterion, deviation }]`
- All PASS → submit normally (omit compliance_failures and compliance_warnings keys).

**Note:** EP gate will independently re-evaluate all semantic checkpoints you
self-assessed as PASS. It will NOT see your self-assessment result. If EP disagrees,
you will receive a send-back with the EP evaluation rationale.

Relevant checkpoints: CP-E* (editing rhythm timing) and applicable CP-B* checkpoints
