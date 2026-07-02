#!/usr/bin/env python3
# File: ./tests/scitex_session/test__hooks.py

"""Tests for the lifecycle-hook registry (the acyclic observer seam).

Every test exercises the real registry in `scitex_session._hooks` — no
mocks, single assertion, AAA-marker comments, descriptive ≥3-word names.
The registries are module-level state, so each test runs inside the
`_clean_registries` fixture which snapshots and restores them.
"""

import pytest

from scitex_session import _hooks


@pytest.fixture(autouse=True)
def _clean_registries():
    # Arrange (shared): snapshot module-level registry state
    start_snapshot = list(_hooks._SESSION_START_HOOKS)
    close_snapshot = list(_hooks._SESSION_CLOSE_HOOKS)
    _hooks._SESSION_START_HOOKS.clear()
    _hooks._SESSION_CLOSE_HOOKS.clear()
    yield
    _hooks._SESSION_START_HOOKS[:] = start_snapshot
    _hooks._SESSION_CLOSE_HOOKS[:] = close_snapshot


class TestRegisterSessionStartHook:
    """Registration behavior for start hooks."""

    def test_register_adds_hook_to_registry(self):
        # Arrange
        def hook(session_id, script_path, metadata):
            pass

        # Act
        _hooks.register_session_start_hook(hook)
        # Assert
        assert hook in _hooks._SESSION_START_HOOKS

    def test_register_returns_the_same_callable(self):
        # Arrange
        def hook(session_id, script_path, metadata):
            pass

        # Act
        returned = _hooks.register_session_start_hook(hook)
        # Assert
        assert returned is hook

    def test_register_twice_is_idempotent(self):
        # Arrange
        def hook(session_id, script_path, metadata):
            pass

        # Act
        _hooks.register_session_start_hook(hook)
        _hooks.register_session_start_hook(hook)
        # Assert
        assert len(_hooks._SESSION_START_HOOKS) == 1


class TestRegisterSessionCloseHook:
    """Registration behavior for close hooks."""

    def test_register_adds_hook_to_registry(self):
        # Arrange
        def hook(status, exit_code):
            pass

        # Act
        _hooks.register_session_close_hook(hook)
        # Assert
        assert hook in _hooks._SESSION_CLOSE_HOOKS

    def test_register_twice_is_idempotent(self):
        # Arrange
        def hook(status, exit_code):
            pass

        # Act
        _hooks.register_session_close_hook(hook)
        _hooks.register_session_close_hook(hook)
        # Assert
        assert len(_hooks._SESSION_CLOSE_HOOKS) == 1


class TestUnregisterHooks:
    """Unregistration behavior for both hook kinds."""

    def test_unregister_removes_registered_start_hook(self):
        # Arrange
        def hook(session_id, script_path, metadata):
            pass

        _hooks.register_session_start_hook(hook)
        # Act
        _hooks.unregister_session_start_hook(hook)
        # Assert
        assert hook not in _hooks._SESSION_START_HOOKS

    def test_unregister_absent_start_hook_is_noop(self):
        # Arrange
        def hook(session_id, script_path, metadata):
            pass

        # Act
        _hooks.unregister_session_start_hook(hook)
        # Assert
        assert hook not in _hooks._SESSION_START_HOOKS

    def test_unregister_removes_registered_close_hook(self):
        # Arrange
        def hook(status, exit_code):
            pass

        _hooks.register_session_close_hook(hook)
        # Act
        _hooks.unregister_session_close_hook(hook)
        # Assert
        assert hook not in _hooks._SESSION_CLOSE_HOOKS

    def test_unregister_absent_close_hook_is_noop(self):
        # Arrange
        def hook(status, exit_code):
            pass

        # Act
        _hooks.unregister_session_close_hook(hook)
        # Assert
        assert hook not in _hooks._SESSION_CLOSE_HOOKS


