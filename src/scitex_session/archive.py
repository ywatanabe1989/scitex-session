#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/archive.py
"""Public CLI shim for scitex_session archive helpers.

Invocation:
    python -m scitex_session.archive compress ROOT [opts]
    python -m scitex_session.archive extract ROOT [opts]

The leading-underscore ``_archive`` package under ``_lifecycle`` holds
the implementation; this module is the public entrypoint.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Optional, Sequence

from ._lifecycle._archive import (
    archive_existing,
    archive_session_dir,
    restore_existing,
    restore_session_archive,
)

__all__ = [
    "archive_session_dir",
    "restore_session_archive",
    "archive_existing",
    "restore_existing",
    "main",
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scitex_session.archive",
        description=(
            "Compress / extract scitex-session output directories. "
            "Replaces a per-session directory of small files with a "
            "single tar.gz archive (or vice versa)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # compress
    p_c = sub.add_parser(
        "compress",
        help="Compress every session-dir under ROOT into a single archive each.",
    )
    p_c.add_argument("root", help="Directory containing session subdirectories.")
    p_c.add_argument(
        "--older-than-days",
        type=float,
        default=None,
        help="Only compress sessions older than this many days.",
    )
    p_c.add_argument(
        "--format",
        choices=("tar.gz", "tar", "tar.xz"),
        default="tar.gz",
        help="Archive format (default: tar.gz).",
    )
    p_c.add_argument(
        "--pattern",
        default=None,
        help="Substring filter on session-dir names.",
    )
    p_c.add_argument(
        "--remove-src",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Remove source dir after a verified archive write.",
    )
    p_c.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Dry-run by default; pass --no-dry-run (or --execute) to write.",
    )
    p_c.add_argument(
        "--execute",
        dest="dry_run",
        action="store_false",
        help="Alias for --no-dry-run.",
    )
    p_c.add_argument(
        "--max-dirs",
        type=int,
        default=10000,
        help="Safety cap (default: 10000). Set to 0 to disable.",
    )
    p_c.add_argument(
        "--track-bytes",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Compute bytes_in/bytes_out summary by walking each candidate "
            "(adds per-session overhead; off by default)."
        ),
    )
    p_c.add_argument(
        "--use-fd",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Use 'fd' subprocess for candidate enumeration when available "
            "(falls back to Python iterdir+stat otherwise)."
        ),
    )
    p_c.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging.",
    )

    # extract
    p_x = sub.add_parser(
        "extract",
        help="Extract every matching archive under ROOT back into a directory.",
    )
    p_x.add_argument("root", help="Directory containing archive files.")
    p_x.add_argument(
        "--pattern",
        default="*.tar.gz",
        help="Glob pattern (default: '*.tar.gz').",
    )
    p_x.add_argument(
        "--dest",
        default=None,
        help="Destination root; defaults to ROOT itself.",
    )
    p_x.add_argument(
        "--remove-archive",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Remove archive file after a verified extract.",
    )
    p_x.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Dry-run by default; pass --no-dry-run (or --execute) to write.",
    )
    p_x.add_argument(
        "--execute",
        dest="dry_run",
        action="store_false",
        help="Alias for --no-dry-run.",
    )
    p_x.add_argument(
        "--max-files",
        type=int,
        default=10000,
        help="Safety cap (default: 10000). Set to 0 to disable.",
    )
    p_x.add_argument(
        "--track-bytes",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="API-symmetric with compress; no-op for extract (no extra walk).",
    )
    p_x.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging.",
    )

    return parser


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _format_summary(prefix: str, summary: dict) -> str:
    parts = [f"{k}={v}" for k, v in summary.items()]
    return f"{prefix}: " + ", ".join(parts)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if args.cmd == "compress":
        max_dirs = args.max_dirs if args.max_dirs and args.max_dirs > 0 else None
        summary = archive_existing(
            root=args.root,
            older_than_days=args.older_than_days,
            format=args.format,
            pattern=args.pattern,
            dry_run=args.dry_run,
            max_dirs=max_dirs,
            track_bytes=args.track_bytes,
            use_fd=args.use_fd,
        )
        mode = "dry-run" if args.dry_run else "executed"
        print(_format_summary(f"compress ({mode})", summary))
        return 0

    if args.cmd == "extract":
        max_files = args.max_files if args.max_files and args.max_files > 0 else None
        summary = restore_existing(
            root=args.root,
            pattern=args.pattern,
            dest_root=args.dest,
            remove_archive=args.remove_archive,
            dry_run=args.dry_run,
            max_files=max_files,
            track_bytes=args.track_bytes,
        )
        mode = "dry-run" if args.dry_run else "executed"
        print(_format_summary(f"extract ({mode})", summary))
        return 0

    parser.error(f"unknown command: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())


# EOF
