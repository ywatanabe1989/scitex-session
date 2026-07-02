#!/usr/bin/env python3
# Timestamp: "2026-02-01 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-python/src/scitex/session/_lifecycle/_start.py
"""Session start function."""

from __future__ import annotations

import inspect
import logging
import os as _os
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from scitex_dict import DotDict
from scitex_repro import RandomStateManager
from scitex_str import clean_path

from .._manager import get_global_session_manager
from ._config import setup_configs
from ._matplotlib import setup_matplotlib
from ._utils import (
    clear_python_log_dir,
    get_debug_mode,
    initialize_env,
    print_header,
    simplify_relative_path,
)

logger = getLogger(__name__)

# For development code flow analysis
from scitex_dev import try_import_optional

analyze_code_flow = try_import_optional(
    "scitex_dev._analyze_code_flow", "analyze_code_flow"
)
if analyze_code_flow is None:

    def analyze_code_flow(file):
        return "Code flow analysis not available"


# Top-level module-name prefixes whose frames belong to the SciTeX
# session/dev plumbing (decorators, wrappers, MCP bridges, …). When
# walking the call stack to find the *user's* script we skip frames
# whose module name starts with any of these — they are intermediate
# wrappers, not the real caller. ``scitex_session`` self-skip handles
# the @stx.session wrapper chain; ``scitex_dev`` handles agent /
# harness / decorator layers that wrap @stx.session further. We match
# on module names (via ``inspect.getmodule``) rather than filename
# substrings so that the ``tests/scitex_session/`` test tree (whose
# *files* contain ``/scitex_session/`` but whose *module* names are
# ``tests.scitex_session.…``) is not falsely flagged as internal.
_INTERNAL_MODULE_PREFIXES: Tuple[str, ...] = (
    "scitex_session.",
    "scitex_session",
    "scitex_dev.",
    "scitex_dev",
)


def _is_internal_module_name(modname: Optional[str]) -> bool:
    """Return True iff ``modname`` is a scitex_session / scitex_dev
    plumbing module (i.e. an intermediate wrapper frame, not the
    user's script)."""
    if not modname:
        return False
    return any(
        modname == prefix.rstrip(".") or modname.startswith(prefix)
        for prefix in _INTERNAL_MODULE_PREFIXES
    )


def _is_internal_frame_file(path: str) -> bool:
    """Filename-based fallback used when a frame has no resolvable
    module (e.g. dynamically-exec'd code). Matches an *installed* or
    src-tree package path — does NOT match ``tests/scitex_session/``
    paths because those are below a ``tests`` parent, not a package
    init."""
    if not path:
        return True
    norm = path.replace("\\", "/")
    # Match "/scitex_session/_..." or "/scitex_dev/_..." (underscored
    # internal submodules), or "/site-packages/scitex_session/" /
    # "/site-packages/scitex_dev/" (installed package frames). The
    # tests/scitex_session/ tree does NOT match either pattern.
    for pkg in ("scitex_session", "scitex_dev"):
        if f"/site-packages/{pkg}/" in norm:
            return True
        if f"/src/{pkg}/" in norm:
            return True
    return False


def _find_user_caller_file(hint: Optional[str] = None) -> str:
    """Resolve the user's script path by walking the call stack outward.

    Walks ``inspect.stack()`` from innermost to outermost and returns
    the filename of the first frame whose module name does NOT start
    with ``scitex_session`` / ``scitex_dev`` (i.e. is not an
    intermediate plumbing frame). The optional ``hint`` (typically the
    ``file=`` parameter that the @stx.session wrapper threads through)
    is used when it is a non-internal path; if the hint itself points
    at an internal wrapper file (the bug operator hit on neurovista —
    the figure landed in ``site-packages/.../decorators_out/`` because
    the wrapper's ``__file__`` was used) we discard it and walk
    instead.

    Falls back to a stable sentinel only if no user frame can be found
    (deep notebook / -c invocation); the existing IPython branch in
    :func:`start` handles those cases after this returns.
    """
    if hint and not _is_internal_frame_file(hint):
        return hint

    for frame_info in inspect.stack():
        candidate = frame_info.filename or ""
        # Skip transient stdlib / runpy frames that are also not the user.
        if candidate.startswith("<"):  # "<string>", "<stdin>", "<frozen ...>"
            continue
        mod = inspect.getmodule(frame_info.frame)
        modname = getattr(mod, "__name__", None)
        if _is_internal_module_name(modname):
            continue
        # When the frame has no resolvable module (rare; dynamically
        # exec'd code), fall back to the filename heuristic.
        if modname is None and _is_internal_frame_file(candidate):
            continue
        return candidate

    # No user frame located; preserve previous behaviour and fall back
    # to whatever the innermost non-self frame was.
    stack = inspect.stack()
    if len(stack) > 1:
        return stack[1].filename
    return hint or "unknown.py"


