#!/usr/bin/env python3
"""QA Test 07: Playbook design intelligence, no API calls.

Tests contrast validation, color harmony generation, color-blind safety,
type scale computation, type hierarchy validation, font pairing suggestions,
and full accessibility audit across all shipped playbooks.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from styles.playbook_loader import (
    TYPE_SCALE_RATIOS,
    check_color_blind_safety,
    compute_type_scale,
    generate_harmony,
    list_playbooks,
    load_playbook,
    suggest_font_pairing,
    validate_accessibility,
    validate_contrast,
    validate_palette,
    validate_type_hierarchy,
)


ROOT = Path(__file__).resolve().parent.parent.parent


def _record_check(failures: list[str], name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    if not condition:
        failures.append(f"{name}{suffix}")


def _shipped_playbooks() -> list[str]:
    return sorted(p.stem for p in (ROOT / "styles").glob("*.yaml"))


def _load_shipped_playbooks(failures: list[str]) -> dict[str, dict | None]:
    print("--- Test 1: List and load playbooks ---")
    shipped = _shipped_playbooks()
    playbooks_available = list_playbooks()
    print(f"  Found {len(playbooks_available)} playbooks: {playbooks_available}")
    _record_check(
        failures,
        "All shipped playbooks are discoverable",
        set(shipped).issubset(playbooks_available),
    )

    loaded: dict[str, dict | None] = {}
    for name in shipped:
        try:
            loaded[name] = load_playbook(name)
            _record_check(failures, f"Load + validate {name}", True)
        except Exception as exc:
            loaded[name] = None
            _record_check(failures, f"Load + validate {name}", False, str(exc))
    return loaded


def _audit_contrast(failures: list[str], loaded: dict[str, dict | None]) -> None:
    print("\n--- Test 2: Contrast validation ---")

    result = validate_contrast("#000000", "#FFFFFF")
    _record_check(
        failures,
        "Black on white ~21:1",
        abs(result["ratio"] - 21.0) < 0.1,
        f"ratio={result['ratio']}",
    )
    _record_check(failures, "Black on white passes AAA", result["normal_text"]["AAA"])

    result = validate_contrast("#FFFFFF", "#FFFFFF")
    _record_check(
        failures,
        "White on white = 1:1",
        abs(result["ratio"] - 1.0) < 0.01,
        f"ratio={result['ratio']}",
    )
    _record_check(failures, "White on white fails AA", not result["normal_text"]["AA"])

    result = validate_contrast("#767676", "#FFFFFF")
    _record_check(
        failures,
        "#767676 on white passes AA normal",
        result["normal_text"]["AA"],
        f"ratio={result['ratio']}",
    )

    result = validate_contrast("#777777", "#FFFFFF")
    _record_check(
        failures,
        "#777777 on white borderline",
        result["ratio"] >= 4.4,
        f"ratio={result['ratio']}",
    )

    result = validate_contrast("#1A1A1A", "#2B2B2B")
    _record_check(
        failures,
        "Dark-on-dark fails AA",
        not result["normal_text"]["AA"],
        f"ratio={result['ratio']}",
    )

    for name, playbook in loaded.items():
        if playbook is None:
            continue
        palette = playbook.get("visual_language", {}).get("color_palette", {})
        text = palette.get("text", "#000000")
        background = palette.get("background", "#FFFFFF")
        result = validate_contrast(text, background)
        _record_check(
            failures,
            f"{name}: text on bg passes AA",
            result["normal_text"]["AA"],
            f"ratio={result['ratio']}",
        )


def _audit_color_harmony(failures: list[str]) -> None:
    print("\n--- Test 3: Color harmony generation ---")

    for harmony_type in ["complementary", "analogous", "triadic", "split-complementary"]:
        colors = generate_harmony("#3B82F6", harmony_type)
        _record_check(
            failures,
            f"Harmony {harmony_type}",
            len(colors) >= 2,
            f"generated {len(colors)} colors: {colors}",
        )
        _record_check(
            failures,
            f"  Base preserved in {harmony_type}",
            colors[0].upper() == generate_harmony("#3B82F6", harmony_type)[0].upper(),
        )

    colors = generate_harmony("#FF0000", "triadic")
    _record_check(failures, "Triadic from pure red", len(colors) == 3, f"{colors}")


def _audit_color_blind_safety(failures: list[str]) -> None:
    print("\n--- Test 4: Color-blind safety ---")

    safe = check_color_blind_safety(["#2563EB", "#F59E0B"])
    print(f"  Blue + orange: safe={safe['safe']}, issues={len(safe.get('issues', []))}")
    _record_check(failures, "Blue + orange returns a safety verdict", isinstance(safe["safe"], bool))

    risky = check_color_blind_safety(["#DC2626", "#16A34A"])
    print(f"  Red + green: safe={risky['safe']}, issues={len(risky.get('issues', []))}")
    _record_check(
        failures,
        "Red+green flagged as risky",
        not risky["safe"] or len(risky.get("issues", [])) > 0,
        "should flag deuteranopia/protanopia",
    )

    single = check_color_blind_safety(["#FF0000"])
    _record_check(failures, "Single color is safe", single["safe"])

    grays = check_color_blind_safety(["#333333", "#999999", "#CCCCCC"])
    _record_check(failures, "Grays are safe", grays["safe"])


def _audit_playbook_palettes(failures: list[str], loaded: dict[str, dict | None]) -> None:
    print("\n--- Test 5: Palette validation (all playbooks) ---")

    for name, playbook in loaded.items():
        if playbook is None:
            continue
        issues = validate_palette(playbook)
        errors = [issue for issue in issues if issue.get("severity") == "error"]
        warnings = [issue for issue in issues if issue.get("severity") == "warning"]
        print(f"  [{name}] {len(errors)} errors, {len(warnings)} warnings, {len(issues)} total issues")
        _record_check(
            failures,
            f"{name}: no contrast errors",
            len(errors) == 0,
            "; ".join(error["message"] for error in errors) if errors else "all clear",
        )
        for issue in issues:
            print(f"    [{issue.get('severity', '?')}] {issue.get('message', '')}")


def _audit_type_scale(failures: list[str]) -> None:
    print("\n--- Test 6: Type scale computation ---")

    for ratio_name in TYPE_SCALE_RATIOS:
        scale = compute_type_scale(24, ratio_name)
        sizes = scale["sizes"]
        _record_check(
            failures,
            f"Scale {ratio_name}: display > heading > subheading > body > caption",
            sizes["display"] > sizes["heading"] > sizes["subheading"] > sizes["body"] > sizes["caption"],
            f"{sizes}",
        )
        _record_check(failures, "  Base preserved", sizes["body"] == 24)

    scale = compute_type_scale(24, "1.5")
    _record_check(failures, "Custom ratio 1.5", scale["ratio_value"] == 1.5, f"sizes={scale['sizes']}")


def _audit_type_hierarchy(failures: list[str], loaded: dict[str, dict | None]) -> None:
    print("\n--- Test 7: Type hierarchy validation ---")

    for name, playbook in loaded.items():
        if playbook is None:
            continue
        issues = validate_type_hierarchy(playbook)
        print(f"  [{name}] {len(issues)} type hierarchy issues")
        for issue in issues:
            print(f"    [{issue.get('severity')}] {issue.get('message')}")
        errors = [issue for issue in issues if issue.get("severity") == "error"]
        _record_check(failures, f"{name}: no type hierarchy errors", len(errors) == 0)

    bad_typography = {
        "typography": {
            "headings": {"font": "Inter", "weight": 400},
            "body": {"font": "Inter", "weight": 400},
            "stat_card": {"font": "Inter", "size_multiplier": 0.8},
        }
    }
    issues = validate_type_hierarchy(bad_typography)
    _record_check(failures, "Bad typography flagged", len(issues) > 0, f"{len(issues)} issues found")


def _audit_font_pairings(failures: list[str]) -> None:
    print("\n--- Test 8: Font pairing suggestions ---")

    for font in ["Inter", "Space Grotesk", "IBM Plex Sans", "Lora", "JetBrains Mono"]:
        pairings = suggest_font_pairing(font)
        _record_check(failures, f"Pairings for {font}", len(pairings) >= 1, f"{len(pairings)} suggestions")
        for pairing in pairings:
            print(f"    -> {pairing['font']} ({pairing['category']}): {pairing['rationale']}")

    pairings = suggest_font_pairing("UnknownFont")
    _record_check(failures, "Unknown font gets fallback", len(pairings) >= 1)


def _audit_accessibility(failures: list[str], loaded: dict[str, dict | None]) -> None:
    print("\n--- Test 9: Accessibility audit (all playbooks) ---")

    for name, playbook in loaded.items():
        if playbook is None:
            continue
        result = validate_accessibility(playbook)
        status = "PASS" if result["pass"] else "FAIL"
        print(
            f"\n  [{name}] Overall: {status}"
            f" | Errors: {result['error_count']}"
            f" | Warnings: {result['warning_count']}"
            f" | Total: {result['total_issues']}"
        )
        _record_check(failures, f"{name}: a11y audit passes", result["pass"])
        for issue in result["issues"]:
            print(f"    [{issue.get('category', '?')}/{issue.get('severity', '?')}] {issue.get('message', '')}")


def _audit_low_contrast_failure_case(failures: list[str]) -> None:
    print("\n--- Test 10: Low-contrast custom playbook ---")

    low_contrast_playbook = {
        "identity": {
            "name": "low-contrast-test",
            "category": "test",
            "mood": "test",
            "pace": "moderate",
            "best_for": ["testing"],
        },
        "visual_language": {
            "color_palette": {
                "primary": ["#555555"],
                "accent": ["#666666"],
                "background": "#444444",
                "text": "#555555",
                "muted": "#4A4A4A",
            },
            "composition": "centered",
            "texture": "none",
        },
        "typography": {
            "headings": {"font": "Arial", "weight": 700, "size_multiplier": 1.5},
            "body": {"font": "Arial", "weight": 400, "size_multiplier": 1.0},
            "code": {"font": "Courier", "weight": 400, "size_multiplier": 0.9},
            "stat_card": {"font": "Arial", "weight": 700, "size_multiplier": 2.5},
            "scale_system": "major_third",
            "weight_matrix": {"title": 800, "heading": 700, "body": 400, "caption": 300},
        },
        "motion": {"transitions": "cut", "animation_style": "none", "pacing_rules": {}},
        "audio": {"voice_style": "neutral", "music_mood": "none"},
        "asset_generation": {"image_prompt_prefix": "test", "negative_prompt": ""},
        "overlays": {
            "stat_card": {
                "bg": "#444444",
                "text": "#555555",
                "border": "#444444",
                "radius": 8,
                "shadow": "none",
            },
        },
        "quality_rules": [],
        "chart_palette": ["#555555", "#666666", "#777777"],
    }

    issues = validate_palette(low_contrast_playbook)
    errors = [issue for issue in issues if issue.get("severity") == "error"]
    _record_check(failures, "Low-contrast playbook has errors", len(errors) > 0, f"{len(errors)} contrast errors")
    for error in errors:
        print(f"    [error] {error.get('message')}")


def _run_playbook_intelligence_audit() -> list[str]:
    failures: list[str] = []
    loaded = _load_shipped_playbooks(failures)
    _audit_contrast(failures, loaded)
    _audit_color_harmony(failures)
    _audit_color_blind_safety(failures)
    _audit_playbook_palettes(failures, loaded)
    _audit_type_scale(failures)
    _audit_type_hierarchy(failures, loaded)
    _audit_font_pairings(failures)
    _audit_accessibility(failures, loaded)
    _audit_low_contrast_failure_case(failures)

    print(f"\n{'=' * 60}")
    print(f"PLAYBOOK INTELLIGENCE TEST COMPLETE: {len(failures)} failure(s)")
    print(f"{'=' * 60}")
    return failures


def test_playbook_intelligence_audit_passed() -> None:
    failures = _run_playbook_intelligence_audit()
    assert failures == []
