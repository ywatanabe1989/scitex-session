#!/usr/bin/env python3
# File: ./src/scitex_session/_hooks.py
# ----------------------------------------
"""In-process lifecycle-hook registry for scitex-session.

This is the observer seam that keeps the dependency graph acyclic. Downstream
packages (e.g. scitex-clew, which records session lineage) SUBSCRIBE to session
lifecycle events instead of session importing them by name. It mirrors the
scitex-io post-save/-load hook seam: the producer exposes a hook point and
never names the consumer; the consumer subscribes lazily (clew installs a
``sys.meta_path`` finder that registers on ``import scitex_session``). Direction
of dependency is therefore always ``observer -> scitex_session``, never the
reverse.

Contract (stable, do not change without coordinating with subscribers):

- ``register_session_start_hook(fn)`` — ``fn`` is called at session start as
  ``fn(session_id, script_path, metadata)`` (positional).
- ``register_session_close_hook(fn)`` — ``fn`` is called at session close as
  ``fn(status, exit_code)`` (positional).

Every hook is fired inside an isolated ``try/except Exception: pass`` — a
misbehaving or absent subscriber can never break a session (the same
silent-fail semantics the direct clew import had).
"""

from __future__ import annotations

from typing import Any, Callable, List

# Module-level registries. Kept as plain lists so ordering is deterministic
# (registration order) and membership checks stay simple.
_SESSION_START_HOOKS: List[Callable[..., Any]] = []
_SESSION_CLOSE_HOOKS: List[Callable[..., Any]] = []


def register_session_start_hook(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register ``fn`` to be called at session start.

    ``fn`` is invoked as ``fn(session_id, script_path, metadata)``. Registration
    is idempotent (registering the same callable twice is a no-op). Returns
    ``fn`` so it can also be used as a decorator.
    """
    if fn not in _SESSION_START_HOOKS:
        _SESSION_START_HOOKS.append(fn)
    return fn


def register_session_close_hook(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register ``fn`` to be called at session close.

    ``fn`` is invoked as ``fn(status, exit_code)``. Registration is idempotent.
    Returns ``fn`` so it can also be used as a decorator.
    """
    if fn not in _SESSION_CLOSE_HOOKS:
        _SESSION_CLOSE_HOOKS.append(fn)
    return fn


def unregister_session_start_hook(fn: Callable[..., Any]) -> None:
    """Remove a previously registered start hook (no-op if absent)."""
    try:
        _SESSION_START_HOOKS.remove(fn)
    except ValueError:
        pass


def unregister_session_close_hook(fn: Callable[..., Any]) -> None:
    """Remove a previously registered close hook (no-op if absent)."""
    try:
        _SESSION_CLOSE_HOOKS.remove(fn)
    except ValueError:
        pass


def _fire_session_start_hooks(
    session_id: Any, script_path: Any = None, metadata: Any = None
) -> None:
    """Fire all registered start hooks (isolated silent-fail per hook)."""
    for hook in list(_SESSION_START_HOOKS):
        try:
            hook(session_id, script_path, metadata)
        except Exception:
            pass


def _fire_session_close_hooks(status: Any = "success", exit_code: Any = 0) -> None:
    """Fire all registered close hooks (isolated silent-fail per hook)."""
    for hook in list(_SESSION_CLOSE_HOOKS):
        try:
            hook(status, exit_code)
        except Exception:
            pass


# EOF
