#!/usr/bin/env python3
# Timestamp: "2026-05-24 (ywatanabe)"
# File: src/scitex_session/_mcp_server.py
"""MCP server for scitex-session archive helpers.

Exposes the ``archive_existing`` / ``restore_existing`` (and single-dir
helpers) Python API as MCP tools so LLM agents can compress / restore
scitex session directories from a fresh session. Tool names mirror the
public Python API in :mod:`scitex_session`; outputs are JSON-serialized
dicts (same shape the Python API returns).

The §5 ``skills_list`` / ``skills_get`` envelope tools delegate to
``scitex_dev.skills`` so agents can discover this package's skill pages
without a separate filesystem walk.

This module follows the canonical "one FastMCP instance per package"
pattern documented in ``scitex_dev/_skills/general/03_interface_03_mcp/``;
the umbrella ``scitex`` will mount this server via ``safe_mount(...,
namespace="session")``, prefixing every tool name with ``session_`` at
mount time.
"""

from __future__ import annotations

import json
from typing import Any, Optional

try:
    from fastmcp import FastMCP
except ImportError as e:  # pragma: no cover -- exercised only when extra missing
    raise ImportError(
        "scitex-session MCP server requires the `fastmcp` package. "
        "Install with: pip install 'scitex-session[mcp]' "
        "(or `pip install fastmcp>=2.0` directly)."
    ) from e

from ._lifecycle._archive import (
    archive_existing as _archive_existing,
    archive_session_dir as _archive_session_dir,
    restore_existing as _restore_existing,
    restore_session_archive as _restore_session_archive,
)

__all__ = ["mcp", "main"]

mcp = FastMCP(
    name="scitex-session",
    instructions=(
        "Tools for compressing and restoring scitex session directories. "
        "Each session-dir under FINISHED_SUCCESS becomes a single .tar.gz "
        "(1 inode vs 7) and the reverse extracts it back to a directory. "
        "Tool names mirror the public Python API in scitex_session."
    ),
)


# --------------------------------------------------------------------- #
# Archive tools — mirror the public Python API one-to-one.              #
# --------------------------------------------------------------------- #


@mcp.tool()
async def archive_existing(
    root: str,
    older_than_days: Optional[float] = None,
    format: str = "tar.gz",
    pattern: Optional[str] = None,
    dry_run: bool = True,
    max_dirs: Optional[int] = None,
) -> str:
    """Compress every session-shaped dir under ``root`` into a single archive each.

    Mirrors ``scitex_session.archive_existing``. Dry-run by default; pass
    ``dry_run=False`` to actually write.

    Returns
    -------
    str
        JSON-encoded summary dict with keys
        ``{scanned, candidates, archived, skipped, failed, bytes_in, bytes_out}``.
    """
    summary = _archive_existing(
        root=root,
        older_than_days=older_than_days,
        format=format,
        pattern=pattern,
        dry_run=dry_run,
        max_dirs=max_dirs,
    )
    return json.dumps(summary)


@mcp.tool()
async def restore_existing(
    root: str,
    pattern: str = "*.tar.gz",
    dest_root: Optional[str] = None,
    remove_archive: bool = False,
    dry_run: bool = True,
    max_files: Optional[int] = None,
) -> str:
    """Extract every matching archive under ``root`` back into a session directory.

    Mirrors ``scitex_session.restore_existing``. Dry-run by default; pass
    ``dry_run=False`` to actually write.

    Returns
    -------
    str
        JSON-encoded summary dict with keys
        ``{scanned, candidates, restored, skipped, failed}``.
    """
    summary = _restore_existing(
        root=root,
        pattern=pattern,
        dest_root=dest_root,
        remove_archive=remove_archive,
        dry_run=dry_run,
        max_files=max_files,
    )
    return json.dumps(summary)


@mcp.tool()
async def archive_session_dir(
    src_dir: str,
    format: str = "tar.gz",
    remove_src: bool = True,
) -> str:
    """Compress a single session directory into a single archive file.

    Mirrors ``scitex_session.archive_session_dir``.

    Returns
    -------
    str
        JSON-encoded ``{"archive_path": "..."}``.
    """
    p = _archive_session_dir(src_dir=src_dir, format=format, remove_src=remove_src)
    return json.dumps({"archive_path": str(p)})


@mcp.tool()
async def restore_session_archive(
    archive_path: str,
    dest_dir: Optional[str] = None,
    remove_archive: bool = False,
) -> str:
    """Extract a single session archive back into a directory.

    Mirrors ``scitex_session.restore_session_archive``.

    Returns
    -------
    str
        JSON-encoded ``{"dest_dir": "..."}``.
    """
    p = _restore_session_archive(
        archive_path=archive_path,
        dest_dir=dest_dir,
        remove_archive=remove_archive,
    )
    return json.dumps({"dest_dir": str(p)})


# --------------------------------------------------------------------- #
# §5 skills envelope — delegates to scitex_dev.skills.                  #
# --------------------------------------------------------------------- #


@mcp.tool()
async def skills_list() -> str:
    """List available skill pages for scitex-session.

    Returns
    -------
    str
        JSON-encoded ``{"skills": [{"name": ..., "description": ...}, ...]}``.
    """
    try:
        from scitex_dev import list_skills
    except ImportError:
        # scitex_dev is optional — surface a clear message rather than crashing.
        return json.dumps(
            {
                "skills": [],
                "error": "scitex_dev not installed; install scitex-dev to enable skill discovery",
            }
        )
    result = list_skills(package="scitex-session")
    return json.dumps(result, default=str)


@mcp.tool()
async def skills_get(name: Optional[str] = None) -> str:
    """Get the content of a skitex-session skill page (defaults to SKILL.md).

    Parameters
    ----------
    name
        Skill page name without ``.md`` (e.g. ``"02_quick-start"``).
        ``None`` returns ``SKILL.md``.

    Returns
    -------
    str
        JSON-encoded ``{"name": ..., "content": ...}``.
    """
    try:
        from scitex_dev import get_skill
    except ImportError:
        return json.dumps(
            {
                "name": name,
                "content": None,
                "error": "scitex_dev not installed; install scitex-dev to enable skill discovery",
            }
        )
    content = get_skill(package="scitex-session", name=name)
    return json.dumps({"name": name or "SKILL", "content": content}, default=str)


# --------------------------------------------------------------------- #
# Stdio entry point — used by the `scitex-session-mcp` console script.   #
# --------------------------------------------------------------------- #


def main(argv: Any = None) -> int:
    """Stdio MCP server entry point for ``scitex-session-mcp``.

    Parameters
    ----------
    argv
        Accepted but ignored; the FastMCP stdio transport reads from
        ``sys.stdin`` and writes to ``sys.stdout``. Present so the console
        script signature is uniform with other entry points.

    Returns
    -------
    int
        0 on clean exit, non-zero on initialisation failure.
    """
    # FastMCP exposes a synchronous ``.run()`` that handles the asyncio
    # event loop internally. Stdio is the default transport.
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# EOF
