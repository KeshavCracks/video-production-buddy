# Ad-Video Pre-Production Intelligence — Design Spec

**Date:** 2026-04-25
**Pipeline:** `ad-video`
**Status:** Approved — ready for implementation planning
**Companion spec:** `2026-04-24-ad-video-pipeline-design.md` (original pipeline architecture)

---

## 1. Problem Statement

The current `ad-video` pipeline receives a raw user prompt and passes it directly to `idea-director`, which parses brand context from whatever the user provides. A single-sentence prompt gives the system too little to work with:

- No trend data → concepts are disconnected from what's performing on the target platform
- No hit-ad analysis → narrative structures are invented, not informed by proven patterns
- No emotional rhythm quality gate → flat or incoherent narratives pass through unchallenged
- No pre-production user confirmation → the first human gate (proposal) covers concept selection *and* logistics simultaneously, creating information overload and missed errors
- No structured contract → downstream stages (script, scene_plan, edit) receive soft context and may drift from the approved creative direction

Users give thin prompts, receive misaligned output, and experience the failure only after expensive generation runs. The goal of this spec is to fix the production pipeline at its root: the pre-production phase.

---

## 2. Solution Overview

Insert three new pipeline stages before `idea`: **intake → intelligence → bible**.

These stages implement a two-round interaction model:

- **Round 1 (pre-research):** Intake detects thin prompts and asks only the questions that change research direction. Maximum 3 questions. Rich prompts skip Round 1 entirely.
- **Round 2 (post-research, split into 7a and 7b):** Bible-director presents the synthesized production bible in two steps — strategic (narrative arc) then execution (visual/audio/compliance) — getting user confirmation before advancing.

The bible artifact is a structured, machine-readable contract. Downstream stages (script, scene_plan, edit) don't just receive it as context — they run compliance checks against it and surface violations before the EP gates.

The existing `idea-director` and `proposal-director` are re-scoped (not removed) to eliminate overlap with the new bible ownership. Their responsibilities are redefined in section 8.

---

## 3. Architecture

### Pipeline Stage Sequence (updated)

```
intake → intelligence → bible (Round 2 gate)
                          ↓
                idea (creative execution options) → [user selects]
                          ↓
                proposal (technical parameters)   → [user approves]
                          ↓
                script → scene_plan → assets → edit → compose → publish
```

### Information Flow

```
User prompt
    │
    ▼
[intake-director]
    │ intake_brief
    ▼
[intelligence-director]
    │ intelligence_brief
    ▼
[bible-director] ◄─── Round 2a: narrative approval
    │             ◄─── Round 2b: execution approval
    │ production_bible
    ▼
[idea-director] ◄─── receives: intake_brief + intelligence_brief + production_bible
    │             ──► produces: idea_options[] (execution concepts within bible)
    │ [user selects idea]
    ▼
[proposal-director] ◄─── receives: selected_idea + production_bible
    │                ──► produces: production_proposal (technical parameters only)
    │ [user approves]
    ▼
[script-director] ◄─── receives: production_bible (compliance spine)
    │             ──► self-checks: CP-S* checkpoints before submitting
    ▼
[scene_plan-director] ◄─── compliance: CP-V* checkpoints
[edit-director]       ◄─── compliance: CP-E*, CP-B* checkpoints
```

### New Artifacts

| Artifact | Produced by | Consumed by |
|----------|-------------|-------------|
| `intake_brief` | intake-director | intelligence-director, idea-director |
| `intelligence_brief` | intelligence-director | bible-director, idea-director |
| `production_bible` | bible-director | idea, proposal, script, scene_plan, assets, edit, EP gates |

---

## 4. Production Bible Schema

The bible is the contract between pre-production and production. It is machine-readable and used for compliance checking — not just LLM context injection.

