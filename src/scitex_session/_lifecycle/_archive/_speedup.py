#!/usr/bin/env python3
# Timestamp: "2026-05-25 (ywatanabe)"
# File: src/scitex_session/_lifecycle/_archive/_speedup.py
"""Optional fd/ripgrep conditional fast-path helpers.

This module detects whether `fd` (modern parallel `find` replacement) and
`rg` (ripgrep) are installed at import time. If they are, scoped helpers
can dispatch to them for a measurable speedup on large flat directories;
otherwise callers fall back to the existing Python `iterdir + stat`
implementation.

Public surface
--------------
- ``HAS_FD: bool`` / ``FD_BIN: Optional[str]``
- ``HAS_RG: bool`` / ``RG_BIN: Optional[str]``
- ``iter_session_candidates_fd(root, older_than_days, pattern)`` —
  candidate enumeration via an ``fd`` subprocess. Returns Paths.
  Raises ``FdNotAvailableError`` if fd is missing, and any
  ``subprocess.CalledProcessError`` is propagated to the caller so the
  Python fallback can be invoked transparently.

Rationale
---------
``Path.iterdir() + entry.stat().st_mtime`` is single-threaded; on a
``FINISHED_SUCCESS/`` dir with 176k subdirs (the dominant neurovista
hotspot), the per-entry ``stat()`` syscalls serialize. ``fd`` walks in
parallel and uses fewer syscalls per dir entry.

This module is a thin wrapper. The decision to use fd is made by the
caller (``iter_session_candidates`` in ``_core.py``); this module just
provides the optional implementation. ``rg`` is detected for future
content-search helpers but is not exercised here.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

from ._core import is_session_dir_name

logger = logging.getLogger(__name__)


def _detect(*names: str) -> Optional[str]:
    """Return the first available binary path among ``names``, else None."""
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    return None


FD_BIN: Optional[str] = _detect("fd", "fdfind")
HAS_FD: bool = FD_BIN is not None

RG_BIN: Optional[str] = _detect("rg")
HAS_RG: bool = RG_BIN is not None


class FdNotAvailableError(RuntimeError):
    """Raised when an fd-path helper is called but fd is not installed."""


def iter_session_candidates_fd(
    root: Path,
    older_than_days: Optional[float],
    pattern: Optional[str],
) -> List[Path]:
    """Enumerate scitex-session-shaped subdirs of ``root`` via ``fd``.

    Equivalent to ``_core.iter_session_candidates`` but dispatches to an
    ``fd`` subprocess. ``fd`` walks in parallel and is materially faster
    than ``iterdir + stat`` on dirs with tens of thousands of entries
    (observed: 56k entries/sec single-thread; fd typically ~3-6x).

    Parameters
    ----------
    root : Path
        Directory to scan. Only direct children are considered.
    older_than_days : float or None
        Apply mtime cutoff via ``fd --changed-before <N>d``. ``None``
        means no mtime filter (fd lists every direct subdir).
    pattern : str or None
        Substring filter applied in Python after fd returns. (We do this
        in Python rather than passing fd a regex because the regex we
        need — ``SESSION_DIR_PATTERN`` — must be applied for safety
        anyway; running fd with a more permissive filter and then doing
        the regex pass keeps the surface tight.)

    Returns
    -------
    list of Path
        Absolute paths to scitex-session-shaped subdirs sorted by name.

    Raises
    ------
    FdNotAvailableError
        If ``FD_BIN`` is None (fd not installed).
    subprocess.CalledProcessError
        If fd returns a non-zero exit code. Caller should catch and
        fall back to the Python path.
    """
    if FD_BIN is None:
        raise FdNotAvailableError(
            "fd is not installed; install fd-find or use the Python path."
        )

    cmd: List[str] = [
        FD_BIN,
        "--type",
        "d",
        "--max-depth",
        "1",
        "--absolute-path",
    ]
    if older_than_days is not None:
        # fd's --changed-before syntax accepts ``<N>d`` for days.
        cmd += ["--changed-before", f"{int(older_than_days)}d"]
    # Match anything at this depth; we filter by regex + substring below.
    cmd += [".", str(root)]

    completed = subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
        timeout=300,
    )
    raw_paths = completed.stdout.splitlines()

    candidates: List[Path] = []
    for raw in raw_paths:
        p = Path(raw)
        name = p.name
        if name == root.name and p.resolve() == root.resolve():
            # fd may include the root itself when --max-depth 1; skip.
            continue
        if not is_session_dir_name(name):
            continue
        if pattern is not None and pattern not in name:
            continue
        candidates.append(p)
    candidates.sort(key=lambda x: x.name)
    return candidates


__all__ = [
    "FD_BIN",
    "HAS_FD",
    "RG_BIN",
    "HAS_RG",
    "FdNotAvailableError",
    "iter_session_candidates_fd",
]


# EOF
