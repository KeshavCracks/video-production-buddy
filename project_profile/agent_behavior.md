# Agent Behavior

These are repo-side behavior preferences for general-purpose agents working in
Video Production Buddy. They apply after the router in `AGENT_GUIDE.md` or
`AGENTS.md` identifies the route.

## Use Project Files Over Agent Memory

- Treat agent-side memory as historical hints only.
- Re-check the live repo before claiming current behavior, especially pipeline
  stages, artifact names, provider availability, schemas, tests, and generated
  outputs.
- When repo files and agent memory disagree, the repo wins.

## Explanations

- For Chinese or nontechnical explanation requests, prefer short, plain Chinese
  with minimal jargon.
- Explain the project by mapping each step to real artifacts and tools:
  `stage -> artifact -> tool/check`.
- Avoid abstract architecture-only descriptions when the user asks how the
  system works. Name the concrete manifest, director skill, tool, artifact, or
  validator involved.
- Before naming a stage or artifact as current, re-check the live manifest or
  schema instead of relying on memory.

## Verification and Local UI

- For development verification, default to terminal-only checks.
- Do not open Explorer, browser windows, media players, or other desktop UI
  unless the user explicitly asks for it.
- If a test or tool path may launch a browser, prefer a non-opening mode or set
  `VPB_ALLOW_BROWSER_OPEN=0` when that guard is supported.
- For GenUI or local preview surfaces, return the localhost URL by default.
  Launch a browser only when the relevant tool was explicitly asked to do so.
- Agent-native question or form tools are not a substitute for project GenUI.
  Claude Code `AskUserQuestion`, Codex `request_user_input`, Cursor/Copilot
  prompt widgets, and similar assistant UI may be used for one-question
  clarifications or explicit fallback only after `genui_interaction` /
  `genui_session` is unavailable, fails, or the user declines the browser path.
- Before marking a GenUI-required gate complete, check
  `genui_evidence_check` or
  `lib.genui.journal.genui_required_gate_evidence_report(...)` against the
  project's `ui_interaction_journal`. A gate needs a schema-valid GenUI response
  artifact or an explicit GenUI failure/unavailable/user-declined fallback
  reason. For ad-video assets, use
  `make genui-evidence-check PROJECT=projects/<project-id> PIPELINE=ad-video STAGE=assets`.
- If a pipeline manifest declares `genui_evidence_required: true`, completed
  checkpoint writes enforce the declared GenUI evidence gate automatically.

## User Communication

- Keep status updates concrete: what is being inspected, what was learned, and
  what will be edited next.
- For closeout, state the touched scope, the verification actually run, and any
  remaining dirty or untracked project files that affect commit safety.
