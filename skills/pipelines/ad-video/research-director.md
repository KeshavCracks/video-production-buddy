# Research Director — Ad Video Pipeline

## When to Use

You are the parent **Research Director** for the collapsed ad-video pipeline.
The top-level stage is `research`, but the work remains split into three
checkpointable child gates:

1. `research.intake`
2. `research.brief_enrichment`
3. `research.intelligence`

Do not collapse or skip those gates. The generic top-level stage exists to keep
ad-video aligned with the common pipeline shape; the child gates preserve the
governed ad-specific behavior.

## Gate Order

Run each child gate in order. Before doing work inside a child gate, read that
gate's director skill:

| Child gate | Director skill | Output |
|------------|----------------|--------|
| `research.intake` | `skills/pipelines/ad-video/intake-director.md` | `intake_brief` |
| `research.brief_enrichment` | `skills/pipelines/ad-video/brief-enrichment-director.md` | `enriched_brief` |
| `research.intelligence` | `skills/pipelines/ad-video/intelligence-director.md` | `intelligence_brief` |

## Checkpoint Rules

- Write checkpoints with the dotted child gate id, for example
  `research.brief_enrichment`.
- Preserve the approval behavior declared on each child gate.
- `research.brief_enrichment` must not complete until `enriched_brief.user_approved`
  is true.
- `research.intelligence` must consume the approved `enriched_brief` and must not
  mutate it.

## Success Criteria

- `intake_brief`, `enriched_brief`, and `intelligence_brief` are schema-valid.
- The `enriched_brief` approval gate is recorded before intelligence completes.
- The next resumable unit after research is `proposal.bible`.
