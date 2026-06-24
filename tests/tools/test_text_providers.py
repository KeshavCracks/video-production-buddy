from __future__ import annotations

import sys
from types import SimpleNamespace

import jsonschema
import pytest

from tools.text.minimax_chat import MinimaxChat
from tools.text.qwen_chat import QwenChat


def test_qwen_chat_success_payload_matches_output_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_path = "projects/test-text/artifacts/qwen-response.md"
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "Polished script copy."}}],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 4,
                    "total_tokens": 15,
                },
            }

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse()

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=fake_post))

    output_properties = QwenChat.output_schema["properties"]
    assert {
        "provider",
        "model",
        "model_name",
        "text",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "output",
        "output_path",
    } <= set(output_properties)

    result = QwenChat().execute(
        {
            "prompt": "Polish this line.",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data == {
        "provider": "bailian",
        "model": "qwen3.7-plus",
        "model_name": "Qwen3.7 Plus",
        "text": "Polished script copy.",
        "prompt_tokens": 11,
        "completion_tokens": 4,
        "total_tokens": 15,
        "output": output_path,
        "output_path": output_path,
    }
    assert (tmp_path / output_path).read_text(encoding="utf-8") == result.data["text"]
    assert result.artifacts == [output_path]
    assert len(calls) == 1
    jsonschema.validate(instance=result.data, schema=QwenChat.output_schema)


def test_minimax_chat_success_payload_matches_output_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_path = "projects/test-text/artifacts/minimax-response.md"
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "base_resp": {"status_code": 0, "status_msg": "success"},
                "choices": [{"message": {"content": "Concise summary."}}],
                "usage": {
                    "prompt_tokens": 9,
                    "completion_tokens": 3,
                    "total_tokens": 12,
                },
            }

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse()

    monkeypatch.setenv("MINIMAX_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=fake_post))

    output_properties = MinimaxChat.output_schema["properties"]
    assert {
        "provider",
        "model",
        "model_name",
        "text",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "output",
        "output_path",
    } <= set(output_properties)

    result = MinimaxChat().execute(
        {
            "prompt": "Summarize this line.",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data == {
        "provider": "minimax",
        "model": "MiniMax-M3",
        "model_name": "MiniMax-M3",
        "text": "Concise summary.",
        "prompt_tokens": 9,
        "completion_tokens": 3,
        "total_tokens": 12,
        "output": output_path,
        "output_path": output_path,
    }
    assert (tmp_path / output_path).read_text(encoding="utf-8") == result.data["text"]
    assert result.artifacts == [output_path]
    assert len(calls) == 1
    jsonschema.validate(instance=result.data, schema=MinimaxChat.output_schema)


@pytest.mark.parametrize(
    ("tool_cls", "env_name"),
    [
        (QwenChat, "DASHSCOPE_API_KEY"),
        (MinimaxChat, "MINIMAX_API_KEY"),
    ],
)
@pytest.mark.parametrize(
    "output_path",
    [
        "response.md",
        "projects/test-text/tmp/response.md",
        "/tmp/response.md",
        "projects/test-text/artifacts",
    ],
)
def test_text_providers_reject_non_project_sidecar_output_paths_before_api_call(
    tool_cls,
    env_name: str,
    output_path: str,
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(env_name, "test-key")
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("text provider should reject output_path before API call")

    monkeypatch.setitem(sys.modules, "requests", SimpleNamespace(post=fake_post))

    result = tool_cls().execute(
        {
            "prompt": "Write one sentence.",
            "output_path": output_path,
        }
    )

    assert result.success is False
    assert calls == []
    assert not (tmp_path / output_path).exists()
    assert "projects/<project-name>/" in (result.error or "")