```jsonc
// schemas/artifacts/production_bible.schema.json
// v1 — populated across three stages; see "populated by" annotations

{
  "version": "1.0",
  "pipeline": "ad-video",
  "project_id": "string",
  "approval": {
    "strategic_approved": false,   // set after Round 2a
    "execution_approved": false,   // set after Round 2b
    "modifications_log": []        // records each change and which round it came from
  },

  // ── Section 1: Identity Contract ──────────────────────────────────────
  // populated by: intake-director (demographic + explicit user fields)
  //               intelligence-director (emotional_profile, core_pain_point, aspiration)
  // enforced by: ALL downstream stages — these fields never drift
  "identity": {
    "product": "string",
    "brand_name": "string",
    "target_audience": {
      "demographic": "string",           // intake: user-stated (e.g. "urban professionals 25-35")
      "emotional_profile": "string",     // intelligence: research-inferred
      "core_pain_point": "string",       // intelligence: research-inferred
      "aspiration": "string"             // intelligence: research-inferred
    },
    "platform": "youtube|tiktok|instagram|linkedin|tv|generic",
    "duration_target_seconds": "number",
    "key_message": "string",             // single sentence viewer must retain tomorrow
    "cta": "string",                     // exact CTA text — no paraphrasing allowed downstream
                                         // populated by: intake (if user stated) or bible Round 2b (if still null)
                                         // MUST be non-null before bible approval completes
    "tone": "string"
  },

  // ── Section 2: Narrative Contract ─────────────────────────────────────
  // populated by: intelligence-director (arc_type, hook_mechanic, pacing_model recommendations)
  //               bible-director (beat_sequence design, intensity curve application)
  // enforced by: script-director (CP-S* compliance checks) + EP gate G-post-script
  "narrative": {
    "arc_type": "problem-solution|desire-fulfillment|contrast|journey|social-proof|demo-reveal",
    "pacing_model": "slow-burn|punchy|escalating|wave",
    "hook_mechanic": "question|statement|visual-contrast|sound-interrupt|stat",
    "hook_window_seconds": "number",     // platform-specific: TikTok=1.5, YouTube=5, TV=8
    "tension_peak_at_seconds": "number", // where arc intensity peaks — validates scene ordering
    "resolution_type": "relief|aspiration|social-validation|authority",

    "emotional_beat_sequence": [
      {
        "beat_id": "string",             // e.g. "B1", "B2" — the compliance spine key
        "name": "hook|tension|turn|revelation|resolution|cta",
        "duration_seconds": "number",    // target; CP-S compliance threshold ±10%
        "emotional_target": "string",    // e.g. "curiosity", "recognition", "desire"
        "intensity": "number 0.0–1.0",   // position on the pacing_model's intensity curve
        "script_constraint": "string",   // what the script section MUST achieve
        "visual_constraint": "string"    // what the visual MUST show at this beat
      }
    ]
  },

  // ── Section 3: Intelligence Sources ───────────────────────────────────
  // populated by: intelligence-director
  // used by: bible-director (synthesis input); audit trail for future review
  "intelligence": {
    "trending_signals": [
      {
        "signal": "string",
        "source": "string",
        "applied_to": "string"           // which bible field this shaped
      }
    ],
    "reference_ads_analyzed": [
      {
        "title": "string",
        "platform": "string",
        "what_works": "string",
        "adopted": "boolean",
        "adaptation": "string"
      }
    ],
    "rejected_approaches": [
      {
        "approach": "string",
        "reason": "string"               // prevents rediscovery in revision loops
      }
    ]
  },

  // ── Section 4: Visual Contract ────────────────────────────────────────
  // populated by: bible-director
  // enforced by: scene_plan-director (CP-V*) + edit-director (CP-E*)
  "visual": {
    "style_mode": "animated|cinematic",
    "render_runtime": "remotion|hyperframes|ffmpeg",
    "color_direction": "string",

    "visual_motifs": [
      {
        "motif": "string",
        "mandatory": "boolean",          // true only if appeared in 3+ hit ads AND not rejected
        "minimum_scene_count": "number"
      }
    ],

    "key_visual_moments": [
      {
        "moment_id": "string",
        "description": "string",
        "maps_to_beat": "string",        // beat_id
        "mandatory": "boolean"
      }
    ],

    // Per-beat editing rhythm — derived from hit ad pacing analysis
    // confidence tier from intelligence propagates to CP-E checkpoints
    "editing_rhythm": [
      {
        "maps_to_beat": "string",                    // beat_id
        "cuts_density": "rapid|moderate|slow|held",
        "avg_shot_duration_seconds": "number",
        "transition_style": "hard_cut|dissolve|whip|match_cut",
        "confidence": "research-grounded|pattern-inferred|default-heuristic"
      }
    ]
  },

  // ── Section 5: Audio Contract ──────────────────────────────────────────
  // populated by: bible-director
  // enforced by: asset-director (TTS selection, music gen) + edit-director (mixing)
  "audio": {
    "voice_character": {
      "tone": "string",
      "pacing": "measured|energetic|conversational",
      "persona": "string"
    },
    "music_direction": {
      "mood": "string",
      "tempo": "slow|medium|fast",
      "genre_direction": "string",
      "arc": "string"                    // e.g. "sparse at hook, full arrangement at revelation"
    },
    "av_sync_notes": "string"
  },

  // ── Section 6: Brand Constraints ──────────────────────────────────────
  // populated by: intake-director (brand_name, cta) + bible-director (guardrails)
  // enforced by: ALL downstream stages — never-drift rules
  "brand_constraints": {
    "brand_name_in_final_frame": true,
    "mandatory_elements": ["string"],
    "prohibited_elements": ["string"],
    "tone_guardrails": ["string"]
  },

  // ── Section 7: Deliverables ────────────────────────────────────────────
  // primary populated by: bible-director (from platform + duration target)
  // derivatives populated by: proposal-director (user opt-in choices)
  // enforced by: edit-director (must produce all listed variants)
  "deliverables": {
    "primary": {
      "aspect_ratio": "16:9|9:16|1:1",
      "duration_seconds": "number"
    },
    "derivatives": [
      {
        "variant_id": "string",
        "aspect_ratio": "string",
        "duration_seconds": "number",
        "adaptation_notes": "string"     // e.g. "center-crop; cut B2 tension to 4s for 15s version"
      }
    ]
  },

  // ── Section 8: Compliance Manifest ────────────────────────────────────
  // populated by: bible-director (mechanically derived — see section 7 generation rules)
  // read by: script, scene_plan, assets, edit directors + EP gates
  "compliance_manifest": {
    "checkpoints": [
      {
        "id": "string",                  // CP-S{n}, CP-V{n}, CP-E{n}, CP-B{n}
        "applies_to_stage": "script|scene_plan|assets|edit",
        "description": "string",
        "check_type": "structural|content|timing|presence",
        "evaluation_method": "structural|semantic",
        // structural: MUST be evaluated by deterministic code logic (word count,
        //   string matching, regex, arithmetic comparison). Never routed through LLM.
        // semantic: evaluated by stage director self-assessment + independent EP gate
        //   re-evaluation. EP re-evaluation uses a separate LLM call that does not
        //   see the director's self-assessment result — preventing rubber-stamping.
        "criterion": "string",
        // NOTE: criterion uses natural language in v1.
        // Migration target for v2: structured expression {field, operator, value, tolerance}.
        // Do not build parsing logic against free-text format — it will be replaced.
        "source_confidence": "research-grounded|pattern-inferred|default-heuristic",
        "failure_action": "revise|flag"
        // revise: EP sends stage back for correction
        // flag:   EP logs warning and proceeds — used when source_confidence=default-heuristic
      }
    ]
  }
}
```

---

## 5. Intake Director

### Responsibility

Thin-prompt detection → minimum Round 1 questions → `intake_brief`

### Minimum Information Schema

Four fields determine research direction. All others can be inferred or confirmed later.

| Field | Why it changes research | Can intelligence fill it without a hint? |
|-------|------------------------|------------------------------------------|
| `product` | Defines ad category; determines competitor pool | No — must come from user |
| `platform` | Determines trend search domain, pacing norms, aspect ratio default | No — critical for research direction |
| `demographic` | Determines which pain points and aspiration research to run | Partially — a hint prevents wrong direction |
| `emotional_intent` | Determines which hook mechanics and arc types to study | Partially — user-stated intent beats inference |

### Detection and Scoring

