from __future__ import annotations

import math

import pytest

from tests.eval.replay_harness.harness import EvalMode, GoldenScenario


def test_golden_scenario_load_rejects_non_strict_json(tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(
        """
{
  "name": "bad-numeric-scenario",
  "pipeline_type": "talking-head",
  "inputs": {"prompt": "hello"},
  "expected_artifacts": {
    "render_report": {"duration_seconds": NaN}
  },
  "eval_mode": "stochastic",
  "tolerance": 0.1,
  "tags": []
}
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strict JSON"):
        GoldenScenario.load(scenario_path)


def test_golden_scenario_save_rejects_non_finite_json_before_writing(tmp_path):
    scenario = GoldenScenario(
        name="bad-numeric-scenario",
        pipeline_type="talking-head",
        inputs={"prompt": "hello"},
        expected_artifacts={"render_report": {"duration_seconds": math.nan}},
        eval_mode=EvalMode.STOCHASTIC,
        tolerance=0.1,
    )
    output_path = tmp_path / "scenario.json"

    with pytest.raises(ValueError, match="strict JSON"):
        scenario.save(output_path)

    assert not output_path.exists()
