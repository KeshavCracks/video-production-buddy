# Ad Video Pipeline — Design Spec

**Date:** 2026-04-24
**Status:** Approved — ready for implementation
**Pipeline name:** `ad-video`

---

## Context

OpenMontage has no pipeline for advertising video. Existing pipelines are either too narrow (animated-explainer, animation) or footage-led (cinematic, hybrid). This pipeline is needed to produce fluid-motion advertisement videos — TV-commercial and streaming-ad quality — from a text brief, with optional reference images and clips.

The key requirements that distinguish this from existing pipelines:

- Text description as primary input (no source footage required)
- Fluid motion video mandatory — not slideshows, not Ken Burns
- Visual style is either **animated** (cartoon/3D) or **cinematic** (live-action-style), selected per brief
- TTS narration is **required** (not optional)
- Subtitles are **required** (not optional)
- Output: 1920×1080 primary + opt-in platform derivatives (9:16, 1:1, 15s short)
- Narrative-driven, brand/product advertising quality gates

---

## Architecture Decision: New Pipeline

**Verdict: new `ad-video` pipeline, not an extension of an existing one.**

Gap analysis against the closest candidates:

| Requirement | animated-explainer | animation | cinematic | hybrid |
| --- | --- | --- | --- | --- |
| Text-description as primary input | ✅ | ✅ | ⚠️ footage-led | ⚠️ footage-anchor |
| Fluid video (not slideshow) | ⚠️ optional | ⚠️ optional | ✅ | ✅ |
| Animated OR cinematic mode | ❌ | ❌ animation only | ❌ cinematic only | ❌ |
| TTS narration required | ✅ | ⚠️ no cinematic path | ❌ absent | ⚠️ optional |
| Subtitles required | ❌ optional | ❌ optional | ❌ optional | ❌ optional |
| Ad-copy scripting quality gates | ❌ | ❌ | ❌ | ❌ |
| Brand/CTA creative logic | ❌ | ❌ | ❌ | ❌ |

The creative logic for advertising diverges from explainer and cinematic DNA at the `idea` stage and propagates through every director skill. Extending any existing pipeline would require fighting its assumptions throughout.

---

## Stage Sequence

```
idea → proposal → script → scene_plan → assets → edit → compose → publish
```

No research stage. The user supplies the brief; `idea` formalizes it into a canonical artifact. Unlike explainer/animation pipelines (which research a topic), ad-video starts from client-supplied copy.

---

## Pipeline Manifest

```yaml
name: ad-video
version: "1.0"
description: >
  Advertising video pipeline. Generates fluid motion video (animated or cinematic)
  from a text brief, with optional reference images/clips as source material or
  style references. Produces a primary 1920x1080 MP4 with mandatory narration
  and subtitles, plus opt-in platform derivatives.
category: advertising
stability: beta

default_checkpoint_policy: guided

reference_input:
  supported: true
  analysis_depth: standard
  intent_inference: true
  analysis_tools:
    - video_analyzer
    - frame_sampler
    - scene_detect

extensions:
  custom_scripts: true
  custom_playbooks: true
  custom_skills: true
  custom_tools: false

orchestration:
  mode: executive-producer
  skill: pipelines/ad-video/executive-producer
  budget_default_usd: 5.00
  max_revisions_per_stage: 3
  max_send_backs: 3
  max_wall_time_minutes: 30

compatible_playbooks:
  recommended:
    - ad-brand
    - flat-motion-graphics
  also_works:
    - clean-professional
  custom_allowed: true

required_skills:
  - pipelines/ad-video/executive-producer
  - pipelines/ad-video/idea-director
  - pipelines/ad-video/proposal-director
  - pipelines/ad-video/script-director
  - pipelines/ad-video/scene-director
  - pipelines/ad-video/scene-director-animated
  - pipelines/ad-video/scene-director-cinematic
  - pipelines/ad-video/asset-director
  - pipelines/ad-video/asset-director-animated
  - pipelines/ad-video/asset-director-cinematic
  - pipelines/ad-video/edit-director
  - pipelines/ad-video/compose-director
  - pipelines/ad-video/publish-director
  - meta/reviewer
  - meta/checkpoint-protocol
  - meta/animation-runtime-selector
```

---

## Style Mode System

### Detection and Locking

Style mode determination is a two-step process to prevent misclassification:

**Step 1 — `idea` stage:** Agent scans the brief for explicit style keywords.

