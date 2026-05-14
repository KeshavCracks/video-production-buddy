"""Enforce the 'present both composition runtimes' governance contract.

For every pipeline in `pipeline_defs/`, the planning-stage skill (proposal
or idea) MUST instruct the agent about runtime selection — either by
presenting both runtimes to the user when they are a real choice, or by
surfacing the constraint when the pipeline is locked to one runtime.

This test prevents a new pipeline from being added without the conversation
contract. A fresh-session agent that reads a pipeline's planning skill and
finds no runtime guidance will silently default to Remotion — which is the
exact failure mode this contract prevents.

See:
- AGENT_GUIDE.md → "Present Both Composition Runtimes (HARD RULE)"
- skills/core/hyperframes.md → "Hard rule: present both runtimes"
- skills/meta/reviewer.md → finding #6
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
PIPELINE_DIR = ROOT / "pipeline_defs"
SKILLS_DIR = ROOT / "skills"

# Tokens we expect in any compliant planning-stage skill. A skill needs AT
# LEAST one from each group to pass. The groups are intentionally loose —
# this test is a tripwire, not a style enforcer.
_REQUIRED_RUNTIME_TOKENS = [
    "render_runtime",      # the field name must appear
    "hyperframes",         # the alternative runtime must be named
]
# And at least one of these phrases showing the conversation-not-default contract.
_CONVERSATION_TOKENS = [
    "present both",
    "Present Both",
    "PRESENT BOTH",
    "render_runtime_selection",  # pointing at the decision_log category
]


def _planning_stages(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every 'proposal' or 'idea' stage (a pipeline may have one or both)."""
    out: list[dict[str, Any]] = []
    for stage in manifest.get("stages", []):
        if stage.get("name") in {"proposal", "idea"}:
            out.append(stage)
        for sub_stage in stage.get("sub_stages", []):
            if stage.get("name") in {"proposal", "idea"} or sub_stage.get("name") in {"proposal", "idea", "technical_proposal"}:
                out.append(sub_stage)
    return out


