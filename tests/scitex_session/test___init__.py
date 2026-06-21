#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-06-21 (ywatanabe)"
# File: ./tests/scitex_session/test___init__.py

"""Public-API-surface contract for ``scitex_session``.

The ``@scitex_session.session`` decorator is THE public entry point. The
low-level ``start()`` and the imperative ``run()`` are INTERNAL: they are
easy to misfire (``@scitex_session.start`` binds ``main`` to the ``sys``
parameter; ``run(name=...)`` raises ``TypeError`` from ``start()``), so a
scanning agent must not be lured into them via ``dir(scitex_session)``.

This module pins that contract with a real import (no mocks):

- ``start`` / ``run`` are absent from ``__all__`` and ``dir()``.
- ``_start`` / ``_run`` are reachable + callable (power-user aliases).
- bare ``start`` / ``run`` stay importable (back-compat) but warn.
- ``session`` (decorator) / ``close`` / ``SessionManager`` are public.

Each test follows AAA with exactly one assertion so a failure pinpoints
the broken clause.
"""

import warnings

import pytest

import scitex_session


class TestDeprecatedNamesHidden:
    """`start` / `run` must not appear on the prominent public surface."""

    def test_start_absent_from_dunder_all(self):
        """`start` is removed from `scitex_session.__all__`."""
        # Arrange
        public_names = scitex_session.__all__
        # Act
        is_present = "start" in public_names
        # Assert
        assert is_present is False

    def test_run_absent_from_dunder_all(self):
        """`run` is removed from `scitex_session.__all__`."""
        # Arrange
        public_names = scitex_session.__all__
        # Act
        is_present = "run" in public_names
        # Assert
        assert is_present is False

    def test_start_absent_from_dir(self):
        """`start` does not appear in `dir(scitex_session)`."""
        # Arrange
        visible = dir(scitex_session)
        # Act
        is_visible = "start" in visible
        # Assert
        assert is_visible is False

    def test_run_absent_from_dir(self):
        """`run` does not appear in `dir(scitex_session)`."""
        # Arrange
        visible = dir(scitex_session)
        # Act
        is_visible = "run" in visible
        # Assert
        assert is_visible is False

    def test_start_stays_absent_from_dir_after_access(self):
        """Accessing bare `start` must not leak it back into `dir()`."""
        # Arrange
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            _ = scitex_session.start
        # Act
        is_visible = "start" in dir(scitex_session)
        # Assert
        assert is_visible is False


class TestPrivateAliasesReachable:
    """Power users keep access via the underscore aliases."""

    def test_private_start_alias_callable(self):
        """`scitex_session._start` resolves to a callable."""
        # Arrange
        alias = scitex_session._start
        # Act
        is_callable = callable(alias)
        # Assert
        assert is_callable

    def test_private_run_alias_callable(self):
        """`scitex_session._run` resolves to a callable."""
        # Arrange
        alias = scitex_session._run
        # Act
        is_callable = callable(alias)
        # Assert
        assert is_callable

    def test_private_start_alias_is_low_level_start(self):
        """`_start` is the same object as the low-level lifecycle `start`."""
        # Arrange
        from scitex_session._lifecycle import start as lifecycle_start

        # Act
        is_same = scitex_session._start is lifecycle_start
        # Assert
        assert is_same

    def test_private_run_alias_is_decorator_run(self):
        """`_run` is the same object as the decorator-package `run`."""
        # Arrange
        from scitex_session._decorator import run as decorator_run

        # Act
        is_same = scitex_session._run is decorator_run
        # Assert
        assert is_same


class TestBareNamesDeprecatedButImportable:
    """Bare `start` / `run` keep working for back-compat but warn."""

    def test_bare_start_access_warns(self):
        """Accessing `scitex_session.start` emits a `DeprecationWarning`."""
        # Arrange
        access = lambda: scitex_session.start  # noqa: E731
        # Act
        warns_cm = pytest.warns(DeprecationWarning)
        # Assert
        with warns_cm:
            access()

    def test_bare_run_access_warns(self):
        """Accessing `scitex_session.run` emits a `DeprecationWarning`."""
        # Arrange
        access = lambda: scitex_session.run  # noqa: E731
        # Act
        warns_cm = pytest.warns(DeprecationWarning)
        # Assert
        with warns_cm:
            access()

    def test_bare_start_resolves_to_callable(self):
        """`from scitex_session import start` still yields a callable."""
        # Arrange
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            bare_start = scitex_session.start
        # Act
        is_callable = callable(bare_start)
        # Assert
        assert is_callable

    def test_bare_run_resolves_to_callable(self):
        """`from scitex_session import run` still yields a callable."""
        # Arrange
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            bare_run = scitex_session.run
        # Act
        is_callable = callable(bare_run)
        # Assert
        assert is_callable

    def test_bare_start_resolves_to_private_alias(self):
        """Bare `start` resolves to the same object as `_start`."""
        # Arrange
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            bare_start = scitex_session.start
        # Act
        is_same = bare_start is scitex_session._start
        # Assert
        assert is_same


class TestPublicSurfaceIntact:
    """The decorator + genuinely-public helpers stay public + usable."""

    def test_session_decorator_in_dunder_all(self):
        """`session` (the decorator) is advertised in `__all__`."""
        # Arrange
        public_names = scitex_session.__all__
        # Act
        is_present = "session" in public_names
        # Assert
        assert is_present

    def test_session_decorator_callable(self):
        """`scitex_session.session` is callable (usable as a decorator)."""
        # Arrange
        decorator = scitex_session.session
        # Act
        is_callable = callable(decorator)
        # Assert
        assert is_callable

    def test_close_in_dunder_all(self):
        """`close` remains a public lifecycle finalizer."""
        # Arrange
        public_names = scitex_session.__all__
        # Act
        is_present = "close" in public_names
        # Assert
        assert is_present

    def test_session_manager_in_dunder_all(self):
        """`SessionManager` remains public for advanced use."""
        # Arrange
        public_names = scitex_session.__all__
        # Act
        is_present = "SessionManager" in public_names
        # Assert
        assert is_present


# EOF
