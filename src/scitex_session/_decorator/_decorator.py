#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-05-26 (ywatanabe)"
# File: src/scitex_session/_decorator/_decorator.py
"""@stx.session decorator factory.

Public entry point that wraps a script's ``main``-style function with
CLI parsing + session lifecycle management. Execution itself lives in
:mod:`scitex_session._decorator._run`.
"""

from __future__ import annotations

import functools
from typing import Callable

from .._lifecycle import UNSET
from ._run import _run_with_session


def session(
    func: Callable = None,
    *,
    verbose: bool = False,
    agg: bool = True,
    notify: bool = False,
    sdir_suffix: str = None,
    archive_format=UNSET,
    **session_kwargs,
) -> Callable:
    """Decorator to wrap a function in a scitex session.

    Automatically handles:

    - CLI argument parsing from the function signature
    - Session initialization (logging, output directories)
    - Execution
    - Cleanup
    - Error handling

    This decorator is designed for script entry points. The decorated
    function should be called without arguments from
    ``if __name__ == '__main__':`` to trigger CLI parsing and session
    management.

    Parameters
    ----------
    func : callable, optional
        Function to wrap (set automatically by the decorator).
    verbose : bool, default False
        Enable verbose logging.
    agg : bool, default True
        Use matplotlib's Agg backend (non-interactive).
    notify : bool, default False
        Send notification on completion.
    sdir_suffix : str, optional
        Suffix for the output directory name (defaults to function name).
    archive_format : str, optional
        Collapse FINISHED_SUCCESS/<session>/ into a single archive file
        (1 inode vs ~7) on close. Defaults to ``"tar.gz"`` (archive on
        close). Pass ``None`` or ``""`` to keep the loose directory. Can
        also be set/overridden via ``CONFIG.SESSION.ARCHIVE_FORMAT``.
    **session_kwargs
        Additional session configuration parameters forwarded to
        ``scitex_session.start`` / ``scitex_session.close``.

    Returns
    -------
    callable
        The wrapped function; calling it with no arguments triggers
        CLI parsing + session management. Calling it with arguments
        bypasses session management entirely and invokes the function
        directly (useful for in-process tests).

    Examples
    --------
    Bare decorator (auto CLI from signature):

    .. code-block:: python

        @stx.session
        def analyze(data_path: str, threshold: float = 0.5):
            '''Analyze data file.'''
            data = stx.io.load(data_path)
            result = process(data, threshold)
            stx.io.save(result, "output.csv")
            return 0

        if __name__ == '__main__':
            analyze()  # CLI mode with session management

        # CLI: python script.py --data-path data.csv --threshold 0.7

    Decorator with options:

    .. code-block:: python

        @stx.session(verbose=True, notify=True)
        def train_model(model_name: str, epochs: int = 10):
            '''Train ML model.'''
            # Available as globals: CONFIG, plt, COLORS, rngg, logger.
            logger.info(f"Session ID: {CONFIG['ID']}")
            logger.info(f"Output directory: {CONFIG['SDIR_RUN']}")
            # ... training code ...
            return 0

        if __name__ == '__main__':
            train_model()

    Notes
    -----
    - Function name can be anything (not just ``main``).
    - Calling with arguments bypasses session management:
      ``analyze('/path', 0.5)``.
    - Only one session-managed function per script.
    - Do NOT call multiple ``@session`` decorated functions from one
      script.
    - Do NOT nest session-decorated function calls without arguments.

    Injected Global Variables
    -------------------------
    When called without arguments (CLI mode), the decorator injects
    these into the wrapped function's module globals:

    - ``CONFIG`` (dict): Session configuration with ID, SDIR, paths, etc.
    - ``plt`` (module): ``matplotlib.pyplot`` configured for the session.
    - ``COLORS`` (CustomColors): Color palette for consistent plotting.
    - ``rngg`` (RandomStateManager): Reproducibility manager; creates
      named generators via ``rngg("name")``.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If called with arguments (not CLI), run directly.
            if args or kwargs:
                return func(*args, **kwargs)

            # Otherwise, parse CLI and run with session management.
            return _run_with_session(
                func,
                verbose=verbose,
                agg=agg,
                notify=notify,
                sdir_suffix=sdir_suffix,
                archive_format=archive_format,
                **session_kwargs,
            )

        wrapper._func = func
        wrapper._is_session_wrapped = True
        return wrapper

    # Handle @stx.session vs @stx.session()
    if func is None:
        # Called with arguments: @stx.session(verbose=True)
        return decorator
    # Called without arguments: @stx.session
    return decorator(func)


# EOF