```
PARSE prompt for each minimum field:
  product_present          = product or service is named or clearly implied
  platform_present         = specific platform mentioned OR strongly implied by brief context
  demographic_present      = any audience description, however thin
  emotional_intent_present = any emotional register, outcome, or feeling stated

missing = [field for field in minimum_schema if not field_present]

IF len(missing) == 0:
    → pass-through. Ask zero questions. Set intake_completeness="rich".

ELIF len(missing) <= 3:
    → ask questions for missing fields only, all in a single message, capped at 3.
      Set intake_completeness="adequate" or "thin" depending on how many missing.

ELIF len(missing) == 4:
    → ask top 3 by priority: product → platform → demographic → emotional_intent.
      Leave emotional_intent for intelligence to infer.
      Set intake_completeness="thin".
```

### Question Rules

**What qualifies as a Round 1 question:** Only questions whose answer changes what to search for. Test: "If the user answers X instead of Y, would the intelligence stage run different searches?" If yes — valid question. If no — not a Round 1 question.

**What does NOT belong in Round 1:** Subtitles, dubbing, derivatives, budget, runtime, reference file roles, style_mode confirmation. These are logistics — they stay in proposal.

**Format rules:**
- Present all missing-field questions in a single message. Each question on its own line, answerable in one sentence.
- Maximum 3 questions per message — never exceed this regardless of how many fields are missing.
- If a question requires a paragraph answer, it's too broad — break it or skip it.
- The user replies once with all answers. intake-director parses the response and populates the intake_brief in a single execution cycle — no multi-turn interaction required.

**Question templates (dynamically generated, not hardcoded):**

```
product missing:
  "What are you advertising? A product name or one-sentence description is enough."

platform missing:
  "Where will this run — TikTok, YouTube, LinkedIn, TV, or somewhere else?"

demographic missing:
  "Who should feel something when they watch this? A short description of your audience works."

emotional_intent missing:
  "What should viewers feel at the end — confident, curious, urgent to act, something else?"
```

**Combined question example** (when product + platform + demographic are all missing):

```
A few quick questions before we start research:

1. What are you advertising? A product name or one-sentence description is enough.
2. Where will this run — TikTok, YouTube, LinkedIn, TV, or somewhere else?
3. Who should feel something when they watch this? A short description of your audience works.
```

### Output — `intake_brief`

```jsonc
{
  "product": "string",
  "brand_name": "string|null",
  "platform": "string",
  "duration_target_seconds": 60,         // default; user can override at proposal
  "demographic": "string",
  "emotional_intent": "string",
  "key_message": "string|null",          // populated if user stated it; else intelligence fills
  "cta": "string|null",                  // populated if user stated it; else bible Round 2b collects it
  "tone": "string|null",
  "reference_files": [
    {
      "filename": "string",
      "inferred_role": "string",          // hypothesis — confirmed at proposal
      "reason": "string"
    }
  ],
  "style_mode_candidate": "animated|cinematic|null",
  "round1_questions_asked": ["string"],
  "intake_completeness": "rich|adequate|thin"
}
```

`intake_completeness` is informational — intelligence-director uses it to calibrate how much to rely on user-stated data vs. inference.

---

## 6. Intelligence Director

### Responsibility

Market research + hit ad analysis + audience psychographic inference → `intelligence_brief`

### Input

`intake_brief`

### Confidence Tiers

Every recommendation field carries a confidence tier. This tier propagates to compliance checkpoints in the bible, determining enforcement level.

| Tier | Meaning | Checkpoint enforcement |
|------|---------|----------------------|
| `research-grounded` | Search results directly support this specific value for this product/platform/demographic | `failure_action: "revise"` |
| `pattern-inferred` | Multiple indirect signals point to this value; no single source states it directly | `failure_action: "revise"` |
| `default-heuristic` | Platform-general best practice; no category-specific data found | `failure_action: "flag"` |

The tier must be honest. `default-heuristic` flag-only checkpoints are correct behavior — they are better than `research-grounded` revise-level checkpoints built on invented data.

### Research Sequence

Four parallel batches, then synthesis. All web search — zero cost.

### Search Query Note

Query templates in each batch below represent **search intent**, not literal API call parameters. Intelligence-director must adapt query formulation to the capabilities of the available search tool. If the search tool does not support `site:` operators, boolean `OR`, or parenthetical grouping, reformulate queries to target the same information need using supported syntax. The goal is the information described in each batch's "Goal" line — not the exact query string.

Multiple queries per batch are expected. If a query returns low-quality results, reformulate and retry rather than proceeding with insufficient data. The batch is complete when the Goal criteria are met, not when all listed query templates have been executed.

---

**Batch 1 — Audience Psychographics**

Goal: infer `emotional_profile`, `core_pain_point`, `aspiration` from research, not hallucination.

```
"{demographic} {product_category} problems OR frustrations"
"{demographic} {product_category} goals OR aspirations"
"{platform} {demographic} content behavior {year}"
site:reddit.com "{product_category}" (frustration|help|wish|tired of)
site:reddit.com "{product_category}" (finally|love|changed my life|best decision)
```

Record specific, citable pain points and aspirations. Vague generalizations do not count.

---

**Batch 2 — Platform Trend Signals**

Goal: identify 3-5 format or creative trends measurably performing on this platform right now.

```
"{platform} ad trends {year}"
"{product_category} ad format performing {platform} {year}"
"viral {product_category} ad {year}"
"{platform} creative best practices {year}"
"best performing {platform} ads {product_category} {year}"
```

For each trend found: record the signal, the source, and a hypothesis for how it applies to this production.

---

**Batch 3 — Hit Ad Analysis**

Goal: extract narrative patterns, pacing models, and hook mechanics from high-performing ads in this category.

```
"best {product_category} ads {year}" site:youtube.com
"{product_category} award-winning commercial {year-1} OR {year}"
"{product_category} ad viral {year}"
"top {product_category} advertisements {year}"
```

**Capability note:** Web search returns article summaries, not video analysis. `cuts_per_minute` and `avg_shot_duration_seconds` are almost never stated in search results. Pacing data will usually be `pattern-inferred` or `default-heuristic` — this is expected and correct. Assign confidence tiers honestly.

For each hit ad found (target 3-5), extract what is accessible from article descriptions:
- `arc_type`: narrative structure (often described in reviews and analyses)
- `hook_mechanic`: how the first 3 seconds opens (often described)
- `emotional_beats`: what the audience feels at each stage (often described)
- `what_works`: one specific, non-generic reason this ad performs
- `pacing_hints`: any cuts/second or pacing language mentioned (rare — record if found)