| Keywords | `candidate_style_mode` |
| --- | --- |
| "animated", "cartoon", "3D", "motion graphics" | `"animated"` |
| "cinematic", "live-action", "film", "realistic" | `"cinematic"` |
| No clear signal | `null` |

`candidate_style_mode` is stored in the brief artifact. It is **not locked here**.

**Step 2 — `proposal` stage (always):**
- If `candidate_style_mode` is set: agent presents concept options all in that mode, user confirms
- If `candidate_style_mode` is null: agent proposes 2–3 concepts with different style modes, user picks

`style_mode` is **locked at proposal approval** and carried through all downstream stages.

### Mode-Aware Skill Structure

Stages divide into two categories based on how much animated vs. cinematic guidance diverges:

**Low-divergence stages** (idea, proposal, script, edit, compose, publish) — single skill file with clearly labelled `[animated]` and `[cinematic]` sections. The divergence is a paragraph or two; a single file stays readable.

**High-divergence stages** (scene_plan, assets) — base skill file plus two mode-specific supplement files. The base covers shared logic; the supplement adds mode-specific vocabulary and quality rules.

Delegation pattern in base skills:

> After completing the shared guidance above, read `skills/pipelines/ad-video/scene-director-{style_mode}.md` and apply its guidance to every scene in the plan.

---

## Stage Specifications

### Stage 1 — `idea`

| Field | Value |
| --- | --- |
| Produces | `brief`, `decision_log` |
| Tools | `video_analyzer`, `frame_sampler`, `scene_detect` (for reference files only) |
| `human_approval_default` | `true` |

**What it does:**
- Parses user description into structured brand context (product, audience, tone, campaign goal, CTA)
- Detects style keywords → sets `candidate_style_mode`
- Establishes `duration_target_seconds` (default: 75, range: 60–180)
- Analyses any reference files → stores `inferred_role` + `reason` per file

**Key `brief` fields:**
```json
{
  "brand_context": { "product": "...", "audience": "...", "tone": "...", "cta": "..." },
  "candidate_style_mode": "animated | cinematic | null",
  "duration_target_seconds": 75,
  "reference_files": [
    { "filename": "...", "inferred_role": "source_material | style_reference", "reason": "..." }
  ]
}
```

**Review focus:** `candidate_style_mode` is set or explicitly null; all reference files have `inferred_role` + `reason`; `brand_context` is populated from the description, not invented.

---

### Stage 2 — `proposal`

| Field | Value |
| --- | --- |
| Produces | `proposal_packet`, `decision_log` |
| Tools | none |
| `human_approval_default` | `true` |

**What it does:**
- Presents and locks `style_mode` (see Style Mode System above)
- Lists **all** reference files with `inferred_role` + `reason` — user confirms or corrects every classification
- Presents derivative variant opt-in:
  - ☑ 1920×1080 (primary — always included)
  - ☐ 9:16 vertical (Reels / TikTok / Shorts)
  - ☐ 1:1 square (Feed)
  - ☐ 15s short cut
- Presents both composition runtimes per the hard rule (AGENT_GUIDE.md) — `render_runtime` locked here
- Presents music plan (library / generate / user provides / none)
- Produces itemised cost estimate

**Locked at approval:** `style_mode`, reference file roles, `derivative_variants[]`, `render_runtime`, `music_plan`

**Review focus:** `style_mode` locked and present; all reference files confirmed; `render_runtime` selection logged in `decision_log` with both runtimes considered (CRITICAL if only one recorded when both available); cost estimate itemised per tool.

---

### Stage 3 — `script`

| Field | Value |
| --- | --- |
| Produces | `script` |
| Tools | none |
| `human_approval_default` | `true` |

**Ad copy structure (four beats, both modes):**

```
hook → build → reveal/climax → CTA + brand landing
```

**Inline mode sections:**
- `[animated]`: beats map to animation cues; on-screen text is short and punchy (≤6 words/line); pacing has deliberate visual holds
- `[cinematic]`: beats map to shot-type suggestions and emotional arc markers; VO cadence is slower with room for visual breathing

**Required:** script word count must produce a TTS narration duration within ±10% of `duration_target_seconds` (target ≈ `duration_target_seconds × 2.5` words for English); CTA present in the final 15% of the script; brand name appears in the landing beat.

---

### Stage 4 — `scene_plan` *(base + supplement)*

| Field | Value |
| --- | --- |
| Produces | `scene_plan` |
| Tools | none |
| `human_approval_default` | `true` |

