#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: tests/scitex_session/test_cli.py
"""Subprocess CLI tests for `python -m scitex_session.archive`.

No mocks; the CLI is exercised in a real child interpreter with
PYTHONPATH wired to the in-tree src/ so the editable install is
not picked up.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _session_name(token: str = "CLI0") -> str:
    return f"2025Y-11M-12D-09h57m48s_{token}"


def _make_session(parent: Path, name: str) -> Path:
    d = parent / name
    (d / "logs").mkdir(parents=True)
    (d / "CONFIGS").mkdir(parents=True)
    (d / "logs" / "stdout.log").write_text("ok\n" * 30)
    (d / "logs" / "stderr.log").write_text("err\n")
    (d / "CONFIGS" / "CONFIG.yaml").write_text("a: 1\n")
    (d / "CONFIGS" / "CONFIG.pkl").write_bytes(b"\x00" * 512)
    return d


def _run_cli(*args, env=None) -> subprocess.CompletedProcess:
    src_dir = Path(__file__).resolve().parents[2] / "src"
    e = os.environ.copy()
    e["PYTHONPATH"] = f"{src_dir}{os.pathsep}{e.get('PYTHONPATH', '')}"
    if env:
        e.update(env)
    return subprocess.run(
        [sys.executable, "-m", "scitex_session.archive", *args],
        env=e,
        capture_output=True,
        text=True,
        timeout=60,
    )


class TestCliCompressDryRun:
    """compress --dry-run reports candidates without touching disk."""

    def test_compress_dry_run_exits_zero(self, tmp_path):
        # Arrange
        _make_session(tmp_path, _session_name("DRY0"))
        _make_session(tmp_path, _session_name("DRY1"))
        # Act
        cp = _run_cli("compress", str(tmp_path), "--dry-run")
        # Assert
        assert cp.returncode == 0, cp.stderr

    def test_compress_dry_run_reports_two_candidates(self, tmp_path):
        # Arrange
        _make_session(tmp_path, _session_name("DRC0"))
        _make_session(tmp_path, _session_name("DRC1"))
        # Act
        cp = _run_cli("compress", str(tmp_path), "--dry-run")
        # Assert
        assert "candidates=2" in cp.stdout

    def test_compress_dry_run_does_not_create_archives(self, tmp_path):
        # Arrange
        _make_session(tmp_path, _session_name("DRN0"))
        _make_session(tmp_path, _session_name("DRN1"))
        # Act
        _run_cli("compress", str(tmp_path), "--dry-run")
        # Assert
        assert list(tmp_path.glob("*.tar.gz")) == []


class TestCliCompressExecute:
    """compress --execute writes archives and removes source dirs."""

    def test_execute_exits_zero(self, tmp_path):
        # Arrange
        _make_session(tmp_path, _session_name("EXZ"))
        # Act
        cp = _run_cli("compress", str(tmp_path), "--execute")
        # Assert
        assert cp.returncode == 0, cp.stderr

    def test_execute_creates_tar_gz_archive(self, tmp_path):
        # Arrange
        name = _session_name("EXC")
        _make_session(tmp_path, name)
        # Act
        _run_cli("compress", str(tmp_path), "--execute")
        # Assert
        assert (tmp_path / (name + ".tar.gz")).exists()

    def test_execute_removes_source_dir(self, tmp_path):
        # Arrange
        name = _session_name("EXR")
        src = _make_session(tmp_path, name)
        # Act
        _run_cli("compress", str(tmp_path), "--execute")
        # Assert
        assert not src.exists()


class TestCliExtractExecute:
    """extract --execute round-trips an archive back into a directory."""

    def test_extract_restores_session_directory(self, tmp_path):
        # Arrange
        name = _session_name("XR")
        _make_session(tmp_path, name)
        _run_cli("compress", str(tmp_path), "--execute")
        # Act
        _run_cli("extract", str(tmp_path), "--execute")
        # Assert
        assert (tmp_path / name).is_dir()

    def test_extract_restores_log_file_content(self, tmp_path):
        # Arrange
        name = _session_name("XF")
        _make_session(tmp_path, name)
        _run_cli("compress", str(tmp_path), "--execute")
        # Act
        _run_cli("extract", str(tmp_path), "--execute")
        # Assert
        assert (tmp_path / name / "logs" / "stdout.log").exists()


class TestCliHelp:
    """The CLI exposes both subcommands in --help output."""

    def test_help_exits_zero(self, tmp_path):
        # Arrange
        argv = ["--help"]
        # Act
        cp = _run_cli(*argv)
        # Assert
        assert cp.returncode == 0

    def test_help_lists_compress_subcommand(self, tmp_path):
        # Arrange
        argv = ["--help"]
        # Act
        cp = _run_cli(*argv)
        # Assert
        assert "compress" in cp.stdout

    def test_help_lists_extract_subcommand(self, tmp_path):
        # Arrange
        argv = ["--help"]
        # Act
        cp = _run_cli(*argv)
        # Assert
        assert "extract" in cp.stdout


# EOF
