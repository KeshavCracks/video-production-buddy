# Ad-Video Pre-Production Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add intake → intelligence → bible stages to the ad-video pipeline, backed by a machine-readable production bible contract that downstream stages (script, scene_plan, edit) verify compliance against before submitting.

**Architecture:** Three new pipeline stages run before `idea`: `intake-director` collects minimum brand context (≤3 questions), `intelligence-director` runs market research and hit-ad analysis, and `bible-director` synthesizes both into a structured `production_bible` artifact with an embedded `compliance_manifest`. A new `compliance_check` Python tool handles deterministic structural checks; semantic checks stay in LLM self-assessment with independent EP re-evaluation. Existing `idea-director` and `proposal-director` are re-scoped to creative execution and logistics respectively.

**Tech Stack:** Python 3.10+, JSON Schema draft 2020-12, pytest, `jsonschema` package, existing `BaseTool` / `ToolResult` / `ToolTier` classes from `tools/base_tool.py`.

**Spec:** `docs/superpowers/specs/2026-04-25-ad-video-pre-production-intelligence-design.md`

---

## File Map

### New files
| File | Responsibility |
|------|----------------|
| `schemas/artifacts/intake_brief.schema.json` | Validates intake-director output |
| `schemas/artifacts/intelligence_brief.schema.json` | Validates intelligence-director output |
| `schemas/artifacts/production_bible.schema.json` | Validates bible-director output — the contract |
| `tools/compliance/__init__.py` | Package marker for auto-discovery |
| `tools/compliance/compliance_check.py` | Structural compliance checking tool |
| `tests/qa/test_schemas_preproduction.py` | Schema validation tests |
| `tests/qa/test_compliance_check.py` | Unit tests for ComplianceCheck |
| `skills/pipelines/ad-video/intake-director.md` | Intake director skill |
| `skills/pipelines/ad-video/intelligence-director.md` | Intelligence director skill |
| `skills/pipelines/ad-video/bible-director.md` | Bible director skill |

### Modified files
| File | Change |
|------|--------|
| `skills/pipelines/ad-video/idea-director.md` | Re-scope: receives bible, generates execution concepts only |
| `skills/pipelines/ad-video/proposal-director.md` | Re-scope: technical parameters only, no narrative decisions |
| `skills/pipelines/ad-video/script-director.md` | Add compliance self-check step |
| `skills/pipelines/ad-video/scene-director.md` | Add compliance self-check step |
| `skills/pipelines/ad-video/edit-director.md` | Add compliance self-check step |
| `skills/pipelines/ad-video/executive-producer.md` | Add G-I gate; expand G3/G4/G6 with compliance + EP re-eval |
| `pipeline_defs/ad-video.yaml` | Add intake/intelligence/bible stages; update idea/proposal |

---

## Phase 1: Schemas

### Task 1: intake_brief schema

**Files:**
- Create: `schemas/artifacts/intake_brief.schema.json`

- [ ] **Step 1: Write the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "openmontage/artifacts/intake_brief",
  "title": "Intake Brief",
  "description": "Brand context collected by intake-director. Minimum research-direction fields.",
  "type": "object",
  "required": ["product", "platform", "duration_target_seconds", "intake_completeness", "round1_questions_asked"],
  "properties": {
    "product": { "type": "string", "minLength": 1 },
    "brand_name": { "type": ["string", "null"] },
    "platform": {
      "type": "string",
      "enum": ["youtube", "tiktok", "instagram", "linkedin", "tv", "generic"]
    },
    "duration_target_seconds": { "type": "number", "minimum": 5, "default": 60 },
    "demographic": { "type": ["string", "null"] },
    "emotional_intent": { "type": ["string", "null"] },
    "key_message": { "type": ["string", "null"] },
    "cta": { "type": ["string", "null"] },
    "tone": { "type": ["string", "null"] },
    "reference_files": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["filename", "inferred_role", "reason"],
        "properties": {
          "filename": { "type": "string" },
          "inferred_role": {
            "type": "string",
            "enum": ["brand_guideline", "competitor_ad", "mood_reference", "product_asset", "style_reference", "existing_ad"]
          },
          "reason": { "type": "string" }
        }
      },
      "default": []
    },
    "style_mode_candidate": {
      "type": ["string", "null"],
      "enum": ["animated", "cinematic", null]
    },
    "round1_questions_asked": {
      "type": "array",
      "items": { "type": "string" },
      "maxItems": 3
    },
    "intake_completeness": {
      "type": "string",
      "enum": ["rich", "adequate", "thin"]
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit**

```bash
git add schemas/artifacts/intake_brief.schema.json
git commit -m "feat(schemas): add intake_brief artifact schema"
```

---

### Task 2: intelligence_brief schema

**Files:**
- Create: `schemas/artifacts/intelligence_brief.schema.json`

- [ ] **Step 1: Write the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "openmontage/artifacts/intelligence_brief",
  "title": "Intelligence Brief",
  "description": "Market research and hit-ad analysis produced by intelligence-director.",
  "type": "object",
  "required": ["audience_psychographics", "platform_trends", "hit_ads_analyzed", "rejected_approaches", "recommendations"],
  "properties": {
    "audience_psychographics": {
      "type": "object",
      "required": ["emotional_profile", "core_pain_point", "aspiration"],
      "properties": {
        "emotional_profile": { "type": "string", "minLength": 1 },
        "core_pain_point": { "type": "string", "minLength": 1 },
        "aspiration": { "type": "string", "minLength": 1 }
      }
    },
    "platform_trends": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["signal", "source", "relevance"],
        "properties": {
          "signal": { "type": "string" },
          "source": { "type": "string" },
          "relevance": { "type": "string" }
        }
      }
    },
    "hit_ads_analyzed": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["title", "platform", "arc_type", "hook_mechanic", "what_works", "adopted"],
        "properties": {
          "title": { "type": "string" },
          "platform": { "type": "string" },
          "arc_type": { "type": "string" },
          "hook_mechanic": { "type": "string" },
          "what_works": { "type": "string" },
          "adopted": { "type": "boolean" },
          "adaptation": { "type": "string", "default": "" }
        }
      }
    },
    "rejected_approaches": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["approach", "reason"],
        "properties": {
          "approach": { "type": "string" },
          "reason": { "type": "string" }
        }
      }
    },
    "recommendations": {
      "type": "object",
      "required": ["arc_type", "pacing_model", "hook_mechanic", "hook_window_seconds", "overall_rationale"],
      "properties": {
        "arc_type": { "$ref": "#/$defs/recommendation_field" },
        "pacing_model": { "$ref": "#/$defs/recommendation_field" },
        "hook_mechanic": { "$ref": "#/$defs/recommendation_field" },
        "hook_window_seconds": { "$ref": "#/$defs/recommendation_field" },
        "editing_rhythm_by_beat": {
          "type": "object",
          "additionalProperties": {
            "type": "object",
            "required": ["value", "confidence"],
            "properties": {
              "value": {
                "type": "object",
                "required": ["cuts_density", "avg_shot_duration_seconds", "transition_style"],
                "properties": {
                  "cuts_density": { "type": "string", "enum": ["rapid", "moderate", "slow", "held"] },
                  "avg_shot_duration_seconds": { "type": "number", "minimum": 0.5 },
                  "transition_style": { "type": "string", "enum": ["hard_cut", "dissolve", "whip", "match_cut"] }
                }
              },
              "confidence": { "$ref": "#/$defs/confidence_tier" }
            }
          }
        },
        "overall_rationale": { "type": "string", "minLength": 1 }
      }
    }
  },
  "$defs": {
    "confidence_tier": {
      "type": "string",
      "enum": ["research-grounded", "pattern-inferred", "default-heuristic"]
    },
    "recommendation_field": {
      "type": "object",
      "required": ["value", "confidence", "rationale"],
      "properties": {
        "value": {},
        "confidence": { "$ref": "#/$defs/confidence_tier" },
        "rationale": { "type": "string" }
      }
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit**

```bash
git add schemas/artifacts/intelligence_brief.schema.json
git commit -m "feat(schemas): add intelligence_brief artifact schema"
```

---

### Task 3: production_bible schema

**Files:**
- Create: `schemas/artifacts/production_bible.schema.json`

- [ ] **Step 1: Write the schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "openmontage/artifacts/production_bible",
  "title": "Production Bible",
  "description": "Machine-readable contract between pre-production and production. Downstream stages validate against compliance_manifest.",
  "type": "object",
  "required": ["version", "pipeline", "project_id", "approval", "identity", "narrative", "intelligence", "visual", "audio", "brand_constraints", "deliverables", "compliance_manifest"],
  "properties": {
    "version": { "type": "string", "const": "1.0" },
    "pipeline": { "type": "string", "const": "ad-video" },
    "project_id": { "type": "string" },
    "approval": {
      "type": "object",
      "required": ["strategic_approved", "execution_approved", "modifications_log"],
      "properties": {
        "strategic_approved": { "type": "boolean" },
        "execution_approved": { "type": "boolean" },
        "modifications_log": { "type": "array", "items": { "type": "object" } }
      }
    },
    "identity": {
      "type": "object",
      "required": ["product", "platform", "duration_target_seconds", "key_message", "cta", "tone"],
      "properties": {
        "product": { "type": "string" },
        "brand_name": { "type": "string" },
        "target_audience": {
          "type": "object",
          "properties": {
            "demographic": { "type": "string" },
            "emotional_profile": { "type": "string" },
            "core_pain_point": { "type": "string" },
            "aspiration": { "type": "string" }
          }
        },
        "platform": { "type": "string", "enum": ["youtube", "tiktok", "instagram", "linkedin", "tv", "generic"] },
        "duration_target_seconds": { "type": "number" },
        "key_message": { "type": "string" },
        "cta": { "type": ["string", "null"] },
        "tone": { "type": "string" }
      }
    },
    "narrative": {
      "type": "object",
      "required": ["arc_type", "pacing_model", "hook_mechanic", "hook_window_seconds", "tension_peak_at_seconds", "resolution_type", "emotional_beat_sequence"],
      "properties": {
        "arc_type": { "type": "string", "enum": ["problem-solution", "desire-fulfillment", "contrast", "journey", "social-proof", "demo-reveal"] },
        "pacing_model": { "type": "string", "enum": ["slow-burn", "punchy", "escalating", "wave"] },
        "hook_mechanic": { "type": "string", "enum": ["question", "statement", "visual-contrast", "sound-interrupt", "stat"] },
        "hook_window_seconds": { "type": "number" },
        "tension_peak_at_seconds": { "type": "number" },
        "resolution_type": { "type": "string", "enum": ["relief", "aspiration", "social-validation", "authority"] },
        "emotional_beat_sequence": {
          "type": "array",
          "minItems": 2,
          "items": {
            "type": "object",
            "required": ["beat_id", "name", "duration_seconds", "emotional_target", "intensity", "script_constraint", "visual_constraint"],
            "properties": {
              "beat_id": { "type": "string" },
              "name": {
                "type": "string",
                "minLength": 1,
                "description": "Beat name is arc-type-specific. See spec §7 Step 2 beat ratio tables for valid names per arc_type. Not enum-constrained because the set is determined dynamically by arc_type selection."
              },
              "duration_seconds": { "type": "number", "minimum": 1 },
              "emotional_target": { "type": "string" },
              "intensity": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "script_constraint": { "type": "string" },
              "visual_constraint": { "type": "string" }
            }
          }
        }
      }
    },
    "intelligence": {
      "type": "object",
      "properties": {
        "trending_signals": { "type": "array", "items": { "type": "object" } },
        "reference_ads_analyzed": { "type": "array", "items": { "type": "object" } },
        "rejected_approaches": {
          "type": "array",
          "minItems": 1,
          "items": {
            "type": "object",
            "required": ["approach", "reason"],
            "properties": {
              "approach": { "type": "string" },
              "reason": { "type": "string" }
            }
          }
        }
      }
    },
    "visual": {
      "type": "object",
      "required": ["style_mode", "render_runtime"],
      "properties": {
        "style_mode": { "type": "string", "enum": ["animated", "cinematic"] },
        "render_runtime": { "type": "string", "enum": ["remotion", "hyperframes", "ffmpeg"] },
        "color_direction": { "type": "string" },
        "visual_motifs": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["motif", "mandatory", "minimum_scene_count"],
            "properties": {
              "motif": { "type": "string" },
              "mandatory": { "type": "boolean" },
              "minimum_scene_count": { "type": "integer", "minimum": 1 }
            }
          }
        },
        "key_visual_moments": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["moment_id", "description", "maps_to_beat", "mandatory"],
            "properties": {
              "moment_id": { "type": "string" },
              "description": { "type": "string" },
              "maps_to_beat": { "type": "string" },
              "mandatory": { "type": "boolean" }
            }
          }
        },
        "editing_rhythm": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["maps_to_beat", "cuts_density", "avg_shot_duration_seconds", "transition_style", "confidence"],
            "properties": {
              "maps_to_beat": { "type": "string" },
              "cuts_density": { "type": "string", "enum": ["rapid", "moderate", "slow", "held"] },
              "avg_shot_duration_seconds": { "type": "number" },
              "transition_style": { "type": "string", "enum": ["hard_cut", "dissolve", "whip", "match_cut"] },
              "confidence": { "type": "string", "enum": ["research-grounded", "pattern-inferred", "default-heuristic"] }
            }
          }
        }
      }
    },
    "audio": {
      "type": "object",
      "properties": {
        "voice_character": {
          "type": "object",
          "properties": {
            "tone": { "type": "string" },
            "pacing": { "type": "string", "enum": ["measured", "energetic", "conversational"] },
            "persona": { "type": "string" }
          }
        },
        "music_direction": {
          "type": "object",
          "properties": {
            "mood": { "type": "string" },
            "tempo": { "type": "string", "enum": ["slow", "medium", "fast"] },
            "genre_direction": { "type": "string" },
            "arc": { "type": "string" }
          }
        },
        "av_sync_notes": { "type": "string" }
      }
    },
    "brand_constraints": {
      "type": "object",
      "required": ["brand_name_in_final_frame"],
      "properties": {
        "brand_name_in_final_frame": { "type": "boolean", "const": true },
        "mandatory_elements": { "type": "array", "items": { "type": "string" } },
        "prohibited_elements": { "type": "array", "items": { "type": "string" } },
        "tone_guardrails": { "type": "array", "items": { "type": "string" } }
      }
    },
    "deliverables": {
      "type": "object",
      "required": ["primary"],
      "properties": {
        "primary": {
          "type": "object",
          "required": ["aspect_ratio", "duration_seconds"],
          "properties": {
            "aspect_ratio": { "type": "string", "enum": ["16:9", "9:16", "1:1"] },
            "duration_seconds": { "type": "number" }
          }
        },
        "derivatives": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["variant_id", "aspect_ratio", "duration_seconds"],
            "properties": {
              "variant_id": { "type": "string" },
              "aspect_ratio": { "type": "string" },
              "duration_seconds": { "type": "number" },
              "adaptation_notes": { "type": "string" }
            }
          },
          "default": []
        }
      }
    },
    "compliance_manifest": {
      "type": "object",
      "required": ["checkpoints"],
      "properties": {
        "checkpoints": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["id", "applies_to_stage", "description", "check_type", "evaluation_method", "criterion", "source_confidence", "failure_action"],
            "properties": {
              "id": { "type": "string" },
              "applies_to_stage": { "type": "string", "enum": ["script", "scene_plan", "assets", "edit"] },
              "description": { "type": "string" },
              "check_type": { "type": "string", "enum": ["structural", "content", "timing", "presence"] },
              "evaluation_method": { "type": "string", "enum": ["structural", "semantic"] },
              "criterion": { "type": "string" },
              "source_confidence": { "type": "string", "enum": ["research-grounded", "pattern-inferred", "default-heuristic"] },
              "failure_action": { "type": "string", "enum": ["revise", "flag"] }
            }
          }
        }
      }
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Commit**