---

**Batch 4 — Rejected Approaches**

Goal: identify what is oversaturated or declining in this category.

```
"{product_category} ad cliché {year}"
"why {product_category} ads fail"
"overused {product_category} advertising tropes"
"tired {product_category} commercial tropes"
```

Record 2-3 specific approaches to avoid. An empty `rejected_approaches` list is a red flag — every category has clichés. Search harder before concluding none exist.

---

### Synthesis — Recommendations

After all four batches, synthesize into concrete recommendations with confidence tiers:

```jsonc
"recommendations": {
  "arc_type": {
    "value": "problem-solution",
    "confidence": "research-grounded",
    "rationale": "string"              // which batch findings support this
  },
  "pacing_model": {
    "value": "escalating",
    "confidence": "pattern-inferred",
    "rationale": "string"
  },
  "hook_mechanic": {
    "value": "visual-contrast",
    "confidence": "research-grounded",
    "rationale": "string"
  },
  "hook_window_seconds": {
    "value": 3,
    "confidence": "research-grounded", // platform specs are always research-grounded
    "rationale": "string"
  },
  "editing_rhythm_by_beat": {
    "hook": {
      "value": {
        "cuts_density": "rapid",
        "avg_shot_duration_seconds": 1.5,
        "transition_style": "hard_cut"
      },
      "confidence": "pattern-inferred"
    },
    "tension": {
      "value": {
        "cuts_density": "moderate",
        "avg_shot_duration_seconds": 3.0,
        "transition_style": "hard_cut"
      },
      "confidence": "default-heuristic"  // no category-specific data found
    }
    // one entry per beat type found in hit ad analysis
  },
  "overall_rationale": "string"          // one paragraph connecting all findings to recommendations
}
```

### Output — `intelligence_brief`

```jsonc
{
  "audience_psychographics": {
    "emotional_profile": "string",
    "core_pain_point": "string",
    "aspiration": "string"
  },
  "platform_trends": [
    {
      "signal": "string",
      "source": "string",
      "relevance": "string"
    }
  ],
  "hit_ads_analyzed": [
    {
      "title": "string",
      "platform": "string",
      "arc_type": "string",
      "hook_mechanic": "string",
      "what_works": "string",
      "adopted": "boolean",
      "adaptation": "string"
    }
  ],
  "rejected_approaches": [
    {
      "approach": "string",
      "reason": "string"
    }
  ],
  "recommendations": { ... }   // see structure above
}
```

---

## 7. Bible Director

### Responsibility

Synthesize `intake_brief` + `intelligence_brief` → design the full production bible → two-step Round 2 user review → `production_bible`

### Input

`intake_brief` + `intelligence_brief`

### Synthesis Steps (internal — no user interaction until Step 7a)

**Step 1 — Assemble identity:**
Merge `intake_brief` fields with `intelligence_brief.audience_psychographics`. Fill null intake fields:
- `key_message` null → derive from `core_pain_point` + `aspiration` synthesis
- `cta` null → flag as "pending — must be collected at Round 2b before bible approval completes"
- `brand_name` null → infer from product name; flag for proposal confirmation

**Step 2 — Design emotional beat sequence:**

Use `recommendations.arc_type` + `identity.duration_target_seconds` with fixed duration ratios:

```
// ── Configuration Note ──────────────────────────────────────────────────
// Beat ratio tables and intensity curves are inline in v1 (single pipeline consumer).
// When a second pipeline (e.g., brand-video, explainer-video) adopts the bible pattern,
// extract these tables to a shared config file (e.g., config/arc_beat_ratios.yaml)
// and reference from both pipeline specs. Do not build abstraction for a single consumer.
// ────────────────────────────────────────────────────────────────────────

Arc type beat ratios (normalized to 1.0 — multiply by duration_target_seconds):

problem-solution:    hook=0.13, problem=0.25, solution_intro=0.17, proof=0.25, resolution=0.12, cta=0.08
desire-fulfillment:  hook=0.08, desire_paint=0.25, gap=0.17, fulfillment=0.30, brand=0.12, cta=0.08
contrast:            hook=0.12, before=0.22, contrast_moment=0.08, after=0.28, evidence=0.22, cta=0.08
journey:             hook=0.10, challenge=0.20, struggle=0.20, turning_point=0.15, triumph=0.25, cta=0.10
social-proof:        hook=0.10, social_scene=0.25, testimonial=0.30, product_reveal=0.20, brand=0.08, cta=0.07
demo-reveal:         hook=0.13, setup=0.17, demo=0.37, payoff=0.20, cta=0.13
```

Apply intensity curve per `recommendations.pacing_model`:

```
escalating:  0.3 → 0.5 → 0.7 → 0.9 → 0.7 → 0.5
wave:        0.5 → 0.8 → 0.4 → 0.9 → 0.6 → 0.5
punchy:      0.8 → 0.6 → 0.8 → 0.7 → 0.5 → 0.8
slow-burn:   0.2 → 0.4 → 0.6 → 0.8 → 0.9 → 0.7
```

Set `tension_peak_at_seconds` as cumulative time at the beat with highest intensity.

For each beat, populate `script_constraint` and `visual_constraint` from the arc semantics and intelligence recommendations.

**Step 3 — Build visual contract:**
- `visual_motifs`: adopt from `hit_ads_analyzed` — `mandatory=true` only for motifs appearing in 3+ analyzed ads AND not in `rejected_approaches`
- `editing_rhythm`: map from `recommendations.editing_rhythm_by_beat`; carry confidence tier to each entry
- `key_visual_moments`: one mandatory moment per beat where `visual_constraint` specifies a concrete visual requirement (product reveal, brand frame, etc.)
- `style_mode` + `render_runtime`: from `intake_brief.style_mode_candidate` — confirmed at proposal

**Step 4 — Build audio contract:**
- `voice_character.tone`: from `identity.tone` + `target_audience.emotional_profile`
- `voice_character.persona`: from `identity.key_message` semantic register
- `music_direction.arc`: derived from intensity curve — "sparse where intensity < 0.5, building to full arrangement at peak, resolving at cta beat"
- `music_direction.tempo` + `genre_direction`: from `platform_trends` + `recommendations.pacing_model`

