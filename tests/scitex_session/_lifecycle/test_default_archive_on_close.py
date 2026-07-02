#!/usr/bin/env python3
# Timestamp: "2026-06-18"
# File: tests/scitex_session/_lifecycle/test_default_archive_on_close.py
"""Tests that compression is the DEFAULT on session close.

Source fix for the Spartan inode crisis: every ``close()`` should
collapse the FINISHED run dir (~6 loose files) into a single
``.tar.gz`` (1 inode) by default, while staying opt-out via the
``archive_format`` kwarg or ``CONFIG.SESSION.ARCHIVE_FORMAT``.

No mocks; the real ``start()`` / ``close()`` lifecycle is exercised
against a pytest ``tmp_path``.
"""

from __future__ import annotations

import os
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("natsort")
pytest.importorskip("h5py")
pytest.importorskip("zarr")


def _finished_dir(sdir: str) -> Path:
    """RUNNING/<session> -> FINISHED_SUCCESS/<session> (loose dir form)."""
    return Path(sdir.replace("RUNNING/", "FINISHED_SUCCESS/"))


def _finished_archive(sdir: str) -> Path:
    """RUNNING/<session> -> FINISHED_SUCCESS/<session>.tar.gz."""
    return Path(sdir.replace("RUNNING/", "FINISHED_SUCCESS/") + ".tar.gz")


def _start(tmp_path: Path, name: str):
    from scitex_session._lifecycle import start

    sdir = os.path.join(str(tmp_path), "out", "RUNNING", name)
    CONFIG, _, _, _, _, _ = start(
        sys=None, plt=None, file="/tmp/test.py", sdir=sdir, verbose=False
    )
    return CONFIG, sdir


class TestDefaultArchiveOnClose:
    """Default close() archives the run dir into a single .tar.gz."""

    def test_default_close_creates_tar_gz_archive(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "default_archive")
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert _finished_archive(sdir).is_file()

    def test_default_close_removes_loose_finished_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "no_loose_dir")
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert not _finished_dir(sdir).exists()

    def test_default_close_removes_running_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "running_gone")
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert not os.path.exists(sdir)

    def test_default_close_archive_is_single_inode(self, tmp_path):
        # Arrange — exactly one filesystem entry should remain in the
        # FINISHED_SUCCESS dir (the archive), proving ~N files -> 1 inode.
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "single_inode")
        finished_parent = _finished_archive(sdir).parent
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        entries = list(finished_parent.iterdir())
        # Assert
        assert entries == [_finished_archive(sdir)]


class TestArchiveOnCloseOptOut:
    """archive_format=None / "" keeps the loose dir (opt-out)."""

    def test_explicit_none_kwarg_keeps_loose_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "kwarg_none")
        # Act
        close(CONFIG, verbose=False, exit_status=0, archive_format=None)
        # Assert
        assert _finished_dir(sdir).is_dir()

    def test_explicit_none_kwarg_creates_no_archive(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "kwarg_none_noarc")
        # Act
        close(CONFIG, verbose=False, exit_status=0, archive_format=None)
        # Assert
        assert not _finished_archive(sdir).exists()

    def test_empty_string_kwarg_keeps_loose_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "kwarg_empty")
        # Act
        close(CONFIG, verbose=False, exit_status=0, archive_format="")
        # Assert
        assert _finished_dir(sdir).is_dir()

    def test_config_session_archive_format_none_disables(self, tmp_path):
        # Arrange — CONFIG.SESSION.ARCHIVE_FORMAT=None opts out for a
        # close() that passes no explicit archive_format.
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "cfg_none")
        CONFIG["SESSION"] = {"ARCHIVE_FORMAT": None}
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert _finished_dir(sdir).is_dir()


class TestArchiveFormatOverride:
    """Config / kwarg can select a non-default archive format."""

    def test_config_session_archive_format_tar_used(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "cfg_tar")
        CONFIG["SESSION"] = {"ARCHIVE_FORMAT": "tar"}
        # Act
        close(CONFIG, verbose=False, exit_status=0)
        # Assert
        assert Path(sdir.replace("RUNNING/", "FINISHED_SUCCESS/") + ".tar").is_file()

    def test_explicit_kwarg_overrides_config(self, tmp_path):
        # Arrange — explicit kwarg None must win over a config that asks
        # for tar.gz (kwarg precedence).
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "kwarg_over_cfg")
        CONFIG["SESSION"] = {"ARCHIVE_FORMAT": "tar.gz"}
        # Act
        close(CONFIG, verbose=False, exit_status=0, archive_format=None)
        # Assert
        assert _finished_dir(sdir).is_dir()


class TestArchiveOnCloseRoundTrip:
    """A default-close archive restores the run contents identically."""

    def test_restore_recovers_config_yaml(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close
        from scitex_session._lifecycle._archive import restore_session_archive

        CONFIG, sdir = _start(tmp_path, "roundtrip")
        close(CONFIG, verbose=False, exit_status=0)
        archive = _finished_archive(sdir)
        # Act
        restored = restore_session_archive(
            archive, dest_dir=tmp_path / "restored", remove_archive=False
        )
        # Assert — CONFIGS/CONFIG.yaml is written by save_configs() on close.
        assert (restored / "CONFIGS" / "CONFIG.yaml").is_file()

    def test_archive_members_include_configs(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle import close

        CONFIG, sdir = _start(tmp_path, "members")
        close(CONFIG, verbose=False, exit_status=0)
        archive = _finished_archive(sdir)
        # Act
        with tarfile.open(archive, "r:*") as tf:
            members = tf.getnames()
        has_config = any(m.endswith("/CONFIGS/CONFIG.yaml") for m in members)
        # Assert
        assert has_config


class TestRunning2FinishedDefaultUnchanged:
    """running2finished (the mechanism) keeps archive_format=None default.

    Policy lives in close(); the low-level mover must not archive unless
    explicitly told, so direct callers / the finalize_session MCP tool
    keep their predictable copytree-only contract.
    """

    def test_running2finished_default_keeps_loose_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name = "2025Y-11M-12D-09h57m48s_R2FD"
        sdir_run = tmp_path / "outroot" / "RUNNING" / name
        (sdir_run / "logs").mkdir(parents=True)
        (sdir_run / "logs" / "stdout.log").write_text("hi\n")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        running2finished(CONFIG, exit_status=0)
        # Assert
        assert (tmp_path / "outroot" / "FINISHED_SUCCESS" / name).is_dir()


# EOF
