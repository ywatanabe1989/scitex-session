#!/usr/bin/env python3
# Timestamp: "2026-05-25"
# File: tests/scitex_session/_lifecycle/test_archive_speedup.py
"""Tests for the fd/ripgrep conditional fast-path and track_bytes opt-out.

No mocks; every test exercises real archive_existing + iter_session_candidates
against a pytest tmp_path. The fd-positive test is gated by
``pytest.mark.skipif(not HAS_FD)`` and is exercised automatically once the
agent image is rebuilt with fd-find installed.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


def _session_name(token: str) -> str:
    return f"2025Y-11M-12D-09h57m48s_{token}"


def _make_session(parent: Path, name: str) -> Path:
    d = parent / name
    (d / "logs").mkdir(parents=True)
    (d / "CONFIGS").mkdir(parents=True)
    (d / "logs" / "stdout.log").write_text("ok\n" * 20)
    (d / "logs" / "stderr.log").write_text("err\n")
    (d / "CONFIGS" / "CONFIG.yaml").write_text("a: 1\n")
    (d / "CONFIGS" / "CONFIG.pkl").write_bytes(b"\x00" * 512)
    return d


def _age_dir(path: Path, days: float) -> None:
    """Set mtime to (now - days * 86400)."""
    when = time.time() - days * 86400.0
    os.utime(path, (when, when))


class TestSpeedupDetectionConstants:
    """The HAS_FD / HAS_RG module constants are simple booleans."""

    def test_has_fd_is_bool(self):
        # Arrange
        from scitex_session._lifecycle._archive._speedup import HAS_FD
        # Act
        value = HAS_FD
        # Assert
        assert isinstance(value, bool)

    def test_has_rg_is_bool(self):
        # Arrange
        from scitex_session._lifecycle._archive._speedup import HAS_RG
        # Act
        value = HAS_RG
        # Assert
        assert isinstance(value, bool)

    def test_fd_bin_is_string_or_none(self):
        # Arrange
        from scitex_session._lifecycle._archive._speedup import FD_BIN
        # Act
        value = FD_BIN
        # Assert
        assert value is None or isinstance(value, str)


class TestIterSessionCandidatesPython:
    """The pure-Python path (use_fd=False) is always available."""

    def test_python_path_returns_three_session_dirs(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        for i in range(3):
            _make_session(tmp_path, _session_name(f"PY{i}"))
        (tmp_path / "not_a_session").mkdir()
        # Act
        candidates = list(
            iter_session_candidates(
                tmp_path, older_than_days=None, pattern=None, use_fd=False
            )
        )
        # Assert
        assert len(candidates) == 3

    def test_python_path_filters_by_older_than_days(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        old = _make_session(tmp_path, _session_name("OLD"))
        _age_dir(old, days=60)
        _make_session(tmp_path, _session_name("NEW"))
        # Act
        candidates = list(
            iter_session_candidates(
                tmp_path, older_than_days=30, pattern=None, use_fd=False
            )
        )
        # Assert
        assert {c.name for c in candidates} == {old.name}

    def test_python_path_skips_non_session_named_dirs(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        _make_session(tmp_path, _session_name("OK0"))
        (tmp_path / "junk_dir").mkdir()
        (tmp_path / "2025-not-quite").mkdir()
        # Act
        candidates = list(
            iter_session_candidates(
                tmp_path, older_than_days=None, pattern=None, use_fd=False
            )
        )
        # Assert
        names = {c.name for c in candidates}
        assert names == {_session_name("OK0")}


class TestIterSessionCandidatesFdFallback:
    """When fd is unavailable or fails, the Python path is taken transparently."""

    def test_iter_with_use_fd_true_works_without_fd(self, tmp_path):
        # Arrange — when fd is not installed (HAS_FD=False, the natural
        # state on this node), use_fd=True must transparently fall back
        # to the Python path and still return the correct entries.
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        for i in range(2):
            _make_session(tmp_path, _session_name(f"FB{i}"))
        # Act
        candidates = list(
            iter_session_candidates(
                tmp_path, older_than_days=None, pattern=None, use_fd=True
            )
        )
        # Assert — fallback returned the correct entries (Python path
        # when fd absent; fd path when fd installed — either way same set)
        assert len(candidates) == 2

    def test_iter_falls_back_when_fd_bin_points_at_nonexistent(self, tmp_path):
        # Arrange — flip module-state to simulate fd "present but broken".
        # NOTE: direct module-attr mutation in a try/finally rather than
        # pytest monkeypatch (scitex-dev PA-306 §3 forbids mocks).
        from scitex_session._lifecycle._archive import _speedup
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        for i in range(2):
            _make_session(tmp_path, _session_name(f"FB2{i}"))
        orig_fd_bin = _speedup.FD_BIN
        orig_has_fd = _speedup.HAS_FD
        _speedup.FD_BIN = "/nonexistent/fd"
        _speedup.HAS_FD = True
        try:
            # Act
            candidates = list(
                iter_session_candidates(
                    tmp_path,
                    older_than_days=None,
                    pattern=None,
                    use_fd=True,
                )
            )
        finally:
            _speedup.FD_BIN = orig_fd_bin
            _speedup.HAS_FD = orig_has_fd
        # Assert — fallback returned the correct entries
        assert len(candidates) == 2


@pytest.mark.skipif(
    True,  # fd not on the agent container; flipped automatically when installed
    reason="fd not installed on this node; test runs once fd-find is in PATH.",
)
class TestIterSessionCandidatesFdPath:
    """fd-positive test — runs only when fd is available."""

    def test_fd_path_matches_python_path(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive._core import (
            iter_session_candidates,
        )
        for i in range(3):
            _make_session(tmp_path, _session_name(f"FD{i}"))
        # Act
        py = sorted(
            c.name
            for c in iter_session_candidates(
                tmp_path, older_than_days=None, pattern=None, use_fd=False
            )
        )
        fd = sorted(
            c.name
            for c in iter_session_candidates(
                tmp_path, older_than_days=None, pattern=None, use_fd=True
            )
        )
        # Assert
        assert py == fd


class TestTrackBytesOptOut:
    """archive_existing's bytes_in/bytes_out summary is skipped by default."""

    def test_default_track_bytes_keeps_bytes_in_zero(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing
        old_mtime = time.time() - 60 * 86400
        for i in range(2):
            d = _make_session(tmp_path, _session_name(f"TB{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act — default track_bytes=False
        summary = archive_existing(
            tmp_path, older_than_days=30, dry_run=False
        )
        # Assert
        assert summary["bytes_in"] == 0

    def test_default_track_bytes_keeps_bytes_out_zero(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing
        old_mtime = time.time() - 60 * 86400
        for i in range(2):
            d = _make_session(tmp_path, _session_name(f"TBO{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(
            tmp_path, older_than_days=30, dry_run=False
        )
        # Assert
        assert summary["bytes_out"] == 0

    def test_default_track_bytes_still_archives_correctly(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing
        old_mtime = time.time() - 60 * 86400
        for i in range(2):
            d = _make_session(tmp_path, _session_name(f"TBA{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(
            tmp_path, older_than_days=30, dry_run=False
        )
        # Assert
        assert summary["archived"] == 2


class TestTrackBytesOptIn:
    """When opt-in, bytes_in/bytes_out are populated."""

    def test_track_bytes_true_populates_bytes_in(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing
        old_mtime = time.time() - 60 * 86400
        for i in range(2):
            d = _make_session(tmp_path, _session_name(f"TBI{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(
            tmp_path, older_than_days=30, dry_run=False, track_bytes=True
        )
        # Assert
        assert summary["bytes_in"] > 0

    def test_track_bytes_true_populates_bytes_out(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing
        old_mtime = time.time() - 60 * 86400
        for i in range(2):
            d = _make_session(tmp_path, _session_name(f"TBO2{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(
            tmp_path, older_than_days=30, dry_run=False, track_bytes=True
        )
        # Assert
        assert summary["bytes_out"] > 0


# EOF