**Step 5 — Build deliverables:**
Derive primary aspect ratio from `identity.platform`:
```
tiktok | instagram | youtube_shorts → "9:16"
youtube | linkedin | tv | generic   → "16:9"
```
Set `deliverables.primary`. Leave `deliverables.derivatives` as empty array — proposal-director populates this based on user opt-in.

**Step 6 — Build brand constraints:**
From `intake_brief`: extract stated mandatory/prohibited elements.
Always set `brand_name_in_final_frame: true` (non-negotiable for ad-video).
Derive `tone_guardrails` from `identity.tone` + `target_audience.emotional_profile`.

**Step 7 — Generate compliance manifest:**

Derive checkpoints mechanically. Confidence tier on the source recommendation determines `failure_action`. Evaluation method determines how each checkpoint is evaluated by downstream stages and the EP.

**Evaluation method assignment rules:**

```
check_type == "timing"     → evaluation_method = "structural"
  (word count estimation, duration arithmetic, ±tolerance comparison — all code-verifiable)

check_type == "presence"   → evaluation_method = "structural"
  (string/keyword search in stage output — code-verifiable)

check_type == "structural" → evaluation_method = "structural"
  (scene ID lookup, beat_id matching — code-verifiable)

check_type == "content"    → evaluation_method = "semantic"
  (emotional target achievement, constraint fulfillment — requires LLM judgment)
```

```
// Script compliance — one pair per beat
FOR EACH beat IN narrative.emotional_beat_sequence:

  CP-S{n}:
    applies_to_stage: "script"
    check_type: "timing"
    evaluation_method: "structural"    // word count → WPM estimate → compare to beat.duration_seconds ±10%
    criterion: "Section covering beat {beat.beat_id} ({beat.name}) must be within ±10% of {beat.duration_seconds}s"
    source_confidence: "research-grounded"   // arc ratio tables are always grounded
    failure_action: "revise"

  CP-S{n}a:
    applies_to_stage: "script"
    check_type: "content"
    evaluation_method: "semantic"      // "achieve emotional_target" requires LLM judgment
    criterion: "Section must achieve emotional_target='{beat.emotional_target}'. Constraint: {beat.script_constraint}"
    source_confidence: "research-grounded"
    failure_action: "revise"

// Scene plan compliance — mandatory visual motifs
FOR EACH motif IN visual.visual_motifs WHERE mandatory=true:

  CP-V{n}:
    applies_to_stage: "scene_plan"
    check_type: "presence"
    evaluation_method: "structural"    // keyword search for motif in scene descriptions
    criterion: "'{motif.motif}' must appear in ≥{motif.minimum_scene_count} scenes"
    source_confidence: "research-grounded"   // mandatory requires 3+ hit ad sources
    failure_action: "revise"

// Scene plan compliance — mandatory key visual moments
FOR EACH moment IN visual.key_visual_moments WHERE mandatory=true:

  CP-V{n}:
    applies_to_stage: "scene_plan"
    check_type: "structural"
    evaluation_method: "structural"    // verify scene exists with maps_to_beat == target beat_id
    criterion: "A scene for '{moment.description}' must be present, mapped to beat {moment.maps_to_beat}"
    source_confidence: "research-grounded"
    failure_action: "revise"

// Edit compliance — editing rhythm
FOR EACH rhythm IN visual.editing_rhythm:

  CP-E{n}:
    applies_to_stage: "edit"
    check_type: "timing"
    evaluation_method: "structural"    // shot count and duration arithmetic
    criterion: "Scenes in beat {rhythm.maps_to_beat}: cuts_density={rhythm.cuts_density}, avg_shot≈{rhythm.avg_shot_duration_seconds}s, transition={rhythm.transition_style}"
    source_confidence: {rhythm.confidence}   // propagated from intelligence tier
    failure_action: rhythm.confidence == "default-heuristic" ? "flag" : "revise"

// Brand compliance
CP-B1:
  applies_to_stage: "scene_plan"
  check_type: "presence"
  evaluation_method: "structural"    // string search in final scene
  criterion: "brand_name '{identity.brand_name}' must appear in final scene (last {cta_beat.duration_seconds}s)"
  source_confidence: "research-grounded"
  failure_action: "revise"

CP-B2:
  applies_to_stage: "assets"
  check_type: "presence"
  evaluation_method: "structural"    // string search in asset manifest
  criterion: "mandatory_elements [{brand_constraints.mandatory_elements}] must each appear in asset_manifest"
  source_confidence: "research-grounded"
  failure_action: "flag"

CP-B3:
  applies_to_stage: "script"
  check_type: "presence"
  evaluation_method: "structural"    // keyword/regex search — literal match, not interpretation
  criterion: "prohibited_elements [{brand_constraints.prohibited_elements}] must not appear in any script section"
  source_confidence: "research-grounded"
  failure_action: "revise"
  // NOTE: if any prohibited_element requires interpretation (e.g., "avoid condescending tone"),
  // split it into a separate semantic checkpoint — keyword matching cannot catch tonal violations.
```

---

### Round 2 — Two-Step User Review

#### Step 7a — Strategic Confirmation (must approve before 7b)

Present ONLY:
- Identity (product, audience, emotional intent, key_message)
- Narrative arc (arc_type, hook_mechanic, beat sequence with timing and emotional targets)
- Rejected approaches

**Format:**

```
STORY DIRECTION — [Brand Name] [Platform] [Duration]s Ad

WHO THIS IS FOR
  [demographic] — [emotional_profile]
  They feel: [core_pain_point]
  They want: [aspiration]

THE STORY WE'RE TELLING
  Arc: [arc_type in plain language]
  Opens with: [hook_mechanic] — must land within [hook_window_seconds]s
  Emotional journey:
    [beat_id] [name] (0–Xs):    [emotional_target] — [script_constraint]
    [beat_id] [name] (X–Ys):    [emotional_target] — [script_constraint]
    ...
  Narrative peak at [tension_peak_at_seconds]s.

APPROACHES WE'RE AVOIDING
  • [rejected_approach] — [reason]
  • ...

Does this story direction feel right?
If anything looks wrong here, now is the time to change it — before we build the production details.
```

