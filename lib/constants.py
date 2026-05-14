"""Shared numeric constants used across the production pipeline.

Constants live here when they're referenced by more than one module and a
silent divergence (e.g. one module updated, another forgotten) would produce
inconsistent enforcement. Single-consumer constants stay in their home
module.
"""

from __future__ import annotations


# Voice-over pacing assumption per spec §9. Used by:
#   * tools/compliance/compliance_check.py (timing checkpoint estimation)
#   * lib/hook_window.py (hook section duration estimation)
# Updating this value must propagate to both consumers — tests assert they
# read from the same source.
WORDS_PER_MINUTE_VO: int = 150
