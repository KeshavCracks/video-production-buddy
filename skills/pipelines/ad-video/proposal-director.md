# Proposal Director — Ad Video Pipeline (post-bible)

> **Post-bible re-scope (v2):** Creative direction, visual direction, audio direction, and
> primary deliverable format are owned by bible-director. This director handles technical
> production parameters only. Do NOT re-decide creative direction here.

## When to Use

You are the **Proposal Director**. You receive `idea_options` + `production_bible`
(fully approved). Creative direction is locked. Your job is to confirm technical
production parameters that require user choice before assets are generated.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Input | `production_bible` (fully approved) | Contract reference |
| Input | `idea_options` artifact | Contains all concepts + `selected_concept_id` from user selection |

Verify `production_bible.approval.strategic_approved == true` AND
`production_bible.approval.execution_approved == true`. If either is false, surface
blocker to EP.

## Responsibilities

1. **Derivative variants** — present opt-in options (9:16, 1:1, 15s short) relative to
   bible's declared primary. Write selected variant ids to
   `production_proposal.derivatives_added`; do not mutate the bible's optional
   derivatives audit copy.
2. **Subtitle configuration** — burnt-in / SRT-only / none + language.
3. **Dubbing preferences** — additional language tracks.
4. **Style_mode confirmation** — bible provides the recommended style mode; get
   user sign-off. Lock `production_proposal.style_mode`.
5. **Runtime selection** — present the runtime shortlist before locking anything.
   Animated mode can use `"remotion"` or `"hyperframes"` when available; cinematic
   mode must include `"ffmpeg"` and should normally lock `"ffmpeg"`. HARD RULE
   from AGENT_GUIDE: present both Remotion and HyperFrames when both are available,
   include any applicable FFmpeg option, and never silently default. Record the
   user's choice in `decision_log` under category `render_runtime_selection`.
6. **Budget confirmation** — itemized cost estimate by stage.
7. **CTA verification** — confirm `production_bible.identity.cta` is non-null. If null,
   this is a pipeline error (should have been set at Round 2b). Surface as blocker to EP.

## What This Director No Longer Owns

- Narrative direction (arc_type, beats, pacing, emotional targets)
- Visual motifs and editing rhythm
- Audio direction (voice character, music arc)
- Primary aspect ratio and duration
- Concept options (owned by idea-director)
- Hook mechanic choice

All of the above are locked in production_bible before this stage runs.

## Process

### Step 1: Read Inputs

Load `idea_options` and `production_bible`. The selected concept is `idea_options.concepts` filtered by `idea_options.selected_concept_id`. Verify approval flags.
Extract `deliverables.primary` as baseline for derivative options.

### Step 2: Present Technical Choices

Present each responsibility item to the user in a single structured message:

```
PRODUCTION PARAMETERS — [Brand Name] [Platform] Ad

DERIVATIVES (optional — primary is [aspect_ratio] [duration]s)
  Would you like additional versions?
  • 9:16 vertical (15s) — for Stories/Reels
  • 1:1 square (30s) — for feed placement
  • [other relevant options based on platform]

SUBTITLES
  • Burnt-in / SRT file / None
  • Language: [default from platform locale]

DUBBING
  • Additional language tracks? (default: none)

STYLE CONFIRMATION
  Bible recommends: [style_mode_candidate]
  Confirm or change?

RENDER ENGINE
  Options available:
  • Remotion — [brief pro/con for this concept]
  • HyperFrames — [brief pro/con for this concept]
  • FFmpeg — [for cinematic/source-footage concepts; brief pro/con]
  Which do you prefer?

ESTIMATED COST
  [Itemized by stage]
  Total: [estimate]
```

### Step 3: Process User Choices

Parse response. Populate:
- `production_proposal.derivatives_added[]` with user-selected variants
- Lock `production_proposal.style_mode`
- Lock `production_proposal.render_runtime`

Do not require `production_bible.visual.render_runtime` before this point. The
bible stage runs before proposal approval, so its `visual.render_runtime` field
is optional audit context only; `production_proposal.render_runtime` is the
authoritative runtime lock for downstream stages.

### Step 3b: Lock the audio_contract (MANDATORY)

Present voice candidates to the user (provider, voice_id, sample if practical) and get explicit sign-off **before** any TTS spend. Voice choice is locked here so all sections in the script use the same voice — preventing tone drift across narration segments. Also lock loudness target by platform.

```json
"audio_contract": {
  "voice_provider": "cosyvoice",        // cosyvoice | elevenlabs | openai
  "voice_id": "Dylan",                   // provider-specific voice id
  "target_speed_wps": 2.5,               // words per second (script-director uses this for word budgets)
  "target_lufs": -14,                    // TikTok/Reels/Shorts=-14, YouTube=-13, broadcast=-23
  "max_section_drift_pct": 5,            // asset-director auto-retries if a section's actual TTS duration overruns by more than this
  "duck_depth_db": -18                   // music ducking depth during speech
}
```

If the user has not chosen, present 2–3 candidates with one **recommended** option labeled, and the trade-offs (cost / regional availability / cloning support).

### Step 3c: Lock the visual_contract (MANDATORY)

Anti-template policy: every ad-video must declare a deliberate visual direction, atmosphere preset, and per-beat overrides. The compose-director and scene-director both consume these.

```json
"visual_contract": {
  "style_direction": "editorial-tech",   // editorial-tech | neo-brutalist | glassmorphism | bento | scrollytelling | dark-luxury | swiss
  "typography_pairing": {
    "display": "Inter 800 italic",
    "body": "Inter 400"
  },
  "color_rhythm": "held-accent",         // intentional-rotation | held-accent | gradient-shift
  "atmosphere": {
    "default_layers": [
      { "type": "grain", "intensity": 0.05, "blendMode": "soft-light" },
      { "type": "vignette", "strength": 0.28 }
    ],
    "per_beat_overrides": {
      "B1": [{ "type": "ambient_glow", "color": "#FF3B30", "intensity": 0.55, "pulse": true }],
      "B5": [{ "type": "light_rays", "color": "#34D399", "angle": 35, "count": 5, "intensity": 0.08 }]
    }
  },
  "anti_template_checklist": [
    "non-uniform spacing across scenes",
    "scale contrast >= 4x between display and body",
    "at least 1 grid-break per scene"
  ]
}
```

`atmosphere.default_layers` and `per_beat_overrides` are consumed verbatim by scene-director (which copies them into each scene's `style_layers` prop). Available `type` values: `grain`, `vignette`, `ambient_glow`, `particle_field`, `light_rays` — see `remotion-composer/scene_type_registry.json#style_layers` for prop schemas.

### Step 4: Submit

Write `production_proposal` artifact to
`projects/<project-name>/artifacts/production_proposal.json`:

```json
{
  "selected_idea_id": "C2",
  "style_mode": "animated",
  "render_runtime": "remotion",
  "subtitles": { "mode": "burnt-in", "language": "en" },
  "dubbing": [],
  "derivatives_added": ["variant_id_1"],
  "budget_confirmed": true,
  "audio_contract": { /* see Step 3b */ },
  "visual_contract": { /* see Step 3c */ }
}
```

## Common Pitfalls

- **Re-deciding creative direction**: Arc, beats, motifs, audio — all locked. Do not re-open.
- **Silently defaulting runtime**: AGENT_GUIDE hard rule — always present both options.
- **Skipping CTA verification**: If `identity.cta` is null here, something went wrong upstream.