Wait for explicit approval. If user requests changes:

1. Bible-director re-executes the full synthesis sequence (Steps 1 through 7) incorporating the user's modifications. All previously generated content (visual contract, audio contract, compliance manifest) is discarded and rebuilt — not patched.

   Rationale: the dependency chain is tight (identity → beats → visual → audio → compliance). Any field change at 7a can cascade unpredictably. Full re-derivation is deterministic and costs only LLM compute — no expensive asset generation occurs at this stage.

2. Re-present Step 7a with the updated strategic direction.

3. Do not advance to 7b until `approval.strategic_approved = true`.

#### Step 7b — Execution Confirmation (can be fast-tracked)

Present:
- Visual direction (motifs, key visual moments, editing rhythm)
- Audio direction (voice character, music arc)
- Deliverables (primary format; note derivatives confirmed at proposal)
- Compliance checkpoints (grouped by stage, in plain English)
- Confidence callouts: flag any `default-heuristic` checkpoints so the user knows what is estimated

**Format:**

```
PRODUCTION DETAILS — derived from the direction you confirmed above

VISUAL
  Style: [style_mode] / [render_runtime candidate — confirmed at proposal]
  Visual motifs to maintain: [mandatory motifs]
  Key visual moments:
    [moment] at [beat_name] beat — [description]
  Editing rhythm:
    [beat_name] beat: [cuts_density] cuts, ~[avg_shot]s per shot, [transition_style]  [⚠ estimated] if default-heuristic
    ...

AUDIO
  Voice: [tone], [pacing], [persona]
  Music: [genre_direction], [tempo] — [arc]

CALL TO ACTION
  [If cta is already populated from intake:]
    CTA: "[cta text]" — this exact text will appear in the final frame. Correct?
  [If cta is null:]
    We need the exact call-to-action text for the final frame.
    Examples: "Try free for 30 days" / "Shop now at [url]" / "Download the app"
    What should the CTA say?

WHAT WILL BE DELIVERED
  Primary: [aspect_ratio] [duration]s
  Additional variants: confirmed at the next step

PRODUCTION RULES (enforced throughout)
  Script stage:
    • [CP-S* in plain English]
  Scene planning:
    • [CP-V* in plain English]
  Edit stage:
    • [CP-E* in plain English]  [⚠ estimated — platform general norm] if default-heuristic
  Brand rules (always enforced):
    • [CP-B* in plain English]

These details are mechanically derived from the story direction you approved.
Review if you'd like — or if this looks right, we'll move to production.
```

Apply changes if requested; regenerate affected compliance checkpoints. Set `approval.execution_approved = true` when confirmed.

CTA must be non-null before `approval.execution_approved` can be set to true. If the user approves 7b without providing a CTA (and it was null at intake), bible-director must explicitly ask for it before finalizing the bible. This is the last opportunity — no downstream stage may invent or modify the CTA.

If user requests changes at 7b: bible-director classifies the requested changes before acting.

**Execution-level changes** (visual style, motifs, editing rhythm, audio direction, deliverables, brand constraints):
Bible-director re-executes Steps 3 through 7 (visual, audio, deliverables, brand constraints, compliance manifest) while preserving the approved narrative section from 7a. Re-present Step 7b. `approval.strategic_approved` remains true; only `approval.execution_approved` is reset to false.

**Narrative-level changes** (arc_type, beat sequence structure, hook_mechanic, key_message, emotional_target on any beat, pacing_model):
These changes invalidate the approved strategic direction. Bible-director must:
1. Reset `approval.strategic_approved = false`.
2. Re-execute the full Step 1–7 synthesis (same as a 7a modification — see Step 7a rules above).
3. Re-present Step 7a for re-approval before returning to 7b.
4. Inform the user: "That change affects the story direction we agreed on — let me rebuild and re-confirm the narrative first, then we'll return to production details."

This prevents narrative drift through execution review. The classification is deterministic: if the user's requested change maps to any field in `production_bible.narrative` or `production_bible.identity.key_message`, it is narrative-level.

**Mixed changes** (both narrative-level and execution-level in the same user message):
Treat as narrative-level — the full re-derivation will rebuild execution details anyway.

---

### Round 2a Regression Rules

When the user requests modifications at Step 7a, the EP must determine whether to re-run only bible-director or also re-run intelligence-director. The rule is based on which `intake_brief` fields changed:

**Re-run intelligence-director + bible-director (full regression):**
- `identity.platform` changed → all search queries contained platform as a variable; trend signals, hit ads, and platform-specific norms are invalidated.
- `identity.product` changed → all search queries contained product_category as a variable; audience psychographics, hit ads, and rejected approaches are invalidated.
- `identity.demographic` materially changed (not a minor refinement like "25-35" → "25-40", but a fundamental shift like "college students" → "retirees") → Batch 1 psychographic research is invalidated.

**Re-run bible-director only (narrative re-derivation):**
- `narrative.arc_type` changed → intelligence recommendations included arc_type as one option among others; switching to a different recommended arc_type uses the same research base.
- `narrative.pacing_model` changed → same reasoning.
- `narrative.hook_mechanic` changed → same reasoning.
- Beat-level modifications (emotional_target, script_constraint, timing adjustments) → bible internal changes only.
- `identity.key_message` changed → does not affect search queries; affects bible synthesis only.
- `identity.tone` changed → does not affect search queries; affects bible synthesis only.

**Determination method:** EP compares the user's requested changes against the `intake_brief` fields. If any of `{product, platform, demographic}` would change, EP updates `intake_brief` accordingly and re-dispatches to intelligence-director. Otherwise, EP re-dispatches to bible-director only.

**Round 2b modifications never trigger intelligence regression.** Execution details (visual, audio, deliverables, compliance) do not affect the research basis.

---

## 8. Re-Scoped Downstream Directors

The bible now owns: `arc_type`, `hook_mechanic`, `emotional_beat_sequence`, `visual_motifs`, `editing_rhythm`, `audio_direction`, primary `deliverables` format, and all compliance checkpoints.

`idea-director` and `proposal-director` are re-scoped to eliminate overlap. Only scope boundaries are defined here — full skill rewrites are separate implementation tasks.

### idea-director (post-bible scope)

**Input:** `intake_brief` + `intelligence_brief` + `production_bible`

