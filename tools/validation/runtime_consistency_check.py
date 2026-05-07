"""Render-runtime consistency validator.

Enforces the AGENT_GUIDE.md HARD RULE that production_proposal.render_runtime
(locked at proposal stage) must equal edit_decisions.render_runtime (used at
compose stage). Silent runtime swaps are forbidden — any difference must be
backed by an explicit decision_log entry tagged `render_runtime_selection`
with `user_approved == true` whose selected runtime equals the actual compose
runtime.

Used by:
  - executive-producer.md G6 (after edit stage, before compose)
  - executive-producer.md G7 (after compose, as part of render verification)
  - CLI ad-hoc:
        python -m tools.validation.runtime_consistency_check \
            projects/<project-name>

The validator does NOT read AGENT_GUIDE.md or apply heuristics — it strictly
checks the proposal-vs-edit contract and the decision_log audit trail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _load_artifact(project_dir: Path, name: str) -> dict[str, Any]:
    path = project_dir / "artifacts" / name
    if not path.exists():
        raise FileNotFoundError(f"missing artifact: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _find_runtime_decision(
    edit_decisions: dict[str, Any],
    decision_log: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Locate a user-visible `render_runtime_selection` decision.

    Returns the entry dict, or None when no such entry exists.
    """
    if decision_log:
        decisions = decision_log.get("decisions")
        if isinstance(decisions, list):
            for decision in reversed(decisions):
                if (
                    isinstance(decision, dict)
                    and decision.get("category") == "render_runtime_selection"
                ):
                    return decision

    # Backwards compatibility for older edit_decisions artifacts that embedded
    # a one-off decision stub under metadata. New ad-video projects use the
    # cumulative decision_log.json schema with decisions[].
    metadata = edit_decisions.get("metadata") or {}
    embedded_log = metadata.get("decision_log") or {}
    if isinstance(embedded_log, dict):
        embedded_decisions = embedded_log.get("decisions")
        if isinstance(embedded_decisions, list):
            for decision in reversed(embedded_decisions):
                if (
                    isinstance(decision, dict)
                    and decision.get("category") == "render_runtime_selection"
                ):
                    return decision
        embedded_decision = embedded_log.get("render_runtime_selection")
        if isinstance(embedded_decision, dict):
            return embedded_decision

    return None


def _selected_runtime(decision: dict[str, Any] | None) -> str | None:
    """Return the runtime explicitly selected by a runtime decision."""
    if not isinstance(decision, dict):
        return None

    selected = decision.get("selected")
    if isinstance(selected, str) and selected:
        return selected

    # Legacy embedded one-off decisions sometimes recorded the compose runtime
    # directly instead of using the decision_log.schema.json `selected` field.
    actual_at_compose = decision.get("actual_at_compose")
    if isinstance(actual_at_compose, str) and actual_at_compose:
        return actual_at_compose

    return None


def check_runtime_consistency(
    proposal: dict[str, Any],
    edit_decisions: dict[str, Any],
    decision_log: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare the locked runtime to the compose-time runtime.

    Returns a verdict dict:
        {
          "status": "PASS" | "FAIL",
          "locked_at_proposal": <runtime or None>,
          "actual_at_compose": <runtime or None>,
          "match": <bool>,
          "decision_present": <bool>,
          "decision_user_approved": <bool>,
          "decision_selected_runtime": <runtime or None>,
          "decision_matches_actual": <bool>,
          "issues": [<str>, ...],
        }
    """
    locked = proposal.get("render_runtime")
    actual = edit_decisions.get("render_runtime")
    issues: list[str] = []

    if locked is None:
        issues.append(
            "production_proposal.render_runtime is unset; "
            "proposal-director must lock the runtime at proposal stage."
        )
    if actual is None:
        issues.append(
            "edit_decisions.render_runtime is unset; "
            "edit-director must carry the locked runtime forward."
        )

    match = locked == actual and locked is not None
    decision = _find_runtime_decision(edit_decisions, decision_log)
    decision_present = decision is not None
    decision_user_approved = bool(
        decision and decision.get("user_approved") is True
    )
    decision_selected_runtime = _selected_runtime(decision)
    decision_matches_actual = (
        actual is not None and decision_selected_runtime == actual
    )

    if not match and (locked is not None and actual is not None):
        # Swap occurred. Require a logged decision with user approval that
        # selects the actual runtime. An old approved proposal decision for the
        # locked runtime does not authorize a later swap.
        if not decision_present:
            issues.append(
                f"Silent runtime swap forbidden: proposal locked '{locked}' but "
                f"edit_decisions uses '{actual}'. No render_runtime_selection entry "
                f"in decision_log.decisions. AGENT_GUIDE HARD RULE "
                f"violation."
            )
        elif not decision_user_approved:
            issues.append(
                f"Runtime swap from '{locked}' to '{actual}' has a decision_log "
                f"entry but user_approved is not true. The HARD RULE requires "
                f"explicit user approval before changing the locked runtime."
            )
        elif not decision_matches_actual:
            if decision_selected_runtime is None:
                issues.append(
                    f"Runtime swap from '{locked}' to '{actual}' has an approved "
                    f"render_runtime_selection entry, but it does not record a "
                    f"selected runtime and does not select actual runtime "
                    f"'{actual}'."
                )
            else:
                issues.append(
                    f"Runtime swap from '{locked}' to '{actual}' has an approved "
                    f"render_runtime_selection entry, but that decision selected "
                    f"'{decision_selected_runtime}' and does not select actual "
                    f"runtime '{actual}'."
                )

    status = "PASS" if not issues else "FAIL"
    return {
        "status": status,
        "locked_at_proposal": locked,
        "actual_at_compose": actual,
        "match": match,
        "decision_present": decision_present,
        "decision_user_approved": decision_user_approved,
        "decision_selected_runtime": decision_selected_runtime,
        "decision_matches_actual": decision_matches_actual,
        "issues": issues,
    }


def check_project(project_dir: Path) -> dict[str, Any]:
    """Convenience entry point for ad-hoc CLI use."""
    proposal = _load_artifact(project_dir, "production_proposal.json")
    edit_decisions = _load_artifact(project_dir, "edit_decisions.json")
    decision_log = _load_decision_log(project_dir)
    return check_runtime_consistency(proposal, edit_decisions, decision_log)


def _load_decision_log(project_dir: Path) -> dict[str, Any] | None:
    for path in (
        project_dir / "decision_log.json",
        project_dir / "artifacts" / "decision_log.json",
    ):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return None


def _cli(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            "usage: python -m tools.validation.runtime_consistency_check "
            "<project-dir>",
            file=sys.stderr,
        )
        return 2
    project_dir = Path(argv[1]).resolve()
    if not project_dir.exists():
        print(f"error: project dir not found: {project_dir}", file=sys.stderr)
        return 2
    verdict = check_project(project_dir)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv))
