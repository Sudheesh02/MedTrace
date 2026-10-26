"""Shared environment-variable helpers so every module parses flags the same way."""

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def env_bool(name: str, default: bool = False) -> bool:
    """True for 1/true/yes/on (case-insensitive, whitespace-trimmed); False for anything else; `default` when unset."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY
