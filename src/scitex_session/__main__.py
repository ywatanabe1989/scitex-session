#!/usr/bin/env python3
# Timestamp: "2026-05-25 (ywatanabe)"
# File: src/scitex_session/__main__.py
"""Module entry point — ``python -m scitex_session``.

Currently delegates to the archive sub-CLI (the only CLI surface this
package ships). New top-level subcommands can be wired up here as the
package grows.

Invocation
----------
    python -m scitex_session archive compress <root>
    python -m scitex_session archive extract <root>

For now the implicit ``archive`` prefix is accepted optionally; bare
``python -m scitex_session compress ...`` also dispatches to the
archive CLI for ergonomics.
"""

from __future__ import annotations

import sys

from .archive import main as _archive_main


def main(argv=None) -> int:
    """Top-level CLI dispatcher.

    The single existing sub-CLI is ``scitex_session.archive`` (compress /
    extract). For now we just forward all args, optionally stripping a
    leading ``archive`` argument so both invocation styles work:

        python -m scitex_session archive compress ROOT
        python -m scitex_session compress ROOT
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "archive":
        args = args[1:]
    return _archive_main(args)


if __name__ == "__main__":
    raise SystemExit(main())


# EOF
