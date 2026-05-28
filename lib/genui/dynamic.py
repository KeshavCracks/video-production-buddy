"""Validate dynamic GenUI interaction requests for per-round surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

INTERACTION_REQUEST_SCHEMA_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "schemas"
    / "genui"
    / "interaction_request.schema.json"
)
INTERACTION_REQUEST_SCHEMA = json.loads(INTERACTION_REQUEST_SCHEMA_PATH.read_text())


def validate_interaction_request(request: dict[str, Any]) -> None:
    """Validate a dynamic GenUI interaction request."""
    jsonschema.Draft202012Validator(INTERACTION_REQUEST_SCHEMA).validate(request)
