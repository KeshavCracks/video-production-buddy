#!/usr/bin/env python3
"""Tests: ad-video pipeline manifest structural validation.

Verifies:
  - YAML parses without error
  - Manifest validates against pipeline_manifest.schema.json
  - All 12 stages present in correct order (includes brief_enrichment)
  - Artifact dependency graph: every required_artifact is produced by a prior stage
  - Key stage fields (checkpoint_required, human_approval_default, optional_tools)
  - Pre-production stages have correct required fields
  - compliance_check declared as optional_tool for script/scene_plan/edit
  - No stale artifact names (proposal_packet, brief, selected_idea)

Run: python3 tests/qa/test_pipeline_manifest.py
"""

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import yaml

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = ROOT / "pipeline_defs" / "ad-video.yaml"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "pipelines" / "pipeline_manifest.schema.json"

EXPECTED_STAGE_ORDER = [
    "intake", "brief_enrichment", "intelligence", "bible", "idea", "proposal",
    "script", "scene_plan", "assets", "edit", "compose", "publish",
]


def load_manifest() -> dict:
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def stage(m: dict, name: str) -> dict:
    return next(s for s in m["stages"] if s["name"] == name)


# ─────────────────────────────────────────────────────────────────────────────
# Basic parsing and schema validation
# ─────────────────────────────────────────────────────────────────────────────

def test_manifest_parses_without_error():
    """ad-video.yaml must load as valid YAML."""
    m = load_manifest()
    assert isinstance(m, dict) and "stages" in m


def test_manifest_has_required_top_level_fields():
    m = load_manifest()
    for field in ("name", "version", "stages"):
        assert field in m, f"Missing required field: {field}"
    assert isinstance(m["stages"], list)


def test_manifest_validates_against_json_schema():
    """Manifest validates against pipeline_manifest.schema.json."""
    if not HAS_JSONSCHEMA:
        print("  [SKIP] jsonschema not installed")
        return
    m = load_manifest()
    with open(MANIFEST_SCHEMA_PATH) as f:
        schema = json.load(f)
    jsonschema.validate(m, schema, format_checker=jsonschema.FormatChecker())


# ─────────────────────────────────────────────────────────────────────────────
# Stage presence and order
# ─────────────────────────────────────────────────────────────────────────────

def test_has_exactly_12_stages():
    m = load_manifest()
    assert len(m["stages"]) == 12, f"Expected 12, got {len(m['stages'])}"


def test_stage_order_is_correct():
    m = load_manifest()
    actual = [s["name"] for s in m["stages"]]
    assert actual == EXPECTED_STAGE_ORDER, (
        f"Stage order mismatch.\nExpected: {EXPECTED_STAGE_ORDER}\nActual:   {actual}"
    )


def test_no_duplicate_stage_names():
    m = load_manifest()
    names = [s["name"] for s in m["stages"]]
    assert len(names) == len(set(names)), f"Duplicate stages: {names}"


# ─────────────────────────────────────────────────────────────────────────────
# Artifact dependency graph
# ─────────────────────────────────────────────────────────────────────────────

def test_artifact_dependency_graph_complete():
    """Every required_artifact must be produced by a prior stage — no broken links."""
    m = load_manifest()
    produced = set()
    errors = []
    for s in m["stages"]:
        for req in s.get("required_artifacts_in", []):
            if req not in produced:
                errors.append(f"'{s['name']}' requires '{req}' but no prior stage produces it")
        for p in s.get("produces", []):
            produced.add(p)
    assert not errors, "Broken dependencies:\n" + "\n".join(f"  ❌ {e}" for e in errors)


def test_intake_produces_intake_brief():
    m = load_manifest()
    assert "intake_brief" in stage(m, "intake").get("produces", [])


def test_brief_enrichment_requires_intake_brief():
    m = load_manifest()
    assert "intake_brief" in stage(m, "brief_enrichment").get("required_artifacts_in", [])


def test_brief_enrichment_produces_enriched_brief():
    m = load_manifest()
    assert "enriched_brief" in stage(m, "brief_enrichment").get("produces", [])


def test_brief_enrichment_requires_human_approval():
    m = load_manifest()
    be = stage(m, "brief_enrichment")
    assert be.get("checkpoint_required") is True
    assert be.get("human_approval_default") is True


def test_brief_enrichment_review_focus_includes_user_approved():
    m = load_manifest()
    focus_text = " ".join(stage(m, "brief_enrichment").get("review_focus", []))
    assert "user_approved" in focus_text


