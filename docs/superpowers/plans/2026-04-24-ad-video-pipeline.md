# Ad-Video Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `ad-video` pipeline — 15 new files (1 playbook, 1 pipeline manifest, 13 director skill Markdown files) that enable fully orchestrated ad/commercial video generation with animated and cinematic render modes, derivative aspect-ratio variants, a mandatory sample approval sub-stage, and required TTS + subtitle generation.

**Architecture:** The pipeline follows the same EP-driven serial pattern as `animated-explainer`: an Executive Producer skill orchestrates 8 stage directors, maintains cumulative EP_STATE, and applies quality gates between stages. High-divergence stages (scene_plan, assets) use a base skill + mode supplement pattern; low-divergence stages (script, edit, compose, publish) inline both modes. Style mode (`animated` vs `cinematic`) is candidate-inferred at the idea stage and locked at proposal; all 8 downstream skills branch on `EP_STATE.style_mode`.

**Tech Stack:** YAML (playbook + manifest), Markdown (director skills), Python (verification via existing loader APIs `load_playbook` / `load_pipeline` / `validate_playbook`)

---

## File Structure

| # | File | Role |
|---|------|------|
| 1 | `styles/ad-brand.yaml` | Playbook: visual identity, motion, audio, quality rules for ad content |
| 2 | `pipeline_defs/ad-video.yaml` | Pipeline manifest: 8 stages, sub-stages, review focus, success criteria |
| 3 | `skills/pipelines/ad-video/executive-producer.md` | EP: EP_STATE schema, EXECUTE_STAGE loop, 8 cross-stage gates, send-back rules |
| 4 | `skills/pipelines/ad-video/idea-director.md` | Stage 1: parse brand context, infer style_mode candidate, analyze reference files |
| 5 | `skills/pipelines/ad-video/proposal-director.md` | Stage 2: lock style_mode, confirm all refs, opt-in derivatives, present 3 concepts |
| 6 | `skills/pipelines/ad-video/script-director.md` | Stage 3: four-beat copy structure, word-count calibration, mode annotations |
| 7 | `skills/pipelines/ad-video/scene-director.md` | Stage 4 base: safe zones, core/trimmable tagging, delegates to supplement |
| 8 | `skills/pipelines/ad-video/scene-director-animated.md` | Stage 4 supplement (animated): motion scene types, keyframe beats |
| 9 | `skills/pipelines/ad-video/scene-director-cinematic.md` | Stage 4 supplement (cinematic): shot type vocab, emotional arc |
| 10 | `skills/pipelines/ad-video/asset-director.md` | Stage 5 base: sample sub-stage (always), TTS required, subtitles required |
| 11 | `skills/pipelines/ad-video/asset-director-animated.md` | Stage 5 supplement (animated): motion graphics + generated video assets |
| 12 | `skills/pipelines/ad-video/asset-director-cinematic.md` | Stage 5 supplement (cinematic): cinematic image/video asset generation |
| 13 | `skills/pipelines/ad-video/edit-director.md` | Stage 6: timeline, subtitle burn, music ducking at -18 dB, derivative edit specs |
| 14 | `skills/pipelines/ad-video/compose-director.md` | Stage 7: CRITICAL pre-render checks, full derivative rendering loop |
| 15 | `skills/pipelines/ad-video/publish-director.md` | Stage 8: output file matrix, metadata, thumbnail concept |

---

## Task 1: Ad-Brand Playbook

**Files:**
- Create: `styles/ad-brand.yaml`

- [ ] **Step 1: Write the playbook file**

```yaml
identity:
  name: "Ad Brand"
  category: custom
  mood: "bold, narrative-driven, emotionally resonant"
  pace: fast
  best_for: "TV commercials, streaming ads, brand launch videos, product campaigns (60–90s)"

visual_language:
  color_palette:
    primary: ["#1A1A2E", "#16213E"]
    accent: ["#E94560", "#0F3460"]
    background: "#0D0D0D"
    text: "#F5F5F5"
    muted: "#888888"
  composition: "Bold product-forward framing; CTA beat always center-weighted; safe zones enforced when derivatives are selected"
  texture: "Clean backgrounds; no decorative noise; product and message dominate every frame"

typography:
  headings:
    font: "Inter"
    weight: 800
    tracking: "-0.02em"
  body:
    font: "Inter"
    weight: 400
    line_height: 1.5
  stat_card:
    font: "Inter"
    weight: 900
    size_multiplier: 3.5
  scale_system: "perfect_fourth"
  weight_matrix:
    title: 900
    heading: 700
    body: 400
    caption: 300

motion:
  transitions: ["cut", "wipe-left", "zoom-in", "dissolve"]
  animation_style: "Commercial pacing — tight cuts aligned to narration beats; CTA moment held for emphasis"
  pacing_rules:
    min_scene_hold_seconds: 2.0
    max_scene_hold_seconds: 10
    text_card_hold_seconds: 2.0
    stat_card_hold_seconds: 2.5
    transition_duration_seconds: 0.2
  entrance: "scale-up with ease-out (0.85 -> 1.0)"
  exit: "cut or dissolve"

audio:
  voice_style: "Professional, warm, authoritative; pacing aligned to commercial rhythm"
  music_mood: "Emotionally supportive; rises at CTA moment"
  music_volume: 0.15
  sfx_style: "Subtle — CTA moment and brand reveal only"
  ducking_threshold_db: -18
  voice_variation_allowed: true
  hero_moment_voice_shift: "Slower, deliberate at CTA; full stop before brand name"

asset_generation:
  image_prompt_prefix: "commercial photography quality, product-forward, cinematic lighting, "
  image_negative_prompt: "amateur, blurry, watermark, text overlay, stock photo cliché"
  diagram_style: "clean product diagrams, dark background, precise lines"
  consistency_anchors:
    - "Product always lit and positioned identically across scenes"
    - "Brand color applied to CTA text and final frame consistently"
    - "Dark backgrounds (#0D0D0D to #1A1A2E) unless brand-supplied"
    - "Typography weight contrast: body is light, key messages are heavy"

overlays:
  stat_card:
    bg: "#1A1A2E"
    border: "#E94560"
    radius: 8
    shadow: "0 0 16px rgba(233,69,96,0.25)"
  key_term:
    bg: "#16213E"
    text: "#F5F5F5"
    radius: 4
  code_block:
    bg: "#0D0D0D"
    text: "#F5F5F5"
    highlight: "#E94560"

quality_rules:
  - "No Ken Burns on product shots — static products use motion backgrounds or camera movement"
  - "CTA beat must be visually distinct: scale up, color shift, or deliberate hold"
  - "Subtitles must be legible on all variants including 9:16 and 1:1 crops"
  - "Brand name must appear in the final frame — non-negotiable"
  - "Music rises to full volume at brand landing beat (final 5–10%)"
  - "Every scene with motion_required:true must contain actual video or animation"
  - "Minimum contrast ratio 4.5:1 for all subtitle and on-screen text"

chart_palette:
  - "#E94560"
  - "#0F3460"
  - "#533483"
  - "#E8C547"
  - "#05C3DE"
  - "#1A1A2E"

color_rules:
  harmony_type: "complementary"
  contrast_validation: true
  colorblind_safe: true
```

- [ ] **Step 2: Validate the playbook loads and passes schema**

Run from the project root:
```bash
python3 -c "
from styles.playbook_loader import load_playbook, validate_playbook
pb = load_playbook('ad-brand')
errors = validate_playbook(pb)
if errors:
    print('ERRORS:', errors)
else:
    print('PASS — ad-brand playbook valid')
    print('identity.name:', pb['identity']['name'])
    print('audio.ducking_threshold_db:', pb['audio']['ducking_threshold_db'])
"
```
Expected output:
```
PASS — ad-brand playbook valid
identity.name: Ad Brand
audio.ducking_threshold_db: -18
```

- [ ] **Step 3: Commit**

```bash
git add styles/ad-brand.yaml
git commit -m "feat: add ad-brand playbook for ad-video pipeline"
```

---

## Task 2: Pipeline Manifest

**Files:**
- Create: `pipeline_defs/ad-video.yaml`

- [ ] **Step 1: Write the manifest file**