**Base skill covers (shared):**
- Safe-zone planning when any non-1080p derivative is selected: 1/6 frame margin on all sides; `crop_regions` per scene for each selected aspect ratio
- Core / trimmable tagging when 15s short cut is selected: every scene gets `core: true` or `trimmable: true`
- Duration math: sum of scene hold times within ±5% of `duration_target_seconds`
- `motion_required: true/false` per scene

**Coupling rule:** safe-zone planning and derivative rendering are coupled. If `derivative_variants` is non-empty, every scene must have `safe_zone.crop_regions` for each selected variant. Missing crop regions at compose time is a CRITICAL violation.

**15s short cut constraint:** when `15s_short` is selected, the scene director must verify that the sum of all `core: true` scene durations is ≤ 15s. If core scenes exceed 15s, mark the least essential scenes `trimmable: true` until the core total fits.

**Example scene entry (with 9:16 and 1:1 variants selected):**

```json
{
  "id": "scene_03",
  "duration_seconds": 6,
  "core": true,
  "trimmable": false,
  "motion_required": true,
  "safe_zone": {
    "active": true,
    "crop_regions": {
      "9x16": { "x": 656, "y": 0, "w": 608, "h": 1080 },
      "1x1":  { "x": 420, "y": 0, "w": 1080, "h": 1080 }
    }
  }
}
```

Note: crop region values are computed at runtime by the scene director. 9:16 at 1080p height = 608×1080 (correct). Do not use 400×1080 in documentation examples.

**Supplements:**

| File | Content |
| --- | --- |
| `scene-director-animated.md` | Remotion/HyperFrames scene types (`anime_scene`, `text_card`, `hero_title`, HyperFrames blocks), keyframe beats, motion-hold rhythm, visual motif reuse |
| `scene-director-cinematic.md` | Shot types (wide, medium, closeup), camera movement direction, emotional arc per scene, live-action-style clip description vocabulary |

---

### Stage 5 — `assets` *(base + supplement, with sample sub-stage)*

| Field | Value |
| --- | --- |
| Produces | `asset_manifest` |
| Required tools | `tts_selector`, `subtitle_gen` |
| Optional tools | `image_selector`, `video_selector`, `music_gen` |
| `human_approval_default` | `false` (full stage) |

**Sample sub-stage (always runs, human approval required):**

```yaml
sub_stages:
  - name: sample
    description: >
      Generate assets for the first 2–3 scenes. Assemble and present a
      10–15 second preview clip before committing to full asset generation.
    human_approval_default: true
    tools_available:
      - tts_selector
      - image_selector
      - video_selector
      - video_compose
      - audio_mixer
    review_focus:
      - Visual style matches approved style_mode and playbook
      - Brand fit is evident — product/tone aligns with the brief
      - Motion quality meets fluid-motion requirement (no slideshow)
      - Narration voice and pacing feel right for ad format
```

User approves preview → full asset generation proceeds. User rejects → agent revises direction before spending on the full run.

**Base skill covers (shared, both modes):**

- **TTS narration: required** — `tts_selector` called for every script section; all narration files must exist before continuing
- **Subtitles: required** — `subtitle_gen` called after narration; SRT file must exist before continuing
- Music plan execution (copy library track / call `music_gen` / skip)
- Reference file handling:
  - `source_material`: copy directly into asset manifest; mark provenance
  - `style_reference`: extract palette/mood notes into `asset_manifest.style_notes`; file does not appear in the video

**Supplements:**

| File | Content |
| --- | --- |
| `asset-director-animated.md` | `image_selector` for visual assets; `video_selector` for motion clips (optional, preferred); Remotion component planning; anime/motion prompt vocabulary; Layer 3 skill refs |
| `asset-director-cinematic.md` | `video_selector` required — static images forbidden as primary visuals; motion is a hard requirement on all `motion_required: true` scenes; live-action prompt vocabulary; Layer 3 skill refs |

---

### Stage 6 — `edit`

| Field | Value |
| --- | --- |
| Produces | `edit_decisions` |
| Tools | none |
| `human_approval_default` | `false` |

**Inline mode sections:**

- `[animated]`: hold times, staggered reveals, motion beat alignment with narration
- `[cinematic]`: emotional pacing, shot rhythm, strong moments not overcut

**Shared (both modes):** subtitle burn config; music ducking at -18 dB during narration; derivative variant edit specs — crop regions per scene for 9:16/1:1 carried through from scene_plan; core/trimmable flags become timeline markers for the 15s cut.

