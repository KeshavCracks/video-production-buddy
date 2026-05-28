# GenUI Interaction Protocol

## When to Use

Before each substantive human interaction, decide whether linear chat is
sufficient. Use GenUI when the current round contains visual demonstration,
media review, side-by-side comparison, multi-axis selection, many options,
structured revision capture, defaults, recommendations, or approval details
that would be tedious to review in a CLI message.

The standard browser path is GenUI: `genui_interaction` routes the round,
records the CLI-vs-browser decision in `ui_interaction_journal`, applies
stage-aware policies and fixed workspace contracts for known gates, and delegates to
`genui_session`. `genui_session` serves an A2UI/CopilotKit React session over
AG-UI transport, supports status/replay/validate/summarize lifecycle modes,
includes durable decision/resume metadata, operation events, cursor-addressable
`events.jsonl` replay, `/events`, `/session.json`, response-only `/draft`
autosave, and conflict-safe source hash checks, and the browser writes
`ui_session_response`. The underlying
`ui_session_config`/`ui_session_response` wire artifacts remain session-contract
compatible and predecessor product sessions remain readable. Use the
`genui_surface` json-render path only as explicit compatibility fallback.

Typical cases: ad-video creative requirements, proposal lock points, product
identity reference choices, runtime selection, derivative variants,
subtitle/dubbing choices, budget approval, media/sample/asset/music review,
and voice/style sample approval.

Skip GenUI for one-question clarifications, source inspection, or short yes/no
approval gates where the CLI is clearer.

## Contract

GenUI is an interaction layer, not an orchestrator.

The agent still owns:
- pipeline selection and stage order,
- reading the pipeline manifest and stage director skill,
- preflight and provider/runtime decisions,
- self-review,
- canonical artifact writes,
- checkpoints and decision logs.

The GenUI session server writes only `ui_session_response` and response-only
draft state. It may
materialize renderer-only `view_spec.json` for A2UI/CopilotKit, but that file
is not canonical and must not turn artifact bindings into executable writes.
It must not write canonical artifacts such as `enriched_brief`,
`production_proposal`, `decision_log`, or checkpoints. The agent validates and
summarizes `ui_session_response` before updating those files.
`ui_interaction_journal` is an agent-owned routing and lifecycle artifact; it
records decisions, fallback reasons, status, replay, and validation outcomes.
The event log is durable session lifecycle state for replay/status only; it is
not an instruction to mutate canonical artifacts.

The compatibility surface server writes only `ui_surface_response`; the same canonical
write boundary applies.

## Workflow

1. Build an `interaction_request` that describes the prompt, choices, fields,
   media items, comparison rows, and capabilities needed for the current round.
2. Call `genui_interaction` so the policy can decide whether linear chat is
   sufficient and, when needed, synthesize a dynamic `ui_session_config` with
   `visual_need_assessment` and record `ui_interaction_journal`.
3. If a director has already produced a complete `ui_session_config`, call
   `genui_session` directly in `serve` mode when a local browser is available.
   Use `genui_surface` directly only for an explicit `ui_surface_config`.
4. Use CLI fallback only when `genui_interaction` cannot route/serve, when
   `genui_session` execution fails and the `genui_surface` fallback is not
   viable, or when the user explicitly declines the browser path. A returned
   localhost URL counts as browser path available; paste that URL and wait for
   `response_path` validation instead of switching to CLI.
5. After submission, read
   `projects/<project>/artifacts/ui/<session_id>/response.json`.
6. Validate it as `ui_session_response` and review the generated patch plan.
   `genui_session` `validate_response` and `summarize` modes are the standard
   helpers for this step. For explicit compatibility surface, validate as
   `ui_surface_response`.
7. Summarize the user's selected values, issue IDs, annotations, and revisions.
8. Only then write canonical artifacts, decision logs, and checkpoints.

## User-Facing Pattern

Keep the terminal message short:

```
I generated a GenUI media review room for Gate G-Assets.
Open: http://127.0.0.1:<port>/
Submit it when ready; I will validate the response before updating artifacts.
```

For CLI fallback, present the same fields in a compact numbered worksheet and
record that `genui_session` execution fails, `genui_surface` fallback is not
viable, or the user explicitly declined the browser path. Localhost URL counts
as browser path available.