```yaml
name: "Ad Video Pipeline"
version: "1.0"
category: custom
stability: beta
description: "Orchestrated ad/commercial video pipeline. Supports animated and cinematic render modes, derivative aspect-ratio variants (9:16, 1:1, 15s short), mandatory sample approval, and required TTS + subtitle generation."

orchestration:
  skill: pipelines/ad-video/executive-producer
  budget_default_usd: 5.00
  max_wall_time_minutes: 30
  max_revisions_per_stage: 3
  max_send_backs: 3

compatible_playbooks:
  - ad-brand
  - flat-motion-graphics
  - clean-professional

required_skills:
  - skills/pipelines/ad-video/executive-producer.md
  - skills/pipelines/ad-video/idea-director.md
  - skills/pipelines/ad-video/proposal-director.md
  - skills/pipelines/ad-video/script-director.md
  - skills/pipelines/ad-video/scene-director.md
  - skills/pipelines/ad-video/scene-director-animated.md
  - skills/pipelines/ad-video/scene-director-cinematic.md
  - skills/pipelines/ad-video/asset-director.md
  - skills/pipelines/ad-video/asset-director-animated.md
  - skills/pipelines/ad-video/asset-director-cinematic.md
  - skills/pipelines/ad-video/edit-director.md
  - skills/pipelines/ad-video/compose-director.md
  - skills/pipelines/ad-video/publish-director.md

stages:
  # ── Pre-Production ──────────────────────────────────────────────
  - name: idea
    skill: pipelines/ad-video/idea-director
    produces:
      - brief
    checkpoint_required: false
    review_focus:
      - "style_mode candidate present (animated or cinematic)"
      - "All reference files assigned inferred_role + reason"
      - "brand_context fields populated: product, audience, tone, platform"
    success_criteria:
      - "brief artifact produced with style_mode_candidate"
      - "reference_files list complete with role annotations"

  - name: proposal
    skill: pipelines/ad-video/proposal-director
    required_artifacts_in:
      - brief
    produces:
      - proposal_packet
    checkpoint_required: true
    human_approval_default: true
    review_focus:
      - "style_mode locked — no further changes allowed downstream"
      - "All reference files confirmed (inferred_role presented to user)"
      - "Derivatives explicitly opted in or out (9:16, 1:1, 15s short)"
      - "3 concept options with cost estimates presented"
    success_criteria:
      - "approval.status == approved or approved_with_changes"
      - "style_mode stored in EP_STATE"
      - "derivative_variants stored in EP_STATE"
      - "approved_budget_usd stored in EP_STATE"

  # ── Production ──────────────────────────────────────────────────
  - name: script
    skill: pipelines/ad-video/script-director
    required_artifacts_in:
      - proposal_packet
    produces:
      - script
    checkpoint_required: false
    review_focus:
      - "Four beats present: hook, build, reveal, cta_brand"
      - "Word count within ±10% of duration_target_seconds × 2.5"
      - "Mode annotations present on lines where animated/cinematic treatment differs"
      - "CTA section ends with brand name — non-negotiable"
    success_criteria:
      - "script artifact produced with sections array"
      - "total_words within ±10% of target"

  - name: scene_plan
    skill: pipelines/ad-video/scene-director
    required_artifacts_in:
      - script
      - proposal_packet
    produces:
      - scene_plan
    checkpoint_required: false
    review_focus:
      - "Total scene duration covers script duration (±0.5s)"
      - "crop_regions present for every scene when derivatives opted in"
      - "core field present on every scene"
      - "No more than 3 consecutive scenes of same type"
      - "motion_required field present on scenes requiring actual video"
    success_criteria:
      - "scene_plan artifact produced"
      - "sum(scene.duration) within ±0.5s of total script duration"
      - "If derivative_variants non-empty: all scenes have crop_regions"

  - name: assets
    skill: pipelines/ad-video/asset-director
    required_artifacts_in:
      - scene_plan
      - script
    produces:
      - asset_manifest
    checkpoint_required: false
    sub_stages:
      - name: sample
        description: "Generate 10–15s preview clip from first 2–3 scenes. Always runs. Human approval required before full asset generation."
        human_approval_default: true
        review_focus:
          - "Sample covers first 2–3 scenes"
          - "Sample duration 10–15s"
          - "Style and quality representative of full video"
          - "sample_clip file exists"
          - "sample_approved == true in EP_STATE after user decision"
      - name: full_generation
        description: "Generate all remaining assets after sample approval."
        human_approval_default: false
        review_focus:
          - "TTS audio file generated for every script section"
          - "Subtitle file (SRT/VTT) generated"
          - "All scene assets match scene_plan required_assets"
          - "Style consistency across all generated images"
          - "asset_manifest complete with all required files"
          - "narration_durations populated in EP_STATE"
          - "subtitle_file present in asset_manifest"
    review_focus:
      - "sample_approved == true before full generation proceeds"
      - "TTS files present for all sections"
      - "Subtitle file present"
      - "Budget not exceeded"
    success_criteria:
      - "asset_manifest artifact produced"
      - "sample_approved == true"
      - "subtitle_file present"

  # ── Post-Production ─────────────────────────────────────────────
  - name: edit
    skill: pipelines/ad-video/edit-director
    required_artifacts_in:
      - scene_plan
      - asset_manifest
    produces:
      - edit_decisions
    checkpoint_required: false
    review_focus:
      - "Timeline covers 0 to total_duration with no gaps"
      - "Music ducking set to -18 dB during all narration segments"
      - "Subtitle burn configured"
      - "Derivative edit specs present when derivative_variants non-empty"
    success_criteria:
      - "edit_decisions artifact produced"
      - "audio.target_db == -18 for all narration windows"
      - "subtitles.burn_in == true"

  - name: compose
    skill: pipelines/ad-video/compose-director
    required_artifacts_in:
      - edit_decisions
      - asset_manifest
    produces:
      - render_report
    checkpoint_required: false
    review_focus:
      - "Primary 16:9 render complete and valid"
      - "crop_regions verified present before each derivative render"
      - "Each derivative is a separate output file"
      - "Duration within ±5% of target"
      - "Audio channels: stereo"
    success_criteria:
      - "render_report artifact produced"
      - "output_files contains primary 16:9 file"
      - "output_files contains one entry per opted-in derivative"

  - name: publish
    skill: pipelines/ad-video/publish-director
    required_artifacts_in:
      - render_report
      - proposal_packet
    produces:
      - publish_log
    checkpoint_required: false
    review_focus:
      - "output_file_matrix present with all rendered files"
      - "Metadata complete: title, description, tags, platform targets"
      - "Thumbnail concept written"
    success_criteria:
      - "publish_log artifact produced"
      - "output_file_matrix non-empty"
```

> **Note:** The manifest uses field names and values from the existing `schemas/pipelines/pipeline_manifest.schema.json` (no schema modifications): `stability: beta` (enum: production|beta), `orchestration.budget_default_usd` (not `budget_usd`), `skill:` + `produces:` on stages (convention matching `animated-explainer.yaml`). Stage-level descriptions are carried in the director skill files, not in the manifest.

- [ ] **Step 2: Validate the manifest loads**

```bash
python3 -c "
from lib.pipeline_loader import load_pipeline
p = load_pipeline('ad-video')
print('PASS — pipeline loaded')
print('name:', p['name'])
print('stages:', [s['name'] for s in p['stages']])
print('required_skills count:', len(p['required_skills']))
"
```
Expected output:
```
PASS — pipeline loaded
name: Ad Video Pipeline
stages: ['idea', 'proposal', 'script', 'scene_plan', 'assets', 'edit', 'compose', 'publish']
required_skills count: 13
```

- [ ] **Step 3: Commit**

```bash
git add pipeline_defs/ad-video.yaml
git commit -m "feat: add ad-video pipeline manifest"
```

---

## Task 3: Executive Producer Skill

**Files:**
- Create: `skills/pipelines/ad-video/executive-producer.md`

- [ ] **Step 1: Create the directory and write the skill file**

```bash
mkdir -p skills/pipelines/ad-video
```

Write `skills/pipelines/ad-video/executive-producer.md`:

````markdown
# Executive Producer — Ad Video Pipeline

## When to Use

You are the **Executive Producer (EP)** for an ad/commercial video. You orchestrate the pipeline serially: spawning each stage director, reviewing their output, and either passing it forward or sending it back. You are the stateful brain; directors are stateless workers.

## EP_STATE Schema

```
EP_STATE:
  pipeline: ad-video
  style_mode: null            # locked at proposal: "animated" | "cinematic"
  render_runtime: null        # locked at proposal: "remotion" | "ffmpeg"
  playbook: ad-brand
  target_duration_seconds: null
  budget_total_usd: 5.00
  budget_spent_usd: 0.0
  budget_remaining_usd: 5.00
  approved_budget_usd: null

  derivative_variants: []     # locked at proposal: subset of ["9:16", "1:1", "15s"]
  sample_approved: false      # set true after sample sub-stage approval

  artifacts:
    idea: null
    proposal: null
    script: null
    scene_plan: null
    assets: null
    edit: null
    compose: null
    publish: null

  brand_context: null         # from idea: {product, audience, tone, platform, reference_files}
  selected_concept: null      # from proposal
  production_plan: null       # from proposal
  reference_files: []         # confirmed at proposal with inferred_role + reason

  narration_durations: {}     # section_id → actual_seconds (populated after TTS)
  total_narration_seconds: 0
  style_anchors: {}
  revision_counts: {}
  issues_log: []
```

## Execution Protocol

### Phase 0: Initialize

1. Load `pipeline_defs/ad-video.yaml`
2. Load playbook (`ad-brand` or user-selected compatible playbook)
3. Set budget: default $5.00, override from `proposal.approval.approved_budget_usd` after proposal
4. Initialize EP_STATE

### Phase 1: Execute Stages Serially

Order: `idea → proposal → script → scene_plan → assets → edit → compose → publish`

**Pre-production stages (idea, proposal)** — zero cost, no tool calls.

After proposal approval, extract and store in EP_STATE:
- `style_mode` from `proposal_packet.style_mode` (LOCKED — never changes downstream)
- `render_runtime` from `proposal_packet.render_runtime`
- `derivative_variants` from `proposal_packet.derivative_variants`
- `selected_concept` from `proposal_packet.selected_concept`
- `production_plan` from `proposal_packet.production_plan`
- `approved_budget_usd` from `proposal_packet.approval.approved_budget_usd`
- `reference_files` (confirmed list with `inferred_role` + `reason`)

```
EXECUTE_STAGE(stage_name):
  1. PREPARE
     Load director skill for this stage.
     Inject EP_STATE (prior artifacts, budget, style_anchors, style_mode).
     Inject EP feedback if this is a revision attempt.

  2. SPAWN DIRECTOR
     Director executes its full process and produces an artifact.

  3. REVIEW
     Schema validation.
     Check review_focus items from pipeline manifest.
     Check success_criteria from pipeline manifest.
     Run EP-SPECIFIC CROSS-STAGE CHECKS (below).

  4. GATE DECISION
     PASS → Store artifact. Update budget/tracking. Log "[stage] PASSED". Continue.
     REVISE → Increment revision_counts[stage]. If >= 3: PASS WITH WARNINGS.
               Else: compose specific feedback, re-run director, re-run review.
     SEND_BACK(target) → Invalidate artifacts after target. Re-execute from target.
                          Max 1 send-back per stage pair. Max 3 total send-backs.
```

### Phase 2: Final QA

After all 8 stages:
1. Probe output video: duration ±5% of target, resolution, audio channels
2. A/V sync: narration timestamps vs visual cut points (tolerance ±0.5s)
3. Style consistency: all generated images look like same video
4. Budget reconciliation: actual spend vs approved budget
5. Derivative file check: one output file per opted-in variant

## EP-Specific Cross-Stage Checks

### After IDEA stage
```
CHECK: Brief completeness
- style_mode_candidate present?
- All reference_files have inferred_role + reason?
- brand_context fields: product, audience, tone, platform all present?
- If any missing: REVISE idea
```

### After PROPOSAL stage — CRITICAL
```
CHECK: Approval gate
- approval.status == "approved" or "approved_with_changes"?
- If "pending" or "rejected": STOP. Present to user and wait.
- style_mode stored in EP_STATE (LOCKED)
- derivative_variants stored in EP_STATE
- approved_budget_usd stored
- render_runtime stored (check: "remotion" or "ffmpeg" only — NO silent runtime swap)
```

### After SCRIPT stage
```
CHECK: Word count vs duration
- target_words = target_duration_seconds × 2.5
- If total_words > target_words × 1.10: REVISE — "Script is N words. Target is T words (±10%). Cut X words."
- If total_words < target_words × 0.90: REVISE — "Script is too short. Add X words."
CHECK: Four beats present
- sections must include: hook, build, reveal, cta_brand
- cta_brand section must end with brand name
```

### After SCENE_PLAN stage
```
CHECK: Duration coverage
- sum(scene.duration_seconds) within ±0.5s of sum(script.sections[].duration_estimate_seconds)
CHECK: Derivative readiness — CRITICAL
- If derivative_variants non-empty:
    Every scene must have crop_regions with entries for each opted-in variant
    If any scene missing crop_regions: REVISE scene_plan
CHECK: Core/trimmable tagging
- Every scene has core field (true/false)
- If "15s" in derivative_variants: verify scenes with core:true sum to ≤15s
```

### After ASSETS stage
```
CHECK: Sample approval
- sample_approved must be true before full generation proceeds
- If sample rejected: SEND_BACK to scene_plan or script depending on feedback
CHECK: Narration duration feedback loop
- For each TTS file: probe actual duration
- Store in EP_STATE.narration_durations
- If actual > planned × 1.15: adjust scene duration OR send back to script
CHECK: Required asset presence
- TTS audio file for every script section? (REQUIRED)
- Subtitle file (SRT or VTT)? (REQUIRED)
- Budget gate: if budget_spent > budget_total × 0.9 and stages remain: alert
```

