# Ad-Video Professional Knowledge Grounding — Design

**Date:** 2026-05-22
**Status:** Approved

## Problem

The ad-video pipeline's professional knowledge system had 8 shallow knowledge cards (3 principles each), only 8 of 10 schema domains filled, flat BM25 scoring that concatenated all fields into a single text blob, no trend-knowledge conflict detection, and no cross-domain interaction tracking. The system worked but was not professional-grade.

## Solution

### Schema Expansion (10 → 15 domains)

Added 5 new professional domains:
- `cinematography` — camera language, shot composition, lens psychology
- `color_theory` — palette strategy, color psychology, mood-color mapping
- `editing_technique` — cut types, transition psychology, rhythm-to-edit mapping
- `sound_design` — ambient texture, foley, silence placement
- `music_direction` — tempo-to-intensity mapping, genre positioning, harmonic events

### Knowledge Cards (8 → 15)

- 7 new cards covering the new domains plus the 2 previously empty ones (`audience_insight`, `narrative_arc`)
- All 8 existing cards deepened from 3 to 6-8 principles
- Every card now includes `failure_patterns` (3-4), `cross_domain_notes` (2-3), and `execution_techniques` (3-4)

### Field-Weighted BM25 Retrieval

Replaced flat text-concatenation BM25 with per-field scoring using weighted contributions:
domain=3.0, keywords=2.5, apply_when=2.0, principles=1.5, execution_techniques=1.0, summary=1.0, avoid_when=0.5, failure_patterns=0.5.

### Trend-Knowledge Conflict Detection

New `lib/conflict_detection.py` cross-checks selected trends against knowledge cards' `avoid_when` and `do_not_overapply` conditions. Integrated into the planning chain check gate and the bible-director skill (Step 5a).

### Cross-Domain Co-Presence Check

Cards that reference each other in `cross_domain_notes` with overlapping `application_targets` must appear in at least one shared scene. Integrated into `check_ad_video_planning_knowledge_alignment()`.

### Alignment Note Quality Filter

`apply_alignment_notes()` now filters notes shorter than 15 characters as too vague to influence generation.

## Files Modified/Created

| File | Change |
|------|--------|
| `schemas/knowledge/ad_video_knowledge_card.schema.json` | 15 domains, new fields |
| `schemas/artifacts/intelligence_brief.schema.json` | 15 domains in domain enum |
| `schemas/artifacts/production_bible.schema.json` | 15 domains in domain enum |
| `lib/ad_knowledge.py` | Protocol-based EmbeddingScorer, field-weighted BM25 |
| `lib/conflict_detection.py` | NEW: trend-knowledge conflict detection |
| `lib/knowledge_alignment.py` | Cross-domain co-presence check |
| `lib/emotional_prompt.py` | Alignment note quality filter |
| `tools/validation/ad_video_planning_chain_check.py` | Conflict detection integration |
| `skills/pipelines/ad-video/bible-director.md` | Step 5a conflict detection |
| `knowledge/ad-video/*.json` | 15 cards (7 new + 8 deepened) |
| `tests/contracts/test_ad_video_professional_knowledge.py` | Expanded for 15 cards, new fields |
| `tests/contracts/test_conflict_detection.py` | NEW: 7 tests |
| `tests/contracts/test_cross_domain_interaction.py` | NEW: 4 tests |
| `tests/contracts/test_alignment_note_quality.py` | NEW: 6 tests |
