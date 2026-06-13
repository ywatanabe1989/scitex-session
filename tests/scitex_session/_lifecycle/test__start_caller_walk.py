#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for the caller-frame walk in `_find_user_caller_file`.

Operator-observed bug (neurovista 2026-06-13): when the user's @stx.session
script is wrapped through one or more intermediate decorator layers, the
old ``frame.f_back.f_back`` heuristic in ``_run_with_session`` (and the
matching ``inspect.stack()[1]`` fallback in ``start``) landed on a
scitex_session / scitex_dev wrapper frame instead of the user's actual
script. As a result, save() resolved ``__file__`` to a path inside
site-packages and the figure landed in
``site-packages/.../decorators_out/RUNNING/<ID>/`` rather than the
user's ``<script>_out/RUNNING/<ID>/``.

The fix introduces ``_find_user_caller_file`` which walks
``inspect.stack()`` outward and skips every frame whose module name
starts with ``scitex_session`` / ``scitex_dev``. These tests pin that
behaviour with real frames — no mocks, no monkeypatch.
"""

from __future__ import annotations

from pathlib import Path

from scitex_session._lifecycle._start import (
    _find_user_caller_file,
    _is_internal_frame_file,
    _is_internal_module_name,
)


def test_is_internal_module_flags_scitex_session_prefix() -> None:
    # Arrange
    modname = "scitex_session._decorator._run"

    # Act
    flagged = _is_internal_module_name(modname)

    # Assert
    assert flagged is True


def test_is_internal_module_flags_scitex_dev_prefix() -> None:
    # Arrange
    modname = "scitex_dev._core.decorators"

    # Act
    flagged = _is_internal_module_name(modname)

    # Assert
    assert flagged is True


def test_is_internal_module_passes_user_module() -> None:
    # Arrange
    modname = "neurovista.scripts.clew.v4i_headline_stats"

    # Act
    flagged = _is_internal_module_name(modname)

    # Assert
    assert flagged is False


def test_is_internal_module_passes_tests_module() -> None:
    # The tests tree mirrors the package name (tests.scitex_session.…)
    # but is NOT the production package; the walker must not skip it.
    # Arrange
    modname = "tests.scitex_session._lifecycle.test__start_caller_walk"

    # Act
    flagged = _is_internal_module_name(modname)

    # Assert
    assert flagged is False


def test_is_internal_file_flags_site_packages_path() -> None:
    # Arrange
    path = "/x/site-packages/scitex_session/_decorator/_run.py"

    # Act
    flagged = _is_internal_frame_file(path)

    # Assert
    assert flagged is True


def test_is_internal_file_flags_src_tree_path() -> None:
    # Arrange
    path = "/x/proj/scitex-session/src/scitex_session/_decorator/_run.py"

    # Act
    flagged = _is_internal_frame_file(path)

    # Assert
    assert flagged is True


def test_is_internal_file_passes_tests_tree_path() -> None:
    # The tests tree path *contains* "/scitex_session/" as a sub-path but
    # is NOT under site-packages or src — the walker must not skip it.
    # Arrange
    path = "/x/proj/scitex-session/tests/scitex_session/_lifecycle/test_x.py"

    # Act
    flagged = _is_internal_frame_file(path)

    # Assert
    assert flagged is False


def test_find_user_caller_returns_hint_when_hint_is_user_path(
    tmp_path: Path,
) -> None:
    # Arrange
    user_script = tmp_path / "from_notebook.py"

    # Act
    resolved = _find_user_caller_file(hint=str(user_script))

    # Assert
    assert resolved == str(user_script)


def test_find_user_caller_discards_hint_when_hint_is_internal_path() -> None:
    # Arrange — the previous-bug symptom: ``file=`` arrived as the
    # @stx.session wrapper's ``__file__`` (i.e. an internal package
    # frame). The walker must discard the hint and return a non-internal
    # filename instead.
    internal_hint = "/x/site-packages/scitex_session/_decorator/_run.py"

    # Act
    resolved = _find_user_caller_file(hint=internal_hint)

    # Assert
    assert not _is_internal_frame_file(resolved)


def test_find_user_caller_returns_test_script_filename_directly() -> None:
    # Direct call from the test frame: the walker must walk past the
    # walker's own frame (scitex_session._lifecycle._start) and return
    # the test file's filename.
    # Arrange
    expected_filename = __file__

    # Act
    resolved = _find_user_caller_file()

    # Assert
    assert resolved == expected_filename
