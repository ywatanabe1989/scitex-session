"""Regression test for scitex-python#145 — close() message differentiates exit_status.

Before the fix, `_close(exit_status=1)` still printed "SUCC: Congratulations!"
even though the directory was correctly named FINISHED_ERROR. The log line
now branches: error → logger.error, success/none → logger.info. (We don't
use `logger.success` anymore — stdlib `logging.Logger` has no such method
and the previous call crashed inside running2finished's try/except,
swallowing the SDIR_RUN update.)
"""

from __future__ import annotations

import inspect


class TestCloseExitStatusMessage:
    def test_close_source_includes_logger_error_call(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "logger.error" in src

    def test_close_source_includes_logger_info_call(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "logger.info" in src

    def test_close_source_branches_on_exit_status_one(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "exit_status == 1" in src

    def test_close_source_branches_on_exit_status_zero(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "exit_status == 0" in src

    def test_close_source_uses_script_failed_message_text(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "Script failed" in src

    def test_close_source_keeps_success_congratulations_text(self):
        # Arrange
        from scitex_session._lifecycle import _close

        # Act
        src = inspect.getsource(_close)
        # Assert
        assert "Congratulations" in src

    def test_close_source_orders_error_branch_before_success_branch(self):
        # Arrange
        from scitex_session._lifecycle import _close

        src = inspect.getsource(_close)
        err_idx = src.find("logger.error")
        succ_idx = src.find("Congratulations")
        # Act
        err_first = 0 <= err_idx < succ_idx
        # Assert
        assert err_first is True


# EOF
