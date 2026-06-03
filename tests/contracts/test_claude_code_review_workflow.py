"""Contract tests for the automated Claude PR review workflow."""

from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "claude-code-review.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text())


def _review_step() -> dict:
    workflow = _load_workflow()
    steps = workflow["jobs"]["claude-review"]["steps"]
    return next(step for step in steps if step.get("id") == "claude-review")


def test_claude_review_workflow_posts_pr_feedback():
    prompt = _review_step()["with"]["prompt"]

    assert "/code-review:code-review" in prompt
    assert "--comment" in prompt


def test_claude_review_workflow_has_comment_permissions():
    permissions = _load_workflow()["jobs"]["claude-review"]["permissions"]

    assert permissions["contents"] == "read"
    assert permissions["pull-requests"] == "write"
    assert permissions["issues"] == "write"