def test_brief_enrichment_review_focus_includes_hypothesis_flags():
    m = load_manifest()
    focus_text = " ".join(stage(m, "brief_enrichment").get("review_focus", []))
    assert "hypothesis_flags" in focus_text


def test_intelligence_requires_intake_brief():
    m = load_manifest()
    assert "intake_brief" in stage(m, "intelligence").get("required_artifacts_in", [])


def test_intelligence_requires_enriched_brief():
    m = load_manifest()
    assert "enriched_brief" in stage(m, "intelligence").get("required_artifacts_in", [])


def test_bible_requires_intake_brief_and_intelligence_brief():
    m = load_manifest()
    reqs = stage(m, "bible").get("required_artifacts_in", [])
    assert "intake_brief" in reqs
    assert "enriched_brief" in reqs
    assert "intelligence_brief" in reqs


def test_bible_produces_production_bible():
    m = load_manifest()
    assert "production_bible" in stage(m, "bible").get("produces", [])


def test_idea_requires_production_bible():
    m = load_manifest()
    assert "production_bible" in stage(m, "idea").get("required_artifacts_in", [])


def test_idea_produces_idea_options():
    m = load_manifest()
    assert "idea_options" in stage(m, "idea").get("produces", [])


def test_proposal_requires_idea_options():
    m = load_manifest()
    assert "idea_options" in stage(m, "proposal").get("required_artifacts_in", [])


def test_proposal_produces_production_proposal():
    m = load_manifest()
    produces = stage(m, "proposal").get("produces", [])
    assert "production_proposal" in produces
    assert "proposal_packet" not in produces


def test_script_requires_production_bible():
    m = load_manifest()
    assert "production_bible" in stage(m, "script").get("required_artifacts_in", [])


def test_script_requires_idea_options():
    """script-director needs the selected concept scenario."""
    m = load_manifest()
    assert "idea_options" in stage(m, "script").get("required_artifacts_in", [])


def test_scene_plan_requires_production_bible():
    m = load_manifest()
    assert "production_bible" in stage(m, "scene_plan").get("required_artifacts_in", [])


def test_edit_requires_production_bible():
    m = load_manifest()
    assert "production_bible" in stage(m, "edit").get("required_artifacts_in", [])


# ─────────────────────────────────────────────────────────────────────────────
# Stale artifact names must not appear anywhere
# ─────────────────────────────────────────────────────────────────────────────

def test_no_stage_requires_proposal_packet():
    """proposal_packet was the old artifact name — must be fully eliminated."""
    m = load_manifest()
    violations = [
        s["name"] for s in m["stages"]
        if "proposal_packet" in s.get("required_artifacts_in", [])
    ]
    assert not violations, f"Stages still requiring stale 'proposal_packet': {violations}"


def test_no_stage_requires_selected_idea():
    """selected_idea was a non-existent artifact name — must be eliminated."""
    m = load_manifest()
    violations = [
        s["name"] for s in m["stages"]
        if "selected_idea" in s.get("required_artifacts_in", [])
    ]
    assert not violations, f"Stages requiring non-existent 'selected_idea': {violations}"


def test_no_stage_produces_brief():
    """'brief' was the old idea output — must be replaced by 'idea_options'."""
    m = load_manifest()
    violations = [
        s["name"] for s in m["stages"]
        if "brief" in s.get("produces", [])
    ]
    assert not violations, f"Stages still producing old 'brief' artifact: {violations}"


# ─────────────────────────────────────────────────────────────────────────────
# Key stage field values
# ─────────────────────────────────────────────────────────────────────────────

def test_bible_requires_human_approval():
    m = load_manifest()
    b = stage(m, "bible")
    assert b.get("checkpoint_required") is True
    assert b.get("human_approval_default") is True


def test_idea_requires_human_approval():
    """User must select a concept — cannot auto-proceed."""
    m = load_manifest()
    idea = stage(m, "idea")
    assert idea.get("checkpoint_required") is True, (
        "checkpoint_required must be True — may be False due to lingering duplicate YAML key"
    )
    assert idea.get("human_approval_default") is True


def test_idea_checkpoint_required_is_true_not_false():
    """Regression: fix commit removed duplicate checkpoint_required=false — must stay fixed."""
    m = load_manifest()
    idea = stage(m, "idea")
    assert idea.get("checkpoint_required") is True, (
        "checkpoint_required=False means the duplicate-key bug was re-introduced. "
        "Expected True because the fix commit should have resolved to True."
    )


def test_intake_runs_without_human_approval():
    """Intake interaction is embedded in the skill — no EP checkpoint gate."""
    m = load_manifest()
    intake_stage = stage(m, "intake")
    assert intake_stage.get("human_approval_default") is False
    assert intake_stage.get("checkpoint_required") is False