def start(
    sys=None,
    plt=None,
    file: Optional[str] = None,
    sdir: Optional[Union[str, Path]] = None,
    sdir_suffix: Optional[str] = None,
    args: Optional[Any] = None,
    os: Optional[Any] = None,
    random: Optional[Any] = None,
    np: Optional[Any] = None,
    torch: Optional[Any] = None,
    seed: int = 42,
    agg: bool = False,
    fig_size_mm: Tuple[int, int] = (160, 100),
    fig_scale: float = 1.0,
    dpi_display: int = 100,
    dpi_save: int = 300,
    fontsize="small",
    autolayout=False,
    show_execution_flow=False,
    hide_top_right_spines: bool = True,
    alpha: float = 0.9,
    line_width: float = 1.0,
    clear_logs: bool = False,
    verbose: bool = True,
) -> Tuple[DotDict, Any, Any, Any, Optional[Dict[str, Any]], Any]:
    """Initialize experiment session with reproducibility settings.

    .. note::
       **INTERNAL / advanced.** This is the low-level lifecycle the
       ``@scitex_session.session`` decorator orchestrates — prefer the
       decorator. Note the signature is ``start(sys, plt, ...)``; it is
       *not* a decorator (``@scitex_session.start`` would bind your
       function to the ``sys`` parameter). Reach it as
       ``scitex_session._start`` for power-user access; the bare
       ``scitex_session.start`` name is deprecated.

    Parameters
    ----------
    sys : module, optional
        Python sys module for I/O redirection
    plt : module, optional
        Matplotlib pyplot module for plotting configuration
    file : str, optional
        Script file path. If None, automatically detected
    sdir : Union[str, Path], optional
        Save directory path
    sdir_suffix : str, optional
        Suffix to append to save directory
    args : object, optional
        Command line arguments or configuration object
    seed : int, default=42
        Random seed for reproducibility
    agg : bool, default=False
        Whether to use matplotlib Agg backend
    verbose : bool, default=True
        Whether to print detailed information

    Returns
    -------
    tuple
        (CONFIGS, stdout, stderr, plt, COLORS, rng)
    """
    IS_DEBUG = get_debug_mode()
    ID, PID = initialize_env(IS_DEBUG)

    # Convert Path objects to strings for internal processing
    if sdir is not None and isinstance(sdir, Path):
        sdir = str(sdir)

    # Defines SDIR
    if sdir is None:
        # Define __file__.
        #
        # The naive `inspect.stack()[1].filename` (and the analogous
        # `frame.f_back` walk in the @stx.session wrapper) lands on the
        # internal scitex_session / scitex_dev wrapper frame when the
        # user's script is wrapped through one or more decorator layers
        # (operator-observed: figures saving to
        # ``site-packages/.../decorators_out/`` instead of
        # ``<user_script>_out/``). Walk the stack OUTWARD to the first
        # frame whose filename is NOT inside a scitex_session /
        # scitex_dev source path — that's the real user script. The
        # ``file=`` parameter (when supplied by a callsite that already
        # knows the user's path, e.g. notebook integrations) is used as
        # a hint, but if it still points at an internal scitex frame
        # we override it with the walked result.
        caller_file = _find_user_caller_file(hint=file)
        if "ipython" in caller_file.lower():
            try:
                from scitex_context import get_notebook_path

                nb_path = get_notebook_path()
                caller_file = nb_path if nb_path else f"/tmp/{_os.getenv('USER')}.py"
            except Exception:
                caller_file = f"/tmp/{_os.getenv('USER')}.py"

        # Convert to absolute path if relative and resolve symlinks
        if not _os.path.isabs(caller_file):
            caller_file = _os.path.realpath(_os.path.abspath(caller_file))
        else:
            caller_file = _os.path.realpath(caller_file)

        # Define sdir
        sdir = clean_path(_os.path.splitext(caller_file)[0] + f"_out/RUNNING/{ID}/")

        # Optional
        if sdir_suffix:
            sdir = sdir[:-1] + f"-{sdir_suffix}/"
    else:
        caller_file = file

    if clear_logs and caller_file:
        clear_python_log_dir(sdir + caller_file + "/")
    _os.makedirs(sdir, exist_ok=True)
    relative_sdir = simplify_relative_path(sdir)

    # Setup configs - use caller_file (computed) instead of file (parameter)
    CONFIGS = setup_configs(
        IS_DEBUG, ID, PID, caller_file, sdir, relative_sdir, verbose
    )

    # Logging
    if sys is not None:
        from scitex_io._flush import flush
        from scitex_logging import tee

        flush(sys)
        sys.stdout, sys.stderr = tee(sys, sdir=sdir, verbose=verbose)
        CONFIGS["_sys"] = sys

        # Redirect logging handlers to use the tee-wrapped streams
        _redirect_logging_handlers(sys)

    # Initialize RandomStateManager
    rng = RandomStateManager(seed=seed, verbose=verbose)
    if verbose:
        logger.info(f"Initialized RandomStateManager with seed {seed}")

    # Matplotlib configurations
    plt, COLORS = setup_matplotlib(
        plt,
        agg,
        fig_size_mm=fig_size_mm,
        fig_scale=fig_scale,
        dpi_display=dpi_display,
        dpi_save=dpi_save,
        hide_top_right_spines=hide_top_right_spines,
        alpha=alpha,
        line_width=line_width,
        fontsize=fontsize,
        autolayout=autolayout,
        verbose=verbose,
    )

    # Adds argument-parsed variables
    if args is not None:
        CONFIGS["ARGS"] = vars(args) if hasattr(args, "__dict__") else args

    CONFIGS = DotDict(CONFIGS)

    # Register session
    session_manager = get_global_session_manager()
    session_manager.create_session(ID, CONFIGS)

    print_header(ID, PID, caller_file, args, CONFIGS, verbose)

    if show_execution_flow:
        from scitex_str import printc as _printc

        structure = analyze_code_flow(caller_file)
        _printc(structure)

    # Start verification tracking
    _start_verification(CONFIGS)

    # Return appropriate values based on whether sys was provided
    if sys is not None:
        return CONFIGS, sys.stdout, sys.stderr, plt, COLORS, rng
    else:
        return CONFIGS, None, None, plt, COLORS, rng


