#!/usr/bin/env python3
# Timestamp: "2026-05-24"
# File: tests/scitex_session/_lifecycle/test_archive.py
"""Round-trip and safety tests for scitex_session._lifecycle._archive.

No mocks; every test exercises the real archive_session_dir,
restore_session_archive, archive_existing, restore_existing and
running2finished collaborators against a pytest tmp_path.
"""

from __future__ import annotations

import hashlib
import io
import os
import tarfile
import time
from pathlib import Path

import pytest


def _session_name(year=2025, month=11, day=12, h=9, m=57, s=48, token="NLRB"):
    """Build a name that matches the session-dir regex."""
    return f"{year:04d}Y-{month:02d}M-{day:02d}D-{h:02d}h{m:02d}m{s:02d}s_{token}"


def _make_session_dir(parent: Path, name: str, content_size: int = 4096) -> Path:
    """Build a realistic 4-file session dir layout under parent/name/."""
    session_dir = parent / name
    (session_dir / "logs").mkdir(parents=True)
    (session_dir / "CONFIGS").mkdir(parents=True)
    (session_dir / "logs" / "stdout.log").write_text("INFO start\n" * 50)
    (session_dir / "logs" / "stderr.log").write_text("warn x\n" * 10)
    (session_dir / "CONFIGS" / "CONFIG.yaml").write_text(
        "key: value\n" * (content_size // 12)
    )
    (session_dir / "CONFIGS" / "CONFIG.pkl").write_bytes(b"\x00" * content_size)
    return session_dir


def _tree_hash(root: Path) -> dict:
    """Map relative-path -> sha256 hex for every regular file under root."""
    out = {}
    root = root.resolve()
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            full = Path(dirpath) / fn
            rel = full.relative_to(root).as_posix()
            out[rel] = hashlib.sha256(full.read_bytes()).hexdigest()
    return out


class TestArchiveSessionDirRoundTrip:
    """archive_session_dir + restore_session_archive happy-path."""

    def test_archive_creates_tar_gz_file_at_expected_path(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="A1A")
        src = _make_session_dir(tmp_path, name)
        # Act
        archive_path = archive_session_dir(src, format="tar.gz", remove_src=True)
        # Assert
        assert archive_path == tmp_path / (name + ".tar.gz")

    def test_archive_removes_source_dir_after_verified_write(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="A1B")
        src = _make_session_dir(tmp_path, name)
        # Act
        archive_session_dir(src, format="tar.gz", remove_src=True)
        # Assert
        assert not src.exists()

    def test_archive_keeps_source_when_remove_src_is_false(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="A1C")
        src = _make_session_dir(tmp_path, name)
        # Act
        archive_session_dir(src, format="tar.gz", remove_src=False)
        # Assert
        assert src.exists()

    def test_restore_reproduces_bit_identical_file_tree(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import (
            archive_session_dir,
            restore_session_archive,
        )

        name = _session_name(token="A1D")
        src = _make_session_dir(tmp_path, name)
        original_hashes = _tree_hash(src)
        archive_path = archive_session_dir(
            src, format="tar.gz", remove_src=True
        )
        restore_root = tmp_path / "restored"
        restore_root.mkdir()
        # Act
        restored = restore_session_archive(
            archive_path, dest_dir=restore_root / name, remove_archive=False
        )
        # Assert
        assert _tree_hash(restored) == original_hashes


class TestArchiveSessionDirAtomicity:
    """archive_session_dir guarantees no partial writes survive errors."""

    def test_pre_existing_archive_raises_file_exists_error(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="ATM1")
        src = _make_session_dir(tmp_path, name)
        (tmp_path / (name + ".tar.gz")).write_bytes(b"placeholder")
        # Act
        ctx = pytest.raises(FileExistsError)
        # Assert
        with ctx:
            archive_session_dir(src, format="tar.gz", remove_src=True)

    def test_pre_existing_archive_leaves_source_dir_intact(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="ATM2")
        src = _make_session_dir(tmp_path, name)
        (tmp_path / (name + ".tar.gz")).write_bytes(b"placeholder")
        try:
            archive_session_dir(src, format="tar.gz", remove_src=True)
        except FileExistsError:
            pass
        # Act
        still_exists = src.exists()
        # Assert
        assert still_exists

    def test_stale_tmp_archive_is_cleaned_before_new_write(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_session_dir

        name = _session_name(token="ATM3")
        src = _make_session_dir(tmp_path, name)
        stale_tmp = tmp_path / (name + ".tar.gz.tmp")
        stale_tmp.write_bytes(b"stale bytes from a crash")
        # Act
        archive_session_dir(src, format="tar.gz", remove_src=True)
        # Assert
        assert not stale_tmp.exists()


class TestArchiveExistingDryRun:
    """archive_existing with dry_run=True does not write or delete."""

    def test_dry_run_counts_three_old_sessions_as_candidates(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"DRO{i}"))
            os.utime(d, (old_mtime, old_mtime))
        for i in range(2):
            _make_session_dir(tmp_path, _session_name(token=f"DRN{i}"))
        # Act
        summary = archive_existing(tmp_path, older_than_days=30, dry_run=True)
        # Assert
        assert summary["candidates"] == 3

    def test_dry_run_archives_zero_sessions(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"DAO{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(tmp_path, older_than_days=30, dry_run=True)
        # Assert
        assert summary["archived"] == 0

    def test_dry_run_leaves_every_source_dir_in_place(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        sources = []
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"DAS{i}"))
            os.utime(d, (old_mtime, old_mtime))
            sources.append(d)
        archive_existing(tmp_path, older_than_days=30, dry_run=True)
        # Act
        survived = all(s.exists() for s in sources)
        # Assert
        assert survived


class TestArchiveExistingExecute:
    """archive_existing with dry_run=False writes archives and removes sources."""

    def test_execute_archives_all_three_old_sessions(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"EX{i}"))
            os.utime(d, (old_mtime, old_mtime))
        # Act
        summary = archive_existing(tmp_path, older_than_days=30, dry_run=False)
        # Assert
        assert summary["archived"] == 3

    def test_execute_removes_old_session_source_dirs(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        sources = []
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"EXR{i}"))
            os.utime(d, (old_mtime, old_mtime))
            sources.append(d)
        archive_existing(tmp_path, older_than_days=30, dry_run=False)
        # Act
        removed = all(not s.exists() for s in sources)
        # Assert
        assert removed

    def test_execute_skips_sessions_newer_than_cutoff(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        new_dirs = [
            _make_session_dir(tmp_path, _session_name(token=f"EXN{i}"))
            for i in range(2)
        ]
        old_mtime = time.time() - 60 * 86400
        d_old = _make_session_dir(tmp_path, _session_name(token="EXO"))
        os.utime(d_old, (old_mtime, old_mtime))
        archive_existing(tmp_path, older_than_days=30, dry_run=False)
        # Act
        preserved = all(d.exists() for d in new_dirs)
        # Assert
        assert preserved

    def test_execute_is_idempotent_when_rerun(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        old_mtime = time.time() - 60 * 86400
        for i in range(3):
            d = _make_session_dir(tmp_path, _session_name(token=f"IDM{i}"))
            os.utime(d, (old_mtime, old_mtime))
        archive_existing(tmp_path, older_than_days=30, dry_run=False)
        # Act
        summary = archive_existing(tmp_path, older_than_days=30, dry_run=False)
        # Assert
        assert summary["archived"] == 0


class TestArchiveExistingSafety:
    """archive_existing refuses to touch dirs that don't match the session regex."""

    def test_non_session_sibling_dir_is_left_alone(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        _make_session_dir(tmp_path, _session_name(token="SAFE"))
        suspicious = tmp_path / "not_a_session"
        suspicious.mkdir()
        (suspicious / "file.txt").write_text("hello")
        # Act
        archive_existing(tmp_path, dry_run=False)
        # Assert
        assert (suspicious / "file.txt").read_text() == "hello"

    def test_non_session_sibling_does_not_count_as_candidate(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        _make_session_dir(tmp_path, _session_name(token="SFC"))
        (tmp_path / "not_a_session").mkdir()
        # Act
        summary = archive_existing(tmp_path, dry_run=False)
        # Assert
        assert summary["candidates"] == 1


class TestArchiveExistingSkipsPreExisting:
    """archive_existing must not double-archive a session that already has one."""

    def _seed_with_pre_archive(self, tmp_path: Path):
        names = [_session_name(token=f"SKP{i}") for i in range(3)]
        sessions = [_make_session_dir(tmp_path, n) for n in names]
        pre_arc = tmp_path / (names[0] + ".tar.gz")
        with tarfile.open(pre_arc, "w:gz") as tf:
            info = tarfile.TarInfo("placeholder.txt")
            info.size = 5
            tf.addfile(info, io.BytesIO(b"hello"))
        return names, sessions

    def test_pre_existing_archive_is_recorded_as_skipped(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        self._seed_with_pre_archive(tmp_path)
        # Act
        summary = archive_existing(tmp_path, dry_run=False)
        # Assert
        assert summary["skipped"] >= 1

    def test_pre_existing_archive_keeps_its_source_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        _names, sessions = self._seed_with_pre_archive(tmp_path)
        archive_existing(tmp_path, dry_run=False)
        # Act
        first_source_exists = sessions[0].exists()
        # Assert
        assert first_source_exists

    def test_other_candidates_are_archived_normally(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import archive_existing

        _names, sessions = self._seed_with_pre_archive(tmp_path)
        archive_existing(tmp_path, dry_run=False)
        # Act
        others_gone = all(not s.exists() for s in sessions[1:])
        # Assert
        assert others_gone


def _prep_running_session(tmp_path: Path, token: str = "R2F"):
    name = _session_name(token=token)
    sdir_run = tmp_path / "outroot" / "RUNNING" / name
    sdir_run.mkdir(parents=True)
    (sdir_run / "logs").mkdir()
    (sdir_run / "CONFIGS").mkdir()
    (sdir_run / "logs" / "stdout.log").write_text("ok\n" * 20)
    (sdir_run / "logs" / "stderr.log").write_text("err\n" * 5)
    (sdir_run / "CONFIGS" / "CONFIG.yaml").write_text("a: 1\n")
    (sdir_run / "CONFIGS" / "CONFIG.pkl").write_bytes(b"\x00" * 256)
    return name, sdir_run


class TestRunning2FinishedWithArchive:
    """running2finished honors archive_format and collapses dir to one file."""

    def test_archive_format_produces_tar_gz_under_finished_success(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name, sdir_run = _prep_running_session(tmp_path, token="R2FA")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        running2finished(CONFIG, exit_status=0, archive_format="tar.gz")
        # Assert
        assert (
            tmp_path / "outroot" / "FINISHED_SUCCESS" / (name + ".tar.gz")
        ).exists()

    def test_archive_format_removes_finished_dest_dir(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name, sdir_run = _prep_running_session(tmp_path, token="R2FB")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        running2finished(CONFIG, exit_status=0, archive_format="tar.gz")
        # Assert
        assert not (tmp_path / "outroot" / "FINISHED_SUCCESS" / name).exists()

    def test_archive_format_archive_contains_session_files(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name, sdir_run = _prep_running_session(tmp_path, token="R2FC")
        CONFIG = {"SDIR_RUN": sdir_run}
        running2finished(CONFIG, exit_status=0, archive_format="tar.gz")
        archive = (
            tmp_path / "outroot" / "FINISHED_SUCCESS" / (name + ".tar.gz")
        )
        with tarfile.open(archive, "r:*") as tf:
            members = set(tf.getnames())
        has_all_four = (
            any(m.endswith("/logs/stdout.log") for m in members)
            and any(m.endswith("/logs/stderr.log") for m in members)
            and any(m.endswith("/CONFIGS/CONFIG.yaml") for m in members)
            and any(m.endswith("/CONFIGS/CONFIG.pkl") for m in members)
        )
        # Act
        result = has_all_four
        # Assert
        assert result

    def test_archive_format_updates_config_sdir_run_to_archive_path(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name, sdir_run = _prep_running_session(tmp_path, token="R2FD")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        out = running2finished(CONFIG, exit_status=0, archive_format="tar.gz")
        # Assert
        assert Path(out["SDIR_RUN"]) == (
            tmp_path / "outroot" / "FINISHED_SUCCESS" / (name + ".tar.gz")
        )


class TestRunning2FinishedDefaultBackwardCompat:
    """archive_format=None keeps the current copytree-only behavior."""

    def test_default_produces_directory_not_archive(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name = _session_name(token="BC0")
        sdir_run = tmp_path / "outroot" / "RUNNING" / name
        sdir_run.mkdir(parents=True)
        (sdir_run / "logs").mkdir()
        (sdir_run / "logs" / "stdout.log").write_text("hi\n")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        running2finished(CONFIG, exit_status=0)
        # Assert
        assert (tmp_path / "outroot" / "FINISHED_SUCCESS" / name).is_dir()

    def test_default_copies_content_to_finished_success(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._close import running2finished

        name = _session_name(token="BC1")
        sdir_run = tmp_path / "outroot" / "RUNNING" / name
        sdir_run.mkdir(parents=True)
        (sdir_run / "logs").mkdir()
        (sdir_run / "logs" / "stdout.log").write_text("hi\n")
        CONFIG = {"SDIR_RUN": sdir_run}
        # Act
        running2finished(CONFIG, exit_status=0)
        # Assert
        assert (
            tmp_path
            / "outroot"
            / "FINISHED_SUCCESS"
            / name
            / "logs"
            / "stdout.log"
        ).read_text() == "hi\n"


class TestRestoreExistingRoundTrip:
    """restore_existing un-tars every matching archive into a directory."""

    def test_restore_reports_two_archives_restored(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import (
            archive_existing,
            restore_existing,
        )

        for i in range(2):
            _make_session_dir(tmp_path, _session_name(token=f"RR{i}"))
        archive_existing(tmp_path, dry_run=False)
        # Act
        summary = restore_existing(
            tmp_path, dry_run=False, remove_archive=True
        )
        # Assert
        assert summary["restored"] == 2

    def test_restore_produces_bit_identical_directory(self, tmp_path):
        # Arrange
        from scitex_session._lifecycle._archive import (
            archive_existing,
            restore_existing,
        )

        name = _session_name(token="RRH")
        src = _make_session_dir(tmp_path, name)
        original = _tree_hash(src)
        archive_existing(tmp_path, dry_run=False)
        # Act
        restore_existing(tmp_path, dry_run=False, remove_archive=True)
        # Assert
        assert _tree_hash(tmp_path / name) == original


# EOF
