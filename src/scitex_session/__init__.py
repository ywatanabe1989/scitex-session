#!/usr/bin/env python3
# Timestamp: "2025-08-21 20:36:45 (ywatanabe)"
# File: /home/ywatanabe/proj/SciTeX-Code/src/scitex/session/__init__.py
# ----------------------------------------
"""scitex-session — the ``@scitex_session.session`` decorator (standalone).

THE one public entry point is the decorator::

    import scitex_session

    @scitex_session.session
    def main(CONFIG=scitex_session.INJECTED, plt=scitex_session.INJECTED):
        ...

    if __name__ == "__main__":
        main()

It parses CLI args from ``main``'s signature, loads ``config/*.yaml``,
configures matplotlib + logging, seeds a reproducible RNG, runs the
function, writes outputs under ``script_out/<status>/<session_id>/``,
and records clew lineage. That is the supported, recommended surface.

The low-level building blocks the decorator orchestrates — ``start()``
(``start(sys, plt, ...)``) and ``run()`` (the imperative, non-decorator
runner) — are INTERNAL. They are easy to misuse: ``@scitex_session.start``
binds ``main`` to the ``sys`` parameter rather than decorating it, and
``run(name=...)`` forwards unknown kwargs into ``start()``. They are
therefore *not* part of the default public surface (absent from
``__all__`` and ``dir(scitex_session)``). Power users who genuinely need
them should reach for the underscore aliases ``scitex_session._start`` /
``scitex_session._run``. The bare ``scitex_session.start`` /
``scitex_session.run`` names remain importable for backward
compatibility but emit a :class:`DeprecationWarning` on access.
"""

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

DEFAULT (recommended) — the ``@scitex_session.session`` decorator::

    import scitex_session as session

    @session.session
    def main(CONFIG=session.INJECTED, plt=session.INJECTED):
        ...

    if __name__ == "__main__":
        main()

ADVANCED / INTERNAL — the low-level lifecycle the decorator wraps. These
are not part of the default public surface; prefer the decorator. Power
users who need manual control use the underscore aliases::

    import sys
    import matplotlib.pyplot as plt
    import scitex_session as session

    # Low-level start (INTERNAL: note the signature is start(sys, plt, ...),
    # NOT a decorator). Use the _-prefixed alias for power-user access.
    CONFIG, sys.stdout, sys.stderr, plt, COLORS, rng = session._start(sys, plt)

    # ... your experiment code ...

    session.close(CONFIG)

    # Class form of the lifecycle for nested / multi-phase runs.
    manager = session.SessionManager()
    active_sessions = manager.get_active_sessions()
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
#
# NOTE on the API surface: the ``@session`` decorator is THE public entry
# point. The low-level lifecycle ``start()`` and the imperative ``run()``
# are INTERNAL — they are exposed here only under the underscore aliases
# ``_start`` / ``_run`` (for power users). The bare ``start`` / ``run``
# names are *not* in this map and *not* in ``__all__``; they remain
# importable via ``__getattr__`` for backward compatibility but emit a
# ``DeprecationWarning`` (see ``_DEPRECATED_ALIASES`` below).
_LAZY_ATTRS = {
    # Session decorator (THE public entry point)
    "session": ("._decorator", "session"),
    # Session lifecycle (public finalizer)
    "close": ("._lifecycle", "close"),
    "running2finished": ("._lifecycle", "running2finished"),
    # Archive helpers (bidirectional)
    "archive_session_dir": ("._lifecycle", "archive_session_dir"),
    "restore_session_archive": ("._lifecycle", "restore_session_archive"),
    "archive_existing": ("._lifecycle", "archive_existing"),
    "restore_existing": ("._lifecycle", "restore_existing"),
    # Advanced session management
    "SessionManager": ("._manager", "SessionManager"),
    # INTERNAL low-level entry points (power-user aliases). Same callables
    # the decorator orchestrates; kept under ``_`` so they do not pollute
    # the prominent ``dir(scitex_session)`` surface a scanning agent sees.
    "_start": ("._lifecycle", "start"),
    "_run": ("._decorator", "run"),
}

# Backward-compat shims: bare ``start`` / ``run`` are demoted to INTERNAL.
# Accessing them still works (so existing code does not break) but resolves
# to the underscore alias and emits a ``DeprecationWarning``. They are
# deliberately absent from ``__all__`` and from ``__dir__`` so that
# ``dir(scitex_session)`` no longer advertises them — an agent scanning the
# surface should land on ``@scitex_session.session`` instead.
_DEPRECATED_ALIASES = {
    "start": "_start",
    "run": "_run",
}


def __getattr__(name: str):
    """PEP 562 lazy-loader: import on first access, cache, return.

    The matplotlib ``Agg`` backend side-effect for headless/WSL lives in
    ``_lifecycle/_matplotlib.py`` and therefore fires the first time any
    session function is resolved here — which is also the first time pyplot
    is imported — so backend ordering is preserved.

    Deprecated bare names (``start`` / ``run``) resolve to their underscore
    aliases and emit a ``DeprecationWarning`` on *every* access. They are
    deliberately NOT cached into ``globals()`` so the warning keeps firing
    and so they never leak back into ``dir(scitex_session)``.
    """
    target = _DEPRECATED_ALIASES.get(name)
    if target is not None:
        import warnings

        warnings.warn(
            f"scitex_session.{name} is internal; use the "
            f"@scitex_session.session decorator (the supported entry "
            f"point), or scitex_session.{target} for low-level access.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Resolve via the underscore alias but do NOT cache under the bare
        # name — keep it out of globals()/dir() and keep the warning live.
        return __getattr__(target)

    spec = _LAZY_ATTRS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    mod_name, attr_name = spec
    attr = getattr(import_module(mod_name, __name__), attr_name)
    globals()[name] = attr  # cache for subsequent accesses
    return attr


def __dir__() -> list[str]:
    # Never advertise the deprecated bare ``start`` / ``run`` names — even
    # if a stray access cached one into globals(), filter it back out so
    # the prominent surface stays the ``@session`` decorator.
    names = (set(_LAZY_ATTRS) | set(globals())) - set(_DEPRECATED_ALIASES)
    return sorted(names)


# Export public API. ``start`` and ``run`` are intentionally omitted: the
# decorator ``session`` is THE entry point; ``start``/``run`` are internal
# (reach them via ``_start`` / ``_run`` if you must).
__all__ = [
    "__version__",
    # Sentinel for injected parameters
    "INJECTED",
    # Session decorator (THE public entry point)
    "session",
    # Session lifecycle finalizer
    "close",
    "running2finished",
    # Advanced session management
    "SessionManager",
    # Archive helpers (bidirectional)
    "archive_session_dir",
    "restore_session_archive",
    "archive_existing",
    "restore_existing",
]

# EOF
