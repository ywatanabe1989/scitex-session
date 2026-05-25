#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/_lifecycle/_archive/_bulk.py
"""Bulk archive / restore over a directory of sessions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from ._core import (
    dir_size,
    format_to_suffix,
    is_session_dir_name,
    iter_session_candidates,
    validate_root,
)
from ._single import archive_session_dir, restore_session_archive

logger = logging.getLogger(__name__)


def archive_existing(
    root: Union[str, Path],
    older_than_days: Optional[float] = None,
    format: str = "tar.gz",
    pattern: Optional[str] = None,
    dry_run: bool = True,
    max_dirs: Optional[int] = None,
    track_bytes: bool = False,
    use_fd: bool = True,
) -> dict:
    """Bulk compress every session-shaped child of ``root``.

    Parameters
    ----------
    track_bytes : bool, default False
        When True, run a per-candidate ``dir_size()`` (os.walk +
        getsize per file) so that ``bytes_in`` / ``bytes_out`` in the
        returned summary are populated. Off by default because the
        size accounting adds a measurable per-session overhead on top
        of the mandatory tar IO (observed on neurovista 2026-05-25:
        80,408 sessions / 47 min wall-clock — the byte stats are a
        meaningful contributor).
    use_fd : bool, default True
        Forwarded to ``iter_session_candidates``. When True and ``fd``
        is installed, candidate enumeration uses the parallel
        subprocess path; otherwise the Python ``iterdir+stat`` path.

    Returns
    -------
    dict
        Summary {scanned, candidates, archived, skipped, failed,
        bytes_in, bytes_out}. ``bytes_in`` and ``bytes_out`` stay at 0
        when ``track_bytes`` is False.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Root does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root_path}")
    validate_root(root_path)

    suffix = format_to_suffix(format)

    summary = {
        "scanned": 0,
        "candidates": 0,
        "archived": 0,
        "skipped": 0,
        "failed": 0,
        "bytes_in": 0,
        "bytes_out": 0,
    }

    for _entry in root_path.iterdir():
        summary["scanned"] += 1

    for candidate in iter_session_candidates(
        root_path, older_than_days, pattern, use_fd=use_fd
    ):
        archive_path = candidate.parent / (candidate.name + suffix)
        if archive_path.exists():
            summary["skipped"] += 1
            logger.info("Skipping (archive exists): %s", archive_path)
            continue

        summary["candidates"] += 1
        if max_dirs is not None and summary["candidates"] > max_dirs:
            summary["candidates"] -= 1
            logger.info("Reached max_dirs=%d cap; stopping.", max_dirs)
            break

        if track_bytes:
            try:
                src_bytes = dir_size(candidate)
            except OSError:
                src_bytes = 0
            summary["bytes_in"] += src_bytes
        else:
            src_bytes = 0

        if dry_run:
            if track_bytes:
                logger.info(
                    "[dry-run] would archive: %s (%d bytes)",
                    candidate,
                    src_bytes,
                )
            else:
                logger.info("[dry-run] would archive: %s", candidate)
            continue

        try:
            archive_path = archive_session_dir(
                candidate, format=format, remove_src=True
            )
            summary["archived"] += 1
            if track_bytes:
                try:
                    out_bytes = archive_path.stat().st_size
                except OSError:
                    out_bytes = 0
                summary["bytes_out"] += out_bytes
                logger.info(
                    "Archived: %s -> %s (%d -> %d bytes)",
                    candidate,
                    archive_path,
                    src_bytes,
                    out_bytes,
                )
            else:
                logger.info("Archived: %s -> %s", candidate, archive_path)
        except Exception as e:
            summary["failed"] += 1
            logger.warning("Failed to archive %s: %s", candidate, e)

    return summary


def restore_existing(
    root: Union[str, Path],
    pattern: str = "*.tar.gz",
    dest_root: Optional[Union[str, Path]] = None,
    remove_archive: bool = False,
    dry_run: bool = True,
    max_files: Optional[int] = None,
    track_bytes: bool = False,
) -> dict:
    """Bulk restore every archive matching ``pattern`` directly under ``root``.

    Returns
    -------
    dict
        Summary {scanned, candidates, restored, skipped, failed}.
    """
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"Root does not exist: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Root is not a directory: {root_path}")
    validate_root(root_path)

    dest_root_path = Path(dest_root) if dest_root is not None else root_path
    if dest_root is not None:
        validate_root(dest_root_path)
        dest_root_path.mkdir(parents=True, exist_ok=True)

    summary = {
        "scanned": 0,
        "candidates": 0,
        "restored": 0,
        "skipped": 0,
        "failed": 0,
    }

    archives = sorted(p for p in root_path.glob(pattern) if p.is_file())
    summary["scanned"] = len(archives)

    for arc in archives:
        name = arc.name
        stem = name
        for suf in (".tar.gz", ".tar.xz", ".tar"):
            if stem.endswith(suf):
                stem = stem[: -len(suf)]
                break
        if not is_session_dir_name(stem):
            summary["skipped"] += 1
            logger.info("Skipping (non-session-name): %s", arc)
            continue

        dest = dest_root_path / stem
        if dest.exists():
            summary["skipped"] += 1
            logger.info("Skipping (dest exists): %s", dest)
            continue

        summary["candidates"] += 1
        if max_files is not None and summary["candidates"] > max_files:
            summary["candidates"] -= 1
            logger.info("Reached max_files=%d cap; stopping.", max_files)
            break

        if dry_run:
            logger.info("[dry-run] would restore: %s -> %s", arc, dest)
            continue

        try:
            restore_session_archive(
                arc, dest_dir=dest, remove_archive=remove_archive
            )
            summary["restored"] += 1
            logger.info("Restored: %s -> %s", arc, dest)
        except Exception as e:
            summary["failed"] += 1
            logger.warning("Failed to restore %s: %s", arc, e)

    return summary


# EOF
