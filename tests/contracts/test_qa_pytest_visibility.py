from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
QA_DIR = ROOT / "tests" / "qa"
SKILLS_DIR = ROOT / "skills"
TOOLS_DIR = ROOT / "tools"


def test_qa_test_files_are_visible_to_pytest() -> None:
    invisible: list[str] = []
    for path in sorted(QA_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        has_test = any(
            (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            )
            or (
                isinstance(node, ast.ClassDef)
                and node.name.startswith("Test")
            )
            for node in tree.body
        )
        if not has_test:
            invisible.append(str(path.relative_to(ROOT)))

    assert invisible == []


def test_qa_python_files_use_lf_line_endings() -> None:
    offenders: list[str] = []
    for path in sorted(QA_DIR.glob("test_*.py")):
        if b"\r\n" in path.read_bytes():
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_audio_mix_qa_defers_env_and_output_setup_until_test_execution() -> None:
    path = QA_DIR / "test_04_audio_mix.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "load_env",
        "mkdir",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_hyperframes_qa_defers_output_setup_until_test_execution() -> None:
    path = QA_DIR / "test_09_hyperframes_compose.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "mkdir",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_playbook_intelligence_qa_defers_audit_until_test_execution() -> None:
    path = QA_DIR / "test_07_playbook_intelligence.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "check",
        "check_color_blind_safety",
        "compute_type_scale",
        "generate_harmony",
        "list_playbooks",
        "load_playbook",
        "print",
        "suggest_font_pairing",
        "validate_accessibility",
        "validate_contrast",
        "validate_palette",
        "validate_type_hierarchy",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, (ast.For, ast.While, ast.Try)):
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {type(node).__name__}")
            continue
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_video_compose_qa_defers_media_work_until_test_execution() -> None:
    path = QA_DIR / "test_05_video_compose.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "VideoCompose",
        "execute",
        "ensure_audio",
        "ensure_image",
        "ensure_subtitle",
        "ensure_video",
        "ffprobe",
        "load_env",
        "makedirs",
        "print",
        "run",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, (ast.For, ast.While, ast.Try)):
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {type(node).__name__}")
            continue
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_video_stitch_qa_defers_media_work_until_test_execution() -> None:
    path = QA_DIR / "test_06_video_stitch.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "VideoStitch",
        "execute",
        "ensure_video",
        "load_env",
        "makedirs",
        "print",
        "run",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, (ast.For, ast.While, ast.Try)):
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {type(node).__name__}")
            continue
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_end_to_end_qa_defers_pipeline_work_until_test_execution() -> None:
    path = QA_DIR / "test_08_end_to_end.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    side_effect_calls = {
        "AudioMixer",
        "CostTracker",
        "VideoCompose",
        "approve_tool",
        "check",
        "ensure_audio",
        "ensure_video",
        "estimate",
        "execute",
        "get_completed_stages",
        "get_next_stage",
        "load_env",
        "load_playbook",
        "makedirs",
        "print",
        "reconcile",
        "reserve",
        "rmtree",
        "run",
        "validate_accessibility",
        "validate_artifact",
        "write_checkpoint",
    }
    offenders: list[str] = []

    def call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                return func.id
            if isinstance(func, ast.Attribute):
                return func.attr
        return None

    for node in tree.body:
        if isinstance(node, (ast.For, ast.While, ast.Try, ast.With)):
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {type(node).__name__}")
            continue
        if isinstance(node, ast.Expr):
            name = call_name(node.value)
        elif isinstance(node, ast.Assign):
            name = call_name(node.value)
        else:
            name = None
        if name in side_effect_calls:
            offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")

    assert offenders == []


