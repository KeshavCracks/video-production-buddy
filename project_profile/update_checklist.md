# Project Profile Update Checklist

Use this checklist when adding or changing `project_profile/` guidance.

## Belongs Here

- Durable cross-agent behavior that should apply to Claude, Codex, Cursor,
  Copilot, or any other general-purpose agent using this repo.
- Provider/account findings that affect future routing or quality.
- Brand, voice, subtitle, visual identity, or model-default facts that should
  survive across sessions.
- Repo workflow preferences that affect audits, fixes, tests, commits, or
  production quality.

## Does Not Belong Here

- One-off decisions for a single video run. Put those in
  `projects/<project-id>/artifacts/` and `decision_log`.
- Machine-specific Codex/editor setup unless it directly changes project
  behavior for all agents.
- Other repositories' workflow notes.
- Old command transcripts or rollout history without a reusable project rule.
- Claims about "latest" provider/model state without a verification date and a
  practical re-check path.

## Required Steps

1. Add or update the focused profile file.
2. Include `Last verified` and verification commands for provider/model/account
   claims.
3. Add the file to `project_profile/README.md`.
4. Add the file to the `PROJECT_CONTEXT.md` key-files table.
5. Keep `project_profile/conventions.md` as an index, not a duplicate copy of
   every focused file.
6. Run the project-profile contract test:

```bash
VPB_ALLOW_BROWSER_OPEN=0 PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider tests/contracts/test_repo_hygiene_contracts.py -q
```

7. Run scoped whitespace verification:

```bash
git diff --check -- AGENT_GUIDE.md PROJECT_CONTEXT.md AGENTS.md CLAUDE.md CURSOR.md COPILOT.md tests/contracts/test_repo_hygiene_contracts.py project_profile
```
