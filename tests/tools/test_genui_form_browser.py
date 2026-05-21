import json
import time
import urllib.request
from pathlib import Path

import pytest


def _browser_config() -> dict:
    return {
        "version": "1.0",
        "config_id": "cfg-browser",
        "project_id": "browser-ad",
        "pipeline_type": "ad-video",
        "stage": "brief_enrichment",
        "gate": "G-0",
        "title": "Browser Approval",
        "sections": [
            {
                "id": "identity",
                "title": "Identity",
                "fields": [
                    {
                        "id": "product_model",
                        "label": "Product/model",
                        "type": "text",
                        "required": True,
                        "default": "OPPO Find X9 Pro",
                    },
                    {
                        "id": "visual_approach",
                        "label": "Visual approach",
                        "type": "radio",
                        "required": True,
                        "choices": [
                            {"value": "cinematic", "label": "Cinematic", "recommended": True},
                            {"value": "animated", "label": "Animated"},
                        ],
                    },
                ],
            }
        ],
        "submit_actions": [
            {"id": "approve", "label": "Approve", "kind": "approve", "recommended": True}
        ],
    }


def _wait_for_response(path: Path) -> dict:
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text())
        time.sleep(0.05)
    raise AssertionError(f"Expected GenUI response at {path}")


def _shutdown_if_needed(url: str, response_path: Path) -> None:
    if response_path.exists():
        return
    payload = (
        b'{"action":"approve","values":{'
        b'"product_model":"OPPO Find X9 Pro",'
        b'"visual_approach":"cinematic"'
        b"}}"
    )
    request = urllib.request.Request(
        f"{url.rstrip('/')}/submit",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=1.0).close()
    except OSError:
        pass


def test_genui_form_browser_click_writes_response_and_events(tmp_path: Path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from tools.interaction.genui_form import GenUIForm

    result = GenUIForm().execute(
        {
            "project_dir": str(tmp_path / "projects" / "browser-ad"),
            "config": _browser_config(),
            "mode": "serve",
        }
    )
    assert result.success, result.error

    response_path = Path(result.data["response_path"])
    url = result.data["url"]

    with playwright_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            _shutdown_if_needed(url, response_path)
            pytest.skip(f"Chromium unavailable for GenUI browser regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            page.get_by_role("button", name="Approve").click()
            page.wait_for_function(
                "(path) => document.querySelector('#status')?.textContent.includes(path)",
                str(response_path),
                timeout=3000,
            )
            page.wait_for_function(
                "() => document.activeElement?.id === 'status'",
                timeout=3000,
            )
        finally:
            browser.close()
            _shutdown_if_needed(url, response_path)

    response = _wait_for_response(response_path)
    assert response["action"] == "approve"
    assert response["values"]["visual_approach"] == "cinematic"
    assert response["browser_events"]
    assert response["browser_events"][0]["type"] == "action_click"
    assert response["browser_events"][0]["action"] == "approve"