```bash
git add schemas/artifacts/production_bible.schema.json
git commit -m "feat(schemas): add production_bible artifact schema"
```

---

### Task 4: Schema validation tests

**Files:**
- Create: `tests/qa/test_schemas_preproduction.py`

- [ ] **Step 1: Install jsonschema if not present**

```bash
pip install jsonschema
```

- [ ] **Step 2: Write the tests**

```python
#!/usr/bin/env python3
"""Tests: validate intake_brief, intelligence_brief, production_bible schemas."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import jsonschema
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas" / "artifacts"


def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.schema.json"
    assert path.exists(), f"Schema not found: {path}"
    with open(path) as f:
        return json.load(f)


def validate(instance: dict, schema: dict) -> None:
    jsonschema.validate(instance, schema, format_checker=jsonschema.FormatChecker())


class TestIntakeBriefSchema:
    def setup_method(self):
        self.schema = load_schema("intake_brief")

    def test_valid_minimal(self):
        validate({
            "product": "Acme App",
            "platform": "tiktok",
            "duration_target_seconds": 30,
            "intake_completeness": "thin",
            "round1_questions_asked": ["What are you advertising?"]
        }, self.schema)

    def test_valid_rich(self):
        validate({
            "product": "Acme App", "brand_name": "Acme", "platform": "youtube",
            "duration_target_seconds": 60, "demographic": "urban professionals 25-35",
            "emotional_intent": "confidence", "key_message": "Reclaim two hours every day",
            "cta": "Try free at acme.com", "tone": "warm and direct",
            "reference_files": [{"filename": "brand.pdf", "inferred_role": "brand_guideline", "reason": "Has palette"}],
            "style_mode_candidate": "animated",
            "round1_questions_asked": [],
            "intake_completeness": "rich"
        }, self.schema)

    def test_rejects_more_than_3_questions(self):
        with pytest.raises(jsonschema.ValidationError):
            validate({
                "product": "X", "platform": "youtube", "duration_target_seconds": 60,
                "intake_completeness": "thin",
                "round1_questions_asked": ["Q1", "Q2", "Q3", "Q4"]
            }, self.schema)

    def test_rejects_invalid_platform(self):
        with pytest.raises(jsonschema.ValidationError):
            validate({
                "product": "X", "platform": "snapchat", "duration_target_seconds": 60,
                "intake_completeness": "rich", "round1_questions_asked": []
            }, self.schema)

    def test_rejects_missing_required(self):
        with pytest.raises(jsonschema.ValidationError):
            validate({"product": "X"}, self.schema)


class TestIntelligenceBriefSchema:
    def setup_method(self):
        self.schema = load_schema("intelligence_brief")

    def _valid_base(self) -> dict:
        return {
            "audience_psychographics": {
                "emotional_profile": "time-starved achievers",
                "core_pain_point": "feel productive but aren't",
                "aspiration": "reclaim control"
            },
            "platform_trends": [{"signal": "lo-fi aesthetic", "source": "Sprout 2026", "relevance": "calm tone"}],
            "hit_ads_analyzed": [{"title": "Monday.com", "platform": "youtube", "arc_type": "problem-solution",
                                   "hook_mechanic": "statement", "what_works": "pain-first hook", "adopted": True}],
            "rejected_approaches": [{"approach": "celebrity endorsement", "reason": "oversaturated"}],
            "recommendations": {
                "arc_type": {"value": "problem-solution", "confidence": "research-grounded", "rationale": "Dominant pattern"},
                "pacing_model": {"value": "escalating", "confidence": "pattern-inferred", "rationale": "Fast-cut hooks"},
                "hook_mechanic": {"value": "statement", "confidence": "research-grounded", "rationale": "All ads"},
                "hook_window_seconds": {"value": 3, "confidence": "research-grounded", "rationale": "TikTok 3s"},
                "overall_rationale": "Problem-solution with escalating pacing dominates."
            }
        }

    def test_valid_base(self):
        validate(self._valid_base(), self.schema)

    def test_rejects_empty_rejected_approaches(self):
        base = self._valid_base()
        base["rejected_approaches"] = []
        with pytest.raises(jsonschema.ValidationError):
            validate(base, self.schema)

    def test_rejects_invalid_confidence_tier(self):
        base = self._valid_base()
        base["recommendations"]["arc_type"]["confidence"] = "guessed"
        with pytest.raises(jsonschema.ValidationError):
            validate(base, self.schema)


MINIMAL_BIBLE = {
    "version": "1.0", "pipeline": "ad-video", "project_id": "test-001",
    "approval": {"strategic_approved": False, "execution_approved": False, "modifications_log": []},
    "identity": {
        "product": "Acme App", "brand_name": "Acme", "platform": "tiktok",
        "duration_target_seconds": 30, "key_message": "Get two hours back", "cta": None, "tone": "warm"
    },
    "narrative": {
        "arc_type": "problem-solution", "pacing_model": "escalating",
        "hook_mechanic": "statement", "hook_window_seconds": 3,
        "tension_peak_at_seconds": 18, "resolution_type": "aspiration",
        "emotional_beat_sequence": [
            {"beat_id": "B1", "name": "hook", "duration_seconds": 4, "emotional_target": "curiosity",
             "intensity": 0.8, "script_constraint": "Open with the pain", "visual_constraint": "Clock imagery"},
            {"beat_id": "B2", "name": "cta", "duration_seconds": 4, "emotional_target": "action",
             "intensity": 0.5, "script_constraint": "Deliver CTA", "visual_constraint": "Brand frame"}
        ]
    },
    "intelligence": {
        "trending_signals": [{"signal": "lo-fi", "source": "Sprout 2026", "applied_to": "visual"}],
        "reference_ads_analyzed": [{"title": "Monday.com", "platform": "youtube", "what_works": "pain-first", "adopted": True, "adaptation": "shorter"}],
        "rejected_approaches": [{"approach": "celebrity", "reason": "oversaturated"}]
    },
    "visual": {
        "style_mode": "animated", "render_runtime": "remotion", "color_direction": "muted warm",
        "visual_motifs": [{"motif": "clock imagery", "mandatory": True, "minimum_scene_count": 2}],
        "key_visual_moments": [{"moment_id": "KV1", "description": "product reveal", "maps_to_beat": "B1", "mandatory": True}],
        "editing_rhythm": [{"maps_to_beat": "B1", "cuts_density": "rapid", "avg_shot_duration_seconds": 1.5, "transition_style": "hard_cut", "confidence": "pattern-inferred"}]
    },
    "audio": {
        "voice_character": {"tone": "warm", "pacing": "energetic", "persona": "trusted peer"},
        "music_direction": {"mood": "upbeat", "tempo": "medium", "genre_direction": "indie pop", "arc": "sparse to full"},
        "av_sync_notes": "Music swells at tension peak"
    },
    "brand_constraints": {
        "brand_name_in_final_frame": True,
        "mandatory_elements": ["Acme logo"],
        "prohibited_elements": ["competitors"],
        "tone_guardrails": ["never condescending"]
    },
    "deliverables": {"primary": {"aspect_ratio": "9:16", "duration_seconds": 30}, "derivatives": []},
    "compliance_manifest": {
        "checkpoints": [{
            "id": "CP-S1", "applies_to_stage": "script", "description": "Hook timing",
            "check_type": "timing", "evaluation_method": "structural",
            "criterion": "Section covering beat B1 (hook) must be within ±10% of 4s",
            "source_confidence": "research-grounded", "failure_action": "revise"
        }]
    }
}


class TestProductionBibleSchema:
    def setup_method(self):
        self.schema = load_schema("production_bible")

    def test_valid_minimal_bible(self):
        validate(MINIMAL_BIBLE, self.schema)

    def test_rejects_wrong_pipeline(self):
        with pytest.raises(jsonschema.ValidationError):
            validate({**MINIMAL_BIBLE, "pipeline": "animated-explainer"}, self.schema)

    def test_rejects_invalid_arc_type(self):
        bad_narrative = {**MINIMAL_BIBLE["narrative"], "arc_type": "mystery-reveal"}
        with pytest.raises(jsonschema.ValidationError):
            validate({**MINIMAL_BIBLE, "narrative": bad_narrative}, self.schema)

    def test_rejects_invalid_evaluation_method(self):
        bad_cp = [{**MINIMAL_BIBLE["compliance_manifest"]["checkpoints"][0], "evaluation_method": "heuristic"}]
        with pytest.raises(jsonschema.ValidationError):
            validate({**MINIMAL_BIBLE, "compliance_manifest": {"checkpoints": bad_cp}}, self.schema)

    def test_brand_name_in_final_frame_must_be_true(self):
        bad_bc = {**MINIMAL_BIBLE["brand_constraints"], "brand_name_in_final_frame": False}
        with pytest.raises(jsonschema.ValidationError):
            validate({**MINIMAL_BIBLE, "brand_constraints": bad_bc}, self.schema)

    def test_accepts_arc_specific_beat_names(self):
        """Beat names are arc-type-specific (e.g., 'problem', 'proof' for problem-solution).
        Schema must not reject valid arc-specific names."""
        bible = json.loads(json.dumps(MINIMAL_BIBLE))  # deep copy
        bible["narrative"]["emotional_beat_sequence"] = [
            {"beat_id": "B1", "name": "hook", "duration_seconds": 8, "emotional_target": "curiosity",
             "intensity": 0.8, "script_constraint": "Open with pain", "visual_constraint": "Clock"},
            {"beat_id": "B2", "name": "problem", "duration_seconds": 15, "emotional_target": "recognition",
             "intensity": 0.5, "script_constraint": "Show the problem", "visual_constraint": "Overwhelm"},
            {"beat_id": "B3", "name": "solution_intro", "duration_seconds": 10, "emotional_target": "hope",
             "intensity": 0.7, "script_constraint": "Introduce product", "visual_constraint": "Product UI"},
            {"beat_id": "B4", "name": "proof", "duration_seconds": 15, "emotional_target": "trust",
             "intensity": 0.9, "script_constraint": "Show evidence", "visual_constraint": "Stats"},
            {"beat_id": "B5", "name": "resolution", "duration_seconds": 7, "emotional_target": "relief",
             "intensity": 0.7, "script_constraint": "Resolve", "visual_constraint": "Happy user"},
            {"beat_id": "B6", "name": "cta", "duration_seconds": 5, "emotional_target": "action",
             "intensity": 0.5, "script_constraint": "Deliver CTA", "visual_constraint": "Brand frame"},
        ]
        validate(bible, self.schema)

    def test_note_cta_null_with_execution_approved_passes_schema(self):
        """JSON Schema cannot enforce: execution_approved=true → cta non-null.
        This cross-field invariant is enforced by EP gate G-I, not the schema.
        This test documents the limitation."""
        import copy
        approved_null_cta = copy.deepcopy(MINIMAL_BIBLE)
        approved_null_cta["approval"]["strategic_approved"] = True
        approved_null_cta["approval"]["execution_approved"] = True
        # Schema allows this — cta is null but execution_approved is true.
        # EP gate G-I MUST reject this at runtime.
        validate(approved_null_cta, self.schema)  # passes — expected limitation
```

