"""Shared .env loader for Video Production Buddy tools.

Handles quoted values, inline comments, and blank/comment lines.
Both tools/base_tool.py and tools/tool_registry.py delegate here
instead of maintaining separate parsing blocks.
"""

from __future__ import annotations

import os
from pathlib import Path


def _default_env_paths() -> list[Path]:
    """Return default .env search paths in precedence order."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            paths.append(candidate)
    return paths


def _load_env_path(env_path: Path) -> None:
    if not env_path.is_file():
        return
    with open(env_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key.startswith("export "):
                key = key[len("export "):].strip()
            value = value.strip()
            if value.startswith(("'", '"')):
                # Quoted value: extract content between opening and closing quote.
                # Discards any inline comment after the closing quote.
                quote = value[0]
                end = value.find(quote, 1)
                value = value[1:end] if end > 0 else value.strip(quote)
            else:
                # Unquoted: strip inline comments (KEY=value  # comment or KEY=  # comment)
                for sep in ("  #", "\t#", " #"):
                    idx = value.find(sep)
                    if idx != -1:
                        value = value[:idx].rstrip()
                        break
                if value.startswith("#"):
                    value = ""
            if key and key not in os.environ:
                os.environ[key] = value


def load_dotenv(env_path: Path | None = None) -> None:
    """Load a .env file into os.environ (non-overwriting).

    When no explicit path is provided, project-local .env in the current
    working directory takes precedence over the package/source-root .env.
    Only sets variables that are not already present in the environment.
    """
    if env_path is not None:
        _load_env_path(env_path)
        return

    for candidate in _default_env_paths():
        _load_env_path(candidate)