def _load_manifest(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_skill(skill_ref: str) -> tuple[Path, str]:
    """Resolve a manifest `skill:` string to its markdown path + contents."""
    candidate = SKILLS_DIR / f"{skill_ref}.md"
    assert candidate.is_file(), (
        f"Manifest references skill {skill_ref!r} but {candidate} does not exist."
    )
    return candidate, candidate.read_text(encoding="utf-8")


def _stage_named(manifest: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((s for s in manifest.get("stages", []) if s.get("name") == name), None)


def _stage_uses_tool(stage: dict[str, Any] | None, tool_name: str) -> bool:
    if not stage:
        return False
    declared = (
        stage.get("required_tools", [])
        + stage.get("optional_tools", [])
        + stage.get("tools_available", [])
    )
    return tool_name in declared


def _produced_artifacts(manifest: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for stage in manifest.get("stages", []):
        out.update(stage.get("produces") or [])
        for sub_stage in stage.get("sub_stages", []):
            out.update(sub_stage.get("produces") or [])
    return out


def _runtime_lock_artifact(manifest: dict[str, Any]) -> str | None:
    """Return the planning artifact that carries the render_runtime lock."""
    produced = _produced_artifacts(manifest)
    for candidate in ("production_proposal", "proposal_packet", "brief"):
        if candidate in produced:
            return candidate
    return None


def _skill_bodies_for_stages(manifest: dict[str, Any], stage_names: set[str]) -> str:
    bodies: list[str] = []
    for stage in manifest.get("stages", []):
        if stage.get("name") in stage_names:
            skill_ref = stage.get("skill")
            if skill_ref:
                _, body = _load_skill(skill_ref)
                bodies.append(body)
        for sub_stage in stage.get("sub_stages", []):
            if stage.get("name") not in stage_names and sub_stage.get("name") not in stage_names:
                continue
            skill_ref = sub_stage.get("skill")
            if not skill_ref:
                continue
            _, body = _load_skill(skill_ref)
            bodies.append(body)
    return "\n".join(bodies)


ALL_MANIFESTS = sorted(PIPELINE_DIR.glob("*.yaml"))
assert ALL_MANIFESTS, "No pipeline manifests found"

# Test-only pipelines that don't compose final video go on this list with
# an explicit reason. Everything else is required to follow the contract.
_EXCLUDED_PIPELINES = {
    "framework-smoke": "minimal 2-stage smoke test, no compose stage",
}


@pytest.mark.parametrize(
    "manifest_path",
    [p for p in ALL_MANIFESTS if p.stem not in _EXCLUDED_PIPELINES],
    ids=lambda p: p.stem,
)
def test_planning_skill_mentions_runtime_contract(manifest_path: Path):
    """Every pipeline that reaches compose must have runtime guidance in its
    planning-stage skill."""
    manifest = _load_manifest(manifest_path)
    planning = _planning_stages(manifest)
    assert planning, (
        f"Pipeline {manifest_path.stem} has no 'proposal' or 'idea' stage. "
        f"Add one, or add this pipeline to _EXCLUDED_PIPELINES with a reason."
    )

    # At least ONE of the planning skills in this pipeline must cover the
    # contract (pipelines with both proposal+idea only need one to carry it).
    matched_skill: str | None = None
    matched_why: dict[str, bool] = {}
    for stage in planning:
        skill_ref = stage.get("skill")
        if not skill_ref:
            continue
        _, body = _load_skill(skill_ref)
        covers_required = all(token in body for token in _REQUIRED_RUNTIME_TOKENS)
        covers_conversation = any(token in body for token in _CONVERSATION_TOKENS)
        if covers_required and covers_conversation:
            matched_skill = skill_ref
            matched_why = {
                "mentions_render_runtime": "render_runtime" in body,
                "mentions_hyperframes": "hyperframes" in body,
                "conversation_token_found": covers_conversation,
            }
            break

    assert matched_skill, (
        f"Pipeline {manifest_path.stem}: no planning-stage skill covers the "
        f"runtime-selection contract. Each pipeline's proposal- or idea-director "
        f"must discuss render_runtime, name hyperframes, and either 'Present both' "
        f"or a `render_runtime_selection` decision. A fresh-session agent reading "
        f"this pipeline's plan would silently default to Remotion. Fix the skill "
        f"that drives the planning stage."
    )


@pytest.mark.parametrize(
    "manifest_path",
    [p for p in ALL_MANIFESTS if p.stem not in _EXCLUDED_PIPELINES],
    ids=lambda p: p.stem,
)
def test_compose_stage_references_runtime_routing(manifest_path: Path):
    """Compose stage's director skill must also cover runtime routing, so
    that even a pipeline whose planning skill somehow misses the contract
    cannot silently render under the wrong runtime."""
    manifest = _load_manifest(manifest_path)
    compose_stage = next(
        (s for s in manifest.get("stages", []) if s.get("name") == "compose"),
        None,
    )
    if compose_stage is None:
        # Some pipelines use alternate terminal stages; skip.
        pytest.skip(f"{manifest_path.stem} has no 'compose' stage")

    skill_ref = compose_stage.get("skill")
    assert skill_ref, f"{manifest_path.stem} compose stage has no skill reference"
    _, body = _load_skill(skill_ref)
    # Compose-directors must at minimum mention render_runtime AND either
    # route by runtime or surface a hard constraint (HyperFrames deferred).
    assert "render_runtime" in body, (
        f"{skill_ref} does not mention render_runtime. Compose MUST route by "
        f"render_runtime; without this instruction the agent will fall back to "
        f"the tool's legacy behavior (silently pick Remotion)."
    )
    # Must also mention HyperFrames explicitly so a reviewer can tell the
    # author considered it and either enabled or rejected it with reason.
    assert re.search(r"hyperframes|HyperFrames", body), (
        f"{skill_ref} does not mention HyperFrames at all. Even on deferred "
        f"pipelines, the compose-director must name HyperFrames so the agent "
        f"can surface the constraint to the user rather than silently pick "
        f"Remotion. See documentary-montage or talking-head compose-director "
        f"for the deferred-pipeline template."
    )


@pytest.mark.parametrize(
    "manifest_path",
    [p for p in ALL_MANIFESTS if p.stem not in _EXCLUDED_PIPELINES],
    ids=lambda p: p.stem,
)
def test_video_compose_stages_receive_runtime_lock_artifact(manifest_path: Path):
    """Edit and compose must receive the artifact that owns render_runtime."""
    manifest = _load_manifest(manifest_path)
    compose_stage = _stage_named(manifest, "compose")
    if not _stage_uses_tool(compose_stage, "video_compose"):
        pytest.skip(f"{manifest_path.stem} does not render through video_compose")

    runtime_artifact = _runtime_lock_artifact(manifest)
    assert runtime_artifact, (
        f"{manifest_path.stem} uses video_compose but has no planning artifact "
        "that can carry the proposal-time render_runtime lock."
    )

    for stage_name in ("edit", "compose"):
        stage = _stage_named(manifest, stage_name)
        if stage is None:
            continue
        required = set(stage.get("required_artifacts_in") or [])
        assert runtime_artifact in required, (
            f"{manifest_path.stem}.{stage_name} must require {runtime_artifact!r} "
            "so edit_decisions.render_runtime can be copied from the approved "
            "planning artifact and compose can verify it before rendering."
        )


@pytest.mark.parametrize(
    "manifest_path",
    [p for p in ALL_MANIFESTS if p.stem not in _EXCLUDED_PIPELINES],
    ids=lambda p: p.stem,
)
def test_brief_runtime_lock_pipelines_name_required_metadata_field(
    manifest_path: Path,
):
    """Brief-first pipelines must tell agents where the runtime lock lives."""
    manifest = _load_manifest(manifest_path)
    compose_stage = _stage_named(manifest, "compose")
    if not _stage_uses_tool(compose_stage, "video_compose"):
        pytest.skip(f"{manifest_path.stem} does not render through video_compose")
    if _runtime_lock_artifact(manifest) != "brief":
        pytest.skip(f"{manifest_path.stem} does not use brief as the runtime lock")

    planning_text = _skill_bodies_for_stages(manifest, {"idea", "proposal"})
    assert "brief.metadata.render_runtime" in planning_text, (
        f"{manifest_path.stem} uses brief as its runtime lock, but its planning "
        "skill does not name brief.metadata.render_runtime. Agents can produce "
        "schema-invalid briefs or skip final-review runtime-swap detection."
    )


@pytest.mark.parametrize(
    "manifest_path",
    [p for p in ALL_MANIFESTS if p.stem not in _EXCLUDED_PIPELINES],
    ids=lambda p: p.stem,
)
def test_video_compose_stage_receives_decision_log_when_runtime_skills_use_it(
    manifest_path: Path,
):
    """If runtime skills tell agents to log decisions, compose must receive them."""
    manifest = _load_manifest(manifest_path)
    compose_stage = _stage_named(manifest, "compose")
    if not _stage_uses_tool(compose_stage, "video_compose"):
        pytest.skip(f"{manifest_path.stem} does not render through video_compose")

    runtime_skill_text = _skill_bodies_for_stages(manifest, {"idea", "proposal", "compose"})
    if "decision_log" not in runtime_skill_text:
        pytest.skip(f"{manifest_path.stem} runtime skills do not mention decision_log")

    produced = _produced_artifacts(manifest)
    assert "decision_log" in produced, (
        f"{manifest_path.stem} runtime skills mention decision_log, but no stage "
        "declares it in produces."
    )
    required = set(compose_stage.get("required_artifacts_in") or [])
    assert "decision_log" in required, (
        f"{manifest_path.stem}.compose must require decision_log so approved "
        "runtime substitutions can be audited before video_compose renders."
    )


def test_agent_guide_carries_hard_rule():
    """The top-level agent contract must carry the HARD RULE banner so every
    fresh-session agent reads it before picking a pipeline."""
    guide = (ROOT / "AGENT_GUIDE.md").read_text(encoding="utf-8")
    assert "Present Both Composition Runtimes" in guide
    assert "HARD RULE" in guide
    # The rule must explicitly forbid the failure mode.
    assert "silently" in guide.lower()


def test_reviewer_has_critical_finding_for_single_option_runtime():
    """The reviewer meta-skill must treat a single-option render_runtime_selection
    as CRITICAL — otherwise the governance rule has no enforcement at review
    time and a bypass slips through unnoticed."""
    body = (SKILLS_DIR / "meta" / "reviewer.md").read_text(encoding="utf-8")
    # Locate the critical-severity rule explicitly.
    assert "render_runtime_selection" in body
    # The section must carry CRITICAL severity language tied to single-option.
    assert re.search(
        r"render_runtime_selection.{0,800}(CRITICAL|critical)",
        body,
        re.DOTALL,
    ), (
        "Reviewer skill doesn't flag single-option render_runtime_selection "
        "as CRITICAL — the conversation contract has no teeth."
    )


def test_user_facing_hyperframes_docs_use_public_npx_command():
    """User-facing HyperFrames docs must point at the runtime command Video Production Buddy uses."""
    docs = [
        ROOT / "PROMPT_GALLERY.md",
        SKILLS_DIR / "meta" / "onboarding.md",
    ]
    for path in docs:
        body = path.read_text(encoding="utf-8")
        assert "npx @hyperframes/cli" not in body, (
            f"{path.relative_to(ROOT)} still recommends the monorepo-internal "
            "HyperFrames package name; use `npx hyperframes` instead."
        )
        assert "npx hyperframes" in body
