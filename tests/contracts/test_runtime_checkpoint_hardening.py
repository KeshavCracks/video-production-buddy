"""Regression tests for runtime and checkpoint governance hardening."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.checkpoint import get_pipeline_stages, read_checkpoint, write_checkpoint
from tools.character.character_animation import (
    CharacterSpecGenerator,
    PoseLibraryBuilder,
    SvgRigBuilder,
)
from tools.video.video_compose import VideoCompose


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
            "output_path": str(tmp_path / "character_design.json"),
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
        {
            "character_design": character_design,
            "output_path": str(tmp_path / "rig_plan.json"),
        }
    )
    assert rig_result.success
    rig_plan = rig_result.data["rig_plan"]

    pose_result = PoseLibraryBuilder().execute(
        {"rig_plan": rig_plan, "output_path": str(tmp_path / "pose_library.json")}
    )
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


def test_video_compose_blocks_locked_remotion_when_runtime_unavailable(monkeypatch, tmp_path):
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
            "output_path": str(tmp_path / "out.mp4"),
        }
    )

    assert not result.success
    assert "render_runtime='remotion'" in (result.error or "")
    assert "not available" in (result.error or "")
