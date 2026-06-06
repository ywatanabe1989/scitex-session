#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-05-26 (ywatanabe)"
# File: src/scitex_session/_decorator/_run.py
"""CLI execution path for the @stx.session decorator.

Holds ``_run_with_session`` (the decorator's CLI dispatcher) and
``run`` (the imperative alternative). Both call into ``_cli`` for
argparse generation and ``_lifecycle`` for start/close.
"""

from __future__ import annotations

import argparse
import inspect
import sys as sys_module
from logging import getLogger
from typing import Any, Callable

from .. import INJECTED
from .._lifecycle import close, start
from ._cli import _create_parser

# Internal logger for the decorator itself.
_decorator_logger = getLogger(__name__)


def _run_with_session(
    func: Callable,
    verbose: bool,
    agg: bool,
    notify: bool,
    sdir_suffix: str,
    archive_format: str = None,
    **session_kwargs,
) -> Any:
    """Run a function with full session management.

    This is the CLI execution path invoked by :func:`session` when the
    decorated function is called with no arguments. It generates the
    argparse from the function signature, starts a session, executes
    the function with injected globals, then closes the session.
    """
    # Get the calling file (two frames up: wrapper -> _run_with_session).
    frame = inspect.currentframe()
    caller_frame = frame.f_back.f_back
    caller_file = caller_frame.f_globals.get("__file__", "unknown.py")

    parser = _create_parser(func)
    args = parser.parse_args()

    # Clean up INJECTED sentinels from args before passing to session.
    cleaned_args = argparse.Namespace(
        **{
            k: v
            for k, v in vars(args).items()
            if not isinstance(v, type(INJECTED))
        }
    )

    import matplotlib.pyplot as plt

    CONFIG, stdout, stderr, plt, COLORS, rngg = start(
        sys=sys_module,
        plt=plt,
        args=cleaned_args,
        file=caller_file,
        sdir_suffix=sdir_suffix or func.__name__,
        verbose=verbose,
        agg=agg,
        **session_kwargs,
    )

    # Logger for the user's script.
    script_logger = getLogger(func.__module__)

    # Inject session variables into the wrapped function's globals.
    func_globals = func.__globals__
    func_globals["CONFIG"] = CONFIG
    func_globals["plt"] = plt
    func_globals["COLORS"] = COLORS
    func_globals["rngg"] = rngg
    func_globals["logger"] = script_logger

    if verbose:
        _decorator_logger.info("=" * 60)
        _decorator_logger.info(
            "Injected Global Variables (available in your function):"
        )
        _decorator_logger.info("  • CONFIG - Session configuration dict")
        _decorator_logger.info(f"      - CONFIG['ID']: {CONFIG['ID']}")
        _decorator_logger.info(
            f"      - CONFIG['SDIR_RUN']: {CONFIG['SDIR_RUN']}"
        )
        _decorator_logger.info(f"      - CONFIG['PID']: {CONFIG['PID']}")
        _decorator_logger.info(
            "  • plt - matplotlib.pyplot (configured for session)"
        )
        _decorator_logger.info(
            "  • COLORS - CustomColors (for consistent plotting)"
        )
        _decorator_logger.info(
            "  • rngg - RandomStateManager (for reproducibility)"
        )
        _decorator_logger.info(
            "  • logger - SciTeX logger (configured for your script)"
        )
        _decorator_logger.info("=" * 60)

    exit_status = 0
    result = None

    try:
        kwargs = vars(args)

        sig = inspect.signature(func)
        func_params = set(sig.parameters.keys())

        injection_map = {
            "CONFIG": CONFIG,
            "plt": plt,
            "COLORS": COLORS,
            "rngg": rngg,
            "logger": script_logger,
        }

        filtered_kwargs = {}

        # First, add all parsed CLI arguments.
        for k, v in kwargs.items():
            if k in func_params:
                filtered_kwargs[k] = v

        # Then, inject parameters that have INJECTED as default.
        for param_name, param in sig.parameters.items():
            if param.default != inspect.Parameter.empty and isinstance(
                param.default, type(INJECTED)
            ):
                if param_name in injection_map:
                    filtered_kwargs[param_name] = injection_map[param_name]

        if verbose:
            args_summary = {
                k: type(v).__name__ for k, v in filtered_kwargs.items()
            }
            _decorator_logger.info(
                f"Running {func.__name__} with injected parameters:"
            )
            _decorator_logger.info(args_summary, pprint=True, indent=2)

        # Execute function.
        result = func(**filtered_kwargs)

        # Map int returns to exit status.
        if isinstance(result, int):
            exit_status = result
        else:
            exit_status = 0

    except Exception as e:
        _decorator_logger.error(
            f"Error in {func.__name__}: {e}", exc_info=True
        )
        exit_status = 1
        raise

    finally:
        # Close session with error handling.
        try:
            close(
                CONFIG=CONFIG,
                verbose=verbose,
                notify=notify,
                message=f"{func.__name__} completed",
                exit_status=exit_status,
                archive_format=archive_format,
            )
        except SystemExit:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as e:
            try:
                _decorator_logger.error(f"Session cleanup error: {e}")
            except Exception:
                print(f"Session cleanup error: {e}")

        # Final matplotlib cleanup (belt and suspenders).
        try:
            import matplotlib.pyplot as _plt

            _plt.close("all")
        except Exception:
            pass

    return result


def run(
    func: Callable,
    parse_args: Callable = None,
    **session_kwargs,
) -> Any:
    """Run a function with session management — explicit alternative to ``@session``.

    Parameters
    ----------
    func : callable
        Function to run.
    parse_args : callable, optional
        Custom argument parser. If ``None``, an argparse parser is
        auto-generated from ``func``'s signature via :func:`_create_parser`.
    **session_kwargs
        Forwarded to ``scitex_session.start`` / ``close``.

    Returns
    -------
    int
        Exit status. ``0`` on success; non-zero on failure (also re-raised).

    Example::

        def main(args):
            # ... your code ...
            return 0

        if __name__ == '__main__':
            stx.session.run(main)
    """
    if parse_args is None:
        parser = _create_parser(func)
        args = parser.parse_args()
    else:
        args = parse_args()

    frame = inspect.currentframe()
    caller_frame = frame.f_back
    caller_file = caller_frame.f_globals.get("__file__", "unknown.py")

    import matplotlib.pyplot as plt

    CONFIG, stdout, stderr, plt, COLORS, rngg = start(
        sys=sys_module,
        plt=plt,
        args=args,
        file=caller_file,
        **session_kwargs,
    )

    exit_status: int = 0
    try:
        if hasattr(args, "__dict__"):
            exit_status = func(args)
        else:
            exit_status = func()
        exit_status = exit_status or 0
    except Exception as e:
        _decorator_logger.error(f"Error: {e}", exc_info=True)
        exit_status = 1
        raise
    finally:
        close(
            CONFIG=CONFIG,
            exit_status=exit_status,
            **session_kwargs,
        )

    return exit_status


# EOF
