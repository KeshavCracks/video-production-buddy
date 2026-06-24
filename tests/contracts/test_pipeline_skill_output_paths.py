from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SKILLS_DIR = ROOT / "skills" / "pipelines"
CORE_SKILLS_DIR = ROOT / "skills" / "core"

OUTPUT_FIELD_ASSIGNMENT = re.compile(
    r"""["'](?P<field>output_(?:path|dir)|metadata_path)["']\s*:\s*f?["'](?P<value>[^"']+)["']"""
)
COMPOSITION_PATH_ASSIGNMENT = re.compile(
    r"""["']composition_path["']\s*:\s*f?["'](?P<value>[^"']+)["']"""
)


def test_pipeline_skill_output_examples_use_project_scoped_paths() -> None:
    offenders: list[str] = []
    for path in sorted(PIPELINE_SKILLS_DIR.rglob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for match in OUTPUT_FIELD_ASSIGNMENT.finditer(line):
                field = match.group("field")
                value = match.group("value")
                if not value.startswith("projects/"):
                    offenders.append(
                        f"{path.relative_to(ROOT)}:{lineno}: {field}={value!r}"
                    )

    assert offenders == []


def test_pipeline_skill_local_artifact_examples_do_not_use_root_placeholders() -> None:
    bare_project_placeholder = re.compile(r"(?<!projects/)<project>/")
    offenders: list[str] = []
    for path in sorted(PIPELINE_SKILLS_DIR.rglob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "path/to/" in line or bare_project_placeholder.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")

    assert offenders == []


def test_core_remotion_composition_validator_example_uses_project_artifact_path() -> None:
    remotion_skill = CORE_SKILLS_DIR / "remotion.md"
    offenders: list[str] = []
    for lineno, line in enumerate(remotion_skill.read_text(encoding="utf-8").splitlines(), start=1):
        for match in COMPOSITION_PATH_ASSIGNMENT.finditer(line):
            value = match.group("value")
            if not value.startswith("projects/"):
                offenders.append(
                    f"{remotion_skill.relative_to(ROOT)}:{lineno}: composition_path={value!r}"
                )

    assert offenders == []
