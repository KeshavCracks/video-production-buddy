from __future__ import annotations

import builtins
import types

import jsonschema
import pytest

from tools.base_tool import ToolStatus
from tools.video import _shared
from tools.video.cogvideo_video import CogVideoVideo
from tools.video.hunyuan_video import HunyuanVideo
from tools.video.ltx_video_local import LTXVideoLocal
from tools.video._shared import upload_image_heygen
from tools.video.wan_video import WanVideo


class _FakeHeyGenUploadResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "data": {
                "upload_url": "https://upload.example.test/frame",
                "url": "https://cdn.example.test/frame.jpg",
            }
        }


class _FakePutResponse:
    def raise_for_status(self) -> None:
        return None


def test_upload_image_heygen_uses_extension_specific_content_type(
    monkeypatch, tmp_path
):
    image_path = tmp_path / "frame.jpg"
    image_path.write_bytes(b"jpeg bytes")
    post_payloads: list[dict] = []
    put_headers: list[dict] = []

    def fake_post(url, headers, json, timeout):
        post_payloads.append(json)
        return _FakeHeyGenUploadResponse()

    def fake_put(url, headers, data, timeout):
        put_headers.append(headers)
        return _FakePutResponse()

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr("requests.put", fake_put)

    result = upload_image_heygen(str(image_path), "test-key")

    assert result == "https://cdn.example.test/frame.jpg"
    assert post_payloads[0]["content_type"] == "image/jpeg"
    assert put_headers[0]["Content-Type"] == "image/jpeg"


def test_local_generation_status_requires_cuda_when_enabled(monkeypatch):
    monkeypatch.setenv("VIDEO_GEN_LOCAL_ENABLED", "true")
    original_import = builtins.__import__

    fake_diffusers = types.SimpleNamespace()
    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: False)
    )

    def fake_import(name, *args, **kwargs):
        if name == "diffusers":
            return fake_diffusers
        if name == "torch":
            return fake_torch
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert _shared.local_generation_status() == ToolStatus.UNAVAILABLE


def test_local_video_tool_status_requires_diffusers_pipeline_class(monkeypatch):
    monkeypatch.setenv("VIDEO_GEN_LOCAL_ENABLED", "true")
    original_import = builtins.__import__

    fake_diffusers = types.SimpleNamespace()
    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: True)
    )

    def fake_import(name, *args, **kwargs):
        if name == "diffusers":
            return fake_diffusers
        if name == "torch":
            return fake_torch
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert WanVideo().get_status() == ToolStatus.UNAVAILABLE


def test_generate_local_video_rejects_unknown_operation_before_runtime_import(
    monkeypatch,
):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "torch" or name.startswith("diffusers"):
            raise AssertionError("runtime imported before input validation")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    result = _shared.generate_local_video(
        tool_name="wan_video",
        variants=_shared.WAN_VARIANTS,
        default_variant="wan2.1-1.3b",
        inputs={"prompt": "A product hero shot", "operation": "reference_to_video"},
    )

    assert not result.success
    assert "Unknown operation" in result.error


def test_local_video_tools_require_project_output_path_before_runtime_status(
    monkeypatch,
):
    tools = [WanVideo(), HunyuanVideo(), LTXVideoLocal(), CogVideoVideo()]

    for tool in tools:
        def fail_status(tool_name=tool.name):
            raise AssertionError(f"{tool_name} checked runtime before output_path validation")

        monkeypatch.setattr(tool, "get_status", fail_status)
        result = tool.execute({"prompt": "A product hero shot", "output_path": "clip.mp4"})

        assert not result.success
        assert "output_path" in (result.error or "")
        assert "projects/<project-name>/" in (result.error or "")


@pytest.mark.parametrize("tool", [WanVideo(), HunyuanVideo(), LTXVideoLocal(), CogVideoVideo()])
def test_local_video_schemas_require_output_path(tool):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"prompt": "A product hero shot"},
            schema=tool.input_schema,
        )


def test_load_reference_image_closes_opened_file(monkeypatch):
    opened_images = []

    class FakeOpenedImage:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

        def convert(self, mode):
            assert mode == "RGB"
            return FakeConvertedImage()

    class FakeConvertedImage:
        def resize(self, size, resample):
            return {"size": size, "resample": resample}

    def fake_open(_path):
        image = FakeOpenedImage()
        opened_images.append(image)
        return image

    monkeypatch.setattr("PIL.Image.open", fake_open)

    result = _shared.load_reference_image({"reference_image_path": "frame.png"}, 320, 180)

    assert result["size"] == (320, 180)
    assert opened_images[0].closed