### After EDIT stage
```
CHECK: Timeline completeness
- Covers 0 to total_duration with no gaps
- All asset references point to existing files
CHECK: Music ducking
- target_db == -18 for all narration windows (playbook requirement)
CHECK: Subtitle burn
- subtitles.burn_in == true
```

### After COMPOSE stage
```
CHECK: Output validation
- Probe primary file: duration ±5%, resolution, stereo audio
- If derivative_variants non-empty: one output file per variant
CHECK: Derivative contract
- crop_regions were verified before each derivative render
- If any derivative missing: REVISE compose
```

## Feedback Templates

### To Script Director
```
EP FEEDBACK — Script Revision Required
Reason: {reason}
Issue: {detail}
Constraint: {word_count_limit}
Keep: {what was good}
Change: {specific rewrite instructions}
```

### To Scene Director
```
EP FEEDBACK — Scene Plan Revision Required
Reason: {reason}
Affected scenes: {scene_ids}
Constraint: {crop_regions / duration / core-trimmable / motion_required}
style_mode: {animated | cinematic}
```

### To Asset Director
```
EP FEEDBACK — Asset Revision Required
Reason: {reason}
Affected assets: {asset_ids}
Style anchors: {from EP_STATE.style_anchors}
Budget remaining: ${remaining}
sample_approved: {true|false}
```

### To Compose Director
```
EP FEEDBACK — Re-render Required
Reason: {reason}
Issue: {audio_sync | duration | derivative_missing | crop_region_error}
Expected: {description}
Actual: {what was produced}
```

## Quality Gates Summary

| Gate | After Stage | Critical Checks | Fail Action |
|------|------------|----------------|-------------|
| G1 | idea | Brief completeness, style_mode_candidate, ref role annotations | Revise idea |
| G2 | proposal | User approval, style_mode locked, derivatives locked | Wait for user |
| G3 | script | Word count ±10%, four beats, brand name in CTA | Revise script |
| G4 | scene_plan | Duration coverage, crop_regions if derivatives, core tagging | Revise scene_plan |
| G5 | assets | sample_approved, TTS required, subtitles required, budget | Send-back or revise |
| G6 | edit | Timeline complete, ducking -18 dB, subtitle burn | Revise edit |
| G7 | compose | Duration ±5%, one file per derivative | Revise compose |
| G8 | publish | output_file_matrix non-empty, metadata complete | Revise publish |

## Execution Limits

| Limit | Value |
|-------|-------|
| Max revisions per stage | 3 |
| Max send-backs per stage pair | 1 |
| Max total send-backs | 3 |
| Max budget | $5.00 (default) |
| Max wall time | 30 minutes |

After any limit hit: **proceed with warnings**, never block indefinitely.
````

- [ ] **Step 2: Verify the file exists**

```bash
test -f skills/pipelines/ad-video/executive-producer.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/executive-producer.md
git commit -m "feat: add ad-video executive-producer skill"
```

---

## Task 4: Idea Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/idea-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/idea-director.md`:

````markdown
# Idea Director — Ad Video Pipeline

## When to Use

You are the Idea Director for the ad-video pipeline. You receive a brand brief (or raw text description) from the user and produce a `brief` artifact that becomes the creative foundation for the entire pipeline.

Unlike the explainer pipeline, you do NOT research topic angles. Instead, you parse the brand's own brief and surface the creative direction already embedded in their materials.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/brief.schema.json` | Artifact validation |
| Playbook | `styles/ad-brand.yaml` (default) | Style constraints |
| Pipeline | `pipeline_defs/ad-video.yaml` | Stage context |

## Process

### Step 1: Parse Brand Context

Extract from the user's input:

| Field | What to extract | Required |
|-------|----------------|----------|
| `product` | What is being advertised | Yes |
| `audience` | Primary target demographic | Yes |
| `tone` | Desired emotional register | Yes |
| `platform` | Where the ad will run (TV, YouTube, TikTok, streaming) | Yes |
| `duration_target_seconds` | Requested ad length (default: 60s if not specified) | Yes |
| `brand_name` | The brand/product name that must appear at end | Yes |
| `key_message` | The single message the viewer must retain | Yes |

If any required field is missing, ask the user before proceeding.

### Step 2: Analyse Reference Files

The user may provide reference files: existing ads, brand guidelines, competitor examples, mood board images, product photos.

For each file, determine:
- `inferred_role`: one of `brand_guideline`, `competitor_ad`, `mood_reference`, `product_asset`, `style_reference`, `existing_ad`
- `reason`: one sentence explaining why you assigned this role

**These inferences will be presented to the user at proposal for confirmation. Do not treat them as facts — treat them as hypotheses.**

```json
{
  "filename": "brand_guide_2024.pdf",
  "inferred_role": "brand_guideline",
  "reason": "Document contains color palette, typography specifications, and logo usage rules consistent with a brand standards document."
}
```

### Step 3: Infer Style Mode Candidate

Based on brand context and reference files, infer the most likely render mode:

| Signal | Suggests |
|--------|----------|
| Live product shots, lifestyle imagery, cinematic references | `cinematic` |
| Motion graphics in existing ads, tech brand, data-driven product | `animated` |
| Mixed signals | `animated` (default when uncertain) |

Set `style_mode_candidate` in the brief. This is a **hypothesis** — the user confirms it at proposal.

Logic:
```
IF reference_files contain live action footage or cinematic photos:
    style_mode_candidate = "cinematic"
ELIF reference_files contain motion graphics OR product is tech/SaaS/app:
    style_mode_candidate = "animated"
ELSE:
    style_mode_candidate = "animated"  # safe default
```

### Step 4: Assemble Brief Artifact

```json
{
  "version": "1.0",
  "title": "{brand_name} — {key_message} ({duration}s {platform} ad)",
  "hook": "{opening hook line — first thing the viewer sees/hears}",
  "key_points": [
    "{concrete claim the ad will prove — beat 2}",
    "{concrete claim the ad will prove — beat 3}",
    "{CTA — what the viewer should do}"
  ],
  "core_message": "{single sentence the viewer will remember tomorrow}",
  "cta": "{specific action: visit URL, download app, call number, etc.}",
  "tone": "{extracted tone}",
  "style": "ad-brand",
  "target_audience": "{extracted audience}",
  "target_platform": "{youtube|instagram|tiktok|linkedin|tv|generic}",
  "target_duration_seconds": 60,
  "brand_name": "{brand_name}",
  "brand_context": {
    "product": "{product}",
    "audience": "{audience}",
    "tone": "{tone}",
    "platform": "{platform}",
    "key_message": "{key_message}"
  },
  "reference_files": [
    {
      "filename": "{filename}",
      "inferred_role": "{role}",
      "reason": "{one sentence reason}"
    }
  ],
  "style_mode_candidate": "animated",
  "angle_options": [
    {"name": "{angle 1}", "description": "{description}"},
    {"name": "{angle 2}", "description": "{description}"},
    {"name": "{angle 3}", "description": "{description}"}
  ],
  "selected_angle": "{selected}"
}
```

### Step 5: Self-Evaluate Before Submitting

| Criterion | Check |
|-----------|-------|
| Hook strength | Is the opening line a genuine attention-grabber for this audience? |
| Brand name present | Will the brand name appear in the final frame? |
| CTA specificity | Is the CTA actionable (URL, number, specific action)? |
| Reference roles | Is each role a plausible hypothesis, not a guess? |
| style_mode_candidate | Is the inference grounded in actual evidence from the brief/refs? |
| Duration fit | Does 60s (or specified duration) match the platform? |

If any criterion fails, iterate before submitting.

### Step 6: Submit

Call `handle_ad_idea(state, {"brief": brief_json})` to validate and persist.

## Common Pitfalls

- **Inventing brand context**: Never invent product details not present in the user's input. Ask.
- **style_mode_candidate as certainty**: Always frame this as "based on your references, I'd suggest animated — confirm at proposal."
- **Missing brand_name**: The brand name MUST appear in the brief. It is required for the final frame rule.
- **Vague CTA**: "Learn more" is not a CTA. "Visit brand.com/launch" is a CTA.
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/idea-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/idea-director.md
git commit -m "feat: add ad-video idea-director skill"
```

---

## Task 5: Proposal Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/proposal-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/proposal-director.md`:

````markdown
# Proposal Director — Ad Video Pipeline

## When to Use

You are the Proposal Director. You receive the `brief` artifact from the idea director and produce a `proposal_packet` that the EP presents to the user for approval. This is the last stage before money is spent.

**Critical responsibilities:**
1. Lock `style_mode` (confirm the candidate from idea stage)
2. Confirm all reference files (present inferred roles, get user sign-off)
3. Opt-in derivative variants (9:16, 1:1, 15s short)
4. Present 3 concept options with cost estimates
5. Select render runtime

## Hard Rule: Runtime Selection — Present Both

Read `AGENT_GUIDE.md` → "Present Both Composition Runtimes (HARD RULE)" for the governance contract. A silent default is a CRITICAL reviewer finding.

`style_mode` narrows the `render_runtime` choice but does NOT unilaterally select it. The valid set is:

| `style_mode` | Eligible `render_runtime` engines | Reasoning |
|--------------|-----------------------------------|-----------|
| `animated` | `remotion` **AND** `hyperframes` | Both are animation engines; different creative grammars (React scene stack vs. HTML/GSAP kinetic typography) |
| `cinematic` | `ffmpeg` only | HyperFrames and Remotion don't render live-action composites; ffmpeg is the only viable engine |

**MANDATORY workflow — Present Both, don't silently default:**

1. Query `video_compose.get_info()["render_engines"]`. Determine which of `remotion` and `hyperframes` are available.
2. **If `style_mode == "animated"`**:
   - If both `remotion` and `hyperframes` are available: **Present Both** runtimes to the user with one-line fit + one-line tradeoff for this concept:
     - **Remotion** — React scene stack, composable components, strong for data-driven and typographic ads with clear structural beats.
     - **HyperFrames** — HTML/GSAP motion, registry blocks, strong for kinetic typography, brand-forward title sequences, and GSAP-native transitions.
   - If only one is available: state which and explain the other is unavailable (do NOT silently default).