- [ ] **Step 3: Run tests — expect PASS**

```bash
cd /mnt/f/zhouzhoushen/work/OpenMontage
python -m pytest tests/qa/test_schemas_preproduction.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/qa/test_schemas_preproduction.py
git commit -m "test(schemas): validate intake_brief, intelligence_brief, production_bible schemas"
```

---

## Phase 2: Compliance Check Tool

### Task 5: compliance_check tool + tests (TDD)

**Files:**
- Create: `tools/compliance/__init__.py`
- Create: `tools/compliance/compliance_check.py`
- Create: `tests/qa/test_compliance_check.py`

- [ ] **Step 1: Write failing tests first**

```python
#!/usr/bin/env python3
# tests/qa/test_compliance_check.py
"""Unit tests for ComplianceCheck — structural checkpoint evaluation."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import will fail until tool is implemented — correct (TDD RED phase)
from tools.compliance.compliance_check import ComplianceCheck


@pytest.fixture
def tool():
    return ComplianceCheck()


# ── Timing ───────────────────────────────────────────────────────────────────

def test_timing_pass_within_tolerance(tool):
    # 120 words at 150 WPM = 48s. Target 50s ±5s. PASS.
    stage = {"sections": [{"beat_id": "B1", "narration": " ".join(["word"] * 120)}]}
    cp = {"id": "CP-S1", "check_type": "timing", "evaluation_method": "structural",
          "criterion": "Section covering beat B1 (hook) must be within ±10% of 50s",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True and r.data["deviation"] is None


def test_timing_fail_too_short(tool):
    # 10 words = 4s. Target 50s ±5s. FAIL.
    stage = {"sections": [{"beat_id": "B1", "narration": " ".join(["word"] * 10)}]}
    cp = {"id": "CP-S1", "check_type": "timing", "evaluation_method": "structural",
          "criterion": "Section covering beat B1 (hook) must be within ±10% of 50s",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False and r.data["deviation"] is not None


def test_timing_sums_multiple_sections_for_beat(tool):
    # Two B1 sections: 60+60=120 words → 48s. Target 50s. PASS. B2 ignored.
    stage = {"sections": [
        {"beat_id": "B1", "narration": " ".join(["word"] * 60)},
        {"beat_id": "B1", "narration": " ".join(["word"] * 60)},
        {"beat_id": "B2", "narration": " ".join(["word"] * 200)},
    ]}
    cp = {"id": "CP-S1", "check_type": "timing", "evaluation_method": "structural",
          "criterion": "Section covering beat B1 (hook) must be within ±10% of 50s",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True


def test_timing_unparseable_beat_id_fails_safe(tool):
    """If criterion doesn't contain 'beat <ID>', fail-safe instead of silently summing all sections."""
    stage = {"sections": [{"beat_id": "B1", "narration": " ".join(["word"] * 120)}]}
    cp = {"id": "CP-S1", "check_type": "timing", "evaluation_method": "structural",
          "criterion": "The hook section should be about 50s",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False


# ── Presence ──────────────────────────────────────────────────────────────────

def test_presence_brand_name_found(tool):
    stage = {"scenes": [{"description": "Acme Corp logo fades in", "maps_to_beat": "B6"}]}
    cp = {"id": "CP-B1", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "brand_name 'Acme Corp' must appear in final scene (last 5s)",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True


def test_presence_brand_name_missing(tool):
    stage = {"scenes": [{"description": "Generic outro", "maps_to_beat": "B6"}]}
    cp = {"id": "CP-B1", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "brand_name 'Acme Corp' must appear in final scene (last 5s)",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False


def test_presence_motif_minimum_count_met(tool):
    stage = {"scenes": [
        {"description": "clock imagery ticking"},
        {"description": "clock imagery on wall"},
        {"description": "product reveal"},
    ]}
    cp = {"id": "CP-V1", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "'clock imagery' must appear in ≥2 scenes",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True


def test_presence_motif_minimum_count_not_met(tool):
    stage = {"scenes": [
        {"description": "clock imagery ticking"},
        {"description": "product showcase"},
    ]}
    cp = {"id": "CP-V1", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "'clock imagery' must appear in ≥3 scenes",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False


# ── Presence: Negated (prohibited elements) ───────────────────────────────────

def test_presence_prohibited_element_found(tool):
    """CP-B3: prohibited terms found → FAIL."""
    stage = {"sections": [{"narration": "Our competitor Brand X is worse"}]}
    cp = {"id": "CP-B3", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "prohibited_elements ['competitor', 'brand x'] must not appear in any script section",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False


def test_presence_prohibited_element_clean(tool):
    """CP-B3: no prohibited terms found → PASS."""
    stage = {"sections": [{"narration": "Our product is amazing"}]}
    cp = {"id": "CP-B3", "check_type": "presence", "evaluation_method": "structural",
          "criterion": "prohibited_elements ['competitor'] must not appear in any script section",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True


# ── Structural (beat mapping) ─────────────────────────────────────────────────

def test_structural_beat_mapping_found(tool):
    stage = {"scenes": [
        {"maps_to_beat": "B1", "description": "hook scene"},
        {"maps_to_beat": "B3", "description": "product reveal with full-screen close-up"},
    ]}
    cp = {"id": "CP-V2", "check_type": "structural", "evaluation_method": "structural",
          "criterion": "A scene for 'product reveal' must be present, mapped to beat B3",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is True


def test_structural_beat_mapping_not_found(tool):
    stage = {"scenes": [{"maps_to_beat": "B1", "description": "hook"}]}
    cp = {"id": "CP-V2", "check_type": "structural", "evaluation_method": "structural",
          "criterion": "A scene for 'product reveal' must be present, mapped to beat B3",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": stage, "checkpoint": cp})
    assert r.success and r.data["pass"] is False


# ── Guards ────────────────────────────────────────────────────────────────────

def test_rejects_semantic_checkpoint(tool):
    cp = {"id": "CP-S1a", "check_type": "content", "evaluation_method": "semantic",
          "criterion": "Section must achieve emotional_target='curiosity'",
          "failure_action": "revise"}
    r = tool.execute({"stage_output": {}, "checkpoint": cp})
    assert r.success is False and "structural" in r.error.lower()


def test_rejects_missing_stage_output(tool):
    r = tool.execute({"checkpoint": {"id": "CP-S1", "check_type": "timing",
                                      "evaluation_method": "structural",
                                      "criterion": "x", "failure_action": "revise"}})
    assert r.success is False


def test_rejects_missing_checkpoint(tool):
    r = tool.execute({"stage_output": {"sections": []}})
    assert r.success is False


def test_rejects_unknown_check_type(tool):
    cp = {"id": "CP-X1", "check_type": "unknown_type",
          "evaluation_method": "structural", "criterion": "x", "failure_action": "flag"}
    r = tool.execute({"stage_output": {}, "checkpoint": cp})
    assert r.success is False
```

