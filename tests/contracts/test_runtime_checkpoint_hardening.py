"""Regression tests for runtime and checkpoint governance hardening."""

from __future__ import annotations

import sys
import shutil
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.checkpoint import (
    CheckpointValidationError,
    get_pipeline_stages,
    read_checkpoint,
    write_checkpoint,
)
from tools.character.character_animation import (
    CharacterSpecGenerator,
    PoseLibraryBuilder,
    SvgRigBuilder,
)
from tools.video.video_compose import VideoCompose


@pytest.fixture
def project_renders_dir(tmp_path):
    project_dir = PROJECT_ROOT / "projects" / f"pytest-runtime-checkpoint-{tmp_path.name}"
    shutil.rmtree(project_dir, ignore_errors=True)
    renders_dir = project_dir / "renders"
    yield renders_dir
    shutil.rmtree(project_dir, ignore_errors=True)


def _minimal_proposal_packet() -> dict:
    return {
        "version": "1.0",
        "concept_options": [
            {
                "id": "c1",
                "title": "The Surprising Truth About X",
                "hook": "You think X is slow.",
                "narrative_structure": "myth_busting",
                "visual_approach": "animated diagrams",
                "target_duration_seconds": 60,
                "why_this_works": "Strong misconception found in research",
            },
            {
                "id": "c2",
                "title": "X From Scratch",
                "hook": "Build X in 5 minutes.",
                "narrative_structure": "tutorial",
                "visual_approach": "code walkthrough",
                "target_duration_seconds": 90,
                "why_this_works": "High demand in audience questions",
            },
            {
                "id": "c3",
                "title": "Why X Matters Now",
                "hook": "X just changed everything.",
                "narrative_structure": "timeline",
                "visual_approach": "motion graphics",
                "target_duration_seconds": 75,
                "why_this_works": "Recent announcement creates timeliness",
            },
        ],
        "selected_concept": {
            "concept_id": "c1",
            "rationale": "Strongest research backing",
        },
        "production_plan": {
            "pipeline": "animated-explainer",
            "render_runtime": "remotion",
            "stages": [
                {"stage": "script", "tools": [], "approach": "Write from research"},
            ],
        },
        "cost_estimate": {
            "total_estimated_usd": 0.0,
            "line_items": [],
            "budget_verdict": "within_budget",
        },
        "approval": {"status": "approved"},
    }


def _minimal_decision_log(project_id: str = "explainer-project") -> dict:
    return {
        "version": "1.0",
        "project_id": project_id,
        "decisions": [
            {
                "decision_id": "d-runtime-001",
                "stage": "proposal",
                "category": "render_runtime_selection",
                "subject": "Render runtime",
                "options_considered": [
                    {
                        "option_id": "remotion",
                        "label": "Remotion",
                        "score": 1.0,
                        "reason": "Best fit for the approved scene stack",
                    },
                    {
                        "option_id": "hyperframes",
                        "label": "HyperFrames",
                        "score": 0.6,
                        "reason": "Available alternative runtime considered at proposal",
                        "rejected_because": "Remotion matches the approved proposal runtime",
                    }
                ],
                "selected": "remotion",
                "reason": "Matches the approved proposal runtime",
                "user_visible": True,
                "user_approved": True,
            }
        ],
    }


def test_explicit_unknown_pipeline_type_does_not_fallback_to_legacy_order():
    with pytest.raises(FileNotFoundError):
        get_pipeline_stages("not-a-real-pipeline")


def test_character_animation_custom_stages_checkpoint_with_manifest_artifacts(tmp_path):
    character_result = CharacterSpecGenerator().execute(
        {
            "characters": [
                {
                    "id": "lead",
                    "role": "host",
                    "body_type": "round mascot",
                    "required_actions": ["idle", "gesture"],
                }
            ],
        }
    )
    assert character_result.success
    character_design = character_result.data["character_design"]

    design_path = write_checkpoint(
        tmp_path,
        "character-project",
        "character_design",
        "completed",
        {"character_design": character_design},
        pipeline_type="character-animation",
    )
    assert design_path.exists()

    rig_result = SvgRigBuilder().execute(
        {"character_design": character_design}
    )
    assert rig_result.success
    rig_plan = rig_result.data["rig_plan"]

    pose_result = PoseLibraryBuilder().execute({"rig_plan": rig_plan})
    assert pose_result.success
    pose_library = pose_result.data["pose_library"]

    rig_path = write_checkpoint(
        tmp_path,
        "character-project",
        "rig_plan",
        "completed",
        {"rig_plan": rig_plan, "pose_library": pose_library},
        pipeline_type="character-animation",
    )
    assert rig_path.exists()

    checkpoint = read_checkpoint(tmp_path, "character-project", "rig_plan")
    assert checkpoint is not None
    assert checkpoint["artifacts"]["rig_plan"]["version"] == "1.0"


