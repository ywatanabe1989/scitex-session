#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: tests/scitex_session/test_mcp_server.py
"""Tests for scitex_session._mcp_server.

These tests skip cleanly when `fastmcp` is unavailable so the suite
stays green for users without the ``mcp`` extra. No mocks — the real
FastMCP instance is exercised against a pytest tmp_path.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

# Skip the whole module if the optional `fastmcp` dep is not present.
pytest.importorskip("fastmcp")

from fastmcp import FastMCP  # noqa: E402  (after importorskip)


def _session_name(token: str = "MCP0") -> str:
    return f"2025Y-11M-12D-09h57m48s_{token}"


def _make_session_dir(parent: Path, name: str) -> Path:
    d = parent / name
    (d / "logs").mkdir(parents=True)
    (d / "CONFIGS").mkdir(parents=True)
    (d / "logs" / "stdout.log").write_text("ok\n" * 20)
    (d / "logs" / "stderr.log").write_text("warn\n" * 4)
    (d / "CONFIGS" / "CONFIG.yaml").write_text("key: value\n" * 30)
    (d / "CONFIGS" / "CONFIG.pkl").write_bytes(b"\x00" * 512)
    return d


def _list_tool_names() -> set[str]:
    """Synchronously list tool names on the module-level mcp instance."""
    from scitex_session._mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    return {t.name for t in tools}


def _call_tool(name: str, **kwargs):
    """Invoke a tool on the module-level mcp instance and normalise the result.

    FastMCP 2.x vs 3.x return slightly different result shapes; this
    helper collapses both to the underlying JSON payload (a dict) so
    tests have a single assertion target.
    """
    from scitex_session._mcp_server import mcp

    async def _run():
        result = await mcp.call_tool(name, kwargs)
        # FastMCP 3.x: structured_content with optional {"result": "<json>"}.
        sc = getattr(result, "structured_content", None)
        if sc:
            if (
                isinstance(sc, dict)
                and "result" in sc
                and isinstance(sc["result"], str)
            ):
                return json.loads(sc["result"])
            if isinstance(sc, dict):
                return sc
        # FastMCP content blocks (any version).
        blocks = getattr(result, "content", None)
        if blocks:
            text = getattr(blocks[0], "text", None)
            if text:
                return json.loads(text)
        # FastMCP 2.x bare string.
        if isinstance(result, str):
            return json.loads(result)
        raise AssertionError(f"unexpected call_tool result shape: {type(result)!r}")

    return asyncio.run(_run())


class TestMcpInstance:
    """The module-level ``mcp`` object is a FastMCP server."""

    def test_mcp_is_fastmcp_instance(self):
        # Arrange
        from scitex_session._mcp_server import mcp
        # Act
        is_instance = isinstance(mcp, FastMCP)
        # Assert
        assert is_instance

    def test_mcp_server_name_is_scitex_session(self):
        # Arrange
        from scitex_session._mcp_server import mcp
        # Act
        name = getattr(mcp, "name", None) or getattr(mcp, "_name", None)
        # Assert
        assert name == "scitex-session"

    def test_main_entrypoint_is_callable(self):
        # Arrange
        from scitex_session._mcp_server import main
        # Act
        ok = callable(main)
        # Assert
        assert ok


class TestRegisteredTools:
    """The required tools (archive helpers + §5 skills envelope) are registered."""

    def test_archive_existing_registered(self):
        # Arrange
        # Act
        names = _list_tool_names()
        # Assert
        assert "archive_existing" in names

    def test_restore_existing_registered(self):
        # Arrange
        # Act
        names = _list_tool_names()
        # Assert
        assert "restore_existing" in names

    def test_archive_session_dir_registered(self):
        # Arrange
        # Act
        names = _list_tool_names()
        # Assert
        assert "archive_session_dir" in names

    def test_restore_session_archive_registered(self):
        # Arrange
        # Act
        names = _list_tool_names()
        # Assert
        assert "restore_session_archive" in names

    def test_skills_list_registered(self):
        # Arrange — §5 mandates `skills_list` on every SciTeX MCP server.
        # Act
        names = _list_tool_names()
        # Assert
        assert "skills_list" in names

    def test_skills_get_registered(self):
        # Arrange — §5 mandates `skills_get` on every SciTeX MCP server.
        # Act
        names = _list_tool_names()
        # Assert
        assert "skills_get" in names


class TestArchiveExistingTool:
    """``archive_existing`` tool returns a JSON summary against real dirs."""

    def test_dry_run_summary_has_expected_keys(self, tmp_path: Path):
        # Arrange — empty root, dry-run.
        # Act
        summary = _call_tool("archive_existing", root=str(tmp_path), dry_run=True)
        # Assert
        assert set(summary).issuperset(
            {
                "scanned",
                "candidates",
                "archived",
                "skipped",
                "failed",
                "bytes_in",
                "bytes_out",
            }
        )

    def test_empty_root_has_zero_candidates(self, tmp_path: Path):
        # Arrange — empty root, dry-run.
        # Act
        summary = _call_tool("archive_existing", root=str(tmp_path), dry_run=True)
        # Assert
        assert summary["candidates"] == 0

    def test_dry_run_finds_three_session_dirs(self, tmp_path: Path):
        # Arrange — three session-shaped dirs under tmp_path.
        for i in range(3):
            _make_session_dir(tmp_path, _session_name(f"MCP{i}"))
        # Act
        summary = _call_tool("archive_existing", root=str(tmp_path), dry_run=True)
        # Assert
        assert summary["candidates"] == 3

    def test_dry_run_does_not_create_archives(self, tmp_path: Path):
        # Arrange — three session-shaped dirs under tmp_path.
        for i in range(3):
            _make_session_dir(tmp_path, _session_name(f"MCN{i}"))
        # Act
        _call_tool("archive_existing", root=str(tmp_path), dry_run=True)
        # Assert
        assert list(tmp_path.glob("*.tar.gz")) == []


# EOF
