#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/_lifecycle/_archive/_single.py
"""Single-session archive and restore helpers."""

from __future__ import annotations

import logging
import os
import shutil
import tarfile
from pathlib import Path
from typing import Optional, Union

from ._core import (
    MIN_ARCHIVE_BYTES,
    SUPPORTED_FORMATS,
    dir_size,
    format_to_mode,
    format_to_suffix,
)

logger = logging.getLogger(__name__)


def archive_session_dir(
    src_dir: Union[str, Path],
    format: str = "tar.gz",
    remove_src: bool = True,
    compresslevel: int = 1,
) -> Path:
    """Compress a single session dir into a single archive file.

    Writes to a temp path adjacent to the destination, then atomically
    renames into place. Only after the archive exists and passes a
    size sanity check do we delete the source (when ``remove_src=True``).
    On any error the source is left untouched.

    Returns
    -------
    Path
        Absolute path to the final archive file.
    """
    src = Path(src_dir)
    if not src.exists():
        raise FileNotFoundError(f"Source dir does not exist: {src}")
    if not src.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {src}")

    if format not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported archive format {format!r}; "
            f"expected one of {SUPPORTED_FORMATS}"
        )

    suffix = format_to_suffix(format)
    final_path = src.parent / (src.name + suffix)
    tmp_path = src.parent / (src.name + suffix + ".tmp")

    # Clean any stale tmp left behind by an earlier crash.
    if tmp_path.exists():
        logger.warning("Removing stale tmp archive: %s", tmp_path)
        try:
            tmp_path.unlink()
        except OSError as e:
            raise OSError(f"Could not remove stale tmp {tmp_path}: {e}") from e

    if final_path.exists():
        raise FileExistsError(
            f"Archive already exists: {final_path}. Refusing to overwrite."
        )

    mode = format_to_mode(format)

    open_kwargs = {}
    if format == "tar.gz":
        open_kwargs["compresslevel"] = compresslevel
    elif format == "tar.xz":
        open_kwargs["preset"] = compresslevel

    try:
        with tarfile.open(tmp_path, mode=mode, **open_kwargs) as tf:
            # arcname=src.name preserves the session dir name as the
            # archive's top-level directory.
            tf.add(str(src), arcname=src.name)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise

    try:
        size = tmp_path.stat().st_size
    except OSError as e:
        raise OSError(f"Archive tmp disappeared: {tmp_path}: {e}") from e

    # For very small inputs (e.g. an empty session dir in tests), the
    # archive may legitimately be smaller than 1 KB. Only enforce the
    # minimum size when the source itself has nontrivial content.
    src_bytes = dir_size(src)
    if src_bytes > MIN_ARCHIVE_BYTES and size < 64:
        tmp_path.unlink()
        raise OSError(
            f"Archive {tmp_path} suspiciously small ({size} bytes) "
            f"for source ({src_bytes} bytes); aborting."
        )

    os.replace(tmp_path, final_path)

    if remove_src:
        try:
            shutil.rmtree(src)
        except OSError as e:
            logger.warning(
                "Archive ok but could not remove source %s: %s", src, e
            )

    return final_path


def restore_session_archive(
    archive_path: Union[str, Path],
    dest_dir: Optional[Union[str, Path]] = None,
    remove_archive: bool = False,
) -> Path:
    """Extract a session archive back into a session directory.

    Extraction is done into a temp dir adjacent to the final destination
    and atomically renamed into place. If ``remove_archive=True`` the
    archive file is deleted only after a successful rename.

    Returns
    -------
    Path
        Absolute path to the restored directory.
    """
    arc = Path(archive_path)
    if not arc.exists():
        raise FileNotFoundError(f"Archive does not exist: {arc}")
    if not arc.is_file():
        raise ValueError(f"Archive is not a file: {arc}")

    if dest_dir is None:
        name = arc.name
        for suf in (".tar.gz", ".tar.xz", ".tar"):
            if name.endswith(suf):
                name = name[: -len(suf)]
                break
        dest = arc.parent / name
    else:
        dest = Path(dest_dir)

    if dest.exists():
        raise FileExistsError(
            f"Destination already exists: {dest}. Refusing to overwrite."
        )

    tmp_dest = dest.parent / (dest.name + ".restoring")
    if tmp_dest.exists():
        logger.warning("Removing stale tmp restore dir: %s", tmp_dest)
        shutil.rmtree(tmp_dest)

    tmp_dest.mkdir(parents=True, exist_ok=False)

    try:
        with tarfile.open(arc, mode="r:*") as tf:
            # Python 3.12+ requires explicit filter; "data" rejects
            # absolute paths and parent-traversal.
            try:
                tf.extractall(path=tmp_dest, filter="data")
            except TypeError:
                tf.extractall(path=tmp_dest)
    except Exception:
        shutil.rmtree(tmp_dest, ignore_errors=True)
        raise

    children = list(tmp_dest.iterdir())
    if len(children) == 1 and children[0].is_dir():
        os.replace(str(children[0]), str(dest))
        try:
            tmp_dest.rmdir()
        except OSError:
            shutil.rmtree(tmp_dest, ignore_errors=True)
    else:
        os.replace(str(tmp_dest), str(dest))

    if remove_archive:
        try:
            arc.unlink()
        except OSError as e:
            logger.warning(
                "Restore ok but could not remove archive %s: %s", arc, e
            )

    return dest


# EOF
