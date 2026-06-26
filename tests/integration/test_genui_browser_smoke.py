import json
import time
import urllib.request
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.browser]


LOCAL_SERVER_TIMEOUT_SECONDS = 5.0


def _surface_config() -> dict:
    return {
        "contract": "genui_surface",
        "surface_id": "browser-workspace",
        "project_id": "browser-ad",
        "pipeline_type": "ad-video",
        "stage": "proposal",
        "gate": "G-2",
        "mode": "gate_workspace",
        "title": "Browser Workspace",
        "ag_ui": {
            "thread_id": "browser-ad",
            "run_id": "browser-workspace",
        },
        "media_refs": [],
        "artifact_refs": [],
        "trace_refs": [
            {
                "id": "boundary",
                "label": "Agent boundary",
                "source": "AGENT_GUIDE.md",
                "summary": "The server writes only ui_surface_response.",
            }
        ],
        "blocks": [
            {
                "id": "runtime",
                "type": "RuntimeComparison",
                "title": "Runtime",
                "options": [
                    {"id": "remotion", "label": "Remotion", "recommended": True},
                    {"id": "hyperframes", "label": "HyperFrames"},
                ],
            },
            {
                "id": "trace",
                "type": "ArtifactTracePanel",
                "title": "Trace",
                "trace_ref_ids": ["boundary"],
            },
            {
                "id": "approval",
                "type": "ApprovalChecklist",
                "title": "Approval",
                "items": [
                    {
                        "id": "reviewed",
                        "label": "I reviewed this workspace.",
                        "required": True,
                    }
                ],
            },
        ],
        "actions": [
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
    base_url = url.rstrip("/")
    spec = json.loads(urllib.request.urlopen(f"{base_url}/spec.json", timeout=LOCAL_SERVER_TIMEOUT_SECONDS).read().decode("utf-8"))
    payload = json.dumps(
        {
            "action": "approve",
            "nonce": spec["metadata"]["submit_nonce"],
            "values": {"runtime.selection": "remotion", "approval.reviewed": True},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/submit",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Origin": base_url},
    )
    try:
        urllib.request.urlopen(request, timeout=LOCAL_SERVER_TIMEOUT_SECONDS).close()
    except OSError:
        pass


def _shutdown_session_if_needed(url: str, response_path: Path) -> None:
    if response_path.exists():
        return
    base_url = url.rstrip("/")
    spec = json.loads(urllib.request.urlopen(f"{base_url}/spec.json", timeout=LOCAL_SERVER_TIMEOUT_SECONDS).read().decode("utf-8"))
    payload = json.dumps(
        {
            "action": "abort",
            "nonce": spec["metadata"]["submit_nonce"],
            "values": {},
            "issues": [],
            "interaction_evidence": {
                "media_opened": [],
                "timeline_inspected": [],
                "seconds_watched": 0,
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/submit",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Origin": base_url},
    )
    try:
        urllib.request.urlopen(request, timeout=LOCAL_SERVER_TIMEOUT_SECONDS).close()
    except OSError:
        pass


def test_genui_surface_browser_click_writes_surface_response_and_events(tmp_path: Path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from tools.interaction.genui_surface import GenUISurface

    result = GenUISurface().execute(
        {
            "project_dir": str(tmp_path / "projects" / "browser-ad"),
            "config": _surface_config(),
            "mode": "serve",
        }
    )
    assert result.success, result.error

    response_path = Path(result.data["response_path"])
    url = result.data["url"]
    events_text = urllib.request.urlopen(f"{url.rstrip('/')}/events", timeout=LOCAL_SERVER_TIMEOUT_SECONDS).read().decode("utf-8")
    assert "RUN_STARTED" in events_text
    assert "STATE_SNAPSHOT" in events_text

    with playwright_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            _shutdown_if_needed(url, response_path)
            pytest.skip(f"Chromium unavailable for GenUI compatibility browser regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            page.get_by_label("I reviewed this workspace.").check()
            page.get_by_role("button", name="Approve").click()
            page.wait_for_function(
                "(path) => document.querySelector('#status')?.textContent.includes(path)",
                arg=str(response_path),
                timeout=3000,
            )
        finally:
            browser.close()
            _shutdown_if_needed(url, response_path)

    response = _wait_for_response(response_path)
    assert response["contract"] == "genui_surface_response"
    assert response["action"] == "approve"
    assert response["surface_id"] == "browser-workspace"
    assert response["values"]["runtime.selection"] == "remotion"
    assert response["values"]["approval.reviewed"] is True
    assert response["approval_attestations"] == [
        {
            "id": "reviewed",
            "label": "I reviewed this workspace.",
            "approved": True,
        }
    ]
    assert response["event_summary"]["event_count"] >= 1


def test_genui_session_browser_gate_choices_and_fields_write_session_response(tmp_path: Path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from tools.interaction.genui_session import GenUISession

    project_dir = tmp_path / "projects" / "browser-session-gate"
    result = GenUISession().execute(
        {
            "project_dir": str(project_dir),
            "interaction_request": {
                "request_id": "proposal-options",
                "project_id": "browser-session-gate",
                "pipeline_type": "ad-video",
                "stage": "proposal",
                "gate": "proposal_lock",
                "title": "Lock proposal options",
                "prompt": "Choose the runtime and capture structured approval notes.",
                "interaction_kind": "option_comparison",
                "capabilities_needed": [
                    "side_by_side_comparison",
                    "multi_axis_selection",
                    "structured_revision_capture",
                ],
                "selection_field_id": "selected_runtime",
                "selection_label": "Render runtime",
                "selection_binding": {
                    "artifact": "production_proposal",
                    "path": "render_runtime_selection.selected_runtime",
                },
                "choices": [
                    {"value": "remotion", "label": "Remotion", "recommended": True},
                    {"value": "hyperframes", "label": "HyperFrames"},
                    {"value": "ffmpeg", "label": "FFmpeg"},
                ],
                "fields": [
                    {
                        "id": "approval_notes",
                        "label": "Approval notes",
                        "type": "textarea",
                        "binding": {
                            "artifact": "production_proposal",
                            "path": "human_feedback.approval_notes",
                        },
                    }
                ],
            },
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
            _shutdown_session_if_needed(url, response_path)
            pytest.skip(f"Chromium unavailable for GenUI gate regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            page.get_by_label("HyperFrames").check()
            page.get_by_label("Approval notes").fill("Use the timeline-driven runtime for this cut.")
            page.get_by_role("button", name="Request revisions").click()
            page.wait_for_function(
                "(path) => document.querySelector('#status')?.textContent.includes(path)",
                arg=str(response_path),
                timeout=3000,
            )
        finally:
            browser.close()
            _shutdown_session_if_needed(url, response_path)

    response = _wait_for_response(response_path)
    assert response["contract"] == "genui_session_response"
    assert response["action"] == "revise"
    assert response["values"]["selected_runtime"] == "hyperframes"
    assert response["values"]["approval_notes"] == "Use the timeline-driven runtime for this cut."
    assert response["selected_refs"] == ["hyperframes"]
    assert {
        (patch["artifact"], patch["path"], patch["value"])
        for patch in response["revision_patches"]
    } == {
        ("production_proposal", "render_runtime_selection.selected_runtime", "hyperframes"),
        ("production_proposal", "human_feedback.approval_notes", "Use the timeline-driven runtime for this cut."),
    }


def test_genui_session_browser_media_review_writes_session_response(tmp_path: Path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from tools.interaction.genui_session import GenUISession

    project_dir = tmp_path / "projects" / "browser-session-ad"
    renders_dir = project_dir / "renders"
    renders_dir.mkdir(parents=True)
    (renders_dir / "sample.png").write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360f8cf00000004000301a0f4a8"
            "0000000049454e44ae426082"
        )
    )
    result = GenUISession().execute(
        {
            "project_dir": str(project_dir),
            "interaction_request": {
                "request_id": "sample-review",
                "project_id": "browser-session-ad",
                "pipeline_type": "ad-video",
                "stage": "assets",
                "gate": "sample_review",
                "title": "Review sample media",
                "prompt": "Review the sample image and capture exact revisions.",
                "interaction_kind": "media_review",
                "capabilities_needed": ["media_review", "structured_revision_capture"],
                "media_items": [
                    {
                        "id": "sample_clip",
                        "title": "Sample image",
                        "kind": "image",
                        "path": "/media/renders/sample.png",
                    }
                ],
            },
            "mode": "serve",
        }
    )
    assert result.success, result.error

    response_path = Path(result.data["response_path"])
    url = result.data["url"]
    events_text = urllib.request.urlopen(f"{url.rstrip('/')}/events", timeout=LOCAL_SERVER_TIMEOUT_SECONDS).read().decode("utf-8")
    assert "RUN_STARTED" in events_text
    assert "STATE_SNAPSHOT" in events_text

    with playwright_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            _shutdown_session_if_needed(url, response_path)
            pytest.skip(f"Chromium unavailable for GenUI browser regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            assert page.locator("#status").get_attribute("aria-live") == "polite"
            assert page.get_by_role("button", name="Set range start").count() == 1
            assert page.get_by_role("button", name="Set range end").count() == 1
            page.get_by_role("button", name="Mark opened").click()
            page.get_by_role("button", name="Mark timeline checked").click()
            page.get_by_label("Timestamp seconds").fill("1.4")
            page.get_by_label("Range start seconds").fill("1.1")
            page.get_by_label("Range end seconds").fill("2.0")
            page.get_by_label("Region x").fill("0.42")
            page.get_by_label("Region y").fill("0.22")
            page.get_by_label("Region width").fill("0.2")
            page.get_by_label("Region height").fill("0.16")
            page.get_by_label("Annotation").fill("Logo reflection changes shape.")
            page.get_by_role("button", name="Add annotation").click()
            page.locator(".om-session-issues textarea").fill("Regenerate the first shot with stable product reflection.")
            page.get_by_label("Issue status").select_option("needs_recheck")
            page.get_by_role("button", name="Add issue").click()
            page.get_by_role("button", name="Request revisions").click()
            page.wait_for_function(
                "(path) => document.querySelector('#status')?.textContent.includes(path)",
                arg=str(response_path),
                timeout=3000,
            )
        finally:
            browser.close()
            _shutdown_session_if_needed(url, response_path)

    response = _wait_for_response(response_path)
    assert response["contract"] == "genui_session_response"
    assert response["action"] == "revise"
    assert response["session_id"] == "sample-review"
    assert response["annotations"][0]["target_ref"] == "sample_clip"
    assert response["annotations"][0]["timestamp_seconds"] == 1.4
    assert response["annotations"][0]["time_range"] == {"start_seconds": 1.1, "end_seconds": 2.0}
    assert response["annotations"][0]["region"] == {"x": 0.42, "y": 0.22, "width": 0.2, "height": 0.16}
    assert response["issues"][0]["target_ref"] == "sample_clip"
    assert response["issues"][0]["status"] == "needs_recheck"
    assert response["interaction_evidence"]["media_opened"] == ["sample_clip"]
    assert response["interaction_evidence"]["timeline_inspected"] == ["sample_clip"]
    assert response["event_summary"]["event_count"] >= 1


def test_genui_session_browser_media_review_defaults_new_issue_to_open(tmp_path: Path):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from tools.interaction.genui_session import GenUISession

    project_dir = tmp_path / "projects" / "browser-session-default-issue"
    renders_dir = project_dir / "renders"
    renders_dir.mkdir(parents=True)
    (renders_dir / "sample.png").write_bytes(
        bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d49444154789c6360f8cf00000004000301a0f4a8"
            "0000000049454e44ae426082"
        )
    )
    result = GenUISession().execute(
        {
            "project_dir": str(project_dir),
            "interaction_request": {
                "request_id": "sample-review-default-issue",
                "project_id": "browser-session-default-issue",
                "pipeline_type": "ad-video",
                "stage": "assets",
                "gate": "sample_review",
                "title": "Review sample media",
                "prompt": "Review the sample image and capture exact revisions.",
                "interaction_kind": "media_review",
                "capabilities_needed": ["media_review", "structured_revision_capture"],
                "media_items": [
                    {
                        "id": "sample_clip",
                        "title": "Sample image",
                        "kind": "image",
                        "path": "/media/renders/sample.png",
                    }
                ],
            },
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
            _shutdown_session_if_needed(url, response_path)
            pytest.skip(f"Chromium unavailable for GenUI issue-status regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            page.get_by_role("button", name="Mark opened").click()
            page.get_by_role("button", name="Mark timeline checked").click()
            page.get_by_label("Annotation").fill("Logo reflection changes shape.")
            page.get_by_role("button", name="Add annotation").click()
            page.get_by_label("Requested change").fill("Regenerate the first shot with stable product reflection.")
            page.get_by_role("button", name="Add issue").click()
            page.get_by_role("button", name="Request revisions").click()
            page.wait_for_function(
                "(path) => document.querySelector('#status')?.textContent.includes(path)",
                arg=str(response_path),
                timeout=3000,
            )
        finally:
            browser.close()
            _shutdown_session_if_needed(url, response_path)

    response = _wait_for_response(response_path)
    assert response["issues"][0]["status"] == "open"


@pytest.mark.parametrize(
    ("interaction_kind", "heading", "expected_text"),
    [
        ("project_cockpit", "Project cockpit", "Read-only overview"),
        ("background_status", "Background status", "Trace Links"),
    ],
)
def test_genui_session_browser_read_only_status_modes_render_without_actions(
    tmp_path: Path,
    interaction_kind: str,
    heading: str,
    expected_text: str,
):
    playwright_api = pytest.importorskip("playwright.sync_api")
    from lib.genui import cleanup_server
    from tools.interaction.genui_session import GenUISession

    project_dir = tmp_path / "projects" / f"browser-session-{interaction_kind}"
    result = GenUISession().execute(
        {
            "project_dir": str(project_dir),
            "interaction_request": {
                "request_id": f"status-{interaction_kind}",
                "project_id": f"browser-session-{interaction_kind}",
                "pipeline_type": "ad-video",
                "stage": "assets",
                "gate": "status",
                "title": heading,
                "prompt": "Inspect current project status without advancing the pipeline.",
                "interaction_kind": interaction_kind,
                "capabilities_needed": ["status_timeline", "artifact_trace"],
            },
            "mode": "serve",
        }
    )
    assert result.success, result.error

    response_path = Path(result.data["response_path"])
    url = result.data["url"]
    state_path = Path(result.data["config_path"]).with_name("server.json")

    with playwright_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=True)
        except Exception as exc:
            cleanup_server(state_path)
            pytest.skip(f"Chromium unavailable for GenUI status regression: {exc}")

        try:
            page = browser.new_page()
            page.goto(url)
            page.locator("h2", has_text=heading).wait_for(timeout=3000)
            assert page.get_by_text(expected_text).count() >= 1
            assert page.get_by_role("button", name="Approve").count() == 0
            assert page.get_by_role("button", name="Request revisions").count() == 0
            assert page.get_by_role("button", name="Abort").count() == 0
        finally:
            browser.close()
            cleanup_server(state_path)

    assert not response_path.exists()