- [ ] **Step 2: Run tests — expect ModuleNotFoundError**

```bash
python -m pytest tests/qa/test_compliance_check.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'tools.compliance'`

- [ ] **Step 3: Create package marker**

```python
# tools/compliance/__init__.py
# empty — presence enables pkgutil.walk_packages auto-discovery
```

- [ ] **Step 3a: Verify tool registry discovery mechanism**

```bash
# Check how the registry discovers tools
grep -n "discover\|walk_packages\|import_module\|register\|_tools" tools/tool_registry.py | head -10
```

Inspect the output:
- If the registry uses `pkgutil.walk_packages` or `importlib` scanning on the `tools/` directory:
  → The empty `__init__.py` is sufficient. Proceed to Step 4.
- If the registry uses an explicit list or manual registration:
  → Find where tools are registered (e.g., a `TOOL_CLASSES` list or `register()` calls).
  → Add `from tools.compliance.compliance_check import ComplianceCheck` and register it
    following the same pattern as existing tools.
  → Document what you added in the commit message.

- [ ] **Step 4: Implement the tool**

```python
# tools/compliance/compliance_check.py
"""Structural compliance checker for production_bible checkpoints.

Evaluates check_type IN ['timing', 'presence', 'structural'] deterministically.
Rejects semantic checkpoints — those require LLM judgment.
"""
from __future__ import annotations

import json
import re
from typing import Any

from tools.base_tool import (
    BaseTool, Determinism, ExecutionMode,
    ToolResult, ToolRuntime, ToolStability, ToolTier,
)

_WORDS_PER_MINUTE = 150   # VO pacing assumption per spec §9
_TIMING_TOLERANCE = 0.10  # ±10%


class ComplianceCheck(BaseTool):
    """Evaluate a structural compliance checkpoint against stage output.

    Accepts: { stage_output: dict, checkpoint: dict }
    Returns ToolResult.data: { checkpoint_id, pass, actual_value, deviation, failure_action }
    """

    name = "compliance_check"
    version = "1.0.0"
    tier = ToolTier.CORE
    stability = ToolStability.BETA
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.LOCAL
    capability = "compliance"
    provider = "openmontage"
    best_for = ["structural compliance checking", "bible checkpoint evaluation"]
    not_good_for = ["semantic compliance — use LLM judgment instead"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        stage_output = inputs.get("stage_output")
        checkpoint = inputs.get("checkpoint")

        if stage_output is None:
            return ToolResult(success=False, error="stage_output is required")
        if not checkpoint:
            return ToolResult(success=False, error="checkpoint is required")

        eval_method = checkpoint.get("evaluation_method", "")
        if eval_method != "structural":
            return ToolResult(
                success=False,
                error=(
                    f"compliance_check only handles structural checkpoints; "
                    f"got evaluation_method='{eval_method}'. "
                    f"Semantic checkpoints require LLM judgment."
                ),
            )

        check_type = checkpoint.get("check_type", "")
        dispatch = {
            "timing": self._check_timing,
            "presence": self._check_presence,
            "structural": self._check_structural,
        }
        handler = dispatch.get(check_type)
        if not handler:
            return ToolResult(
                success=False,
                error=f"Unknown check_type: '{check_type}'. Valid: {list(dispatch)}"
            )

        result = handler(stage_output, checkpoint)
        return ToolResult(
            success=True,
            data={
                "checkpoint_id": checkpoint.get("id"),
                "pass": result["pass"],
                "actual_value": result.get("actual_value"),
                "deviation": result.get("deviation"),
                "failure_action": checkpoint.get("failure_action", "flag"),
            },
        )

    def _check_timing(self, stage_output: dict, checkpoint: dict) -> dict:
        """Word count → WPM estimate → compare to target_seconds ±10%."""
        criterion = checkpoint.get("criterion", "")
        # Prefer anchored match ("of Xs") for precision; fall back to any "Ns" pattern.
        # NOTE: v1 uses natural-language criteria. This parser will be replaced in v2
        # when criteria migrate to structured {field, operator, value, tolerance} format.
        duration_match = re.search(r"\bof\s+(\d+(?:\.\d+)?)s\b", criterion)
        if not duration_match:
            duration_match = re.search(r"(\d+(?:\.\d+)?)s\b", criterion)
        if not duration_match:
            return {"pass": False, "actual_value": None,
                    "deviation": f"Cannot parse target duration from: {criterion!r}"}
        target_seconds = float(duration_match.group(1))
        beat_match = re.search(r"\bbeat (\w+)", criterion)
        if not beat_match:
            return {"pass": False, "actual_value": None,
                    "deviation": (
                        f"Cannot parse beat_id from criterion: {criterion!r}. "
                        f"Expected 'beat <ID>' pattern. "
                        f"NOTE: v1 uses natural-language criteria; this parser will be replaced in v2."
                    )}
        beat_id = beat_match.group(1)

        total_words = 0
        for section in stage_output.get("sections", []):
            if section.get("beat_id") != beat_id and section.get("maps_to_beat") != beat_id:
                continue
            text = section.get("narration", section.get("text", ""))
            total_words += len(text.split())

        estimated = (total_words / _WORDS_PER_MINUTE) * 60
        tolerance = target_seconds * _TIMING_TOLERANCE
        passed = abs(estimated - target_seconds) <= tolerance
        return {
            "pass": passed,
            "actual_value": f"{estimated:.1f}s",
            "deviation": (None if passed else
                          f"estimated {estimated:.1f}s vs target {target_seconds}s "
                          f"(tolerance ±{tolerance:.1f}s)"),
        }

    def _check_presence(self, stage_output: dict, checkpoint: dict) -> dict:
        """String/keyword search across serialised stage_output.
        Supports both positive ('must appear') and negated ('must not appear') checks."""
        criterion = checkpoint.get("criterion", "")
        output_str = json.dumps(stage_output).lower()
        quoted_terms = re.findall(r"'([^']+)'", criterion)
        if not quoted_terms:
            return {"pass": False, "actual_value": None,
                    "deviation": f"Cannot parse presence target from: {criterion!r}"}

        # Detect negation — prohibited / must-not checks
        is_negated = bool(re.search(
            r"\bmust not\b|\bprohibited\b|\bmust never\b|\bnot appear\b",
            criterion.lower(),
        ))

        found_map = {t: output_str.count(t.lower()) for t in quoted_terms}

        if is_negated:
            # Prohibited: PASS only if NONE of the terms are found
            violations = {t: c for t, c in found_map.items() if c > 0}
            return {
                "pass": len(violations) == 0,
                "actual_value": found_map,
                "deviation": (None if not violations else
                              "; ".join(f"prohibited '{t}' found {c} time(s)"
                                        for t, c in violations.items())),
            }

        # Positive: must appear ≥ min_count times
        count_match = re.search(r"[≥>=]\s*(\d+)", criterion)
        min_count = int(count_match.group(1)) if count_match else 1

        results = [{"term": t, "found": found_map[t], "required": min_count}
                   for t in quoted_terms]
        all_passed = all(r["found"] >= r["required"] for r in results)
        failing = [r for r in results if r["found"] < r["required"]]
        return {
            "pass": all_passed,
            "actual_value": found_map,
            "deviation": (None if all_passed else
                          "; ".join(f"'{r['term']}' found {r['found']}, required ≥{r['required']}"
                                    for r in failing)),
        }

    def _check_structural(self, stage_output: dict, checkpoint: dict) -> dict:
        """Beat ID mapping: verify ≥1 scene maps to the target beat."""
        criterion = checkpoint.get("criterion", "")
        beat_match = re.search(r"\bbeat (\w+)", criterion)
        if not beat_match:
            return self._check_presence(stage_output, checkpoint)
        target_beat = beat_match.group(1)
        scenes = stage_output.get("scenes", [])
        matched = [s for s in scenes
                   if s.get("maps_to_beat") == target_beat or s.get("beat_id") == target_beat]
        passed = len(matched) > 0
        return {
            "pass": passed,
            "actual_value": f"{len(matched)} scene(s) mapped to beat {target_beat}",
            "deviation": (None if passed else f"No scene found mapped to beat {target_beat}"),
        }
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
python -m pytest tests/qa/test_compliance_check.py -v
```

