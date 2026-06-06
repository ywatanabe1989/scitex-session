#!/usr/bin/env python3
# Timestamp: "2026-05-26 (ywatanabe)"
# File: src/scitex_session/_decorator/__init__.py
"""Re-export aggregator for the @stx.session decorator sub-package.

Split from a single 648-line _decorator.py into three modules
(_decorator, _run, _cli) under the size-limit hook. All existing
imports `from scitex_session._decorator import session, run` continue
to resolve transparently via this __init__.
"""

from ._cli import _add_argument, _create_parser, _generate_short_form
from ._decorator import session
from ._run import _run_with_session, run

__all__ = [
    "session",
    "run",
    "_run_with_session",
    "_create_parser",
    "_add_argument",
    "_generate_short_form",
]

# EOF
