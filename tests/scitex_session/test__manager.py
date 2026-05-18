#!/usr/bin/env python3
# Time-stamp: "2026-05-18"
# File: ./tests/scitex_session/test__manager.py

"""Tests for SessionManager class.

Every test exercises the real `SessionManager` — no mocks, single
assertion, AAA-marker comments, descriptive ≥3-word names.
"""

from datetime import datetime

import pytest

# Required for scitex_session module
pytest.importorskip("natsort")
pytest.importorskip("h5py")
pytest.importorskip("zarr")

from scitex_session import SessionManager
from scitex_session._manager import get_global_session_manager


class TestSessionManagerBasic:
    """Basic SessionManager functionality tests."""

    def test_initialization_returns_non_none_instance(self):
        # Arrange / Act
        # Arrange
        # Act
        manager = SessionManager()
        # Assert
        assert manager is not None

    def test_initialization_exposes_active_sessions_attr(self):
        # Arrange
        # Act
        manager = SessionManager()
        # Assert
        assert hasattr(manager, "active_sessions")

    def test_initialization_active_sessions_starts_empty(self):
        # Arrange
        # Act
        manager = SessionManager()
        # Assert
        assert manager.active_sessions == {}

    def test_create_session_records_session_id(self):
        # Arrange
        manager = SessionManager()
        # Act
        manager.create_session("test_id", {"test": "value"})
        # Assert
        assert "test_id" in manager.active_sessions

    def test_create_session_stores_supplied_config(self):
        # Arrange
        manager = SessionManager()
        config = {"test": "value"}
        # Act
        manager.create_session("test_id", config)
        # Assert
        assert manager.active_sessions["test_id"]["config"] == config

    def test_create_session_sets_status_running(self):
        # Arrange
        manager = SessionManager()
        # Act
        manager.create_session("test_id", {"test": "value"})
        # Assert
        assert manager.active_sessions["test_id"]["status"] == "running"

    def test_create_session_records_datetime_start_time(self):
        # Arrange
        manager = SessionManager()
        # Act
        manager.create_session("test_id", {"test": "value"})
        # Assert
        assert isinstance(manager.active_sessions["test_id"]["start_time"], datetime)

    def test_close_session_sets_status_closed(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("test_id", {"test": "value"})
        # Act
        manager.close_session("test_id")
        # Assert
        assert manager.active_sessions["test_id"]["status"] == "closed"

    def test_close_session_records_end_time_field(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("test_id", {"test": "value"})
        # Act
        manager.close_session("test_id")
        # Assert
        assert "end_time" in manager.active_sessions["test_id"]

    def test_close_session_end_time_is_datetime_object(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("test_id", {"test": "value"})
        # Act
        manager.close_session("test_id")
        # Assert
        assert isinstance(manager.active_sessions["test_id"]["end_time"], datetime)

    def test_close_nonexistent_session_does_not_raise(self):
        # Arrange
        manager = SessionManager()
        # Act
        manager.close_session("nonexistent")
        # Assert
        assert True  # no exception is the observed behaviour


class TestSessionManagerQueries:
    """Test SessionManager query methods."""

    def test_get_active_sessions_returns_empty_dict_when_no_sessions(self):
        # Arrange
        manager = SessionManager()
        # Act
        active = manager.get_active_sessions()
        # Assert
        assert active == {}

    def test_get_active_sessions_includes_running_session(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("session1", {"data": "1"})
        manager.create_session("session2", {"data": "2"})
        manager.close_session("session1")
        # Act
        active = manager.get_active_sessions()
        # Assert
        assert "session2" in active

    def test_get_active_sessions_excludes_closed_session(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("session1", {"data": "1"})
        manager.create_session("session2", {"data": "2"})
        manager.close_session("session1")
        # Act
        active = manager.get_active_sessions()
        # Assert
        assert "session1" not in active

    def test_get_session_returns_stored_config(self):
        # Arrange
        manager = SessionManager()
        config = {"test": "value"}
        manager.create_session("test_id", config)
        # Act
        session_info = manager.get_session("test_id")
        # Assert
        assert session_info["config"] == config

    def test_get_session_returns_running_status_for_open_session(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("test_id", {"test": "value"})
        # Act
        session_info = manager.get_session("test_id")
        # Assert
        assert session_info["status"] == "running"

    def test_get_session_returns_empty_dict_for_nonexistent_id(self):
        # Arrange
        manager = SessionManager()
        # Act
        session_info = manager.get_session("nonexistent")
        # Assert
        assert session_info == {}

    def test_list_sessions_includes_running_session_id(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("session1", {"data": "1"})
        manager.create_session("session2", {"data": "2"})
        manager.close_session("session1")
        # Act
        all_sessions = manager.list_sessions()
        # Assert
        assert "session2" in all_sessions

    def test_list_sessions_includes_closed_session_id(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("session1", {"data": "1"})
        manager.create_session("session2", {"data": "2"})
        manager.close_session("session1")
        # Act
        all_sessions = manager.list_sessions()
        # Assert
        assert "session1" in all_sessions

    def test_list_sessions_records_closed_status_for_closed_session(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("session1", {"data": "1"})
        manager.close_session("session1")
        # Act
        all_sessions = manager.list_sessions()
        # Assert
        assert all_sessions["session1"]["status"] == "closed"


class TestSessionManagerMultiple:
    """Test SessionManager with multiple sessions."""

    def test_multiple_create_sessions_all_counted_active(self):
        # Arrange
        manager = SessionManager()
        for i in range(5):
            manager.create_session(f"session{i}", {"index": i})
        # Act
        active = manager.get_active_sessions()
        # Assert
        assert len(active) == 5

    def test_after_partial_close_active_count_drops(self):
        # Arrange
        manager = SessionManager()
        for i in range(5):
            manager.create_session(f"session{i}", {"index": i})
        manager.close_session("session0")
        manager.close_session("session2")
        # Act
        active = manager.get_active_sessions()
        # Assert
        assert len(active) == 3

    def test_after_partial_close_list_keeps_all_entries(self):
        # Arrange
        manager = SessionManager()
        for i in range(5):
            manager.create_session(f"session{i}", {"index": i})
        manager.close_session("session0")
        manager.close_session("session2")
        # Act
        all_sessions = manager.list_sessions()
        # Assert
        assert len(all_sessions) == 5

    def test_recreate_session_with_same_id_overwrites_config(self):
        # Arrange
        manager = SessionManager()
        manager.create_session("test", {"version": 1})
        manager.create_session("test", {"version": 2})
        # Act
        session_info = manager.get_session("test")
        # Assert
        assert session_info["config"]["version"] == 2


class TestGlobalSessionManager:
    """Test global session manager singleton."""

    def test_get_global_session_manager_returns_singleton_instance(self):
        # Arrange
        manager1 = get_global_session_manager()
        # Act
        manager2 = get_global_session_manager()
        # Assert
        assert manager1 is manager2

    def test_get_global_session_manager_returns_session_manager_type(self):
        # Arrange
        # Act
        manager = get_global_session_manager()
        # Assert
        assert isinstance(manager, SessionManager)

    def test_global_manager_persists_data_across_calls(self):
        # Arrange
        manager1 = get_global_session_manager()
        manager1.create_session("persistent", {"data": "value"})
        # Act
        manager2 = get_global_session_manager()
        session_info = manager2.get_session("persistent")
        # Assert
        assert session_info["config"]["data"] == "value"


class TestSessionManagerIntegration:
    """Integration tests for SessionManager."""

    def test_typical_workflow_lists_closed_session(self):
        # Arrange
        manager = SessionManager()
        session_id = "exp_001"
        manager.create_session(session_id, {"experiment": "test", "seed": 42})
        manager.close_session(session_id)
        # Act
        all_sessions = manager.list_sessions()
        # Assert
        assert all_sessions[session_id]["status"] == "closed"

    def test_session_end_time_is_after_start_time(self):
        # Arrange
        import time

        manager = SessionManager()
        manager.create_session("timing_test", {})
        start_time = manager.active_sessions["timing_test"]["start_time"]
        time.sleep(0.1)  # ensure timestamp resolution can differentiate.
        manager.close_session("timing_test")
        # Act
        end_time = manager.active_sessions["timing_test"]["end_time"]
        # Assert
        assert end_time > start_time


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