Expected: All 16 tests pass. (Original 13 + unparseable_beat_id + 2 prohibited_element tests)

- [ ] **Step 6: Verify auto-discovery**

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
tool = registry.get('compliance_check')
print('Found:', tool.name if tool else 'NOT FOUND')
"
```

Expected: `Found: compliance_check`

- [ ] **Step 7: Commit**

```bash
git add tools/compliance/__init__.py tools/compliance/compliance_check.py tests/qa/test_compliance_check.py
git commit -m "feat(compliance): add ComplianceCheck structural checkpoint evaluation tool"
```

---

## Phase 3: New Director Skills

### Task 6: intake-director.md

**Files:**
- Create: `skills/pipelines/ad-video/intake-director.md`

- [ ] **Step 1: Write the skill**

```markdown
# Intake Director — Ad Video Pipeline

## When to Use

You are the **Intake Director** for the ad-video pipeline. You receive the user's raw
prompt, detect whether it contains enough information to run useful research, and either
proceed directly or ask up to 3 clarifying questions in a single message.

You do NOT research. You do NOT make creative decisions. You collect information only.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/intake_brief.schema.json` | Artifact validation |
| User input | Raw prompt | Source of truth |

## Minimum Information Schema

Four fields determine research direction. If present in the prompt, do not ask.

| Field | Why it changes research | Can intelligence fill it? |
|-------|------------------------|--------------------------|
| `product` | Defines ad category; determines competitor pool | No — must come from user |
| `platform` | Determines trend domain, pacing norms, aspect ratio | No — critical |
| `demographic` | Determines pain point and aspiration research | Partially |
| `emotional_intent` | Determines hook mechanics and arc types to study | Partially |

## Process

### Step 1: Parse the Prompt

Extract: `product`, `brand_name`, `platform`, `duration_target_seconds` (default 60),
`demographic`, `emotional_intent`, `key_message`, `cta`, `tone`.

Mark each as present or absent.

### Step 2: Analyze Reference Files (if provided)

Infer `inferred_role` for each file:
- `brand_guideline` — color palettes, typography, logo rules
- `competitor_ad` — advertisement from another brand
- `mood_reference` — imagery conveying a desired aesthetic
- `product_asset` — product photos or screenshots
- `style_reference` — video/image representing a visual style
- `existing_ad` — a prior ad from this brand

Infer `style_mode_candidate`:
- Live action / cinematic references → `cinematic`
- Motion graphics / tech / SaaS → `animated`
- No references or mixed → `animated` (safe default — animated does not require live-action
  footage, so all assets can be generated; this minimizes asset-stage failure risk)

These are hypotheses, confirmed at proposal.

### Step 3: Detect and Score Missing Fields

```
missing = [field for field in [product, platform, demographic, emotional_intent]
           if field is not present in prompt]

IF len(missing) == 0:
    intake_completeness = "rich". Skip to Step 5.

ELIF len(missing) <= 3:
    Ask all missing-field questions in a single message. Capped at 3.
    intake_completeness = "adequate" (1-2 missing) or "thin" (3 missing).

ELIF len(missing) == 4:
    Ask top 3: product → platform → demographic.
    Leave emotional_intent for intelligence to infer.
    intake_completeness = "thin".
```

### Step 4: Ask Round 1 Questions (if needed)

Present all questions in **one message**. Each question on its own line. Max 3 total.

**Valid questions** — answer changes what intelligence searches for.
**Invalid questions** — subtitles, dubbing, derivatives, budget, runtime, reference roles.
  These belong in proposal.

Templates (adapt to context):
```
product missing:
  "What are you advertising? A product name or one-sentence description is enough."
platform missing:
  "Where will this run — TikTok, YouTube, LinkedIn, TV, or somewhere else?"
demographic missing:
  "Who should feel something when they watch this? A short description works."
emotional_intent missing:
  "What should viewers feel at the end — confident, curious, urgent to act, something else?"
```

Combined example (product + platform + demographic all missing):
```
A few quick questions before we start research:

1. What are you advertising? A product name or one-sentence description is enough.
2. Where will this run — TikTok, YouTube, LinkedIn, TV, or somewhere else?
3. Who should feel something when they watch this? A short description works.
```

Parse the reply and populate fields. Proceed to Step 5.

### Step 5: Assemble intake_brief

Write validated artifact to `projects/<project-name>/artifacts/intake_brief.json`.
Validate against `schemas/artifacts/intake_brief.schema.json` before submitting.

### Step 6: Self-Evaluate Before Submitting

- `round1_questions_asked.length ≤ 3` — never exceed
- Questions only for research-direction fields — no logistics
- `intake_completeness` is honest — "rich" only if zero minimum fields missing

## Common Pitfalls

- **Asking logistics questions**: Subtitles, derivatives, budget, runtime → proposal.
- **Over-asking**: product + platform + demographic present = skip questions, even if
  emotional_intent is absent. Intelligence can infer it.
- **Marking thin as rich**: "make me an ad for my app" → `intake_completeness = "thin"`.
```

- [ ] **Step 2: Verify required sections**

```bash
grep -c "## When to Use\|## Process\|## Prerequisites\|## Common Pitfalls\|Step 1\|Step 2\|Step 3\|Step 4\|Step 5\|Step 6" \
  skills/pipelines/ad-video/intake-director.md
```

Expected: ≥ 10

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/intake-director.md
git commit -m "feat(ad-video): add intake-director skill"
```

---

### Task 7: intelligence-director.md

**Files:**
- Create: `skills/pipelines/ad-video/intelligence-director.md`

- [ ] **Step 1: Write the skill**

```markdown
# Intelligence Director — Ad Video Pipeline

## When to Use

You are the **Intelligence Director**. You receive `intake_brief` and produce
`intelligence_brief` — the raw research layer that bible-director synthesizes into the
production bible. You do NOT make creative decisions. You gather, verify, and rate
market intelligence.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/intelligence_brief.schema.json` | Artifact validation |
| Input | `intake_brief` | Research scope |
| Tools | Web search | All research (zero cost) |

## Confidence Tiers

Every recommendation field MUST carry a confidence tier. Be honest.

| Tier | When to use |
|------|-------------|
| `research-grounded` | Search results directly state this value for this product/platform/demographic |
| `pattern-inferred` | Multiple indirect signals point to this; no source states it directly |
| `default-heuristic` | Platform-general norm; no category-specific data found |

A `default-heuristic` checkpoint that only flags is better than fabricated
`research-grounded` data that hard-blocks production.

## Search Query Note

Query templates below represent **search intent**, not literal API parameters. Adapt to
your available search tool's syntax. If `site:` or boolean `OR` are unsupported,
reformulate to target the same information. Retry reformulated queries if results are
low quality. The batch is complete when the Goal criteria are met — not when all listed
templates have been executed.

## Process

### Step 1: Batch 1 — Audience Psychographics

**Goal:** Infer `emotional_profile`, `core_pain_point`, `aspiration` from research.
Record specific, citable findings. Vague generalizations do not count.

```
"{demographic} {product_category} problems OR frustrations"
"{demographic} {product_category} goals OR aspirations"
"{platform} {demographic} content behavior {year}"
site:reddit.com "{product_category}" (frustration|help|wish|tired of)
site:reddit.com "{product_category}" (finally|love|changed my life|best decision)
```

### Step 2: Batch 2 — Platform Trend Signals

**Goal:** Identify 3-5 format or creative trends measurably performing on this platform now.

```
"{platform} ad trends {year}"
"{product_category} ad format performing {platform} {year}"
"viral {product_category} ad {year}"
"{platform} creative best practices {year}"
```

For each trend: record signal, source URL, hypothesis for how it applies.

### Step 3: Batch 3 — Hit Ad Analysis

**Goal:** Extract narrative patterns from high-performing ads in this category (3-5 ads).

**Capability note:** Web search returns summaries, not video analysis. Pacing data
(`cuts_per_minute`, `avg_shot_duration_seconds`) is rarely stated — most editing_rhythm
entries will be `pattern-inferred` or `default-heuristic`. This is correct.

```
"best {product_category} ads {year}" site:youtube.com
"{product_category} award-winning commercial {year}"
"{product_category} ad viral {year}"
```

For each ad found, extract: `arc_type`, `hook_mechanic`, `what_works`,
`pacing_hints` (if any).

### Step 4: Batch 4 — Rejected Approaches

**Goal:** Identify oversaturated or declining approaches. An empty `rejected_approaches`
list is a red flag — every category has clichés. Search harder before concluding none exist.

```
"{product_category} ad cliché {year}"
"why {product_category} ads fail"
"overused {product_category} advertising tropes"
```

Record 2-3 specific approaches with reasons.

### Step 5: Synthesize Recommendations

After all batches, synthesize with confidence tiers:

```json
{
  "arc_type": { "value": "problem-solution", "confidence": "research-grounded", "rationale": "..." },
  "pacing_model": { "value": "escalating", "confidence": "pattern-inferred", "rationale": "..." },
  "hook_mechanic": { "value": "statement", "confidence": "research-grounded", "rationale": "..." },
  "hook_window_seconds": { "value": 3, "confidence": "research-grounded", "rationale": "TikTok 3s scroll threshold" },
  "editing_rhythm_by_beat": {
    "hook": { "value": { "cuts_density": "rapid", "avg_shot_duration_seconds": 1.5, "transition_style": "hard_cut" }, "confidence": "pattern-inferred" }
  },
  "overall_rationale": "One paragraph connecting all findings."
}
```

### Step 6: Assemble and Submit

Build `intelligence_brief` per schema. Validate against
`schemas/artifacts/intelligence_brief.schema.json`. Write to
`projects/<project-name>/artifacts/intelligence_brief.json`.

## Quality Bar

| Criterion | Minimum |
|-----------|---------|
| Psychographics sourced from research | All 3 fields from real findings |
| Platform trends | ≥ 3 |
| Hit ads analyzed | ≥ 3 |
| Rejected approaches | ≥ 2 (non-empty required) |
| All recommendations carry confidence tier | 100% |

## Common Pitfalls

- **Inventing psychographics**: If data is missing, mark as `default-heuristic`. Never fabricate.
- **Skipping rejected approaches**: Try `"predictable {category} ad"` or `"boring {category} commercial"`.
- **Claiming research-grounded for inferred pacing**: Unless an article states cut rate explicitly,
  mark editing_rhythm as `pattern-inferred` or `default-heuristic`.
```

- [ ] **Step 2: Verify required sections**

