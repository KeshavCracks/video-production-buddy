import jsonschema
import pytest

from tools.audio.qwen_asr import QwenASR


def test_qwen_asr_schema_accepts_local_audio_path_without_url():
    jsonschema.validate(
        instance={"audio_path": "/tmp/local.wav"},
        schema=QwenASR.input_schema,
    )


def test_qwen_asr_schema_requires_some_audio_source():
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"model": "qwen3-asr-flash"},
            schema=QwenASR.input_schema,
        )


def test_qwen_asr_idempotency_includes_local_audio_path():
    assert "audio_path" in QwenASR.idempotency_key_fields


@pytest.mark.parametrize("output_path", ["transcript.txt", "/tmp/transcript.txt"])
def test_qwen_asr_rejects_non_project_output_path_before_api_key(
    output_path, monkeypatch
):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    result = QwenASR().execute(
        {
            "audio_url": "https://example.test/speech.wav",
            "output_path": output_path,
        }
    )

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")


def test_qwen_asr_rejects_non_project_output_path_before_network(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("network should not be called for non-project output_path")

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr("requests.post", fake_post)

    result = QwenASR().execute(
        {
            "audio_url": "https://example.test/speech.wav",
            "output_path": "transcript.txt",
        }
    )

    assert result.success is False
    assert "output_path" in (result.error or "")
    assert "projects/<project-name>/" in (result.error or "")
    assert calls == []


def test_qwen_asr_writes_transcript_to_project_sidecar_path(tmp_path, monkeypatch):
    output_path = "projects/test-audio/artifacts/transcript.txt"
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": {
                    "choices": [
                        {
                            "message": {
                                "content": [{"text": "hello world"}],
                                "annotations": [
                                    {"type": "audio_info", "language": "en"}
                                ],
                            }
                        }
                    ]
                }
            }

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr("requests.post", fake_post)

    result = QwenASR().execute(
        {
            "audio_url": "https://example.test/speech.wav",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert (tmp_path / output_path).read_text(encoding="utf-8") == "hello world"
    assert result.data["output"] == output_path
    assert result.artifacts == [output_path]
    assert len(calls) == 1


def test_qwen_asr_success_payload_matches_output_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_path = "projects/test-audio/artifacts/transcript.txt"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": {
                    "choices": [
                        {
                            "message": {
                                "content": [{"text": "hello world"}],
                                "annotations": [
                                    {"type": "audio_info", "language": "en"}
                                ],
                            }
                        }
                    ]
                }
            }

    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-key")
    monkeypatch.setattr("requests.post", lambda *args, **kwargs: FakeResponse())

    output_properties = QwenASR.output_schema["properties"]
    assert {
        "provider",
        "model",
        "transcript",
        "language",
        "output",
        "output_path",
    } <= set(output_properties)

    result = QwenASR().execute(
        {
            "audio_url": "https://example.test/speech.wav",
            "output_path": output_path,
        }
    )

    assert result.success is True
    assert result.data == {
        "provider": "bailian",
        "model": "qwen3-asr-flash",
        "transcript": "hello world",
        "language": "en",
        "output": output_path,
        "output_path": output_path,
    }
    jsonschema.validate(instance=result.data, schema=QwenASR.output_schema)
