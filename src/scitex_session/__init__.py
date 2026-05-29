#!/usr/bin/env python3
# Timestamp: "2025-08-21 20:36:45 (ywatanabe)"
# File: /home/ywatanabe/proj/SciTeX-Code/src/scitex/session/__init__.py
# ----------------------------------------
"""scitex-session — @session decorator + lifecycle management (standalone)."""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _v

    try:
        __version__ = _v("scitex-session")
    except PackageNotFoundError:
        __version__ = "0.0.0+local"
    del _v, PackageNotFoundError
except ImportError:  # pragma: no cover — only on ancient Pythons
    __version__ = "0.0.0+local"
import os

__FILE__ = __file__
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""Experiment session management for SciTeX.

This module provides session lifecycle management functionality that was previously
in scitex.session.start and scitex.session.close, now as a dedicated session management system.

Usage:
    # Session management (replaces scitex.session.start/close)
    import sys
    import matplotlib.pyplot as plt
    import scitex_session as session

    # Start a session
    CONFIG, sys.stdout, sys.stderr, plt, COLORS, rng = session.start(sys, plt)

    # Your experiment code here

    # Close the session
    session.close(CONFIG)

    # Session manager for advanced use cases
    manager = session.SessionManager()
    active_sessions = manager.get_active_sessions()

    # Using INJECTED sentinel for decorator parameters
    @stx.session
    def main(CONFIG=stx.session.INJECTED, plt=stx.session.INJECTED):
        ...
"""


# Sentinel object for decorator-injected parameters
class _InjectedSentinel:
    """Sentinel value indicating a parameter will be injected by a decorator."""

    def __repr__(self):
        return "<INJECTED>"


INJECTED = _InjectedSentinel()


# Lazy attribute map: public name -> (submodule, attr in submodule).
# Heavy imports (matplotlib / figrecipe / pandas / scitex_io) live behind
# these submodules and are deferred until first access (PEP 562). A bare
# ``import scitex_session`` previously pulled _lifecycle -> _start ->
# _matplotlib, which imported matplotlib + figrecipe (pyplot) + pandas at
# module scope (~3.6s). Deferring them keeps cold import well under the
# scitex-dev §10 budget (<500ms).
_LAZY_ATTRS = {
    # Session decorator (new simplified API)
    "session": ("._decorator", "session"),
    "run": ("._decorator", "run"),
    # Session lifecycle (main functions)
    "start": ("._lifecycle", "start"),
    "close": ("._lifecycle", "close"),
    "running2finished": ("._lifecycle", "running2finished"),
    # Archive helpers (bidirectional)
    "archive_session_dir": ("._lifecycle", "archive_session_dir"),
    "restore_session_archive": ("._lifecycle", "restore_session_archive"),
    "archive_existing": ("._lifecycle", "archive_existing"),
    "restore_existing": ("._lifecycle", "restore_existing"),
    # Advanced session management
    "SessionManager": ("._manager", "SessionManager"),
}


def __getattr__(name: str):
    """PEP 562 lazy-loader: import on first access, cache, return.

    The matplotlib ``Agg`` backend side-effect for headless/WSL lives in
    ``_lifecycle/_matplotlib.py`` and therefore fires the first time any
    session function is resolved here — which is also the first time pyplot
    is imported — so backend ordering is preserved.
    """
    spec = _LAZY_ATTRS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    mod_name, attr_name = spec
    attr = getattr(import_module(mod_name, __name__), attr_name)
    globals()[name] = attr  # cache for subsequent accesses
    return attr


def __dir__() -> list[str]:
    return sorted(set(_LAZY_ATTRS) | set(globals()))


# Export public API
__all__ = [
    "__version__",
    # Sentinel for injected parameters
    "INJECTED",
    # Session lifecycle (main functions)
    "start",
    "close",
    "running2finished",
    # Session decorator (new simplified API)
    "session",
    "run",
    # Advanced session management
    "SessionManager",
    # Archive helpers (bidirectional)
    "archive_session_dir",
    "restore_session_archive",
    "archive_existing",
    "restore_existing",
]

# EOF