def test_intelligence_runs_without_human_approval():
    m = load_manifest()
    intel = stage(m, "intelligence")
    assert intel.get("human_approval_default") is False


def test_proposal_requires_human_approval():
    m = load_manifest()
    p = stage(m, "proposal")
    assert p.get("checkpoint_required") is True
    assert p.get("human_approval_default") is True


# ─────────────────────────────────────────────────────────────────────────────
# compliance_check tool availability
# ─────────────────────────────────────────────────────────────────────────────

def test_compliance_check_available_to_script():
    m = load_manifest()
    assert "compliance_check" in stage(m, "script").get("optional_tools", [])


def test_compliance_check_available_to_scene_plan():
    m = load_manifest()
    assert "compliance_check" in stage(m, "scene_plan").get("optional_tools", [])


def test_compliance_check_available_to_edit():
    m = load_manifest()
    assert "compliance_check" in stage(m, "edit").get("optional_tools", [])


# ─────────────────────────────────────────────────────────────────────────────
# Required skills list
# ─────────────────────────────────────────────────────────────────────────────

def test_required_skills_include_pre_production_directors():
    m = load_manifest()
    skills_str = " ".join(m.get("required_skills", []))
    for director in ("intake-director", "brief-enrichment-director",
                     "intelligence-director", "bible-director"):
        assert director in skills_str, f"Missing from required_skills: {director}"


# ─────────────────────────────────────────────────────────────────────────────
# review_focus quality
# ─────────────────────────────────────────────────────────────────────────────

def test_idea_review_focus_does_not_mention_old_brief_fields():
    m = load_manifest()
    focus_text = " ".join(stage(m, "idea").get("review_focus", []))
    assert "brief artifact" not in focus_text
    assert "style_mode_candidate" not in focus_text
    assert "brand_context fields" not in focus_text


def test_idea_review_focus_references_bible_constraints():
    m = load_manifest()
    focus_text = " ".join(stage(m, "idea").get("review_focus", []))
    assert "production_bible" in focus_text or "bible" in focus_text.lower()


def test_bible_review_focus_includes_cta_check():
    m = load_manifest()
    focus_text = " ".join(stage(m, "bible").get("review_focus", []))
    assert "cta" in focus_text.lower()


def test_bible_review_focus_includes_both_approval_flags():
    m = load_manifest()
    focus_text = " ".join(stage(m, "bible").get("review_focus", []))
    assert "strategic_approved" in focus_text
    assert "execution_approved" in focus_text


# ─────────────────────────────────────────────────────────────────────────────
# Standalone runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_manifest_parses_without_error,
        test_manifest_has_required_top_level_fields,
        test_manifest_validates_against_json_schema,
        test_has_exactly_12_stages,
        test_stage_order_is_correct,
        test_no_duplicate_stage_names,
        test_artifact_dependency_graph_complete,
        test_intake_produces_intake_brief,
        test_brief_enrichment_requires_intake_brief,
        test_brief_enrichment_produces_enriched_brief,
        test_brief_enrichment_requires_human_approval,
        test_brief_enrichment_review_focus_includes_user_approved,
        test_brief_enrichment_review_focus_includes_hypothesis_flags,
        test_intelligence_requires_intake_brief,
        test_intelligence_requires_enriched_brief,
        test_bible_requires_intake_brief_and_intelligence_brief,
        test_bible_produces_production_bible,
        test_idea_requires_production_bible,
        test_idea_produces_idea_options,
        test_proposal_requires_idea_options,
        test_proposal_produces_production_proposal,
        test_script_requires_production_bible,
        test_script_requires_idea_options,
        test_scene_plan_requires_production_bible,
        test_edit_requires_production_bible,
        test_no_stage_requires_proposal_packet,
        test_no_stage_requires_selected_idea,
        test_no_stage_produces_brief,
        test_bible_requires_human_approval,
        test_idea_requires_human_approval,
        test_idea_checkpoint_required_is_true_not_false,
        test_intake_runs_without_human_approval,
        test_intelligence_runs_without_human_approval,
        test_proposal_requires_human_approval,
        test_compliance_check_available_to_script,
        test_compliance_check_available_to_scene_plan,
        test_compliance_check_available_to_edit,
        test_required_skills_include_pre_production_directors,
        test_idea_review_focus_does_not_mention_old_brief_fields,
        test_idea_review_focus_references_bible_constraints,
        test_bible_review_focus_includes_cta_check,
        test_bible_review_focus_includes_both_approval_flags,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    import sys; sys.exit(0 if failed == 0 else 1)
