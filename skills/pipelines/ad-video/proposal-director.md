# Proposal Director — Ad Video Pipeline

## When to Use

You are the parent **Proposal Director** for the collapsed ad-video pipeline.
The top-level stage is `proposal`, but the governed ad-video work remains split
into three checkpointable child gates:

1. `proposal.bible`
2. `proposal.idea`
3. `proposal.technical_proposal`

Do not merge these responsibilities into a single approval. The generic
top-level stage keeps ad-video aligned with the common pipeline model; the child
gates preserve strategy approval, concept selection, and technical production
locks.

Enter this parent stage only after `research.intake`,
`research.brief_enrichment`, and `research.intelligence` have produced
`intake_brief`, `enriched_brief`, and `intelligence_brief`. Those artifacts are
the shared inputs for the child gates below.

## Gate Order

Run each child gate in order. Before doing work inside a child gate, read that
gate's director skill:

| Child gate | Director skill | Output |
|------------|----------------|--------|
| `proposal.bible` | `skills/pipelines/ad-video/bible-director.md` | `production_bible` |
| `proposal.idea` | `skills/pipelines/ad-video/idea-director.md` | `idea_options` |
| `proposal.technical_proposal` | `skills/pipelines/ad-video/technical-proposal-director.md` | `production_proposal`, `decision_log` |

## Checkpoint Rules

- Write checkpoints with the dotted child gate id, for example
  `proposal.technical_proposal`.
- `proposal.bible` must not complete until both
  `production_bible.approval.strategic_approved` and
  `production_bible.approval.execution_approved` are true.
- `proposal.idea` must not complete until the user has selected one concept in
  `idea_options.selected_concept_id`.
- `proposal.technical_proposal` owns technical production choices only:
  render runtime, derivatives, subtitles, dubbing, music strategy, product
  reference strategy, voice/audio contract, and budget.

## GenUI Fallback Rule

Use the browser/GenUI path for proposal child-gate approvals whenever available.
The CLI fallback is allowed only when `genui_session execution fails` or the
user `explicitly declines the browser path`. A localhost URL counts as browser
path available. The browser session must not write canonical artifacts directly;
it writes `ui_session_response`, then the agent validates and writes the
canonical artifacts/checkpoints.

## Success Criteria

- `production_bible`, `idea_options`, `production_proposal`, and `decision_log`
  are schema-valid.
- All user-visible choices required by the child gates are explicitly approved.
- The next resumable unit after proposal is `script`.