def test_checkpoint_requires_manifest_output_needed_by_later_stage(tmp_path):
    rig_plan = {
        "version": "1.0",
        "characters": [
            {
                "character_id": "lead",
                "parts": [{"id": "body", "kind": "torso", "layer": 0}],
                "joints": {"body": {"pivot": [0, 0]}},
                "layers": ["body"],
                "required_poses": ["idle"],
            }
        ],
    }

    with pytest.raises(CheckpointValidationError, match="pose_library"):
        write_checkpoint(
            tmp_path,
            "character-project",
            "rig_plan",
            "completed",
            {"rig_plan": rig_plan},
            pipeline_type="character-animation",
        )


def test_completed_checkpoint_requires_every_manifest_declared_output(tmp_path):
    with pytest.raises(CheckpointValidationError, match="decision_log"):
        write_checkpoint(
            tmp_path,
            "explainer-project",
            "proposal",
            "completed",
            {"proposal_packet": _minimal_proposal_packet()},
            pipeline_type="animated-explainer",
        )


def test_completed_checkpoint_accepts_all_manifest_declared_outputs(tmp_path):
    path = write_checkpoint(
        tmp_path,
        "explainer-project",
        "proposal",
        "completed",
        {
            "proposal_packet": _minimal_proposal_packet(),
            "decision_log": _minimal_decision_log(),
        },
        pipeline_type="animated-explainer",
    )

    assert path.exists()


def test_compose_checkpoint_requires_final_review_when_publish_requires_it(tmp_path):
    render_report = {
        "version": "1.0",
        "outputs": [
            {
                "path": "renders/final.mp4",
                "format": "mp4",
                "resolution": "1920x1080",
                "duration_seconds": 30,
            }
        ],
    }

    with pytest.raises(CheckpointValidationError, match="final_review"):
        write_checkpoint(
            tmp_path,
            "explainer-project",
            "compose",
            "completed",
            {"render_report": render_report},
            pipeline_type="animated-explainer",
        )


def test_compose_checkpoint_rejects_non_passing_final_review_for_any_pipeline(tmp_path):
    render_report = {
        "version": "1.0",
        "outputs": [
            {
                "path": "renders/final.mp4",
                "format": "mp4",
                "resolution": "1920x1080",
                "duration_seconds": 30,
            }
        ],
    }
    final_review = {
        "version": "1.0",
        "output_path": "renders/final.mp4",
        "status": "revise",
        "checks": {
            "technical_probe": {"valid_container": True, "issues": []},
            "visual_spotcheck": {"frames_sampled": 4, "issues": []},
            "audio_spotcheck": {"issues": []},
            "promise_preservation": {
                "runtime_swap_detected": False,
                "issues": [],
            },
            "subtitle_check": {"issues": []},
        },
    }

    with pytest.raises(CheckpointValidationError, match="final_review.status"):
        write_checkpoint(
            tmp_path,
            "explainer-project",
            "compose",
            "completed",
            {"render_report": render_report, "final_review": final_review},
            pipeline_type="animated-explainer",
        )


def test_video_compose_blocks_locked_remotion_when_runtime_unavailable(
    monkeypatch,
    tmp_path,
    project_renders_dir,
):
    composer = VideoCompose()
    monkeypatch.setattr(composer, "_remotion_available", lambda: False)
    monkeypatch.setattr(composer, "_pre_compose_validation", lambda *args, **kwargs: None)

    def fail_compose(_inputs):
        raise AssertionError("locked Remotion should not route to FFmpeg")

    monkeypatch.setattr(composer, "_compose", fail_compose)

    result = composer.execute(
        {
            "operation": "render",
            "edit_decisions": {
                "version": "1.0",
                "renderer_family": "explainer-data",
                "render_runtime": "remotion",
                "cuts": [
                    {
                        "id": "cut-1",
                        "source": "clip-1",
                        "in_seconds": 0,
                        "out_seconds": 1,
                    }
                ],
            },
            "asset_manifest": {
                "version": "1.0",
                "assets": [
                    {
                        "id": "clip-1",
                        "type": "video",
                        "path": str(tmp_path / "clip.mp4"),
                        "source_tool": "fixture",
                        "scene_id": "scene-1",
                    }
                ],
            },
            "output_path": str(project_renders_dir / "out.mp4"),
        }
    )

    assert not result.success
    assert "render_runtime='remotion'" in (result.error or "")
    assert "not available" in (result.error or "")
