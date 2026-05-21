import json
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from schemas.artifacts import validate_artifact
from tools.tool_registry import registry


def _sample_config(project_id: str = "demo-ad") -> dict:
    return {
        "version": "1.0",
        "config_id": "cfg-demo",
        "project_id": project_id,
        "pipeline_type": "ad-video",
        "stage": "brief_enrichment",
        "gate": "G-0",
        "title": "Creative Requirements Worksheet",
        "sections": [
            {
                "id": "identity",
                "title": "Identity",
                "description": "Confirm the product identity.",
                "fields": [
                    {
                        "id": "product_model",
                        "label": "Product/model",
                        "type": "text",
                        "required": True,
                        "default": "OPPO Find X9 Pro",
                        "help_text": "<script>alert('unsafe')</script>",
                        "binding": {
                            "artifact": "enriched_brief",
                            "path": "creative_requirements.product_model.value",
                        },
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
                    {
                        "id": "derivatives",
                        "label": "Derivative variants",
                        "type": "multiselect",
                        "choices": [
                            {"value": "9:16", "label": "9:16 vertical"},
                            {"value": "1:1", "label": "1:1 square"},
                        ],
                    },
                ],
            }
        ],
        "submit_actions": [
            {"id": "approve", "label": "Approve", "kind": "approve", "recommended": True}
        ],
    }


def test_write_form_bundle_materializes_config_html_and_response_path(tmp_path: Path):
    from lib.genui import write_form_bundle

    project_dir = tmp_path / "projects" / "demo-ad"
    bundle = write_form_bundle(project_dir, _sample_config())

    assert bundle.config_path.exists()
    assert bundle.html_path.exists()
    assert bundle.response_path.parent.exists()
    assert not bundle.response_path.exists()

    validate_artifact("ui_form_config", bundle.config)
    html = bundle.html_path.read_text()
    assert "Creative Requirements Worksheet" in html
    assert "<script>alert('unsafe')</script>" not in html
    assert "&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in html


def test_write_form_bundle_removes_stale_response_for_regenerated_config(tmp_path: Path):
    from lib.genui import write_form_bundle

    project_dir = tmp_path / "projects" / "demo-ad"
    first_bundle = write_form_bundle(project_dir, _sample_config())
    first_bundle.response_path.write_text('{"action":"approve"}\n')

    regenerated_bundle = write_form_bundle(project_dir, _sample_config())

    assert regenerated_bundle.response_path == first_bundle.response_path
    assert not regenerated_bundle.response_path.exists()


def test_render_form_html_does_not_submit_info_card_fields():
    from lib.genui import render_form_html

    config = _sample_config()
    config["sections"][0]["fields"].insert(
        0,
        {
            "id": "context_note",
            "label": "Context",
            "type": "info_card",
            "help_text": "Read this before approving.",
        },
    )

    html = render_form_html(config)
    fields_match = re.search(r"const GENUI_FIELDS = (.*?);", html)
    assert fields_match is not None
    submitted_fields = json.loads(fields_match.group(1))

    assert "info-card" in html
    assert submitted_fields == [
        {"id": "product_model", "type": "text"},
        {"id": "visual_approach", "type": "radio"},
        {"id": "derivatives", "type": "multiselect"},
    ]


def test_render_form_html_preselects_recommended_radio_when_default_missing():
    from lib.genui import render_form_html

    html = render_form_html(_sample_config())

    assert 'value="cinematic" checked' in html
    assert 'value="animated" checked' not in html


def test_render_form_html_binds_action_buttons_without_inline_onclick():
    from lib.genui import render_form_html

    html = render_form_html(_sample_config(), submit_url="/submit")

    assert "onclick=" not in html
    assert 'data-action-kind="approve"' in html
    assert "addEventListener('click'" in html
    assert 'aria-live="polite"' in html
    assert 'tabindex="-1"' in html
    assert "result.response_path" in html


def test_response_payload_preserves_browser_submission_events():
    from lib.genui import response_payload_from_submission

    response = response_payload_from_submission(
        _sample_config(),
        {
            "action": "approve",
            "values": {
                "product_model": "OPPO Find X9 Pro",
                "visual_approach": "cinematic",
                "derivatives": ["9:16"],
            },
            "browser_events": [
                {
                    "type": "action_click",
                    "action": "approve",
                    "field_count": 3,
                    "timestamp": "2026-05-21T00:00:00.000Z",
                }
            ],
        },
    )

    assert response["browser_events"] == [
        {
            "type": "action_click",
            "action": "approve",
            "field_count": 3,
            "timestamp": "2026-05-21T00:00:00.000Z",
        }
    ]


def test_project_path_containment_rejects_parent_escape(tmp_path: Path):
    from lib.genui import resolve_project_path

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    with pytest.raises(ValueError, match="outside project directory"):
        resolve_project_path(project_dir, "../escape.json")


def test_response_payload_rejects_unconfigured_submit_action():
    from lib.genui import response_payload_from_submission

    with pytest.raises(ValueError, match="not configured"):
        response_payload_from_submission(
            _sample_config(),
            {"action": "abort", "values": {"product_model": "OPPO Find X9 Pro"}},
        )


def test_response_payload_rejects_missing_required_value():
    from lib.genui import response_payload_from_submission

    with pytest.raises(ValueError, match="product_model"):
        response_payload_from_submission(
            _sample_config(),
            {"action": "approve", "values": {"product_model": ""}},
        )


def test_response_payload_allows_abort_with_missing_required_values():
    from lib.genui import response_payload_from_submission

    config = _sample_config()
    config["sections"][0]["fields"].append(
        {
            "id": "final_approval",
            "label": "Final approval",
            "type": "approval",
            "required": True,
        }
    )
    config["submit_actions"].append({"id": "abort", "label": "Abort", "kind": "abort"})

    response = response_payload_from_submission(
        config,
        {
            "action": "abort",
            "values": {
                "product_model": "",
                "visual_approach": "",
                "derivatives": [],
                "final_approval": False,
            },
        },
    )

    assert response["action"] == "abort"
    assert response["values"]["final_approval"] is False


def test_response_payload_rejects_unconfigured_values():
    from lib.genui import response_payload_from_submission

    with pytest.raises(ValueError, match="not configured"):
        response_payload_from_submission(
            _sample_config(),
            {
                "action": "approve",
                "values": {
                    "product_model": "OPPO Find X9 Pro",
                    "visual_approach": "cinematic",
                    "internal_override": "write enriched_brief directly",
                },
            },
        )


def test_genui_form_tool_prepare_mode_returns_reviewable_paths(tmp_path: Path):
    from tools.interaction.genui_form import GenUIForm

    project_dir = tmp_path / "projects" / "demo-ad"
    result = GenUIForm().execute(
        {
            "project_dir": str(project_dir),
            "config": _sample_config(project_id="demo-ad"),
            "mode": "prepare",
        }
    )

    assert result.success, result.error
    assert result.data["server_state"] == "prepared"
    assert result.data["url"] is None
    assert Path(result.data["config_path"]).exists()
    html_path = Path(result.data["html_path"])
    assert html_path.exists()
    html = html_path.read_text()
    assert "Preview only" in html
    assert "const SUBMIT_URL = null;" in html
    assert "disabled" in html
    assert result.data["response_path"].endswith("response.json")
    assert "enriched_brief" not in [Path(p).name for p in result.artifacts]


def test_genui_form_tool_serve_mode_reports_port_conflict(tmp_path: Path):
    from tools.interaction.genui_form import GenUIForm

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        port = int(sock.getsockname()[1])
        result = GenUIForm().execute(
            {
                "project_dir": str(tmp_path / "projects" / "demo-ad"),
                "config": _sample_config(project_id="demo-ad"),
                "mode": "serve",
                "port": port,
            }
        )

    assert not result.success
    assert "ready" in (result.error or "")


def test_genui_form_serve_mode_static_preview_posts_to_live_server(tmp_path: Path):
    from tools.interaction.genui_form import GenUIForm

    result = GenUIForm().execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "config": _sample_config(project_id="demo-ad"),
            "mode": "serve",
        }
    )

    assert result.success, result.error
    url = result.data["url"].rstrip("/")
    submit_url = f"{url}/submit"
    html = Path(result.data["html_path"]).read_text()

    assert f'const SUBMIT_URL = "{submit_url}";' in html

    preflight = urllib.request.Request(
        submit_url,
        method="OPTIONS",
        headers={
            "Origin": "null",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    with urllib.request.urlopen(preflight, timeout=2.0) as response:
        assert response.status == 204
        assert response.headers["Access-Control-Allow-Origin"] == "null"

    same_origin_preflight = urllib.request.Request(
        submit_url,
        method="OPTIONS",
        headers={
            "Origin": url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    with urllib.request.urlopen(same_origin_preflight, timeout=2.0) as response:
        assert response.status == 204
        assert response.headers["Access-Control-Allow-Origin"] == url

    payload = (
        b'{"action":"approve","values":{'
        b'"product_model":"OPPO Find X9 Pro",'
        b'"visual_approach":"cinematic",'
        b'"derivatives":["9:16"]'
        b"}}"
    )
    request = urllib.request.Request(
        submit_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json", "Origin": "null"},
    )
    with urllib.request.urlopen(request, timeout=2.0) as response:
        assert response.status == 200
        assert response.headers["Access-Control-Allow-Origin"] == "null"

    response_payload = json.loads(Path(result.data["response_path"]).read_text())
    assert response_payload["action"] == "approve"
    assert response_payload["values"]["visual_approach"] == "cinematic"


def test_genui_form_serve_mode_rejects_untrusted_browser_origin(tmp_path: Path):
    from tools.interaction.genui_form import GenUIForm

    result = GenUIForm().execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "config": _sample_config(project_id="demo-ad"),
            "mode": "serve",
        }
    )

    assert result.success, result.error
    submit_url = f"{result.data['url'].rstrip('/')}/submit"
    response_path = Path(result.data["response_path"])
    payload = (
        b'{"action":"approve","values":{'
        b'"product_model":"OPPO Find X9 Pro",'
        b'"visual_approach":"cinematic",'
        b'"derivatives":["9:16"]'
        b"}}"
    )

    try:
        preflight = urllib.request.Request(
            submit_url,
            method="OPTIONS",
            headers={
                "Origin": "https://example.test",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        with pytest.raises(urllib.error.HTTPError) as preflight_error:
            urllib.request.urlopen(preflight, timeout=2.0)
        assert preflight_error.value.code == 403

        malformed_preflight = urllib.request.Request(
            submit_url,
            method="OPTIONS",
            headers={
                "Origin": "http://localhost:not-a-port",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        with pytest.raises(urllib.error.HTTPError) as malformed_preflight_error:
            urllib.request.urlopen(malformed_preflight, timeout=2.0)
        assert malformed_preflight_error.value.code == 403

        request = urllib.request.Request(
            submit_url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json", "Origin": "https://example.test"},
        )
        with pytest.raises(urllib.error.HTTPError) as post_error:
            urllib.request.urlopen(request, timeout=2.0)
        assert post_error.value.code == 403
        assert not response_path.exists()
    finally:
        if not response_path.exists():
            shutdown_request = urllib.request.Request(
                submit_url,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json", "Origin": "null"},
            )
            try:
                with urllib.request.urlopen(shutdown_request, timeout=2.0) as response:
                    assert response.status == 200
            except OSError:
                pass


def test_genui_form_server_stops_after_successful_submission(tmp_path: Path):
    from tools.interaction.genui_form import GenUIForm

    result = GenUIForm().execute(
        {
            "project_dir": str(tmp_path / "projects" / "demo-ad"),
            "config": _sample_config(project_id="demo-ad"),
            "mode": "serve",
        }
    )

    assert result.success, result.error
    url = result.data["url"]
    submit_url = f"{url.rstrip('/')}/submit"
    payload = (
        b'{"action":"approve","values":{'
        b'"product_model":"OPPO Find X9 Pro",'
        b'"visual_approach":"cinematic",'
        b'"derivatives":["9:16"]'
        b"}}"
    )
    request = urllib.request.Request(
        submit_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(request, timeout=2.0) as response:
        assert response.status == 200

    deadline = time.monotonic() + 3.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.2).close()
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
            break
        time.sleep(0.05)

    assert last_error is not None, "GenUI server still accepted requests after submission"


def test_tool_registry_discovers_genui_form():
    registry.clear()
    registry.discover()

    tool = registry.get("genui_form")
    assert tool is not None
    info = tool.get_info()
    assert info["capability"] == "interaction"
    assert info["provider"] == "openmontage"
    assert info["runtime"] == "local"