class TestFireSessionStartHooks:
    """Dispatch contract for start hooks: positional (session_id, script_path, metadata)."""

    def test_fire_delivers_positional_arguments_in_contract_order(self):
        # Arrange
        received = []
        _hooks.register_session_start_hook(
            lambda session_id, script_path, metadata: received.append(
                (session_id, script_path, metadata)
            )
        )
        # Act
        _hooks._fire_session_start_hooks(
            "sid-1", script_path="a.py", metadata={"k": 1}
        )
        # Assert
        assert received == [("sid-1", "a.py", {"k": 1})]

    def test_fire_defaults_script_path_and_metadata_to_none(self):
        # Arrange
        received = []
        _hooks.register_session_start_hook(
            lambda session_id, script_path, metadata: received.append(
                (session_id, script_path, metadata)
            )
        )
        # Act
        _hooks._fire_session_start_hooks("sid-2")
        # Assert
        assert received == [("sid-2", None, None)]

    def test_fire_with_no_hooks_registered_is_noop(self):
        # Arrange
        # Act
        _hooks._fire_session_start_hooks("sid-3")
        # Assert
        assert _hooks._SESSION_START_HOOKS == []

    def test_raising_hook_does_not_block_subsequent_hook(self):
        # Arrange
        received = []

        def raising_hook(session_id, script_path, metadata):
            raise RuntimeError("subscriber bug must stay isolated")

        _hooks.register_session_start_hook(raising_hook)
        _hooks.register_session_start_hook(
            lambda session_id, script_path, metadata: received.append(session_id)
        )
        # Act
        _hooks._fire_session_start_hooks("sid-4")
        # Assert
        assert received == ["sid-4"]

    def test_fire_calls_hooks_in_registration_order(self):
        # Arrange
        received = []
        _hooks.register_session_start_hook(
            lambda session_id, script_path, metadata: received.append("first")
        )
        _hooks.register_session_start_hook(
            lambda session_id, script_path, metadata: received.append("second")
        )
        # Act
        _hooks._fire_session_start_hooks("sid-5")
        # Assert
        assert received == ["first", "second"]


class TestFireSessionCloseHooks:
    """Dispatch contract for close hooks: positional (status, exit_code)."""

    def test_fire_delivers_positional_arguments_in_contract_order(self):
        # Arrange
        received = []
        _hooks.register_session_close_hook(
            lambda status, exit_code: received.append((status, exit_code))
        )
        # Act
        _hooks._fire_session_close_hooks(status="failed", exit_code=1)
        # Assert
        assert received == [("failed", 1)]

    def test_fire_defaults_to_success_and_zero(self):
        # Arrange
        received = []
        _hooks.register_session_close_hook(
            lambda status, exit_code: received.append((status, exit_code))
        )
        # Act
        _hooks._fire_session_close_hooks()
        # Assert
        assert received == [("success", 0)]

    def test_fire_with_no_hooks_registered_is_noop(self):
        # Arrange
        # Act
        _hooks._fire_session_close_hooks(status="failed", exit_code=2)
        # Assert
        assert _hooks._SESSION_CLOSE_HOOKS == []

    def test_raising_hook_does_not_block_subsequent_hook(self):
        # Arrange
        received = []

        def raising_hook(status, exit_code):
            raise RuntimeError("subscriber bug must stay isolated")

        _hooks.register_session_close_hook(raising_hook)
        _hooks.register_session_close_hook(
            lambda status, exit_code: received.append(status)
        )
        # Act
        _hooks._fire_session_close_hooks(status="success", exit_code=0)
        # Assert
        assert received == ["success"]


class TestPublicApiExposure:
    """The registry must be reachable as real eager attributes of the package.

    Downstream subscribers (e.g. clew's ``sys.meta_path`` finder) call
    ``scitex_session.register_session_start_hook`` the instant the package
    is imported, so these names cannot live behind the PEP 562 lazy loader.
    """

    def test_register_start_hook_is_package_attribute(self):
        # Arrange
        import scitex_session

        # Act / Assert
        assert (
            scitex_session.register_session_start_hook
            is _hooks.register_session_start_hook
        )

    def test_register_close_hook_is_package_attribute(self):
        # Arrange
        import scitex_session

        # Act / Assert
        assert (
            scitex_session.register_session_close_hook
            is _hooks.register_session_close_hook
        )

    def test_register_names_are_in_package_all(self):
        # Arrange
        import scitex_session

        # Act / Assert
        assert {
            "register_session_start_hook",
            "register_session_close_hook",
        } <= set(scitex_session.__all__)


# EOF
