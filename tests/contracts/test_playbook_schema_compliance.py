"""Regression test: every style playbook in styles/ validates against the schema.

Pins the silent-drift class of bug where a playbook gets a new field (or the
schema gets a new `additionalProperties: false` lock) without the counterpart
being updated. Until this test existed, ad-brand.yaml was flagged in review
as violating the playbook schema's lock — turned out the schema had been
extended too, but nobody could verify it mechanically. This test makes that
mechanical and covers ALL playbooks (including ad-brand and anime-ghibli,
which were added after the original three preset playbooks).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
PLAYBOOKS_DIR = REPO / "styles"
PLAYBOOK_SCHEMA = REPO / "schemas" / "styles" / "playbook.schema.json"


def _all_playbooks() -> list[Path]:
    return sorted(PLAYBOOKS_DIR.glob("*.yaml"))


@pytest.fixture(scope="module")
def playbook_schema() -> dict:
    return json.loads(PLAYBOOK_SCHEMA.read_text())


@pytest.mark.parametrize("playbook_path", _all_playbooks(), ids=lambda p: p.stem)
def test_playbook_validates(playbook_path: Path, playbook_schema: dict) -> None:
    """Every playbook YAML must validate against playbook.schema.json."""
    payload = yaml.safe_load(playbook_path.read_text())
    try:
        jsonschema.validate(instance=payload, schema=playbook_schema)
    except jsonschema.ValidationError as e:
        pytest.fail(
            f"Playbook {playbook_path.name} violates the schema: {e.message} "
            f"at path {list(e.absolute_path)}"
        )


def test_playbook_schema_is_valid_jsonschema(playbook_schema: dict) -> None:
    """The playbook schema itself must be a valid Draft 2020-12 schema."""
    jsonschema.Draft202012Validator.check_schema(playbook_schema)