**Job:** Generate 2-3 concrete creative execution concepts *within* the bible's constraints. Not "what story to tell" — but "how to execute this story" for this specific brand. Specific scenarios, characters, settings, visual metaphors that satisfy the beat sequence and emotional targets.

**Human gate:** idea-director presents execution options and waits for user selection before passing to proposal.

**Output:** `idea_options[]` — each option is a distinct creative execution of the same approved arc. Options differ in scenario and visual metaphor, not in narrative structure.

**What idea-director no longer owns:** narrative structure selection, pacing decisions, hook mechanic choice, emotional beat design — all owned by bible.

### proposal-director (post-bible scope)

**Input:** `selected_idea` + `production_bible`

**Job:** Confirm technical production parameters that require user choice. Creative direction is locked; this stage handles execution logistics only.

**Specific responsibilities:**
- Derivative variants (additional aspect ratios/durations beyond the primary); populate `deliverables.derivatives` in bible
- Subtitle configuration (burnt-in / SRT-only / none, language)
- Dubbing preferences
- Style_mode confirmation (bible sets candidate; proposal gets user sign-off)
- Runtime selection (Remotion vs. HyperFrames for animated — follows AGENT_GUIDE hard rule to present both)
- Budget confirmation and cost estimate (itemized by stage)

**Output:** `production_proposal` — with `deliverables.derivatives` populated (merged back into bible), style_mode locked, runtime locked, logistics confirmed.

**What proposal-director no longer owns:** narrative direction, visual direction, audio direction, primary format, concept options, emotional arc.

### Ownership Summary

| Decision | Owner |
|----------|-------|
| What story to tell | bible-director |
| How the story is structured (arc, beats, pacing) | bible-director |
| What rules govern production (compliance) | bible-director |
| Which specific creative execution of that story | idea-director |
| Which technical variants and production parameters | proposal-director |
| Write the script | script-director (within bible constraints) |

---

## 9. Downstream Compliance Additions

Each downstream director gains one new step: **compliance self-check before submitting output.**

```
COMPLIANCE SELF-CHECK (script, scene_plan, edit directors):

1. Load production_bible.compliance_manifest.checkpoints
   Filter: applies_to_stage == [current stage]
   Split into: structural_checks[], semantic_checks[]

2. Structural checks (deterministic — code execution, not LLM):
   For each structural checkpoint:
     Run the defined code-level evaluation (word count, string match, ID lookup, arithmetic).
     Result: PASS or FAIL (no ambiguity).

   Execution environment for structural checks:

   Structural checks MUST NOT be evaluated by the director's LLM reasoning. They require
   actual code execution. Implementation must use one of the following approaches:

   Option A — Compliance-check tool:
     Create a tool (e.g., `compliance_check`) that accepts { stage_output, checkpoint }
     and executes the check as code. Directors call this tool for each structural checkpoint
     and receive a deterministic { pass: boolean, actual_value, deviation } response.
     The tool handles: word-count-to-duration estimation (assuming ~150 WPM for VO pacing),
     string/keyword search, beat_id presence verification, and arithmetic comparisons.

   Option B — EP gate code layer:
     Structural checks are not executed by directors at all. Directors only run semantic
     self-checks (step 3 below). The EP gate runs all structural checks as code after
     receiving stage output, before running semantic re-evaluation. Directors submit output
     with semantic self-check results only; EP adds structural check results.

   Either option is valid. The implementation plan MUST specify which option is chosen and
   how the code execution environment is provided. The critical invariant is:

     structural checkpoint evaluation = code execution → deterministic PASS/FAIL
     semantic checkpoint evaluation   = LLM judgment  → requires independent re-evaluation

   If this invariant is violated (e.g., LLM asked to "estimate word count"), the entire
   evaluation_method distinction provides no value and should be removed rather than
   implemented incorrectly.

3. Semantic checks (LLM self-assessment):
   For each semantic checkpoint:
     Director evaluates its own output against the criterion.
     Result: PASS, FAIL, or UNCERTAIN.
     If UNCERTAIN → treat as FAIL (err on side of caution).

4. Aggregate results:
   Any structural FAIL where failure_action == "revise" → do NOT submit. Return with compliance_failures[].
   Any semantic FAIL where failure_action == "revise"  → do NOT submit. Return with compliance_failures[].
   Any check (structural or semantic) where failure_action == "flag" → submit with compliance_warnings[].
   All PASS → submit normally.
   Each compliance_failures[] entry: { checkpoint_id, evaluation_method, criterion, actual_value, deviation }

5. EP gate additional step for semantic checkpoints:
   When EP receives stage output, for any semantic checkpoint the director self-assessed as PASS:
     EP runs an independent LLM evaluation of the same criterion against the stage output.
     This independent evaluation does NOT see the director's self-assessment result.
     If EP independent evaluation returns FAIL → override to FAIL regardless of director's self-assessment.
     This prevents self-evaluation rubber-stamping.

   Structural checkpoints are NOT re-evaluated by EP — they are deterministic and the code result is final.
```

The EP reads `compliance_failures[]` at each gate. Any failure → send back with the checkpoint ID, `evaluation_method`, criterion, and actual deviation. The director receives a specific, actionable correction target — not a vague "it didn't work."

---

## 10. EP Gate Updates

### New Gate G-I (after bible)

```
CHECK: Bible approval status — HARD STOP if not both approved
  IF production_bible.approval.strategic_approved == false: STOP. Wait for Round 2a.
  IF production_bible.approval.execution_approved == false: STOP. Wait for Round 2b.
  ONLY THEN: advance to idea-director.
```

### Updated Gate G3 (after script)

```
EXISTING checks: word count vs duration, narrative arc, research integration
ADD:
  # Step 1: Process director-reported results
  IF script.compliance_failures[] non-empty:
    Send back to script-director with: checkpoint_id, criterion, actual_value, deviation
    (Do not proceed to Step 2 — fix failures first.)

  # Step 2: EP independent re-evaluation of semantic checkpoints
  FOR EACH semantic checkpoint WHERE director self-assessed PASS:
    Run independent LLM evaluation: (script_output, checkpoint.criterion)
    The evaluation prompt MUST NOT include the director's self-assessment result.
    IF independent evaluation returns FAIL:
      Override to FAIL. Append to compliance_failures[] with source="ep_independent_eval".
      Send back to script-director with: checkpoint_id, criterion, ep_evaluation_rationale.

  # Step 3: Process warnings
  IF script.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.

  # Structural checkpoints are NOT re-evaluated — their code-based result is final.
```

