"""Phase 1 golden scenario test — validates the talking-head pipeline
manifest and skill architecture are in place.

The old test ran the Python orchestrator pipeline end-to-end. That layer
has been removed in favor of instruction-driven architecture: the agent
reads pipeline manifests + stage director skills and drives the pipeline
itself.  These tests verify the infrastructure is correctly wired.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.pipeline_loader import (
    load_pipeline,
    get_stage_order,
    list_pipelines,
)
from schemas.artifacts import load_schema, list_schemas


GOLDEN_PATH = PROJECT_ROOT / "tests" / "eval" / "golden_scenarios" / "talking_head_basic.json"
ROOT_EVAL_PATH = PROJECT_ROOT / "eval"


def _load_golden(path: Path) -> dict:
    return json.loads(path.read_text())


def _produced_artifacts(manifest: dict) -> list[str]:
    return [
        artifact
        for stage in manifest["stages"]
        for artifact in stage.get("produces", [])
    ]


class TestTalkingHeadManifest:
    """Verify the talking-head pipeline manifest is well-formed."""

    def test_manifest_loads(self):
        manifest = load_pipeline("talking-head")
        assert manifest["name"] == "talking-head"

    def test_all_stages_present(self):
        manifest = load_pipeline("talking-head")
        stage_names = get_stage_order(manifest)
        expected = ["idea", "script", "scene_plan", "assets", "edit", "compose", "publish"]
        assert stage_names == expected

    def test_manifest_listed(self):
        assert "talking-head" in list_pipelines()


class TestGoldenScenarioArtifacts:
    """Validate golden scenario artifact samples against schemas."""

    def test_root_eval_directory_is_not_used(self):
        assert not ROOT_EVAL_PATH.exists()

    def test_golden_file_structure(self):
        assert GOLDEN_PATH.exists(), f"Golden scenario file not found: {GOLDEN_PATH}"
        golden = _load_golden(GOLDEN_PATH)

        assert "name" in golden
        assert "pipeline_type" in golden
        assert "inputs" in golden
        assert "expected_artifacts" in golden

    def test_golden_pipeline_identity_is_talking_head(self):
        golden = _load_golden(GOLDEN_PATH)

        assert golden["pipeline_type"] == "talking-head"
        assert golden["inputs"]["pipeline"] == golden["pipeline_type"]

    def test_golden_expected_artifacts_match_manifest_outputs(self):
        golden = _load_golden(GOLDEN_PATH)
        manifest = load_pipeline(golden["pipeline_type"])

        assert list(golden["expected_artifacts"]) == _produced_artifacts(manifest)

    def test_golden_expected_artifacts_use_valid_schema_keys(self):
        golden = _load_golden(GOLDEN_PATH)
        known_schemas = set(list_schemas())

        for artifact_name, expectation in golden["expected_artifacts"].items():
            assert artifact_name in known_schemas
            assert "required_keys" in expectation
            assert "required_fields" not in expectation

            schema_required = set(load_schema(artifact_name).get("required", []))
            expected_required = set(expectation["required_keys"])
            assert schema_required <= expected_required

    def test_golden_footage_path_is_portable_fixture_path(self):
        golden = _load_golden(GOLDEN_PATH)
        footage_path = golden["inputs"]["footage_path"]

        assert not Path(footage_path).is_absolute()
        assert not re.match(r"^[A-Za-z]:[\\/]", footage_path)