```bash
grep -c "## When to Use\|## Process\|## Quality Bar\|Step 1\|Step 2\|Step 3\|Step 4\|Step 5\|Step 6" \
  skills/pipelines/ad-video/intelligence-director.md
```

Expected: ≥ 9

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/intelligence-director.md
git commit -m "feat(ad-video): add intelligence-director skill"
```

---

### Task 8: bible-director.md

**Files:**
- Create: `skills/pipelines/ad-video/bible-director.md`

- [ ] **Step 1: Write the skill**

```markdown
# Bible Director — Ad Video Pipeline

## When to Use

You are the **Bible Director**. You receive `intake_brief` + `intelligence_brief` and
synthesize them into a `production_bible` — the machine-readable contract governing all
downstream stages. You conduct two-step user review (Round 2a: narrative, Round 2b:
execution) before the pipeline advances.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/production_bible.schema.json` | Output validation |
| Input | `intake_brief` + `intelligence_brief` | Source data |

## Arc Type Beat Ratios

```
// ── Configuration Note ──────────────────────────────────────────────────
// Beat ratio tables are inline in v1 (single pipeline consumer).
// When a second pipeline adopts the bible pattern, extract to
// config/arc_beat_ratios.yaml. Do not build abstraction for a single consumer.
// ────────────────────────────────────────────────────────────────────────

Arc type beat ratios (normalized to 1.0 — multiply by duration_target_seconds):

problem-solution:    hook=0.13, problem=0.25, solution_intro=0.17, proof=0.25, resolution=0.12, cta=0.08
desire-fulfillment:  hook=0.08, desire_paint=0.25, gap=0.17, fulfillment=0.30, brand=0.12, cta=0.08
contrast:            hook=0.12, before=0.22, contrast_moment=0.08, after=0.28, evidence=0.22, cta=0.08
journey:             hook=0.10, challenge=0.20, struggle=0.20, turning_point=0.15, triumph=0.25, cta=0.10
social-proof:        hook=0.10, social_scene=0.25, testimonial=0.30, product_reveal=0.20, brand=0.08, cta=0.07
demo-reveal:         hook=0.13, setup=0.17, demo=0.37, payoff=0.20, cta=0.13

Intensity curves (values distributed across beats in sequence order):
escalating:  0.3 → 0.5 → 0.7 → 0.9 → 0.7 → 0.5
wave:        0.5 → 0.8 → 0.4 → 0.9 → 0.6 → 0.5
punchy:      0.8 → 0.6 → 0.8 → 0.7 → 0.5 → 0.8
slow-burn:   0.2 → 0.4 → 0.6 → 0.8 → 0.9 → 0.7
```

## Synthesis Steps (internal — no user interaction until Step 7)

### Step 1 — Assemble identity

Merge `intake_brief` fields with `intelligence_brief.audience_psychographics`.
- `key_message` null → derive from core_pain_point + aspiration synthesis
- `cta` null → flag as "pending — must be collected at Round 2b"
- `brand_name` null → infer from product; flag for proposal confirmation

### Step 2 — Design emotional beat sequence

1. Look up `recommendations.arc_type.value` and `recommendations.pacing_model.value`
2. Multiply beat ratios by `identity.duration_target_seconds`
3. Distribute intensity values across beats in sequence order
4. Set `tension_peak_at_seconds` = cumulative time at highest-intensity beat
5. Populate `script_constraint` and `visual_constraint` per beat from arc semantics

### Step 3 — Build visual contract

- `visual_motifs`: from `hit_ads_analyzed`. `mandatory=true` only for motifs in ≥3 ads
  AND not in `rejected_approaches`
- `editing_rhythm`: map from `recommendations.editing_rhythm_by_beat`; carry `confidence` tier
- `key_visual_moments`: one mandatory moment per beat with a concrete visual requirement
- `style_mode` + `render_runtime`: from `intake_brief.style_mode_candidate` (confirmed at proposal)

### Step 4 — Build audio contract

- `voice_character.tone`: from identity.tone + emotional_profile
- `music_direction.arc`: derived from intensity curve
- `music_direction.tempo` + `genre_direction`: from platform_trends + pacing_model

### Step 5 — Build deliverables

Primary aspect ratio from platform:
- tiktok / instagram → `"9:16"`
- youtube / linkedin / tv / generic → `"16:9"`

Set `deliverables.primary`. Leave `deliverables.derivatives = []` — proposal fills this.

### Step 6 — Build brand constraints

- `brand_name_in_final_frame`: always `true`
- `mandatory_elements`, `prohibited_elements`, `tone_guardrails`: from intake_brief

### Step 7 — Generate compliance manifest

Evaluation method assignment:
```
check_type == "timing"     → evaluation_method = "structural"
check_type == "presence"   → evaluation_method = "structural"
check_type == "structural" → evaluation_method = "structural"
check_type == "content"    → evaluation_method = "semantic"
```

failure_action:
```
source_confidence == "default-heuristic"        → failure_action = "flag"
source_confidence IN [research-grounded, pattern-inferred] → failure_action = "revise"
```

For editing_rhythm checkpoints: `source_confidence = rhythm.confidence` (propagated directly).
`failure_action = rhythm.confidence == "default-heuristic" ? "flag" : "revise"`

Generate at minimum:
- CP-S{n} (timing, structural) + CP-S{n}a (content, semantic) per beat
- CP-V{n} (presence, structural) per mandatory visual_motif
- CP-V{n} (structural, structural) per mandatory key_visual_moment
- CP-E{n} (timing, structural) per editing_rhythm entry
- CP-B1 (presence, structural) — brand name in final scene
- CP-B3 (presence, structural) — prohibited elements

## Round 2 — Two-Step User Review

### Step 7a — Strategic Confirmation (must approve before 7b)

Present: identity + narrative arc + rejected approaches ONLY.

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
    [B1] [name] (0–Xs):  [emotional_target] — [script_constraint]
    [B2] [name] (X–Ys):  [emotional_target] — [script_constraint]
    ...
  Narrative peak at [tension_peak_at_seconds]s.

APPROACHES WE'RE AVOIDING
  • [rejected_approach] — [reason]

Does this story direction feel right?
```

**If user requests changes at 7a:**
Re-execute Steps 1–7 (full re-derivation — no patching). Re-present 7a.
Do not advance to 7b until `approval.strategic_approved = true`.

**Round 2a Regression — when to re-run intelligence:**
- `product`, `platform`, or `demographic` changed materially → re-run intelligence-director
  with updated intake_brief before re-running bible-director.
- arc_type / pacing / hook / key_message / tone changed → re-run bible-director only.

### Step 7b — Execution Confirmation (can be fast-tracked)

Present: visual direction, audio direction, deliverables primary, compliance checkpoints
in plain English. Flag ⚠ on `default-heuristic` checkpoints.

**CTA collection** (insert between AUDIO and WHAT WILL BE DELIVERED):
```
CALL TO ACTION
  [If cta set:] CTA: "[cta text]" — exact text in final frame. Correct?
  [If cta null:] We need the exact call-to-action text for the final frame.
    Examples: "Try free for 30 days" / "Visit acme.com" / "Download the app"
    What should the CTA say?
```

CTA MUST be non-null before `approval.execution_approved = true`.

**If user requests execution-level changes** (visual, motifs, rhythm, audio, deliverables):
Re-execute Steps 3–7. Preserve narrative. Reset `approval.execution_approved = false` only.

**If user requests narrative-level changes at 7b** (arc_type, beats, hook_mechanic,
key_message, emotional_target, pacing_model):
Reset `approval.strategic_approved = false`. Re-execute Steps 1–7. Re-present 7a.
Tell user: "That change affects the story direction we agreed on — rebuilding and
re-confirming the narrative first."

**Mixed changes** (narrative + execution in one message): treat as narrative-level.

### Step 8: Submit

Write to `projects/<project-name>/artifacts/production_bible.json`.
Set both `approval.strategic_approved` and `approval.execution_approved` to `true`
only after both rounds complete. EP gate G-I checks both flags.

## Common Pitfalls

- **Patching after 7a changes**: Always re-derive from Step 1. Patching one section
  leaves audio, visual, and compliance out of sync.
- **Leaving cta null after 7b**: CTA null at bible completion blocks script-director.
- **Fabricating compliance**: Generate compliance_manifest mechanically from beat sequence
  and visual motifs, not from memory.
```

- [ ] **Step 2: Verify required sections**

```bash
grep -c "## When to Use\|Step 1\|Step 2\|Step 3\|Step 4\|Step 5\|Step 6\|Step 7\|Step 8\|Round 2\|7a\|7b" \
  skills/pipelines/ad-video/bible-director.md
```

Expected: ≥ 12

- [ ] **Step 3: Commit**

```bash
git add skills/pipelines/ad-video/bible-director.md
git commit -m "feat(ad-video): add bible-director skill"
```

---

## Phase 4: Re-scope Existing Directors

### Task 9: idea-director re-scope

**Files:**
- Modify: `skills/pipelines/ad-video/idea-director.md`

- [ ] **Step 1: Read the current file**

```bash
head -30 skills/pipelines/ad-video/idea-director.md
```

- [ ] **Step 2: Replace the full file content**

The current idea-director parses brand context and generates angle options. With the bible
in place, it now generates creative execution concepts within bible constraints. Replace
the entire file with:

```markdown
# Idea Director — Ad Video Pipeline (post-bible)

## When to Use

You are the **Idea Director**. You receive `intake_brief`, `intelligence_brief`, and
`production_bible` (fully approved — both `strategic_approved` and `execution_approved`
must be true). You generate 2-3 creative execution concepts *within* the bible's
constraints.

You do NOT decide arc_type, beats, pacing, emotional targets, or visual motifs.
The bible owns all of that. You decide *how to execute* the approved story for this
specific brand: scenarios, characters, settings, visual metaphors.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Input | `production_bible` (fully approved) | Creative constraints |
| Input | `intake_brief` | Brand context |
| Input | `intelligence_brief` | Research context |

Verify `production_bible.approval.strategic_approved == true` AND
`production_bible.approval.execution_approved == true` before proceeding. If either is
false, surface a blocker to EP: "Bible not approved — cannot generate execution concepts."

## What You Own vs. What Bible Owns

| Decision | Owner |
|----------|-------|
| Arc type, beats, pacing, emotional targets | bible-director |
| Visual motifs (mandatory), editing rhythm | bible-director |
| Which creative execution of that story | **YOU** |
| Characters, scenarios, visual metaphors | **YOU** |

## Process

### Step 1: Read the Bible Constraints