### Updated Gate G4 (after scene_plan)

```
EXISTING checks: coverage, variety, asset feasibility
ADD:
  # Step 1: Process director-reported results
  IF scene_plan.compliance_failures[] non-empty:
    Send back to scene_plan-director with: checkpoint_id, criterion, actual_value, deviation
    (Do not proceed to Step 2 — fix failures first.)

  # Step 2: EP independent re-evaluation of semantic checkpoints
  FOR EACH semantic checkpoint WHERE director self-assessed PASS:
    Run independent LLM evaluation: (scene_plan_output, checkpoint.criterion)
    The evaluation prompt MUST NOT include the director's self-assessment result.
    IF independent evaluation returns FAIL:
      Override to FAIL. Append to compliance_failures[] with source="ep_independent_eval".
      Send back to scene_plan-director with: checkpoint_id, criterion, ep_evaluation_rationale.

  # Step 3: Process warnings
  IF scene_plan.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.
```

### Updated Gate G6 (after edit)

```
EXISTING checks: timeline completeness, A/V pre-sync
ADD:
  # Step 1: Process director-reported results
  IF edit.compliance_failures[] non-empty:
    Send back to edit-director with: checkpoint_id, criterion, actual_value, deviation
    (Do not proceed to Step 2 — fix failures first.)

  # Step 2: EP independent re-evaluation of semantic checkpoints
  FOR EACH semantic checkpoint WHERE director self-assessed PASS:
    Run independent LLM evaluation: (edit_output, checkpoint.criterion)
    The evaluation prompt MUST NOT include the director's self-assessment result.
    IF independent evaluation returns FAIL:
      Override to FAIL. Append to compliance_failures[] with source="ep_independent_eval".
      Send back to edit-director with: checkpoint_id, criterion, ep_evaluation_rationale.

  # Step 3: Process warnings
  IF edit.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.

  # Structural checkpoints are NOT re-evaluated — their code-based result is final.
```

---

## 11. Pipeline Manifest Changes Required

Changes to `pipeline_defs/ad-video.yaml`:

**Add three new stages before `idea`:**

```yaml
- name: intake
  skill: pipelines/ad-video/intake-director
  produces:
    - intake_brief
  checkpoint_required: false
  human_approval_default: false        # interaction is within the skill, not a checkpoint gate
  review_focus:
    - intake_completeness is honest (not "rich" when prompt was actually thin)
    - round1_questions_asked contains only research-direction questions
    - round1_questions_asked.length ≤ 3

- name: intelligence
  skill: pipelines/ad-video/intelligence-director
  required_artifacts_in:
    - intake_brief
  produces:
    - intelligence_brief
  checkpoint_required: false
  human_approval_default: false
  review_focus:
    - All recommendations carry a confidence tier
    - rejected_approaches is non-empty (empty = insufficient research)
    - audience_psychographics are specific and research-cited, not generic
    - At least 3 hit ads analyzed

- name: bible
  skill: pipelines/ad-video/bible-director
  required_artifacts_in:
    - intake_brief
    - intelligence_brief
  produces:
    - production_bible
  checkpoint_required: true
  human_approval_default: true         # Round 2a and Round 2b are both approval gates
  review_focus:
    - strategic_approved == true before advancing
    - execution_approved == true before advancing
    - compliance_manifest is derived, not hardcoded
    - default-heuristic checkpoints use failure_action=flag only
    - deliverables.primary aspect_ratio matches platform default
    - rejected_approaches present in intelligence section
```

**Update existing `idea` stage:**

```yaml
- name: idea
  skill: pipelines/ad-video/idea-director
  required_artifacts_in:
    - intake_brief          # add
    - intelligence_brief    # add
    - production_bible      # add
  produces:
    - idea_options          # renamed from brief
  checkpoint_required: true
  human_approval_default: true   # now a selection gate, not just review
```

**Update existing `proposal` stage:**

```yaml
- name: proposal
  skill: pipelines/ad-video/proposal-director
  required_artifacts_in:
    - selected_idea         # replaces brief
    - production_bible      # add
  produces:
    - production_proposal   # renamed from proposal_packet
```

---

## 12. New Artifacts Summary

| Artifact | Schema file (to create) | Key fields |
|----------|------------------------|------------|
| `intake_brief` | `schemas/artifacts/intake_brief.schema.json` | product, platform, demographic, emotional_intent, intake_completeness, round1_questions_asked |
| `intelligence_brief` | `schemas/artifacts/intelligence_brief.schema.json` | audience_psychographics, platform_trends, hit_ads_analyzed, rejected_approaches, recommendations (with confidence tiers) |
| `production_bible` | `schemas/artifacts/production_bible.schema.json` | identity, narrative, intelligence, visual, audio, brand_constraints, deliverables, compliance_manifest |

---

## 13. What This Does NOT Change

- No changes to `assets`, `compose`, `publish` directors
- No changes to tool registry, tool contracts, or selector tools
- No changes to existing style playbooks (`ad-brand`, `flat-motion-graphics`, etc.)
- No changes to EP revision limits or send-back policy
- HyperFrames/Remotion runtime presentation rule (AGENT_GUIDE hard rule) remains in proposal — unaffected by re-scoping
- `scene-director-animated.md` and `scene-director-cinematic.md` unchanged — they add compliance self-check only

---

## 14. Open Questions (not blocking implementation)

1. **Bible mid-production modification:** When a user modifies the bible during a script send-back, does the entire `compliance_manifest` regenerate or only the affected checkpoints? Recommend: regenerate only affected checkpoints and log the delta in `modifications_log`. Confirm at EP design time.

2. ~~**Intelligence re-run on Round 2a change**~~ — Resolved. See "Round 2a Regression Rules" in Section 7.

3. **idea-director option count:** Spec says 2-3 execution concepts. Because bible now heavily constrains arc and narrative, the creative differentiation space is smaller — 2 options may be sufficient. Confirm during idea-director skill authoring.
