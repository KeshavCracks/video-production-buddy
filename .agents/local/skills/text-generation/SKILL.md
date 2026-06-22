---
name: text-generation
description: Use when routing standalone ad-hoc text generation to Qwen or MiniMax provider tools, including setup, model choice, cost discipline, output persistence, and the boundary that the agent remains the primary reasoner.
---

# Text Generation Provider Calls

Use this skill for standalone text-generation provider tools:

- `qwen_chat`
- `minimax_chat`

These tools are optional provider calls for bounded text sub-tasks. They do not
replace the coding assistant or become a Python pipeline orchestrator.

## Boundary

Video Production Buddy is agent-first. The agent remains the primary reasoner
and owner of pipeline decisions, artifacts, validation, and checkpoint writes.

Use text-generation tools only when a specific bounded text job benefits from a
billed provider call, such as:

- bulk script polishing
- translation variants
- long-document summarization
- style rewrites
- structured copy alternatives

Do not auto-wire these tools into pipeline stages. Do not use them to bypass
stage director skills, artifact schemas, reviewer skills, checkpoint policy, or
human approval gates.

## Provider Setup

`qwen_chat` requires `DASHSCOPE_API_KEY` and calls Bailian / DashScope's
OpenAI-compatible chat-completions endpoint.

`minimax_chat` requires `MINIMAX_API_KEY`. The default API base is the
China-mainland MiniMax host; use `MINIMAX_API_BASE` when an overseas host is
required.

Both providers are network API tools. Confirm setup through the tool status or
`provider_menu_summary()` before proposing them as available.

## Model Choice

Use Qwen when the task needs Qwen's long-context models, strong Chinese and
multilingual handling, or Qwen Coder.

Use MiniMax when the task needs MiniMax-M3/M2.7 behavior, MiniMax account
routing, or multimodal message support exposed by the provider.

Prefer the lower-cost or faster model for drafts and alternatives. Reserve the
highest-quality model for final polish, difficult reasoning, or long-context
review.

## Output Persistence

When `output_path` is provided, it must be project-scoped and should point under
`projects/<project-name>/artifacts/...`, `projects/<project-name>/assets/...`,
or `projects/<project-name>/renders/...` as accepted by the tool.

Persist outputs when the generated text becomes evidence, a draft artifact, or
an input to later review. For one-off exploratory calls, returning the text in
the `ToolResult` is enough.

## Cost Discipline

Keep prompts narrow and explicit. Include only the source text and constraints
needed for the sub-task. Avoid sending secrets, credentials, private keys,
personal contact/payment data, or unrelated project files.

Record provider, model, token counts, output path, and cost from the tool
result when the call contributes to a production artifact.