3. **If `style_mode == "cinematic"`**: runtime is locked to `ffmpeg` — state this explicitly so the user confirms rather than defaults.
4. Wait for explicit user approval before writing `render_runtime` into `proposal_packet.production_plan`.
5. Log a `render_runtime_selection` decision in `decision_log` with:
   - `options_considered`: all runtimes that were real choices (include `ffmpeg` in cinematic mode even when it's the only option, and mark rejected runtimes with `rejected_because: "runtime not available on this machine"` or `rejected_because: "style_mode == cinematic — hyperframes/remotion do not support live-action composites"`).
   - `selected`: user's choice.
   - `reason`: one-sentence rationale for why this concept's creative grammar fits the selected runtime.

**Silent runtime swap is a CRITICAL failure.** A `render_runtime_selection` decision with only one option considered when both were available is a CRITICAL reviewer finding. Once the user has approved, the runtime is locked — do NOT change it downstream without user confirmation and a new decision log entry.

## Process

### Step 1: Pre-flight Check

Before presenting anything to the user, check tool availability:

| Tool category | Required for |
|--------------|-------------|
| TTS provider (ElevenLabs or equivalent) | All modes — narration REQUIRED |
| Image generator (Flux, DALL-E, or equivalent) | All modes |
| Video generator (Wan, Kling, or equivalent) | Scenes with motion_required:true |
| Music generator (MiniMax Music or equivalent) | All modes |
| Remotion renderer | animated mode only |
| ffmpeg | cinematic mode only |

Log unavailable tools. If a REQUIRED tool is unavailable (TTS, image gen), alert the user.

### Step 2: Confirm Style Mode

Present the idea director's style_mode_candidate to the user with reasoning:

> "Based on your reference files, I'm suggesting **{animated|cinematic}** mode.
> - Animated: motion graphics, text animations, generated video backgrounds, Remotion renderer
> - Cinematic: AI-generated photography, real-footage treatment, ffmpeg renderer
>
> Your references suggest {animated|cinematic} because: {reason from idea brief}.
> Confirm or choose the other mode?"

Store confirmed value in `proposal_packet.style_mode`. **This cannot change after proposal approval.**

### Step 3: Confirm Reference Files

For each reference file in `brief.reference_files`, present the inferred role:

> "I've reviewed your reference files. Please confirm or correct these roles:
> - `{filename}` → **{inferred_role}**: {reason}
> - `{filename}` → **{inferred_role}**: {reason}"

The user must confirm or correct ALL reference files. No inference passes through silently.

Store confirmed list in `proposal_packet.reference_files`.

### Step 4: Derivative Variants Opt-In

Present derivative options:

> "Your primary output is 16:9. Would you like any of these additional variants?
> - **9:16** (vertical): Instagram Stories, TikTok, YouTube Shorts — requires safe zone planning in scene design
> - **1:1** (square): Instagram Feed, LinkedIn — requires safe zone planning
> - **15s short**: A condensed cut using only core scenes — requires scene tagging in scene design
>
> Select any combination, or none. Each adds ~$0.30–$0.80 to the estimated cost."

Store selection in `proposal_packet.derivative_variants`.

Crop regions for reference (pass to EP_STATE for scene director):
```
9:16 crop: {x: 656, y: 0, w: 608, h: 1080}   # center-crop from 1920×1080
1:1 crop:  {x: 420, y: 0, w: 1080, h: 1080}  # center-crop from 1920×1080
```

### Step 5: Present 3 Concept Options

Generate 3 genuinely different creative concepts for the ad. Each must differ in narrative structure, not just wording.

For each concept:

| Field | What |
|-------|------|
| `name` | Short title (5–8 words) |
| `hook` | Opening line (under 15 words) |
| `narrative_structure` | One of: problem-solution, desire-fulfillment, contrast, journey, social-proof, demo-reveal |
| `style_mode` | Must match confirmed style_mode |
| `suggested_playbook` | `ad-brand` (or other compatible playbook) |
| `estimated_cost_usd` | Breakdown: TTS + image_gen + video_gen + music + render |
| `estimated_duration_seconds` | Target duration |

**Concept diversity checklist:**
- [ ] No two concepts use the same narrative structure
- [ ] At least one concept leads with emotional appeal
- [ ] At least one concept leads with product proof/demo
- [ ] Cost estimates differ (reflect asset count and tool usage)

### Step 6: Assemble Proposal Packet

```json
{
  "version": "1.0",
  "pipeline": "ad-video",
  "style_mode": "animated",
  "render_runtime": "remotion",
  "derivative_variants": ["9:16"],
  "reference_files": [
    {
      "filename": "brand_guide_2024.pdf",
      "confirmed_role": "brand_guideline",
      "reason": "User confirmed: contains color palette and typography specs"
    }
  ],
  "concept_options": [
    {
      "id": "C1",
      "name": "The Problem You Didn't Know You Had",
      "hook": "Every morning, you're wasting 45 minutes you can't get back.",
      "narrative_structure": "problem-solution",
      "style_mode": "animated",
      "suggested_playbook": "ad-brand",
      "estimated_cost_usd": 1.85,
      "estimated_duration_seconds": 60
    },
    {
      "id": "C2",
      "name": "Watch It Work in 60 Seconds",
      "hook": "Here's exactly what happens when you press start.",
      "narrative_structure": "demo-reveal",
      "style_mode": "animated",
      "suggested_playbook": "ad-brand",
      "estimated_cost_usd": 2.10,
      "estimated_duration_seconds": 60
    },
    {
      "id": "C3",
      "name": "The People Who Already Switched",
      "hook": "12,000 people made this decision last week.",
      "narrative_structure": "social-proof",
      "style_mode": "animated",
      "suggested_playbook": "ad-brand",
      "estimated_cost_usd": 1.65,
      "estimated_duration_seconds": 60
    }
  ],
  "selected_concept": null,
  "production_plan": {
    "stages": [
      {"name": "assets", "tools": ["elevenlabs_tts", "flux_image_gen", "wan_video_gen", "minimax_music"], "estimated_cost_usd": 1.50},
      {"name": "compose", "tools": ["remotion"], "estimated_cost_usd": 0.00}
    ]
  },
  "approval": {
    "status": "pending",
    "approved_budget_usd": null,
    "modifications": null
  }
}
```

### Step 7: Present to User and Await Approval

Present all three concepts. Include:
- Total estimated cost (including derivatives if opted in)
- Breakdown by concept
- Which concept you recommend and why

Wait for the user to:
- Select a concept as-is, or
- Request modifications, or
- Describe a custom direction

Update `approval.status` to `"approved"` or `"approved_with_changes"`.

**Do NOT proceed past this stage without explicit approval.**

### Step 8: Submit

Call `handle_ad_proposal(state, {"proposal_packet": proposal_packet_json})`.

## Common Pitfalls

- **Silent runtime swap**: Never change render_runtime without also changing style_mode. Log it. State it. Never hide it.
- **Skipping reference confirmation**: All reference files must be confirmed by the user. No inference passes silently.
- **Identical concepts**: Three versions of "show the product working" are not three concepts. Use different narrative structures.
- **Missing cost breakdown**: Cost estimates must be itemized. A lump sum is not a cost estimate.
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/proposal-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/proposal-director.md
git commit -m "feat: add ad-video proposal-director skill"
```

---

## Task 6: Script Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/script-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/script-director.md`:

````markdown
# Script Director — Ad Video Pipeline

## When to Use

You are the Script Director. You receive the approved `proposal_packet` (including `selected_concept`) and produce a `script` artifact with four-beat ad copy structured for the target duration.

## Word Count Calibration

**Formula:** `target_words = target_duration_seconds × 2.5`

At ad narration pace (~2.5 words per second, including natural pauses and ad pacing):
- 30s ad → ~75 words narration
- 60s ad → ~150 words narration
- 90s ad → ~225 words narration

**Acceptable range:** ±10% of `target_words`

The EP will reject scripts outside this range. Do not pad or compress unnaturally — adjust sentence structure.

## Four-Beat Structure

Every ad script must have exactly these four beats in order:

| Beat | Section ID | Duration % | Purpose |
|------|-----------|-----------|---------|
| Hook | `hook` | ~15% | Arrest attention. Create urgency or curiosity. No brand name yet. |
| Build | `build` | ~40% | Develop the problem or desire. Stack evidence. |
| Reveal / Climax | `reveal` | ~30% | Introduce the solution. The emotional peak. |
| CTA + Brand Landing | `cta_brand` | ~15% | Call to action. Brand name must appear. Music peaks here. |

**Rule:** The `cta_brand` section MUST end with the brand name. This is a hard requirement enforced at every stage.

## Mode Annotations

Add mode-specific direction notes inline using `[ANIMATED: ...]` or `[CINEMATIC: ...]` markers. These guide the scene director without duplicating content.

Examples:
```
"Forty-five minutes." [ANIMATED: counter animation spinning down]
"That's what the average commuter loses every morning." [CINEMATIC: slow-motion crowd shot, faces blurred]
"Not anymore." [ANIMATED: bold text cut + color flash] [CINEMATIC: hard cut to product hero]
```

## Script Artifact Format

```json
{
  "version": "1.0",
  "title": "{from proposal selected_concept.name}",
  "style_mode": "{from EP_STATE.style_mode}",
  "target_duration_seconds": 60,
  "target_words": 150,
  "total_words": 148,
  "sections": [
    {
      "id": "hook",
      "beat": "hook",
      "narration": "Every morning, you're wasting 45 minutes you can't get back.",
      "word_count": 12,
      "duration_estimate_seconds": 5,
      "mode_annotations": {
        "animated": "Countdown timer animation: 0:45 → 0:00",
        "cinematic": "Close-up alarm clock, hand slamming snooze"
      }
    },
    {
      "id": "build_1",
      "beat": "build",
      "narration": "Traffic. Queues. Systems that weren't built for how you actually work.",
      "word_count": 14,
      "duration_estimate_seconds": 6,
      "mode_annotations": {
        "animated": "Split-screen pain points with motion graphics labels",
        "cinematic": "Quick cuts: traffic jam, queue, frustrated face"
      }
    },
    {
      "id": "build_2",
      "beat": "build",
      "narration": "The average team loses 4 hours a week to tasks a machine could do in seconds.",
      "word_count": 17,
      "duration_estimate_seconds": 7,
      "mode_annotations": {
        "animated": "Animated stat card: 4 HRS/WEEK",
        "cinematic": "Stat text overlay on footage of desk work"
      }
    },
    {
      "id": "reveal",
      "beat": "reveal",
      "narration": "Introducing Flowcut — the workflow tool that learns your patterns and eliminates the drag.",
      "word_count": 16,
      "duration_estimate_seconds": 7,
      "mode_annotations": {
        "animated": "Product logo reveal with motion graphics burst",
        "cinematic": "Hero product shot, camera push-in"
      }
    },
    {
      "id": "cta_brand",
      "beat": "cta_brand",
      "narration": "Start free at flowcut.io. Flowcut.",
      "word_count": 6,
      "duration_estimate_seconds": 4,
      "mode_annotations": {
        "animated": "URL text animation + brand logo hold",
        "cinematic": "URL lower-third overlay, brand logo fade in"
      }
    }
  ],
  "cta": "Start free at flowcut.io",
  "brand_name": "Flowcut"
}
```

## Validation Before Submitting

- [ ] `total_words` is within ±10% of `target_words`
- [ ] Sections include: `hook`, at least one `build`, `reveal`, `cta_brand`
- [ ] `cta_brand.narration` ends with `brand_name`
- [ ] `mode_annotations` present on every section
- [ ] `duration_estimate_seconds` values sum to approximately `target_duration_seconds`

## Common Pitfalls

- **Over-writing the build**: Build sections often bloat. If total words exceed target, cut build first.
- **Weak hook**: The hook must arrest attention in 3–5 seconds. It does NOT introduce the brand.
- **Missing brand name at CTA**: Non-negotiable. The last word(s) of `cta_brand` narration must be the brand name.
- **Generic CTA**: "Visit our website" is not a CTA. Include the actual URL or specific action.
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/script-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/script-director.md
git commit -m "feat: add ad-video script-director skill"
```

---

## Task 7: Scene Director Base Skill

**Files:**
- Create: `skills/pipelines/ad-video/scene-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/scene-director.md`:

````markdown
# Scene Director — Ad Video Pipeline (Base)

## When to Use

You are the Scene Director (base). You receive the `script` artifact and map each script section to one or more visual scenes. You then delegate to the appropriate mode supplement for scene-type-specific guidance.

**Always read the mode supplement before producing the scene_plan:**
- `EP_STATE.style_mode == "animated"` → read `scene-director-animated.md`
- `EP_STATE.style_mode == "cinematic"` → read `scene-director-cinematic.md`

## Safe Zones

When `derivative_variants` is non-empty, all text and critical visual elements must stay within safe zones:

```
16:9 primary canvas: 1920×1080
Safe zone (inner): x=200, y=80, w=1520, h=920  (no text outside this)

9:16 visible area after crop: x=656, y=0, w=608, h=1080
9:16 safe zone: x=720, y=100, w=480, h=880     (text must be within this)

1:1 visible area after crop: x=420, y=0, w=1080, h=1080
1:1 safe zone: x=520, y=80, w=880, h=920       (text must be within this)
```

**CTA beat exception:** The CTA scene's main text is always center-weighted. The brand name must be visible in ALL variants.

## Core / Trimmable Tagging

Every scene must have a `core` field:
- `core: true` → scene is retained in the 15s short cut
- `core: false` → scene may be dropped in the 15s short cut

Rules for core tagging:
- Hook opening scene: always `core: true`
- CTA + brand landing: always `core: true`
- Build scenes: `core: false` unless they contain the primary proof point
- Reveal scene: always `core: true`
- If "15s" is in `derivative_variants`: sum of `core: true` scene durations must be ≤ 15s

## Crop Regions

When `derivative_variants` is non-empty, every scene must declare `crop_regions`:

```json
"crop_regions": {
  "9:16": {"x": 656, "y": 0, "w": 608, "h": 1080},
  "1:1":  {"x": 420, "y": 0, "w": 1080, "h": 1080}
}
```

Include only the variants that are opted in. If no derivatives: omit `crop_regions`.

## Scene Plan Artifact Format

```json
{
  "version": "1.0",
  "style_mode": "animated",
  "total_duration_seconds": 60,
  "derivative_variants": ["9:16"],
  "scenes": [
    {
      "id": "scene-1",
      "script_section_id": "hook",
      "beat": "hook",
      "duration_seconds": 5,
      "scene_type": "...",
      "description": "...",
      "required_assets": [],
      "motion_required": false,
      "core": true,
      "crop_regions": {
        "9:16": {"x": 656, "y": 0, "w": 608, "h": 1080}
      }
    }
  ]
}
```

## Delegation Protocol

After reading this base document:
1. Read the mode supplement (`scene-director-animated.md` or `scene-director-cinematic.md`)
2. Use the supplement's scene type vocabulary to fill in `scene_type` and `description`
3. Use the supplement's keyframe beat guidance for `required_assets`
4. Produce the `scene_plan` artifact

## Validation Before Submitting

- [ ] `sum(scene.duration_seconds)` within ±0.5s of script's total `duration_estimate_seconds`
- [ ] Every scene has `core` field
- [ ] If derivative_variants non-empty: every scene has `crop_regions`
- [ ] No more than 3 consecutive scenes of the same `scene_type`
- [ ] Scenes with `motion_required: true` are realistic given production plan
- [ ] CTA scene is center-weighted and brand name visible in all crop regions
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/scene-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/scene-director.md
git commit -m "feat: add ad-video scene-director base skill"
```

---

## Task 8: Scene Director Mode Supplements

**Files:**
- Create: `skills/pipelines/ad-video/scene-director-animated.md`
- Create: `skills/pipelines/ad-video/scene-director-cinematic.md`

- [ ] **Step 1: Write scene-director-animated.md**

Write `skills/pipelines/ad-video/scene-director-animated.md`:

````markdown
# Scene Director — Animated Mode Supplement

## Scene Type Vocabulary

| Scene Type | Description | Typical Duration | motion_required |
|-----------|-------------|-----------------|-----------------|
| `text_card` | Bold text on dark background, entrance animation | 2–4s | false |
| `stat_reveal` | Animated statistic: number counts up or slams in | 3–5s | false |
| `motion_loop` | Generated looping video background + text overlay | 4–8s | true |
| `logo_reveal` | Product/brand logo animated entrance | 3–5s | false |
| `split_screen` | Side-by-side comparison with motion graphics | 5–8s | false |
| `icon_sequence` | Animated icon series (feature list, steps) | 4–7s | false |
| `product_demo` | Screen recording or generated product UI walkthrough | 5–10s | true |
| `cta_hold` | CTA text + URL, center-weighted, held for 3–5s | 3–5s | false |

## Keyframe Beats

For each beat of the four-beat structure, recommend scene types:

### Hook (~15% of duration)
- Primary: `text_card` with short hook text (≤8 words)
- Optional follow: `stat_reveal` if hook uses a statistic
- Energy: fast entrance, overshooting spring animation

### Build (~40% of duration)
- Primary: `stat_reveal`, `split_screen`, `icon_sequence`
- Avoid: consecutive `text_card` scenes (visual monotony)
- Energy: building rhythm, each scene slightly faster than last

### Reveal (~30% of duration)
- Primary: `logo_reveal` or `motion_loop` with product name
- Secondary: `product_demo` if product has UI to show
- Energy: peak visual complexity, then sudden hold for emphasis

### CTA + Brand Landing (~15% of duration)
- Must use: `cta_hold`
- CTA text: center-weighted, within all safe zones
- Brand name: visible in full at end of `cta_hold`
- Music: rises to full volume here (ducking lifted)

## Asset Requirements per Scene Type

| Scene Type | Required Assets |
|-----------|----------------|
| `text_card` | None (generated from script text + playbook) |
| `stat_reveal` | None (generated from stat data) |
| `motion_loop` | 1× generated video clip (Wan/Kling), 4–8s duration |
| `logo_reveal` | 1× brand logo file (from reference_files or generated) |
| `split_screen` | 2× image assets or 1× image + 1× generated clip |
| `icon_sequence` | 1× icon set (generated or from reference_files) |
| `product_demo` | 1× screen recording or 1× generated UI video |
| `cta_hold` | None (generated from CTA text + brand name) |

## Example Scene Plan (60s animated ad)

> This example assumes `derivative_variants` does not include `"15s"`. If `"15s"` is opted in, mark additional scenes as `core: false` so that `sum(core:true durations) ≤ 15s`.

```json
[
  {"id": "scene-1", "scene_type": "text_card", "beat": "hook", "duration_seconds": 5, "core": true,
   "description": "Hook text slams in: '45 minutes. Gone.'", "motion_required": false},
  {"id": "scene-2", "scene_type": "stat_reveal", "beat": "build", "duration_seconds": 6, "core": false,
   "description": "Counter: 4 HRS/WEEK lost to manual tasks", "motion_required": false},
  {"id": "scene-3", "scene_type": "split_screen", "beat": "build", "duration_seconds": 8, "core": false,
   "description": "Before/after: chaos vs. Flowcut dashboard", "motion_required": false},
  {"id": "scene-4", "scene_type": "motion_loop", "beat": "build", "duration_seconds": 7, "core": false,
   "description": "Looping background: tasks auto-completing", "motion_required": true},
  {"id": "scene-5", "scene_type": "logo_reveal", "beat": "reveal", "duration_seconds": 8, "core": true,
   "description": "Flowcut logo bursts in with motion graphics", "motion_required": false},
  {"id": "scene-6", "scene_type": "product_demo", "beat": "reveal", "duration_seconds": 10, "core": true,
   "description": "15-second product walkthrough compressed to 10s", "motion_required": true},
  {"id": "scene-7", "scene_type": "cta_hold", "beat": "cta_brand", "duration_seconds": 8, "core": true,
   "description": "flowcut.io CTA + Flowcut brand name hold", "motion_required": false}
]
```
````

- [ ] **Step 2: Write scene-director-cinematic.md**

Write `skills/pipelines/ad-video/scene-director-cinematic.md`:

````markdown
# Scene Director — Cinematic Mode Supplement

## Scene Type Vocabulary

| Scene Type | Description | Typical Duration | motion_required |
|-----------|-------------|-----------------|-----------------|
| `hero_shot` | Product or subject as hero — dramatic lighting, slow reveal | 4–8s | false |
| `lifestyle_moment` | Person using product in aspirational context | 5–10s | true |
| `detail_close` | Extreme close-up on product feature or material quality | 2–5s | false |
| `environment_wide` | Establishing or mood-setting wide shot | 3–6s | true |
| `text_overlay` | Cinematic text over still or motion image | 3–5s | false |
| `stat_lower_third` | Statistic as lower-third text over cinematic image | 4–6s | false |
| `social_proof_quick` | Fast-cut quote or user testimonial text | 3–5s | false |
| `brand_landing` | Final brand frame: logo on dark/brand-color background | 4–6s | false |
| `cta_overlay` | CTA text over closing shot or brand landing | 3–5s | false |

## Shot Type Reference

| Shot | Abbreviation | When to Use |
|------|-------------|-------------|
| Extreme close-up | ECU | Texture, detail, emotion |
| Close-up | CU | Face, product hero |
| Medium close-up | MCU | Person + product interaction |
| Medium shot | MS | Action context |
| Wide shot | WS | Environment, scale |
| Over-the-shoulder | OTS | Demonstration, POV |

## Emotional Arc

Cinematic ads follow an emotional arc, not just a logical one:

| Beat | Emotional Goal | Suggested Shots |
|------|---------------|----------------|
| Hook | Disruption or recognition | ECU or unexpected WS |
| Build | Empathy or aspiration | MCU lifestyle, slow pace |
| Reveal | Resolution or wonder | CU product hero, rising music |
| CTA + Brand | Confidence and trust | brand_landing, WS with text |

## Asset Requirements per Scene Type

| Scene Type | Required Assets |
|-----------|----------------|
| `hero_shot` | 1× AI-generated product image (Flux/DALL-E, cinematic prompt) |
| `lifestyle_moment` | 1× AI-generated video clip (Wan/Kling) OR 1× stock video |
| `detail_close` | 1× AI-generated macro image |
| `environment_wide` | 1× AI-generated video clip or wide image |
| `text_overlay` | 1× background image + text from script |
| `stat_lower_third` | 1× background image + stat data |
| `social_proof_quick` | Text only (from brand_context reference_files or fabricated from concept) |
| `brand_landing` | Brand logo (from reference_files) or generated brand frame |
| `cta_overlay` | Background image + CTA text from script |

## Image Generation Prompt Structure (Cinematic)

```
{playbook.asset_generation.image_prompt_prefix}
{scene description in detail}
{shot type}: {ECU|CU|MCU|MS|WS}
lighting: {cinematic, motivated, {direction}}
color: {aligned to brand palette from playbook}
{playbook.asset_generation.image_negative_prompt} [negative]
```

## Example Scene Plan (60s cinematic ad)

> This example assumes `derivative_variants` does not include `"15s"`. If `"15s"` is opted in, mark additional scenes as `core: false` so that `sum(core:true durations) ≤ 15s`.

```json
[
  {"id": "scene-1", "scene_type": "environment_wide", "beat": "hook", "duration_seconds": 5, "core": true,
   "description": "Slow-motion city morning rush — people hurrying, clock in frame", "motion_required": true},
  {"id": "scene-2", "scene_type": "text_overlay", "beat": "hook", "duration_seconds": 4, "core": true,
   "description": "'45 minutes. Every morning.' over blurred commute background", "motion_required": false},
  {"id": "scene-3", "scene_type": "lifestyle_moment", "beat": "build", "duration_seconds": 8, "core": false,
   "description": "Person frustrated at desk, switching tabs, sighing", "motion_required": true},
  {"id": "scene-4", "scene_type": "stat_lower_third", "beat": "build", "duration_seconds": 5, "core": false,
   "description": "'4 hours/week wasted' over productivity context", "motion_required": false},
  {"id": "scene-5", "scene_type": "hero_shot", "beat": "reveal", "duration_seconds": 6, "core": true,
   "description": "Product hero shot — clean desk, Flowcut on screen, warm light", "motion_required": false},
  {"id": "scene-6", "scene_type": "lifestyle_moment", "beat": "reveal", "duration_seconds": 10, "core": true,
   "description": "Person calmly finishing work, leaning back satisfied", "motion_required": true},
  {"id": "scene-7", "scene_type": "brand_landing", "beat": "cta_brand", "duration_seconds": 7, "core": true,
   "description": "Flowcut logo on dark background, URL lower-third", "motion_required": false},
  {"id": "scene-8", "scene_type": "cta_overlay", "beat": "cta_brand", "duration_seconds": 5, "core": true,
   "description": "'Start free at flowcut.io' — center frame, fade in", "motion_required": false}
]
```
````

- [ ] **Step 3: Verify both files**

```bash
test -f skills/pipelines/ad-video/scene-director-animated.md && \
test -f skills/pipelines/ad-video/scene-director-cinematic.md && \
echo "PASS both" || echo "FAIL"
```
Expected: `PASS both`

- [ ] **Step 4: Commit**

```bash
git add skills/pipelines/ad-video/scene-director-animated.md \
        skills/pipelines/ad-video/scene-director-cinematic.md
git commit -m "feat: add ad-video scene-director mode supplements (animated + cinematic)"
```

---

## Task 9: Asset Director Base Skill

**Files:**
- Create: `skills/pipelines/ad-video/asset-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/asset-director.md`:

````markdown
# Asset Director — Ad Video Pipeline (Base)

## When to Use

You are the Asset Director (base). You receive `scene_plan`, `script`, and `production_plan` and generate all assets. You run the **sample sub-stage first** (always), await human approval, then proceed to full generation.

**Always read the mode supplement before generating visual assets:**
- `EP_STATE.style_mode == "animated"` → read `asset-director-animated.md`
- `EP_STATE.style_mode == "cinematic"` → read `asset-director-cinematic.md`

## Required Assets (Non-Negotiable)

These are REQUIRED for ALL style modes and ALL ads:

1. **TTS narration audio** — one audio file per `script.sections[]` item
   - Provider: ElevenLabs (default) or equivalent TTS
   - Format: MP3 or WAV, 44.1 kHz
   - Voice style: `EP_STATE.playbook.audio.voice_style`
   - Hero moment variation: apply `playbook.audio.hero_moment_voice_shift` on `cta_brand` section

2. **Subtitle file** — one file covering all narration
   - Format: SRT (preferred) or VTT
   - Timecodes must align to TTS audio files (use actual TTS durations)
   - Must be legible at 720p on mobile (minimum 24px equivalent)

Missing either of these is a CRITICAL failure. Abort and alert the EP.

## Sample Sub-Stage (Always Runs)

The sample sub-stage generates a preview clip from the **first 2–3 scenes** before full asset generation proceeds.

### Sample Generation Protocol

1. Generate assets for scenes 1–3 only (or first 2 if scenes are long)
2. Generate TTS for the hook section only
3. Assemble the sample clip using compose tools (10–15 second target)
4. Present the sample to the user:

> "Here is your 10–15 second sample clip covering the opening of your ad.
> Review the style, pacing, and quality before I generate all remaining assets.
> **Approve** to continue, or **Reject** with feedback to adjust the approach."

5. If **approved**: set `EP_STATE.sample_approved = true`. Proceed to full generation.
6. If **rejected**: set `EP_STATE.sample_approved = false`. Return the user's feedback to the EP.
   - EP will determine whether to send back to `scene_plan` (visual issue) or `script` (content issue).

**The EP gates all further work on `sample_approved == true`.**

## Full Generation Protocol

After sample approval, generate all remaining assets:

### Step 1: TTS Narration (Complete)
For each `script.sections[]` item not yet generated:
- Call TTS provider with narration text
- Apply voice variation on `cta_brand` section
- Store: `{section_id}_narration.mp3`
- Record actual duration in `asset_manifest.narration_durations`

### Step 2: Visual Assets
Delegate to mode supplement for all visual asset generation (images, video clips).

### Step 3: Subtitle File
Generate subtitle file from actual TTS durations:
- Do NOT estimate — use the actual durations from Step 1
- Format: SRT
- Store: `subtitles.srt`

### Step 4: Music
Generate or select background music:
- Duration: match total video duration
- Mood: `EP_STATE.playbook.audio.music_mood`
- At CTA beat: music rises to full volume (ducking lifted)
- Store: `background_music.mp3`

## Asset Manifest Format

```json
{
  "version": "1.0",
  "style_mode": "animated",
  "narration_files": [
    {"section_id": "hook", "file": "assets/hook_narration.mp3", "duration_seconds": 5.2},
    {"section_id": "build_1", "file": "assets/build_1_narration.mp3", "duration_seconds": 6.1}
  ],
  "subtitle_file": "assets/subtitles.srt",
  "music_file": "assets/background_music.mp3",
  "narration_durations": {
    "hook": 5.2,
    "build_1": 6.1,
    "build_2": 7.3,
    "reveal": 7.8,
    "cta_brand": 4.1
  },
  "visual_assets": [],
  "sample_clip": "assets/sample_preview.mp4",
  "total_narration_seconds": 30.5,
  "costs": [
    {"tool": "elevenlabs_tts", "cost_usd": 0.30},
    {"tool": "flux_image_gen", "cost_usd": 0.12}
  ],
  "total_cost_usd": 0.42
}
```

## Budget Tracking

After each tool call, record the cost in the asset_manifest:
- Add to `asset_manifest.costs[]`: `{"tool": "{tool_name}", "cost_usd": {amount}}`
- Accumulate `asset_manifest.total_cost_usd`
- If `total_cost_usd > EP_STATE.budget_total * 0.9` and asset generation is not complete: include a budget warning in the artifact.
- If `total_cost_usd > EP_STATE.budget_total`: STOP. Return partial artifact to EP. Do not continue without new budget approval.

The EP will read `asset_manifest.total_cost_usd` and update `EP_STATE.budget_spent_usd` after reviewing the artifact. Directors never write to EP_STATE directly.

## Validation Before Submitting

- [ ] `sample_approved == true` in EP_STATE
- [ ] TTS file present for every `script.sections[]` item
- [ ] `subtitle_file` present in asset_manifest
- [ ] All visual assets listed in asset_manifest exist on disk
- [ ] `narration_durations` populated for all sections
- [ ] Budget not exceeded
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/asset-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/asset-director.md
git commit -m "feat: add ad-video asset-director base skill (with sample sub-stage)"
```

---

## Task 10: Asset Director Mode Supplements

**Files:**
- Create: `skills/pipelines/ad-video/asset-director-animated.md`
- Create: `skills/pipelines/ad-video/asset-director-cinematic.md`

- [ ] **Step 1: Write asset-director-animated.md**

Write `skills/pipelines/ad-video/asset-director-animated.md`:

````markdown
# Asset Director — Animated Mode Supplement

## Visual Asset Generation

For each scene in `scene_plan.scenes[]` where `motion_required: false`:

No external image generation needed for text-based scenes (`text_card`, `stat_reveal`, `cta_hold`). These are rendered from data by Remotion using the playbook's typography and color tokens.

For scenes requiring visual backgrounds (`motion_loop`, `split_screen`, `logo_reveal`, `product_demo`):

### Image Generation (Flux or DALL-E)

Prompt structure:
```
{playbook.asset_generation.image_prompt_prefix}
{scene.description} — flat vector illustration style, bold colors
Primary color: {playbook.visual_language.color_palette.primary[0]}
Accent: {playbook.visual_language.color_palette.accent[0]}
Background: {playbook.visual_language.color_palette.background}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_bg.png`, 1920×1080

### Video Generation (motion_required: true)

For `motion_loop` and `product_demo` scenes:

Provider: Wan 2.7 (Bailian/DashScope) — primary
Fallback: Kling

Prompt structure:
```
{scene.description}
style: motion graphics, flat animation, bold colors
duration: {scene.duration_seconds}s
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_video.mp4`, 1920×1080, duration ≥ scene.duration_seconds

### Style Consistency

After generating each image/video:
- Check that primary color `#1A1A2E` or `#E94560` (accent) appears in frame
- Check that background is dark (luminance < 0.3 on average)
- If mismatch: regenerate with stronger color directive in prompt
- Store passing style token in `EP_STATE.style_anchors`:
  ```
  EP_STATE.style_anchors["animated_palette_confirmed"] = true
  EP_STATE.style_anchors["first_bg_seed"] = "{seed or prompt hash}"
  ```

## Remotion-Specific Asset Notes

Remotion renders text cards, stat reveals, and CTA holds from data — no pre-generated images needed.

Pass to compose director via `asset_manifest.remotion_data`:
```json
{
  "text_cards": [
    {"scene_id": "scene-1", "text": "45 minutes. Gone.", "font_weight": 900, "entrance": "scale-up-bounce"}
  ],
  "stat_reveals": [
    {"scene_id": "scene-2", "value": "4 HRS", "label": "wasted every week", "animation": "count-up"}
  ],
  "cta_data": {
    "scene_id": "scene-7",
    "cta_text": "Start free at flowcut.io",
    "brand_name": "Flowcut",
    "url": "flowcut.io"
  }
}
```
````

- [ ] **Step 2: Write asset-director-cinematic.md**

Write `skills/pipelines/ad-video/asset-director-cinematic.md`:

````markdown
# Asset Director — Cinematic Mode Supplement

## Visual Asset Generation

For each scene in `scene_plan.scenes[]`:

### Still Image Generation (hero_shot, detail_close, text_overlay, stat_lower_third)

Provider: Flux (preferred) or DALL-E

Prompt structure:
```
{playbook.asset_generation.image_prompt_prefix}
{scene.description}
shot type: {scene shot type from scene_plan}
lighting: cinematic, {motivated direction}
color grade: {aligned to playbook primary palette}
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_img.jpg`, 1920×1080, JPEG quality 95

### Video Generation (lifestyle_moment, environment_wide)

Provider: Wan 2.7 (Bailian/DashScope) — primary
Fallback: Kling

Prompt structure:
```
{scene.description}
cinematic quality, {shot type} shot
camera movement: {slow push-in | static | slow pan} depending on scene
duration: {scene.duration_seconds}s, 24fps
{playbook.asset_generation.image_negative_prompt} [negative]
```

Output: `assets/scene_{id}_video.mp4`, 1920×1080

### Brand Landing Frame

For `brand_landing` scene:
1. If brand logo file exists in confirmed reference_files: use it directly
2. If no logo: generate a clean text logo using playbook typography
   - Background: `playbook.visual_language.color_palette.background` (#0D0D0D)
   - Brand name: `playbook.typography.headings` (Inter 800, #F5F5F5)
   - Accent line: `playbook.visual_language.color_palette.accent[0]` (#E94560)

Output: `assets/brand_landing.jpg`, 1920×1080

### Style Consistency

After generating first image, record the visual treatment as a style anchor:
```
EP_STATE.style_anchors["cinematic_lighting"] = "{direction from first successful image}"
EP_STATE.style_anchors["cinematic_color_grade"] = "{grade description}"
EP_STATE.style_anchors["cinematic_first_prompt"] = "{first image prompt}"
```

For all subsequent images: include `EP_STATE.style_anchors["cinematic_lighting"]` explicitly in every prompt.

Consistency check: visually compare each generated image/frame for:
- Consistent color temperature (warm or cool, not mixed)
- Consistent lighting direction
- Consistent depth of field treatment

If inconsistency detected: regenerate with explicit anchor-matching prompt addition.
````

- [ ] **Step 3: Verify both files**

```bash
test -f skills/pipelines/ad-video/asset-director-animated.md && \
test -f skills/pipelines/ad-video/asset-director-cinematic.md && \
echo "PASS both" || echo "FAIL"
```
Expected: `PASS both`

- [ ] **Step 4: Commit**

```bash
git add skills/pipelines/ad-video/asset-director-animated.md \
        skills/pipelines/ad-video/asset-director-cinematic.md
git commit -m "feat: add ad-video asset-director mode supplements (animated + cinematic)"
```

---

## Task 11: Edit Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/edit-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/edit-director.md`:

````markdown
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

## Subtitle Burn Configuration

```json
"subtitles": {
  "source_file": "assets/subtitles.srt",
  "burn_in": true,
  "style": {
    "font": "Inter",
    "font_size": 28,
    "font_weight": 700,
    "color": "#F5F5F5",
    "background": "rgba(0,0,0,0.6)",
    "position": "bottom_center",
    "margin_bottom_px": 60,
    "safe_zone_margin_px": 80
  }
}
```

Note: `safe_zone_margin_px: 80` ensures subtitles remain visible in 9:16 and 1:1 crops.

## Timeline Construction

For each scene in `scene_plan.scenes[]`:
1. Set `video_in` to cumulative offset from scene durations
2. Set `video_out` to `video_in + scene.duration_seconds`
3. Match narration audio: `audio_in` = `video_in + narration_offset` (default 0.0s)
4. Verify: `narration_duration ≤ scene.duration_seconds`

```json
"timeline": [
  {
    "scene_id": "scene-1",
    "video_in": 0.0,
    "video_out": 5.0,
    "video_asset": "assets/scene_1_video.mp4",
    "narration_asset": "assets/hook_narration.mp3",
    "narration_in": 0.0,
    "narration_duration": 4.8,
    "transition_in": null,
    "transition_out": {"type": "cut"}
  },
  {
    "scene_id": "scene-2",
    "video_in": 5.0,
    "video_out": 11.0,
    "video_asset": null,
    "remotion_component": "StatReveal",
    "remotion_data": {"value": "4 HRS", "label": "wasted every week"},
    "narration_asset": "assets/build_1_narration.mp3",
    "narration_in": 5.0,
    "narration_duration": 6.1,
    "transition_in": {"type": "cut"},
    "transition_out": {"type": "wipe-left"}
  }
]
```

## Derivative Edit Specifications

When `derivative_variants` is non-empty, the edit_decisions must include a `derivative_specs` section:

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
- [ ] All `video_asset` and `narration_asset` references point to files in `asset_manifest`
- [ ] `audio_ducking` covers all narration windows
- [ ] `audio_ducking[].target_db == -18` (playbook requirement)
- [ ] `subtitles.burn_in == true`
- [ ] If derivative_variants non-empty: `derivative_specs` present with entries for each variant
- [ ] Every `narration_duration ≤ scene.duration_seconds` for all timeline entries
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/edit-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/edit-director.md
git commit -m "feat: add ad-video edit-director skill"
```

---

## Task 12: Compose Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/compose-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/compose-director.md`:

````markdown
# Compose Director — Ad Video Pipeline

## When to Use

You receive `edit_decisions`, `asset_manifest`, and `EP_STATE` and render the final video outputs. You render the primary 16:9 video first, then all opted-in derivative variants as separate output files.

## CRITICAL Pre-Render Checks

**Before any render begins, run ALL of these checks. Do not skip any.**

### Check 1: render_runtime verification
```
EP_STATE.style_mode == "animated" → render_runtime ∈ {remotion, hyperframes}
EP_STATE.style_mode == "cinematic" → render_runtime == ffmpeg
```

The user's choice (Remotion vs. HyperFrames for animated mode) was locked at the proposal stage via the `render_runtime_selection` decision in `decision_log`. Compose MUST route by `render_runtime` — do NOT fall back to the tool's legacy default, do NOT silently pick Remotion, do NOT treat HyperFrames as "basically Remotion." Each engine has a distinct renderer invocation (see Primary Render section).

If `EP_STATE.render_runtime` is unset or does not match the `style_mode` constraint above, OR if the renderer in `production_plan` does not match `EP_STATE.render_runtime`: **ABORT. Alert EP. Do not render.** A runtime mismatch is a CRITICAL failure — this is the silent runtime swap prevention.

### Check 2: Asset file existence
For every asset reference in `edit_decisions.timeline[]`:
- `video_asset` file exists on disk (skip if null)
- `narration_asset` file exists on disk
If any file missing: **ABORT. Alert EP with missing file list.**

### Check 3: Derivative readiness
If `derivative_variants` is non-empty:
- Every scene in `edit_decisions` has `crop_regions` in `scene_plan`
- `edit_decisions.derivative_specs` is present
If any scene is missing crop_regions: **ABORT. Send back to scene_plan director.**

### Check 4: Subtitle file
- `asset_manifest.subtitle_file` exists on disk
- `edit_decisions.subtitles.burn_in == true`
If missing: **ABORT. Alert EP.**

## Primary Render (16:9)

Select renderer based on `EP_STATE.render_runtime`:

### Remotion (animated mode — when `render_runtime == "remotion"`)
```
npx remotion render \
  --composition=AdVideo \
  --props='{"timeline": ..., "remotion_data": ..., "subtitle_file": "assets/subtitles.srt"}' \
  --output=renders/output_16x9.mp4 \
  --codec=h264 \
  --width=1920 --height=1080
```

### HyperFrames (animated mode — when `render_runtime == "hyperframes"`)
Call `video_compose.render` with `render_engine: "hyperframes"` and the HyperFrames scene spec assembled from `edit_decisions.timeline[]`. The engine consumes the same timeline and subtitle file as Remotion but drives HTML/GSAP motion primitives instead of React scene components. Do NOT fall through to the Remotion branch — HyperFrames uses a different composition graph and silently invoking Remotion here is a CRITICAL failure.

### ffmpeg (cinematic mode)
Construct ffmpeg command from `edit_decisions.timeline[]`:
```
ffmpeg \
  -i {video_assets_concat} \
  -i {narration_concat} \
  -i background_music.mp3 \
  -filter_complex "[audio_ducking_filter][subtitle_filter]" \
  -map "[v_out]" -map "[a_out]" \
  -c:v libx264 -crf 18 -preset slow \
  -c:a aac -b:a 192k \
  -t {total_duration_seconds} \
  renders/output_16x9.mp4
```

### Post-primary probe
```bash
ffprobe -v quiet -print_format json -show_streams renders/output_16x9.mp4
```
Verify: duration within ±5% of target, resolution 1920×1080, audio channels 2 (stereo).
If probe fails any check: alert EP before proceeding to derivatives.

## Derivative Rendering Loop

For each variant in `EP_STATE.derivative_variants`:

**Before each derivative render, verify crop_regions for that variant are present in scene_plan. This check is NOT skipped for subsequent derivatives.**

### 9:16 Variant
```
Crop filter: crop=608:1080:656:0 (x=656, y=0, w=608, h=1080)
Output resolution: 608×1080
Scale to: 1080×1920 (pad to standard vertical)
Output: renders/output_9x16.mp4
Subtitle override: font_size=32, margin_bottom=80
```

### 1:1 Variant
```
Crop filter: crop=1080:1080:420:0 (x=420, y=0, w=1080, h=1080)
Output resolution: 1080×1080
Output: renders/output_1x1.mp4
Subtitle override: font_size=30, margin_bottom=70
```

### 15s Short Cut
```
Include only scenes where core:true in scene_plan
Verify sum(core_scene_durations) ≤ 15.0s
Re-render with filtered timeline
Output: renders/output_15s.mp4
```

### Cross-Product Derivatives
If both a duration variant (15s) AND an aspect-ratio variant (9:16 or 1:1) are opted in, render cross-products:
```
15s + 9:16 → renders/output_15s_9x16.mp4
15s + 1:1  → renders/output_15s_1x1.mp4
```

## Render Report Format

```json
{
  "version": "1.0",
  "renderer": "remotion",
  "output_files": [
    {
      "variant": "16:9",
      "file": "renders/output_16x9.mp4",
      "duration_seconds": 59.8,
      "resolution": "1920x1080",
      "audio_channels": 2,
      "file_size_mb": 42.3
    },
    {
      "variant": "9:16",
      "file": "renders/output_9x16.mp4",
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
- [ ] `output_files` contains `16:9` entry
- [ ] `output_files` contains one entry per opted-in derivative (and cross-products)
- [ ] All probe results PASS
- [ ] `render_report.renderer` matches `EP_STATE.render_runtime`
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/compose-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/compose-director.md
git commit -m "feat: add ad-video compose-director skill (with derivative rendering loop)"
```

---

## Task 13: Publish Director Skill

**Files:**
- Create: `skills/pipelines/ad-video/publish-director.md`

- [ ] **Step 1: Write the skill file**

Write `skills/pipelines/ad-video/publish-director.md`:

````markdown
# Publish Director — Ad Video Pipeline

## When to Use

You receive `render_report`, `proposal_packet`, `script`, and `EP_STATE` and produce the final `publish_log`: output file matrix, platform metadata, and thumbnail concept.

## Output File Matrix

For every file in `render_report.output_files`, assign platform targets and usage notes:

| File | Variant | Primary Platform Targets | Typical Use |
|------|---------|--------------------------|------------|
| `output_16x9.mp4` | 16:9 | YouTube, LinkedIn, TV | Hero placement |
| `output_9x16.mp4` | 9:16 | TikTok, Instagram Stories, YouTube Shorts | Vertical social |
| `output_1x1.mp4` | 1:1 | Instagram Feed, Twitter/X, LinkedIn feed | Square social |
| `output_15s.mp4` | 15s | Pre-roll, bumper | Short-form |
| `output_15s_9x16.mp4` | 15s 9:16 | TikTok, IG Stories short | Short vertical |
| `output_15s_1x1.mp4` | 15s 1:1 | Short square | Short square |

Include only files that were actually rendered (check `render_report.output_files`).

## Metadata

For each output file:

```json
{
  "file": "renders/output_16x9.mp4",
  "title": "{proposal.selected_concept.name}",
  "description": "{script.sections[hook].narration} ... {cta}",
  "tags": ["{brand_name}", "{product}", "{platform}", "ad", "commercial"],
  "cta_url": "{script.cta}",
  "brand_name": "{script.brand_name}",
  "target_platforms": ["youtube", "linkedin"],
  "duration_seconds": "{from render_report}",
  "variant": "16:9"
}
```

## Thumbnail Concept

Provide a written thumbnail concept for each output file's primary platform use:

Format:
```
Thumbnail concept for {variant}:
- Frame: {describe the ideal freeze-frame or custom thumbnail moment}
- Text overlay: {headline text if any, ≤5 words}
- Brand element: {how brand name/logo appears}
- Emotional tone: {what expression/action is shown}
```

Example:
```
Thumbnail concept for 16:9:
- Frame: Product hero shot from reveal scene, 70% into the video
- Text overlay: "4 HRS BACK EVERY WEEK"
- Brand element: Flowcut logo lower-right, 20% opacity overlay
- Emotional tone: Clean, confident, aspirational
```

## Publish Log Format

```json
{
  "version": "1.0",
  "pipeline": "ad-video",
  "brand_name": "Flowcut",
  "output_file_matrix": [
    {
      "file": "renders/output_16x9.mp4",
      "variant": "16:9",
      "duration_seconds": 59.8,
      "target_platforms": ["youtube", "linkedin", "tv"],
      "metadata": {
        "title": "The Problem You Didn't Know You Had — Flowcut",
        "description": "Every morning, you're wasting 45 minutes. Start free at flowcut.io",
        "tags": ["Flowcut", "productivity", "workflow", "ad"],
        "cta_url": "https://flowcut.io"
      },
      "thumbnail_concept": "Product hero from reveal scene, '4 HRS BACK/WEEK' overlay"
    }
  ],
  "total_files_rendered": 2,
  "budget_summary": {
    "approved_usd": 2.50,
    "spent_usd": 2.18,
    "remaining_usd": 0.32
  }
}
```

## Validation Before Submitting

- [ ] `output_file_matrix` is non-empty
- [ ] Every file in `render_report.output_files` has an entry in the matrix
- [ ] All metadata fields populated (title, description, tags, cta_url, brand_name)
- [ ] Thumbnail concept written for each entry
- [ ] Budget summary accurate (matches EP_STATE)
````

- [ ] **Step 2: Verify**

```bash
test -f skills/pipelines/ad-video/publish-director.md && echo "PASS" || echo "FAIL"
```
Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/publish-director.md
git commit -m "feat: add ad-video publish-director skill"
```

---

## Task 14: Integration Validation

**Files:**
- No new files. Validation only.

- [ ] **Step 1: Verify all 15 files exist**

```bash
python3 -c "
from pathlib import Path
files = [
    'styles/ad-brand.yaml',
    'pipeline_defs/ad-video.yaml',
    'skills/pipelines/ad-video/executive-producer.md',
    'skills/pipelines/ad-video/idea-director.md',
    'skills/pipelines/ad-video/proposal-director.md',
    'skills/pipelines/ad-video/script-director.md',
    'skills/pipelines/ad-video/scene-director.md',
    'skills/pipelines/ad-video/scene-director-animated.md',
    'skills/pipelines/ad-video/scene-director-cinematic.md',
    'skills/pipelines/ad-video/asset-director.md',
    'skills/pipelines/ad-video/asset-director-animated.md',
    'skills/pipelines/ad-video/asset-director-cinematic.md',
    'skills/pipelines/ad-video/edit-director.md',
    'skills/pipelines/ad-video/compose-director.md',
    'skills/pipelines/ad-video/publish-director.md',
]
missing = [f for f in files if not Path(f).exists()]
if missing:
    print('MISSING:', missing)
else:
    print(f'PASS — all {len(files)} files present')
"
```
Expected: `PASS — all 15 files present`

- [ ] **Step 2: Validate playbook schema**

```bash
python3 -c "
from styles.playbook_loader import load_playbook, validate_playbook
pb = load_playbook('ad-brand')
errors = validate_playbook(pb)
if errors:
    print('SCHEMA ERRORS:', errors)
else:
    print('PASS — playbook valid')
    assert pb['identity']['category'] == 'custom', 'category must be custom'
    assert pb['audio']['ducking_threshold_db'] == -18, 'ducking must be -18 dB'
    assert 'quality_rules' in pb, 'quality_rules required'
    print('PASS — key field assertions passed')
    print('  category:', pb['identity']['category'])
    print('  ducking_threshold_db:', pb['audio']['ducking_threshold_db'])
    print('  quality_rules count:', len(pb['quality_rules']))
"
```
Expected:
```
PASS — playbook valid
PASS — key field assertions passed
  category: custom
  ducking_threshold_db: -18
  quality_rules count: 7
```

- [ ] **Step 3: Validate pipeline manifest**

```bash
python3 -c "
from lib.pipeline_loader import load_pipeline
p = load_pipeline('ad-video')
print('PASS — manifest loaded')
stage_names = [s['name'] for s in p['stages']]
assert stage_names == ['idea', 'proposal', 'script', 'scene_plan', 'assets', 'edit', 'compose', 'publish'], f'stages mismatch: {stage_names}'
print('PASS — stages in correct order:', stage_names)
assert len(p['required_skills']) == 13, f'expected 13 skills, got {len(p[\"required_skills\"])}'
print('PASS — required_skills count:', len(p['required_skills']))
assert p['category'] == 'custom', f'category must be custom, got {p[\"category\"]}'
print('PASS — category: custom')
"
```
Expected:
```
PASS — manifest loaded
PASS — stages in correct order: ['idea', 'proposal', 'script', 'scene_plan', 'assets', 'edit', 'compose', 'publish']
PASS — required_skills count: 13
PASS — category: custom
```

- [ ] **Step 4: Check required_skills file existence (pipeline contract)**

```bash
python3 -c "
from pathlib import Path
from lib.pipeline_loader import load_pipeline
p = load_pipeline('ad-video')
missing = [s for s in p['required_skills'] if not Path(s).exists()]
if missing:
    print('MISSING SKILL FILES:', missing)
else:
    print(f'PASS — all {len(p[\"required_skills\"])} required skill files exist on disk')
"
```
Expected: `PASS — all 13 required skill files exist on disk`

- [ ] **Step 5: Spot-check critical content in skill files**

```bash
python3 -c "
from pathlib import Path

checks = [
    # (file, required substring, description)
    ('skills/pipelines/ad-video/executive-producer.md', 'sample_approved', 'EP tracks sample_approved'),
    ('skills/pipelines/ad-video/executive-producer.md', 'style_mode', 'EP tracks style_mode'),
    ('skills/pipelines/ad-video/executive-producer.md', 'derivative_variants', 'EP tracks derivatives'),
    ('skills/pipelines/ad-video/proposal-director.md', 'render_runtime', 'proposal locks render_runtime'),
    ('skills/pipelines/ad-video/proposal-director.md', 'Silent runtime swap', 'proposal has runtime swap warning'),
    ('skills/pipelines/ad-video/script-director.md', 'target_words = target_duration_seconds × 2.5', 'word count formula present'),
    ('skills/pipelines/ad-video/script-director.md', 'cta_brand', 'four beats: cta_brand present'),
    ('skills/pipelines/ad-video/asset-director.md', 'sample_approved', 'asset director gates on sample_approved'),
    ('skills/pipelines/ad-video/asset-director.md', 'Subtitle file', 'subtitles marked REQUIRED'),
    ('skills/pipelines/ad-video/asset-director.md', 'TTS narration audio', 'TTS marked REQUIRED'),
    ('skills/pipelines/ad-video/edit-director.md', 'ducking_threshold_db: -18', 'edit director enforces -18 dB ducking'),
    ('skills/pipelines/ad-video/compose-director.md', 'CRITICAL Pre-Render Checks', 'compose has CRITICAL checks section'),
    ('skills/pipelines/ad-video/compose-director.md', 'silent runtime swap', 'compose checks runtime swap'),
    ('styles/ad-brand.yaml', 'ducking_threshold_db: -18', 'playbook has -18 dB ducking'),
]

failures = []
for filepath, substring, description in checks:
    content = Path(filepath).read_text()
    if substring not in content:
        failures.append(f'FAIL: {filepath} missing \"{substring}\" ({description})')

if failures:
    for f in failures:
        print(f)
else:
    print(f'PASS — all {len(checks)} content spot-checks passed')
"
```
Expected: `PASS — all 14 content spot-checks passed`

- [ ] **Step 6: Final commit**

```bash
git add -A
git status
```

If there are no uncommitted changes (all tasks committed individually), this confirms clean state.

```bash
echo "All 15 files committed. Integration validation complete."
```

---

## Verification Summary

After completing all tasks, the following confirms the implementation is complete:

| Check | Command | Expected |
|-------|---------|----------|
| All 15 files exist | Task 14, Step 1 | PASS — all 15 files present |
| Playbook schema valid | Task 14, Step 2 | PASS — key field assertions passed |
| Manifest loads | Task 14, Step 3 | PASS — stages correct, 13 skills |
| Skill files on disk | Task 14, Step 4 | PASS — all 13 files exist |
| Content spot-checks | Task 14, Step 5 | PASS — all 14 checks passed |