def _redirect_logging_handlers(sys) -> None:
    """Redirect logging handlers to use tee-wrapped streams."""
    # Update all existing StreamHandler instances
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        try:
            lgr = logging.getLogger(logger_name)
            for handler in lgr.handlers:
                if isinstance(handler, logging.StreamHandler):
                    if not hasattr(handler, "stream"):
                        continue
                    if handler.stream in (sys.__stderr__, sys.__stdout__):
                        handler.stream = (
                            sys.stderr
                            if handler.stream == sys.__stderr__
                            else sys.stdout
                        )
        except Exception:
            pass

    # Also update the root logger handlers
    try:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                if not hasattr(handler, "stream"):
                    continue
                if handler.stream in (sys.__stderr__, sys.__stdout__):
                    handler.stream = (
                        sys.stderr if handler.stream == sys.__stderr__ else sys.stdout
                    )
    except Exception:
        pass


def _start_verification(CONFIG) -> None:
    """Start verification tracking for this session.

    Dispatches to registered session-start hooks (e.g. clew lineage) via the
    acyclic registry; session never imports the subscriber. See _hooks.py.
    """
    try:
        from .._hooks import _fire_session_start_hooks

        session_id = CONFIG.get("ID", "unknown")
        file_path = CONFIG.get("FILE")
        if file_path is not None:
            file_path = str(file_path)

        metadata = None
        if file_path and file_path.endswith(".ipynb"):
            metadata = {"notebook_path": file_path}

        _fire_session_start_hooks(
            session_id, script_path=file_path, metadata=metadata
        )
    except Exception:
        pass


# EOF
