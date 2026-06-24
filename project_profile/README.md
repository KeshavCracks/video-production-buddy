# Project Profile

This directory is the repo-side profile for cross-agent consistency. Any
general-purpose agent producing videos in this project should read this profile
before making creative, provider, runtime, voice, subtitle, brand, or
environment-specific decisions.

## Authority

- `AGENT_GUIDE.md` controls production workflow: pipeline selection, stage order,
  checkpoints, approvals, provider governance, and review rules.
- `PROJECT_CONTEXT.md` controls architecture context: source-of-truth files,
  repository layout, and development conventions.
- `project_profile/` controls durable project-local conventions and technical
  findings that should be shared across agents.
- `projects/<project-id>/artifacts/` and `decision_log` control decisions for a
  specific video run.

If this profile conflicts with agent-side private memory, this profile wins.
Do not write project behavior, provider findings, brand rules, or durable user
preferences only into agent-side memory.

## Files

- `README.md` - authority, file map, and update rule for the repo-side profile.
- `conventions.md` - profile index, memory mechanism, and profile changelog.
- `agent_behavior.md` - cross-agent explanation, verification, local UI, and
  closeout behavior.
- `developer_workflow.md` - repo-side audit, fix, git, generated-artifact, and
  identity-cleanup workflow rules.
- `brand.md` - active product identity, visual identity, and forbidden brand/IP
  usage.
- `provider_findings.md` - dated provider/account availability findings and
  verification commands.
- `voice_and_subtitles.md` - Mandarin male voice routing and CJK subtitle
  rendering requirements.
- `model_defaults.md` - dated model/default observations and re-check commands.
- `hyperframes.md` - HyperFrames CJK font packaging and video-heavy render
  findings.
- `update_checklist.md` - how to decide what belongs in this profile and how to
  update it safely.
- `migration_audit.md` - what was migrated from agent-side memory, what was
  already project-side, and what intentionally remains outside this profile.

## Update Rule

Add durable cross-agent findings here when they affect future production quality
or consistency. Keep transient run decisions in the relevant project artifacts
and decision log.