def test_local_video_idempotency_keys_include_conditioning_and_generation_shape():
    tools = [WanVideo(), HunyuanVideo(), LTXVideoLocal(), CogVideoVideo()]
    base = {
        "prompt": "Animate the approved product frame",
        "operation": "image_to_video",
        "reference_image_path": "projects/demo/reference_assets/product_a.png",
        "width": 768,
        "height": 512,
        "num_frames": 121,
        "num_inference_steps": 30,
        "seed": 123,
    }
    variants = [
        {"output_path": "clips/local-a.mp4"},
        {"reference_image_path": "projects/demo/reference_assets/product_b.png"},
        {"reference_image_url": "https://example.test/product-b.png", "reference_image_path": None},
        {"width": 1024},
        {"height": 576},
        {"num_frames": 193},
        {"num_inference_steps": 40},
    ]

    for tool in tools:
        base_key = tool.idempotency_key(base)
        for variant in variants:
            assert tool.idempotency_key({**base, **variant}) != base_key


@pytest.mark.parametrize(
    ("tool", "variant", "meta"),
    [
        (WanVideo(), "wan2.1-1.3b", _shared.WAN_VARIANTS["wan2.1-1.3b"]),
        (HunyuanVideo(), "hunyuan-1.5", _shared.HUNYUAN_VARIANTS["hunyuan-1.5"]),
        (LTXVideoLocal(), "ltx2-local", _shared.LTX_LOCAL_VARIANTS["ltx2-local"]),
        (CogVideoVideo(), "cogvideo-5b", _shared.COGVIDEO_VARIANTS["cogvideo-5b"]),
    ],
)
def test_local_video_output_schema_matches_shared_success_payload(tool, variant, meta):
    output_path = f"projects/demo/assets/video/{tool.name}.mp4"
    payload = {
        "provider": tool.name,
        "model_variant": variant,
        "provider_name": meta["name"],
        "mode": "local",
        "prompt": "A product hero shot",
        "model_id": meta["hf_id"],
        "width": meta["default_width"],
        "height": meta["default_height"],
        "num_frames": meta["default_num_frames"],
        "fps": meta["fps"],
        "duration_seconds": round(meta["default_num_frames"] / meta["fps"], 2),
        "operation": "text_to_video",
        "output": output_path,
        "output_path": output_path,
        "format": "mp4",
        "license": meta["license"],
        "file_size_bytes": 8,
    }
    expected_properties = {
        "provider",
        "model_variant",
        "provider_name",
        "mode",
        "prompt",
        "model_id",
        "width",
        "height",
        "num_frames",
        "fps",
        "duration_seconds",
        "operation",
        "output",
        "output_path",
        "format",
        "license",
        "file_size_bytes",
    }

    output_properties = tool.output_schema["properties"]
    assert expected_properties <= set(output_properties)
    jsonschema.validate(instance=payload, schema=tool.output_schema)


def test_generate_local_video_success_payload_includes_output_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    original_import = builtins.__import__

    class FakePipeline:
        def __call__(self, **_kwargs):
            return types.SimpleNamespace(frames=[["frame"]])

    class FakeGenerator:
        def __init__(self, device):
            self.device = device

        def manual_seed(self, seed):
            return f"seed-{self.device}-{seed}"

    def fake_export_to_video(_frames, path, fps):
        assert fps == _shared.WAN_VARIANTS["wan2.1-1.3b"]["fps"]
        with open(path, "wb") as output_file:
            output_file.write(b"fake mp4")

    def fake_import(name, *args, **kwargs):
        if name == "torch":
            return types.SimpleNamespace(Generator=FakeGenerator)
        if name == "diffusers.utils":
            return types.SimpleNamespace(export_to_video=fake_export_to_video)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(
        _shared,
        "load_diffusers_pipeline",
        lambda _pipeline_class, _model_id, _enable_offload: FakePipeline(),
    )

    output_path = "projects/demo/assets/video/wan-local.mp4"
    result = _shared.generate_local_video(
        tool_name="wan_video",
        variants=_shared.WAN_VARIANTS,
        default_variant="wan2.1-1.3b",
        inputs={
            "prompt": "A product hero shot",
            "output_path": output_path,
            "seed": 123,
        },
    )

    assert result.success
    assert result.data["output_path"] == output_path
    assert result.data["format"] == "mp4"
