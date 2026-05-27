"""Small I/O helpers for demo Spark jobs."""

from __future__ import annotations


def strip_trailing_slash(path: str) -> str:
    return path.rstrip("/")


def child_path(parent: str, *children: str) -> str:
    parts = [strip_trailing_slash(parent)]
    parts.extend(part.strip("/") for part in children if part)
    return "/".join(parts)