Internalize from `production_bible`:
- `narrative.emotional_beat_sequence` — satisfy every beat
- `narrative.hook_mechanic` — fixed; must be used
- `visual.visual_motifs` where `mandatory=true` — must appear
- `visual.key_visual_moments` where `mandatory=true` — must be included
- `brand_constraints.mandatory_elements` + `prohibited_elements`
- `identity.cta` — exact text; in final beat
- `intelligence.rejected_approaches` — do not use

### Step 2: Generate 2-3 Execution Concepts

Each concept is a distinct creative treatment of the same approved arc. Options differ in:
- **Scenario** — what world and situation do we show?
- **Characters** — who do we follow?
- **Visual metaphor** — what central image carries emotional weight?
- **Hook execution** — HOW does the `hook_mechanic` land in this specific treatment?

Options MUST NOT differ in arc_type, beat structure, emotional targets, or hook_mechanic.

Format per concept:
```
Concept [ID]: [Name]

Scenario: [2-3 sentences describing world and characters]
Hook execution: [How hook_mechanic lands — first 3 seconds described]
Visual metaphor: [Central image that carries the story through all beats]
Beat mapping:
  [B1] hook:   [What specifically happens in this scenario]
  [B2] ...:    [What specifically happens]
  ...
Why this works: [One sentence connecting to intelligence findings]
```

### Step 3: Present and Wait for Selection

Present all concepts. Recommend one with rationale. Wait for user to select.
Record `selected_concept_id`.

### Step 4: Submit

Write `idea_options` artifact to `projects/<project-name>/artifacts/idea_options.json`:
```json
{
  "concepts": [
    { "id": "C1", "name": "...", "scenario": "...", "selected": false },
    { "id": "C2", "name": "...", "scenario": "...", "selected": true }
  ],
  "selected_concept_id": "C2"
}
```

## Common Pitfalls

- **Changing the arc**: bible locked arc_type. Every concept uses the same arc.
- **Ignoring mandatory motifs**: All mandatory `visual_motifs` must appear in each concept.
- **Using rejected approaches**: Check `intelligence.rejected_approaches` before writing.
```

- [ ] **Step 3: Verify no old language remains**

```bash
grep -c "Parse Brand Context\|angle_options\|style_mode_candidate\|Infer Style Mode" \
  skills/pipelines/ad-video/idea-director.md
```

Expected: 0

- [ ] **Step 4: Commit**

```bash
git add skills/pipelines/ad-video/idea-director.md
git commit -m "refactor(ad-video): re-scope idea-director to creative execution within bible constraints"
```

---

### Task 10: proposal-director re-scope

**Files:**
- Modify: `skills/pipelines/ad-video/proposal-director.md`

- [ ] **Step 1: Back up the current file**

```bash
cp skills/pipelines/ad-video/proposal-director.md skills/pipelines/ad-video/proposal-director.md.bak
```

- [ ] **Step 2: Replace the full file content**

The current proposal-director handles both creative direction and logistics. With the bible
in place, it only handles technical production parameters. Replace the entire file with:

```markdown
# Proposal Director — Ad Video Pipeline (post-bible)

> **Post-bible re-scope (v2):** Creative direction, visual direction, audio direction, and
> primary deliverable format are owned by bible-director. This director handles technical
> production parameters only. Do NOT re-decide creative direction here.

## When to Use

You are the **Proposal Director**. You receive `selected_idea` + `production_bible`
(fully approved). Creative direction is locked. Your job is to confirm technical
production parameters that require user choice before assets are generated.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Input | `production_bible` (fully approved) | Contract reference |
| Input | `selected_idea` (from idea_options) | Selected creative execution |

Verify `production_bible.approval.strategic_approved == true` AND
`production_bible.approval.execution_approved == true`. If either is false, surface
blocker to EP.

## Responsibilities

1. **Derivative variants** — present opt-in options (9:16, 1:1, 15s short) relative to
   bible's declared primary. Populate `deliverables.derivatives` in production_bible.
2. **Subtitle configuration** — burnt-in / SRT-only / none + language.
3. **Dubbing preferences** — additional language tracks.
4. **Style_mode confirmation** — bible sets `style_mode_candidate`; get user sign-off.
   Lock `visual.style_mode` in production_bible.
5. **Runtime selection** — Remotion vs. HyperFrames (HARD RULE from AGENT_GUIDE: present
   both when both are available; never silently default). Lock `visual.render_runtime`.
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

Load `selected_idea` and `production_bible`. Verify approval flags.
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
  Two options available:
  • Remotion — [brief pro/con for this concept]
  • HyperFrames — [brief pro/con for this concept]
  Which do you prefer?

ESTIMATED COST
  [Itemized by stage]
  Total: [estimate]
```

### Step 3: Process User Choices

Parse response. Populate:
- `production_bible.deliverables.derivatives[]` with user-selected variants
- Lock `production_bible.visual.style_mode`
- Lock `production_bible.visual.render_runtime`

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
  "budget_confirmed": true
}
```

## Common Pitfalls

- **Re-deciding creative direction**: Arc, beats, motifs, audio — all locked. Do not re-open.
- **Silently defaulting runtime**: AGENT_GUIDE hard rule — always present both options.
- **Skipping CTA verification**: If `identity.cta` is null here, something went wrong upstream.
```

- [ ] **Step 3: Verify no old language remains**

```bash
grep -c "concept_options\|narrative_structure\|arc_type\|3 genuinely different\|Parse Brand\|angle_options" \
  skills/pipelines/ad-video/proposal-director.md
```

Expected: 0

- [ ] **Step 4: Delete backup if verification passes**

```bash
rm skills/pipelines/ad-video/proposal-director.md.bak
```

- [ ] **Step 5: Commit**

```bash
git add skills/pipelines/ad-video/proposal-director.md
git commit -m "refactor(ad-video): re-scope proposal-director to technical parameters only"
```

---

## Phase 5: Compliance Self-Check Additions

### Task 11: compliance step in script-director, scene-director, edit-director

**Files:**
- Modify: `skills/pipelines/ad-video/script-director.md`
- Modify: `skills/pipelines/ad-video/scene-director.md`
- Modify: `skills/pipelines/ad-video/edit-director.md`

- [ ] **Step 1: Survey the structure of all three director files**

```bash
for f in script-director scene-director edit-director; do
  echo "=== $f ==="
  grep -n "^##\|^###" skills/pipelines/ad-video/${f}.md
done
```

Note the heading structure of each file. Identify the LAST `### Step` heading in each —
this is the Submit/Write step. The compliance self-check must be inserted as a new `### Step`
immediately BEFORE this final step.

- [ ] **Step 2: Insert compliance self-check in script-director.md**

Open `skills/pipelines/ad-video/script-director.md`. Find the LAST `### Step` heading
(the one that writes the artifact / submits to EP). Insert the following block as a new
step immediately BEFORE that heading. Use the next available step number.

Filter: `applies_to_stage == "script"`

````markdown
### Step [N]: Compliance Self-Check (run before submitting)

Load `production_bible.compliance_manifest.checkpoints`.
Filter to `applies_to_stage == "script"`.
Split into `structural_checks[]` (`evaluation_method="structural"`) and
`semantic_checks[]` (`evaluation_method="semantic"`).

**Structural checks** — call the `compliance_check` tool for each:
```
compliance_check({
    "stage_output": <the script artifact dict you are about to submit>,
    "checkpoint": <the checkpoint object>
})
→ returns { pass, actual_value, deviation, failure_action }
```
Do NOT attempt to evaluate structural checks yourself — they require deterministic code
execution. The tool handles word count, string matching, and arithmetic.

**Semantic checks** — LLM self-assessment:
Evaluate your own output against each semantic checkpoint's `criterion`.
Be conservative: if UNCERTAIN whether the criterion is met → treat as FAIL.

**Decision logic:**
- Any FAIL where `failure_action == "revise"` → do NOT submit.
  Attempt to fix the issue. Re-run the failed check. If still failing after one
  revision attempt, submit with:
  `compliance_failures: [{ checkpoint_id, evaluation_method, criterion, actual_value, deviation }]`
- Any check where `failure_action == "flag"` → submit with:
  `compliance_warnings: [{ checkpoint_id, criterion, deviation }]`
- All PASS → submit normally (omit compliance_failures and compliance_warnings keys).

**Note:** The EP gate will independently re-evaluate all semantic checkpoints you
self-assessed as PASS. It will NOT see your self-assessment. If the EP disagrees,
you'll receive a send-back with the EP's evaluation rationale.
````

- [ ] **Step 3: Insert compliance self-check in scene-director.md**

Same pattern as Step 2. Differences:
- Filter: `applies_to_stage == "scene_plan"`
- Stage output reference: the scene_plan artifact dict
- Relevant checkpoints: CP-V* (motif presence, beat mapping) and CP-B1 (brand name in final scene)

- [ ] **Step 4: Insert compliance self-check in edit-director.md**

Same pattern as Step 2. Differences:
- Filter: `applies_to_stage == "edit"`
- Stage output reference: the edit_decisions artifact dict
- Relevant checkpoints: CP-E* (editing rhythm timing) and applicable CP-B* checkpoints

- [ ] **Step 5: Verify all three files have the compliance step**

```bash
for f in script-director scene-director edit-director; do
  count=$(grep -c "compliance_check\|compliance_failures\|Compliance Self-Check" \
    skills/pipelines/ad-video/${f}.md)
  echo "$f: $count occurrences (expected ≥3)"
done
```

Expected: all three show ≥ 3.

- [ ] **Step 6: Commit**

```bash
git add skills/pipelines/ad-video/script-director.md \
        skills/pipelines/ad-video/scene-director.md \
        skills/pipelines/ad-video/edit-director.md
git commit -m "feat(ad-video): add compliance self-check step to script, scene, edit directors"
```

---

## Phase 6: EP Gate Updates

### Task 12: executive-producer.md gate updates

**Files:**
- Modify: `skills/pipelines/ad-video/executive-producer.md`

- [ ] **Step 1: Read current EP_STATE definition and gate list**

```bash
grep -n "EP_STATE\|Gate G\|Quality Gates" skills/pipelines/ad-video/executive-producer.md | head -20
```

Note the structure of existing gate definitions.

- [ ] **Step 2: Add intake, intelligence, bible to EP_STATE artifacts**

Find the `artifacts:` block in EP_STATE. Add before `idea:`:

```yaml
    intake: null       # → intake_brief
    intelligence: null # → intelligence_brief
    bible: null        # → production_bible (includes approval flags)
```

