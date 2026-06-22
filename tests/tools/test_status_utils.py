from __future__ import annotations

from tools.base_tool import ToolStatus
from tools.status_utils import (
    is_tool_available,
    safe_tool_info,
    safe_tool_provider,
    safe_tool_status,
)


class BrokenStatusTool:
    name = "broken_status_tool"
    provider = "broken"
    capability = "demo"
    best_for = ("demo",)
    supports = {"demo": True}
    agent_skills = "text-to-speech"

    def get_status(self):
        raise RuntimeError("status backend unavailable")


class SparseInfoTool:
    name = "sparse_info_tool"
    provider = "sparse"
    capability = "tts"
    best_for = ("narration",)
    supports = {"multilingual": True}
    agent_skills = ("text-to-speech",)

    def get_info(self):
        return {
            "name": self.name,
            "agent_skills": self.agent_skills,
            "best_for": self.best_for,
            "input_schema": None,
            "supports": self.supports,
        }


class FailingInfoTool(SparseInfoTool):
    def get_info(self):
        raise ValueError("metadata failure")


def test_safe_tool_status_degrades_when_status_backend_raises() -> None:
    tool = BrokenStatusTool()

    assert safe_tool_status(tool) == ToolStatus.DEGRADED
    assert is_tool_available(tool) is False


def test_safe_tool_provider_tolerates_missing_provider() -> None:
    assert safe_tool_provider(object()) == "unknown"


def test_safe_tool_info_normalizes_successful_metadata_shapes() -> None:
    info = safe_tool_info(SparseInfoTool())

    assert info["name"] == "sparse_info_tool"
    assert info["provider"] == "sparse"
    assert info["agent_skills"] == ["text-to-speech"]
    assert info["best_for"] == ["narration"]
    assert info["input_schema"] == {}
    assert info["supports"] == {"multilingual": True}


def test_safe_tool_info_falls_back_when_get_info_raises() -> None:
    info = safe_tool_info(FailingInfoTool())

    assert info["name"] == "sparse_info_tool"
    assert info["provider"] == "sparse"
    assert info["capability"] == "tts"
    assert info["agent_skills"] == ["text-to-speech"]
    assert info["best_for"] == ["narration"]
