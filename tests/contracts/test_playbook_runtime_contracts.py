"""Runtime contracts for style playbooks.

Schema validation alone is not enough: renderers and validators consume the
same YAML fields at runtime, including custom playbooks generated into
styles/custom/.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import lib.playbook_generator as playbook_generator
import styles.playbook_loader as playbook_loader
from styles.playbook_loader import (
    list_playbooks,
    load_playbook,
    validate_playbook,
    validate_accessibility,
    validate_palette,
)


def test_all_shipped_playbooks_pass_runtime_design_intelligence() -> None:
    for name in list_playbooks():
        playbook = load_playbook(name)

        palette_issues = validate_palette(playbook)
        assert isinstance(palette_issues, list)

        accessibility = validate_accessibility(playbook)
        assert "pass" in accessibility
        assert "issues" in accessibility


def test_accessibility_report_does_not_duplicate_issue_messages() -> None:
    accessibility = validate_accessibility(load_playbook("flat-motion-graphics"))
    issue_keys = [
        (issue.get("category"), issue.get("severity"), issue.get("message"))
        for issue in accessibility["issues"]
    ]

    assert issue_keys == list(dict.fromkeys(issue_keys))


def test_colorblind_safe_playbooks_have_no_color_blind_warnings() -> None:
    for name in list_playbooks():
        playbook = load_playbook(name)
        if not playbook.get("color_rules", {}).get("colorblind_safe"):
            continue

        accessibility = validate_accessibility(playbook)
        color_blind_warnings = [
            issue for issue in accessibility["issues"]
            if issue.get("category") == "color_blind"
        ]
        assert color_blind_warnings == [], name


def test_loader_discovers_custom_playbooks(tmp_path: Path) -> None:
    base = load_playbook("clean-professional")
    base["identity"]["name"] = "Acme Custom"

    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    (custom_dir / "acme-custom.yaml").write_text(
        yaml.safe_dump(base, sort_keys=False),
        encoding="utf-8",
    )

    assert "acme-custom" in list_playbooks(styles_dir=tmp_path)
    assert load_playbook("acme-custom", styles_dir=tmp_path)["identity"]["name"] == "Acme Custom"


def test_validate_playbook_rejects_non_strict_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_path = tmp_path / "playbook.schema.json"
    schema_path.write_text(
        """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "x-non-finite-sentinel": NaN
}
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(playbook_loader, "SCHEMA_PATH", schema_path)

    with pytest.raises(ValueError, match="strict JSON"):
        validate_playbook({"identity": {"name": "Temporary"}})


def test_save_generated_playbook_rejects_non_strict_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_path = tmp_path / "playbook.schema.json"
    schema_path.write_text(
        """
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "x-non-finite-sentinel": NaN
}
""".lstrip(),
        encoding="utf-8",
    )
    custom_dir = tmp_path / "custom"
    monkeypatch.setattr(playbook_generator, "PLAYBOOK_SCHEMA_PATH", schema_path)
    monkeypatch.setattr(playbook_generator, "CUSTOM_STYLES_DIR", custom_dir)

    with pytest.raises(ValueError, match="strict JSON"):
        playbook_generator.save_playbook(
            {"identity": {"name": "Temporary"}},
            project_name="temporary",
        )

    assert not custom_dir.exists()


def test_save_generated_playbook_rejects_python_specific_yaml_tags_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_dir = tmp_path / "custom"
    monkeypatch.setattr(playbook_generator, "CUSTOM_STYLES_DIR", custom_dir)
    playbook = load_playbook("clean-professional")
    playbook["identity"]["name"] = "Unsafe Custom"
    playbook["audio"]["not_json"] = tmp_path / "python-path"

    with pytest.raises(ValueError, match="strict JSON"):
        playbook_generator.save_playbook(playbook, project_name="unsafe-custom")

    assert not (custom_dir / "unsafe-custom.yaml").exists()
