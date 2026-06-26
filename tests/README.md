# Test Suites

The default suite is intentionally lean. It protects durable repo contracts,
mocked provider behavior, output-path safety, selector routing, and JSON-safe
tool results without launching browsers, requiring FFmpeg/Node/HyperFrames, or
calling live providers.

## Commands

```bash
make test            # fast default suite
make test-contracts  # contracts only, same default marker exclusions
make test-integration
make test-qa
make genui-verify
```

`make test-integration` runs every test marked `integration`, including local
runtime smoke checks under `tests/integration/` and integration-marked cases
that live beside their unit-level tool contracts. These tests may need FFmpeg,
Playwright/Chromium, Node.js, or HyperFrames and should skip cleanly when their
runtime is unavailable.

`make test-qa` is the manual/media QA alias. It currently points at the same
opt-in integration surface because generated media review is not part of the
routine default suite.

Live paid or network provider checks must be marked `live_provider` and must not
run from `make test`.
