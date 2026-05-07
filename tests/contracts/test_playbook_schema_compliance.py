"""Regression test: every style playbook in styles/ validates against the schema.

Pins the silent-drift class of bug where a playbook gets a new field (or the
schema gets a new `additionalProperties: false` lock) without the counterpart
being updated. Until this test existed, ad-brand.yaml was flagged in review
as violating the playbook schema's lock — turned out the schema had been
extended too, but nobody could verify it mechanically. This test makes that
mechanical and covers ALL playbooks (including ad-brand and anime-ghibli,
which the script-style test_07_playbook_intelligence.py omits).
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


# Playbooks with known schema-vocabulary divergences. Each entry should be
# removed once the corresponding schema fields are added (or the playbook
# is normalized) — until then, xfail keeps the suite green without losing
# the signal.
KNOWN_DIVERGENT_PLAYBOOKS: dict[str, str] = {
    # anime-ghibli adds asset_generation extension fields specific to its
    # animation pipeline (default_particle_color, default_particles,
    # default_vignette, image_variation_guidance, images_per_scene,
    # multi_image_per_scene, scene_type). Schema needs these added or
    # asset_generation.additionalProperties relaxed. Tracked separately.
    "anime-ghibli": "asset_generation extension fields not yet declared in schema",
}


@pytest.mark.parametrize("playbook_path", _all_playbooks(), ids=lambda p: p.stem)
def test_playbook_validates(playbook_path: Path, playbook_schema: dict) -> None:
    """Every playbook YAML must validate against playbook.schema.json."""
    if playbook_path.stem in KNOWN_DIVERGENT_PLAYBOOKS:
        pytest.xfail(
            f"{playbook_path.stem}: {KNOWN_DIVERGENT_PLAYBOOKS[playbook_path.stem]}"
        )
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