---

### Stage 7 — `compose`

| Field | Value |
| --- | --- |
| Produces | `render_report` |
| Required tools | `video_compose`, `audio_mixer` |
| Optional tools | `video_stitch`, `video_trimmer`, `color_grade`, `audio_enhance` |
| `human_approval_default` | `false` |

**Derivative rendering loop:**

```text
for each variant in edit_decisions.approved_variants:
  "9x16" | "1x1"  → apply crop_regions from scene_plan per scene → renders/final_{variant}.mp4
  "15s_short"     → filter timeline to core-only scenes → renders/final_15s.mp4
                    if "9x16" also selected → additionally render renders/final_15s_9x16.mp4
                    if "1x1"  also selected → additionally render renders/final_15s_1x1.mp4
primary always    → renders/final_1080p.mp4
```

The 15s short cut always includes a 1080p version. When combined with aspect ratio derivatives, the compose stage also renders the 15s cut in each selected aspect ratio using the same core-scene filter + crop-region logic.

**CRITICAL violation triggers:**

- `render_runtime` in `edit_decisions` differs from `proposal_packet` — silent runtime swap
- `approved_variants` is non-empty and any scene is missing `safe_zone.crop_regions` — broken scene_plan coupling

**Inline mode review focus:**

- `[animated]`: text and diagrams sharp at final resolution; motion timing survives render
- `[cinematic]`: mood matches intended pacing and grade; motion-required delivery preserved without silent fallback

---

### Stage 8 — `publish`

| Field | Value |
| --- | --- |
| Produces | `publish_log` |
| Tools | none |
| `human_approval_default` | `true` |

Organises the export package and verifies every expected deliverable is present.

**Output file matrix:**

| File | Condition |
| --- | --- |
| `renders/final_1080p.mp4` | Always |
| `renders/final_9x16.mp4` | If 9:16 selected |
| `renders/final_1x1.mp4` | If 1:1 selected |
| `renders/final_15s.mp4` | If 15s short cut selected |
| `renders/final_15s_9x16.mp4` | If 15s AND 9:16 both selected |
| `renders/final_15s_1x1.mp4` | If 15s AND 1:1 both selected |
| `renders/subtitles_{variant}.srt` | One SRT per unique timeline (1080p/15s are separate timelines; 9:16/1:1 share the 1080p timeline) |
| `renders/metadata.json` | Always — platform-appropriate fields per variant |
| `renders/thumbnail_concept.md` | Always — thumbnail direction for the primary cut |

---

## Reference File Data Flow

```
idea stage
  └── for each reference file:
        run frame_sampler / video_analyzer / scene_detect
        set inferred_role: "source_material" | "style_reference"
        set reason: one sentence
        store in brief.reference_files[]

proposal stage
  └── present ALL reference files to user:
        "I classified your references as follows — please confirm or correct:"
        [filename] → [inferred_role] — [reason]
      user confirms or corrects every file
      locked classifications stored in proposal_packet.reference_files[]

assets stage (base)
  └── for each file in proposal_packet.reference_files:
        source_material  → copy into asset manifest as existing_asset
                           provenance: { source: "user_reference", filename: "..." }
        style_reference  → extract palette/mood/pacing notes
                           store in asset_manifest.style_notes
                           file does NOT appear in the video
```

---

## `ad-brand` Playbook

```yaml
name: ad-brand
version: "1.0"
description: >
  Default playbook for ad-video pipeline. Defines commercial pacing, bold
  visual hierarchy, and CTA-emphasis conventions. Brand-specific overrides
  (colors, typeface, logo rules) are applied via the brief at idea/proposal.

visual_language:
  hierarchy: bold — product and key message dominate every frame
  contrast: high — text legible over any background without overlay hacks
  color_defaults:
    primary: brand-supplied via brief; fallback "#1A1A2E"
    accent:  brand-supplied via brief; fallback "#E94560"
  safe_zones: enforced when derivatives are selected

typography:
  display: large, strong weight — key message lines, CTA text
  body: clean, readable at subtitle size
  on_screen_line_limit: 6 words max per line

motion:
  principle: every motion serves a message beat — no decorative transitions
  cta_moment: deliberate visual emphasis (scale, reveal, or hold)
  cut_rhythm: commercial pacing — tighter than explainer, aligned to narration beats

audio:
  music_role: supports emotional arc; rises at CTA
  narration_ducking: -18 dB under narration segments
  cta_music: rise to full at final brand landing beat

quality_rules:
  - No Ken Burns on product shots — static products use motion backgrounds
  - No decorative transitions that don't serve the narrative
  - CTA beat must be visually distinct from body (scale, color shift, or hold)
  - Subtitles must be present and legible on all variants
  - Brand name must appear in the final frame
```

