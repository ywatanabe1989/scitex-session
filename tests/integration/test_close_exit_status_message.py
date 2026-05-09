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
    def test_close_source_branches_on_exit_status(self):
        """Inspect the source to confirm the exit_status branching exists."""
        from scitex_session._lifecycle import _close

        src = inspect.getsource(_close)
        # Both error and info log calls must be present.
        assert "logger.error" in src
        assert "logger.info" in src
        # The branch key must be the exit_status value we fixed on.
        assert "exit_status == 1" in src
        assert "exit_status == 0" in src

    def test_error_branch_uses_script_failed_message(self):
        """The FINISHED_ERROR branch must emit 'Script failed' via logger.error,
        and the success branch must keep the 'Congratulations' wording."""
        from scitex_session._lifecycle import _close

        src = inspect.getsource(_close)
        assert "Script failed" in src
        # Success message text is preserved (just the level changed).
        assert "Congratulations" in src
        # Error log call should come before the success log call textually
        # (matches the source's `if exit_status == 1: ... elif == 0: ...`
        # ordering).
        err_idx = src.find("logger.error")
        succ_idx = src.find("Congratulations")
        assert err_idx >= 0 and succ_idx >= 0
        assert err_idx < succ_idx


# EOF
