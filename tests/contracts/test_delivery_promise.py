"""Delivery-promise classifier regressions."""

from __future__ import annotations

import pytest

from lib.delivery_promise import PromiseType, classify_from_brief


@pytest.mark.parametrize(
    ("pipeline_type", "expected_type", "motion_required", "source_required"),
    [
        ("talking-head", PromiseType.SOURCE_LED, False, True),
        ("ad-video", PromiseType.MOTION_LED, True, False),
        ("character-animation", PromiseType.MOTION_LED, True, False),
        ("documentary-montage", PromiseType.SOURCE_LED, False, True),
        ("podcast-repurpose", PromiseType.SOURCE_LED, False, True),
        ("clip-factory", PromiseType.SOURCE_LED, False, True),
        ("localization-dub", PromiseType.LOCALIZATION, False, True),
        ("avatar-spokesperson", PromiseType.AVATAR_PRESENTER, True, False),
    ],
)
def test_classify_from_brief_knows_current_pipeline_defaults(
    pipeline_type: str,
    expected_type: PromiseType,
    motion_required: bool,
    source_required: bool,
) -> None:
    promise = classify_from_brief(pipeline_type, {})

    assert promise.promise_type is expected_type
    assert promise.motion_required is motion_required
    assert promise.source_required is source_required