---

## Skill File Inventory

**Total: 15 new files**

| File | Type | Notes |
| --- | --- | --- |
| `pipeline_defs/ad-video.yaml` | Manifest | |
| `skills/pipelines/ad-video/executive-producer.md` | Base skill | Orchestration, budget governance, EP role |
| `skills/pipelines/ad-video/idea-director.md` | Base skill | Keyword detection, reference classification, brief formalization |
| `skills/pipelines/ad-video/proposal-director.md` | Base skill | style_mode lock, reference confirmation, derivative opt-in, runtime selection, music plan, cost |
| `skills/pipelines/ad-video/script-director.md` | Base skill | Four-beat structure, inline [animated]/[cinematic] sections |
| `skills/pipelines/ad-video/scene-director.md` | Base skill | Safe zones, core/trimmable tagging, duration math; delegates to supplement |
| `skills/pipelines/ad-video/scene-director-animated.md` | Supplement | Remotion/HyperFrames scene types, keyframe beats, motif reuse |
| `skills/pipelines/ad-video/scene-director-cinematic.md` | Supplement | Shot types, camera movement, emotional arc vocabulary |
| `skills/pipelines/ad-video/asset-director.md` | Base skill | TTS required, subtitles required, music, reference handling, sample sub-stage; delegates to supplement |
| `skills/pipelines/ad-video/asset-director-animated.md` | Supplement | image_selector path, Remotion components, anime/motion prompts, Layer 3 refs |
| `skills/pipelines/ad-video/asset-director-cinematic.md` | Supplement | video_selector required, motion hard requirement, live-action prompts, Layer 3 refs |
| `skills/pipelines/ad-video/edit-director.md` | Base skill | Inline mode sections, subtitle burn, music ducking, derivative edit specs |
| `skills/pipelines/ad-video/compose-director.md` | Base skill | Derivative rendering loop, runtime routing, quality review |
| `skills/pipelines/ad-video/publish-director.md` | Base skill | Export package, per-variant metadata, thumbnail concept |
| `styles/ad-brand.yaml` | Playbook | Pipeline-level default; brief overrides at runtime |

---

## Verification

### Smoke test (no generation calls)

```bash
# Verify manifest loads and all required_skills exist on disk
python -c "
from lib.pipeline_loader import PipelineLoader
p = PipelineLoader().load('ad-video')
print(p.validate_skills())
"

# Verify ad-brand playbook loads and passes schema
python -c "
from styles.playbook_loader import PlaybookLoader
pb = PlaybookLoader().load('ad-brand')
print(pb.validate())
"
```

### Integration test (no generation)

**Brief:** "Launch video for a noise-cancelling headphone. Cinematic style, 60 seconds. Premium feel."

Expected outputs:
- idea: `candidate_style_mode: "cinematic"`, `duration_target_seconds: 60`
- proposal: `style_mode: "cinematic"` locked; `render_runtime` selection in `decision_log` with both runtimes recorded; `derivative_variants: []`

### Full pipeline test (requires TTS + one video provider)

1. Run all 8 stages with the integration brief
2. At sample sub-stage: verify playable 10–15s MP4 exists
3. At compose: verify `renders/final_1080p.mp4` exists and passes `ffprobe` validation
4. At publish: verify export package contains video, SRT file, and metadata

---

## Implementation Order

1. `styles/ad-brand.yaml`
2. `pipeline_defs/ad-video.yaml`
3. `skills/pipelines/ad-video/executive-producer.md`
4. `skills/pipelines/ad-video/idea-director.md`
5. `skills/pipelines/ad-video/proposal-director.md`
6. `skills/pipelines/ad-video/script-director.md`
7. `skills/pipelines/ad-video/scene-director.md` + supplements (`-animated`, `-cinematic`)
8. `skills/pipelines/ad-video/asset-director.md` + supplements (`-animated`, `-cinematic`)
9. `skills/pipelines/ad-video/edit-director.md`
10. `skills/pipelines/ad-video/compose-director.md`
11. `skills/pipelines/ad-video/publish-director.md`
