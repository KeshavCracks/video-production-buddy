# Agent-Side Memory Migration Audit

This file records which durable Codex-side observations were moved into
project-side instructions so other agents can share them.

## Migrated From Codex-Side Memory

- Concise Chinese/nontechnical explanations should use real implementation
  anchors: `stage -> artifact -> tool/check`.
- Development verification should be terminal-only by default; do not pop
  Explorer, browser windows, or media players unless explicitly requested.
- `VPB_ALLOW_BROWSER_OPEN=0` is the preferred guard when a verification path
  might otherwise open browser UI.
- Project audits should start from live manifests, registries, loaders, schemas,
  tests, and runtime consumers, not stale literal lists.
- `provider_menu_summary()` is the compact provider/runtime availability source
  agents should use before presenting capability menus.
- Review-fix requests should be treated as implementation work with focused
  regressions and verification.
- Git operations need explicit scope, dirty-tree protection, and tree-equality
  proof for history rewrites.
- Generated-artifact cleanup should preserve local files when only untracking is
  requested and should add or run guards when the user asks whether files will
  stay gone.
- Product identity cleanup should remove legacy aliases by default when the
  change is identity-only and compatibility is not requested.

## Migrated From Claude Code Session State

- 2026-06-18: The latest Claude Code session recorded that HyperFrames needed
  explicit Noto Sans SC packaging for Chinese text and safer worker settings for
  video-heavy renders. The follow-up audit also found sparse-keyframe stock
  video prep still lived as manual guidance only. These are now project-side in
  `hyperframes.md`, `skills/core/hyperframes.md`, and `hyperframes_compose`.

## Already Project-Side Before This Audit

- The agent-first pipeline architecture, standard stage flow, checkpoints,
  canonical artifacts, provider governance, and GenUI write boundary already
  live in `AGENT_GUIDE.md`, `PROJECT_CONTEXT.md`, `docs/ARCHITECTURE.md`,
  manifests, skills, schemas, and tests.
- Product-fidelity and hallucination-control contracts already live in ad-video
  stage skills, artifact schemas, validators, and `AGENT_GUIDE.md`.

## Intentionally Not Migrated

- Other repositories' workflow notes, including profile-site and GitHub Pages
  preview flows, do not belong in this project profile.
- Codex CLI, local editor, and cross-config hook cleanup notes are machine-side
  operational details, not Video Production Buddy project behavior.
- One-off authentication observations, such as a historical `gh auth status`
  failure while git HTTPS push still worked, should be re-checked live instead
  of becoming a project rule.
- Exact old rollout commands, commit hashes, and session summaries remain
  historical evidence only; agents must re-check the live repo before acting.