- [ ] **Step 3: Add Gate G-I (after bible stage)**

Find the Quality Gates Summary table or the gate definitions list. Insert G-I before any
existing gate:

````markdown
### Gate G-I (after bible)

```
CHECK: Bible approval — HARD STOP if any condition fails
  IF production_bible.approval.strategic_approved == false:
    STOP. Present Round 2a to user. Wait.
  IF production_bible.approval.execution_approved == false:
    STOP. Present Round 2b to user. Wait.
  IF production_bible.identity.cta is null:
    STOP. "CTA missing — bible-director must collect CTA at Round 2b before advancing."
    (This catches a bible-director bug — cta should never be null when execution_approved=true.)
  ONLY THEN: advance to idea-director.
```
````

- [ ] **Step 4: Replace Gate G3 body (after script)**

Find the existing G3 gate. Replace its ADD block with the 3-step version:

````markdown
### Updated Gate G3 (after script)

```
EXISTING checks: word count vs duration, narrative arc, research integration
ADD:
  # Step 1: Director-reported structural failures
  IF script.compliance_failures[] non-empty WITH evaluation_method="structural":
    Send back to script-director: checkpoint_id, criterion, actual_value, deviation.
    (Do not run Step 2 until structural failures are fixed.)

  # Step 2: EP independent re-evaluation of semantic checkpoints
  FOR EACH semantic checkpoint where director self-assessed PASS:
    Run independent LLM evaluation: (script_artifact, checkpoint.criterion).
    Do NOT include director's self-assessment in this prompt.
    IF independent result is FAIL:
      Append to compliance_failures[] with source="ep_independent_eval".
      Send back: checkpoint_id, criterion, ep_evaluation_rationale.

  # Step 3: Warnings
  IF script.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.

  # Structural check results are NOT re-evaluated — code result is final.
```
````

- [ ] **Step 5: Replace Gate G4 body (after scene_plan)**

````markdown
### Updated Gate G4 (after scene_plan)

```
EXISTING checks: coverage, variety, asset feasibility
ADD:
  # Step 1: Director-reported structural failures (CP-V* checkpoints)
  IF scene_plan.compliance_failures[] non-empty WITH evaluation_method="structural":
    Send back to scene_plan-director: checkpoint_id, criterion, actual_value, deviation.

  # Step 2: Semantic re-evaluation
  FOR EACH semantic checkpoint where director self-assessed PASS:
    Independent LLM evaluation (scene_plan_artifact, criterion). No self-assessment in prompt.
    FAIL → compliance_failures[] source="ep_independent_eval" → send back.

  # Step 3: Warnings
  IF scene_plan.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.
```
````

- [ ] **Step 6: Replace Gate G6 body (after edit)**

````markdown
### Updated Gate G6 (after edit)

```
EXISTING checks: timeline completeness, A/V pre-sync
ADD:
  # Step 1: Director-reported structural failures (CP-E*, CP-B* checkpoints)
  IF edit.compliance_failures[] non-empty WITH evaluation_method="structural":
    Send back to edit-director: checkpoint_id, criterion, actual_value, deviation.

  # Step 2: Semantic re-evaluation
  FOR EACH semantic checkpoint where director self-assessed PASS:
    Independent LLM evaluation (edit_artifact, criterion). No self-assessment in prompt.
    FAIL → compliance_failures[] source="ep_independent_eval" → send back.

  # Step 3: Warnings
  IF edit.compliance_warnings[] non-empty:
    Log in EP_STATE.issues_log. Proceed.

  # Structural results NOT re-evaluated.
```
````

- [ ] **Step 7: Verify all four gates present**

```bash
grep -c "Gate G-I\|Gate G3\|Gate G4\|Gate G6\|ep_independent_eval" \
  skills/pipelines/ad-video/executive-producer.md
```

Expected: ≥ 5

- [ ] **Step 8: Commit**

```bash
git add skills/pipelines/ad-video/executive-producer.md
git commit -m "feat(ad-video): add G-I gate; expand G3/G4/G6 with compliance + EP semantic re-evaluation"
```

---

## Phase 7: Pipeline Manifest

### Task 13: ad-video.yaml updates

**Files:**
- Modify: `pipeline_defs/ad-video.yaml`

- [ ] **Step 1: Check current stage order**

```bash
grep -n "^- name:" pipeline_defs/ad-video.yaml
```

- [ ] **Step 2: Insert three new stages before `idea`**

Find `- name: idea`. Insert these three blocks immediately before it:

```yaml
- name: intake
  skill: pipelines/ad-video/intake-director
  produces:
    - intake_brief
  checkpoint_required: false
  human_approval_default: false
  review_focus:
    - intake_completeness is honest (not "rich" when prompt was actually thin)
    - round1_questions_asked contains only research-direction questions
    - round1_questions_asked.length <= 3
  success_criteria:
    - Schema-valid intake_brief produced

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
  success_criteria:
    - Schema-valid intelligence_brief with recommendations

- name: bible
  skill: pipelines/ad-video/bible-director
  required_artifacts_in:
    - intake_brief
    - intelligence_brief
  produces:
    - production_bible
  checkpoint_required: true
  human_approval_default: true
  review_focus:
    - strategic_approved == true before advancing
    - execution_approved == true before advancing
    - compliance_manifest checkpoints are derived not hardcoded
    - default-heuristic checkpoints use failure_action=flag only
    - deliverables.primary aspect_ratio matches platform default
    - rejected_approaches present in intelligence section
    - cta is non-null (must be set before execution_approved=true)
  success_criteria:
    - Schema-valid production_bible with both approval flags true
```

- [ ] **Step 3: Update `idea` stage `required_artifacts_in` and `produces`**

Find `- name: idea`. Update:

```yaml
- name: idea
  skill: pipelines/ad-video/idea-director
  required_artifacts_in:
    - intake_brief
    - intelligence_brief
    - production_bible
  produces:
    - idea_options
  checkpoint_required: true
  human_approval_default: true
  review_focus:
    - All concepts satisfy every beat in production_bible.narrative.emotional_beat_sequence
    - All mandatory visual_motifs appear in each concept's beat mapping
    - No rejected_approaches used
  success_criteria:
    - idea_options artifact with selected_concept_id set
```

- [ ] **Step 4: Update `proposal` stage `required_artifacts_in` and `produces`**

```yaml
- name: proposal
  skill: pipelines/ad-video/proposal-director
  required_artifacts_in:
    - selected_idea
    - production_bible
  produces:
    - production_proposal
```

Keep all other proposal fields unchanged (checkpoint_required, review_focus, etc.).

- [ ] **Step 5: Add new skills to `required_skills`**

In the `required_skills:` list, add:

```yaml
- skills/pipelines/ad-video/intake-director.md
- skills/pipelines/ad-video/intelligence-director.md
- skills/pipelines/ad-video/bible-director.md
```

- [ ] **Step 6: Validate YAML**

```bash
python -c "import yaml; yaml.safe_load(open('pipeline_defs/ad-video.yaml'))" && echo "YAML valid"
```

Expected: `YAML valid`

- [ ] **Step 7: Verify stage order**

```bash
grep "^- name:" pipeline_defs/ad-video.yaml
```

Expected order: `intake → intelligence → bible → idea → proposal → script → scene_plan → assets → edit → compose → publish`

- [ ] **Step 8: Commit**

```bash
git add pipeline_defs/ad-video.yaml
git commit -m "feat(ad-video): add intake/intelligence/bible stages; re-scope idea/proposal"
```

---

## Phase 8: Integration Verification

### Task 14: registry and smoke tests

- [ ] **Step 1: Verify compliance_check in registry**

```bash
python -c "
from tools.tool_registry import registry
registry.discover()
tool = registry.get('compliance_check')
print('Found:', tool.name if tool else 'NOT FOUND')
print('Status:', tool.get_status() if tool else 'N/A')
"
```

Expected:
```
Found: compliance_check
Status: ToolStatus.AVAILABLE
```

If not found: verify `tools/compliance/__init__.py` exists and is empty.

- [ ] **Step 2: Verify all three new stages in manifest**

```bash
python -c "
import yaml
with open('pipeline_defs/ad-video.yaml') as f:
    p = yaml.safe_load(f)
names = [s['name'] for s in p.get('stages', [])]
for n in ['intake', 'intelligence', 'bible', 'idea', 'proposal']:
    print(('✓' if n in names else '✗ MISSING'), n)
"
```

Expected: all 5 show ✓.

- [ ] **Step 3: Validate all three schemas**

```bash
python -c "
import json, jsonschema
for name in ['intake_brief', 'intelligence_brief', 'production_bible']:
    with open(f'schemas/artifacts/{name}.schema.json') as f:
        schema = json.load(f)
    jsonschema.Draft202012Validator.check_schema(schema)
    print(f'✓ {name}.schema.json valid')
"
```

Expected: 3 lines, all ✓.

- [ ] **Step 4: Run all new tests**

```bash
python -m pytest tests/qa/test_schemas_preproduction.py tests/qa/test_compliance_check.py -v
```

Expected: All tests pass. No failures.

- [ ] **Step 5: Final commit**

```bash
git add .
git status  # verify only expected files remain
git commit -m "test(ad-video): integration smoke test — pre-production schemas and compliance tool verified"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Covered by task |
|-------------|----------------|
| §4 Bible schema | Tasks 3, 4 |
| §5 Intake director | Task 6 |
| §6 Intelligence director | Task 7 |
| §7 Bible director + Round 2 (incl. regression rules) | Task 8 |
| §8 idea-director re-scope | Task 9 |
| §8 proposal-director re-scope | Task 10 |
| §9 Compliance self-check + execution env (Option A) | Tasks 5, 11 |
| §9 EP independent semantic re-evaluation | Task 12 |
| §10 Gate G-I | Task 12 |
| §10 Gates G3/G4/G6 | Task 12 |
| §11 Pipeline manifest | Task 13 |
| §12 New artifact schemas | Tasks 1–4 |
| §13 Unchanged components | Confirmed: assets/compose/publish/tools/playbooks not touched |

**Type consistency:**
- `ComplianceCheck.execute(inputs: dict) → ToolResult` matches BaseTool contract (base_tool.py:301)
- `compliance_check` tool name matches snake_case convention (e.g. `audio_mixer`, `video_compose`)
- `compliance_failures[]` entry shape `{ checkpoint_id, evaluation_method, criterion, actual_value, deviation }` is consistent across §9, §10, Task 12 gate definitions
- `intake_brief`, `intelligence_brief`, `production_bible` field names match schema IDs and director skill references throughout
