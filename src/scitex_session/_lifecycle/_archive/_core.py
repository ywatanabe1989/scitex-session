#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/_lifecycle/_archive/_core.py
"""Shared constants and small helpers for the archive subpackage."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Iterable, Optional
import time

logger = logging.getLogger(__name__)

# A scitex-session session dir name looks like:
#   2025Y-11M-12D-09h57m48s_NLRB
SESSION_DIR_PATTERN = re.compile(
    r"^\d{4}Y-\d{2}M-\d{2}D-\d{2}h\d{2}m\d{2}s_[A-Za-z0-9]+$"
)

# Minimum archive size (bytes) we accept as "valid" before deleting the
# source dir. A gzip header alone is ~20 bytes; a real tar.gz of any
# session is several hundred bytes minimum.
MIN_ARCHIVE_BYTES = 1024

# Paths we refuse to touch even if asked.
_FORBIDDEN_ROOTS = {
    Path("/"),
    Path("/home"),
    Path("/root"),
    Path("/etc"),
    Path("/usr"),
    Path("/var"),
    Path("/boot"),
    Path("/sys"),
    Path("/proc"),
    Path("/dev"),
}

_FORBIDDEN_BASENAMES = {".git", ".claude"}

SUPPORTED_FORMATS = ("tar.gz", "tar", "tar.xz")


def format_to_mode(format: str) -> str:
    """Map our public format names to tarfile mode strings."""
    if format == "tar.gz":
        return "w:gz"
    if format == "tar":
        return "w"
    if format == "tar.xz":
        return "w:xz"
    raise ValueError(
        f"Unsupported archive format {format!r}; "
        f"expected one of {SUPPORTED_FORMATS}"
    )


def format_to_suffix(format: str) -> str:
    """Map our public format names to file suffixes."""
    if format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported archive format {format!r}; "
            f"expected one of {SUPPORTED_FORMATS}"
        )
    return "." + format


def validate_root(root: Path) -> Path:
    """Refuse to touch dangerous filesystem roots."""
    resolved = root.resolve()
    if resolved in _FORBIDDEN_ROOTS:
        raise ValueError(f"Refusing to operate on forbidden root: {resolved}")
    for part in resolved.parts:
        if part in _FORBIDDEN_BASENAMES:
            raise ValueError(
                f"Refusing to operate on path containing {part!r}: {resolved}"
            )
    return resolved


def is_session_dir_name(name: str) -> bool:
    return bool(SESSION_DIR_PATTERN.match(name))


def dir_size(path: Path) -> int:
    """Total byte size of all regular files under path."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def iter_session_candidates_python(
    root: Path,
    older_than_days: Optional[float],
    pattern: Optional[str],
) -> Iterable[Path]:
    """Pure-Python ``iterdir + stat`` enumeration (always available)."""
    now = time.time()
    cutoff = now - older_than_days * 86400.0 if older_than_days else None
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if not is_session_dir_name(name):
            continue
        if pattern is not None and pattern not in name:
            continue
        if cutoff is not None:
            try:
                if entry.stat().st_mtime > cutoff:
                    continue
            except OSError:
                continue
        yield entry


def iter_session_candidates(
    root: Path,
    older_than_days: Optional[float],
    pattern: Optional[str],
    use_fd: bool = True,
) -> Iterable[Path]:
    """Yield direct children of ``root`` that look like session dirs.

    If ``use_fd=True`` (default) and ``fd`` is installed, dispatches to
    the parallel-subprocess implementation in ``_speedup.py``. On any
    fd failure the function falls back to the pure-Python path
    transparently. ``use_fd=False`` forces the Python path (useful in
    tests and when debugging fd output).
    """
    if use_fd:
        try:
            # Local import to avoid a hard dep on the speedup module
            # during collection / cyclic-import edge cases.
            from ._speedup import (
                FdNotAvailableError,
                HAS_FD,
                iter_session_candidates_fd,
            )

            if HAS_FD:
                try:
                    candidates = iter_session_candidates_fd(
                        root, older_than_days, pattern
                    )
                    yield from candidates
                    return
                except FdNotAvailableError:
                    pass
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "fd fast-path failed (%s); falling back to Python iterdir+stat.",
                        e,
                    )
        except Exception as e:  # noqa: BLE001
            logger.debug("_speedup import failed: %s; using Python path.", e)

    yield from iter_session_candidates_python(root, older_than_days, pattern)


# EOF