def test_qa_tests_do_not_prompt_gui_media_player_inspection() -> None:
    gui_prompt_patterns = ("Open in VLC", "media player")
    offenders: list[str] = []
    for path in sorted(QA_DIR.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in gui_prompt_patterns:
            if pattern in text:
                offenders.append(f"{path.relative_to(ROOT)}: {pattern}")

    assert offenders == []


def test_qa_guidance_does_not_prompt_gui_media_inspection() -> None:
    gui_prompt_patterns = (
        "media player",
        "open image",
        "then listen",
        "then view",
        "then watch",
    )
    offenders: list[str] = []
    for path in sorted(QA_DIR.rglob("*.md")):
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for pattern in gui_prompt_patterns:
            if pattern in text:
                offenders.append(f"{path.relative_to(ROOT)}: {pattern}")

    assert offenders == []


def test_qa_guidance_uses_portable_repo_paths() -> None:
    user_specific_path_patterns = (
        "c:/users/",
        "c:\\users\\",
        "/users/ishan/",
        "documents/video production buddy",
    )
    offenders: list[str] = []
    for path in sorted(QA_DIR.rglob("*.md")):
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for pattern in user_specific_path_patterns:
            if pattern in text:
                offenders.append(f"{path.relative_to(ROOT)}: {pattern}")

    assert offenders == []


def test_qa_pytest_command_examples_use_terminal_clean_invocation() -> None:
    offenders: list[str] = []
    for path in sorted(QA_DIR.rglob("*")):
        if path.suffix not in {".md", ".py"}:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "python -m pytest" not in line:
                continue
            command = " ".join(line.strip().split())
            missing: list[str] = []
            if "VPB_ALLOW_BROWSER_OPEN=0" not in command:
                missing.append("VPB_ALLOW_BROWSER_OPEN=0")
            if "PYTHONDONTWRITEBYTECODE=1" not in command:
                missing.append("PYTHONDONTWRITEBYTECODE=1")
            if " -p no:cacheprovider " not in f" {command} ":
                missing.append("-p no:cacheprovider")
            if missing:
                offenders.append(
                    f"{path.relative_to(ROOT)}:{lineno}: missing {', '.join(missing)}"
                )

    assert offenders == []


def test_qa_guidance_does_not_run_pytest_modules_as_plain_scripts() -> None:
    offenders: list[str] = []
    for path in sorted(QA_DIR.rglob("*")):
        if path.suffix not in {".md", ".py"}:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            command = " ".join(line.strip().split())
            if command.startswith("python tests/qa/test_"):
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {command}")

    assert offenders == []


def test_qa_test_modules_do_not_self_invoke_pytest_main() -> None:
    offenders: list[str] = []
    for path in sorted(QA_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "main"
                and isinstance(func.value, ast.Name)
                and func.value.id == "pytest"
            ):
                offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}: pytest.main")

    assert offenders == []


def test_tool_verification_guidance_is_terminal_safe_by_default() -> None:
    unsafe_fragments = (
        "open the returned",
        "open a local browser",
        "launch a local browser",
    )
    offenders: list[str] = []
    for path in sorted(TOOLS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name)
                    and target.id == "user_visible_verification"
                    for target in node.targets
                )
            ):
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            for item in node.value.elts:
                if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                    continue
                guidance = item.value.strip()
                normalized = " ".join(guidance.lower().split())
                if guidance.startswith(("Browse ", "Listen ", "Play ", "Watch ", "Open ")) or any(
                    fragment in normalized for fragment in unsafe_fragments
                ):
                    offenders.append(f"{path.relative_to(ROOT)}: {guidance}")

    assert offenders == []


def test_pipeline_skills_do_not_prompt_agent_driven_media_player_review() -> None:
    unsafe_phrases = (
        "browse ",
        "open in vlc",
        "open the file",
        "media player",
        "play it for the user",
        "please open and review",
        "please open this file",
        "watch it now",
    )
    offenders: list[str] = []
    for path in sorted(SKILLS_DIR.rglob("*.md")):
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for phrase in unsafe_phrases:
            if phrase in text:
                offenders.append(f"{path.relative_to(ROOT)}: {phrase}")

    assert offenders == []
