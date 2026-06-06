#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-05-26 (ywatanabe)"
# File: src/scitex_session/_decorator/_cli.py
"""argparse generation from a function's signature.

Pulled out of the original ``_decorator.py`` (>512 lines) so each piece
of the @stx.session machinery lives in a focused module.
"""

from __future__ import annotations

import argparse
import inspect
import os
from pathlib import Path
from typing import Callable, get_type_hints

from .. import INJECTED


def _create_parser(func: Callable) -> argparse.ArgumentParser:
    """Create an ArgumentParser from ``func``'s signature.

    Parameters
    ----------
    func : callable
        Function to create the parser for. Its annotated parameters
        become CLI arguments; parameters with default value
        ``INJECTED`` are skipped (they're injected by the decorator).

    Returns
    -------
    argparse.ArgumentParser
        Parser configured with the function's args + an epilog that
        documents the decorator-injected globals.
    """
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or f"Run {func.__name__}"

    # Try to get type hints.
    try:
        type_hints = get_type_hints(func)
    except Exception:
        type_hints = {}

    # Get actual values for deterministic items.
    caller_file = func.__globals__.get("__file__", "unknown.py")

    sdir_out = Path(os.path.splitext(caller_file)[0] + "_out")
    sdir_run_example = sdir_out / "RUNNING" / "<SESSION_ID>"

    current_pid = os.getpid()

    # Check for config YAML files and list all variables with values.
    config_status = _summarise_config_yaml_at_help_time()

    # Available colour keys (best-effort; falls back to a short list).
    try:
        import matplotlib.pyplot as plt_temp

        from figrecipe.utils._configure_mpl import configure_mpl

        _, colors_dict = configure_mpl(plt_temp)
        color_keys = ", ".join(f"'{k}'" for k in sorted(colors_dict.keys()))
    except Exception:
        color_keys = "'blue', 'red', 'green', 'yellow', 'purple', 'orange', ..."

    epilog = f"""
Global Variables Injected by @session Decorator:

    CONFIG (DotDict)
        Session configuration with ID, paths, timestamps
        Access: CONFIG['key'] or CONFIG.key (both work!)

        - CONFIG.ID
            <SESSION_ID> (created at runtime, e.g., '2025Y-11M-18D-07h53m37s_Z5MR')
        - CONFIG.FILE
            {Path(caller_file)}
        - CONFIG.SDIR_OUT
            {sdir_out}
        - CONFIG.SDIR_RUN
            {sdir_run_example}
        - CONFIG.PID
            {current_pid} (current Python process)
        - CONFIG.ARGS
            {{'arg1': '<value>'}} (parsed from command line)

{config_status}

    plt (module)
        matplotlib.pyplot configured for session

    COLORS (DotDict)
        Color palette for consistent plotting
        Access: COLORS.blue or COLORS['blue'] (both work!)

        Available keys:
            {color_keys}

        Usage:
            plt.plot(x, y, color=COLORS.blue)
            plt.plot(x, y, color=COLORS['blue'])

    rngg (RandomStateManager)
        Manages reproducible randomness

    logger (SciTeXLogger)
        Logger configured for your script
"""

    parser = argparse.ArgumentParser(
        description=doc,
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    used_short_forms = {"h"}  # Reserve -h for help.

    for param_name, param in sig.parameters.items():
        # Skip parameters with INJECTED as default.
        if param.default != inspect.Parameter.empty and isinstance(
            param.default, type(INJECTED)
        ):
            continue

        short_form = _generate_short_form(param_name, used_short_forms)
        if short_form:
            used_short_forms.add(short_form)

        _add_argument(parser, param_name, param, type_hints, short_form)

    return parser


def _summarise_config_yaml_at_help_time() -> str:
    """Best-effort listing of variables from ./config/*.yaml at --help time."""
    try:
        config_dir = Path("./config")
        if not config_dir.exists():
            return (
                "        CONFIG from YAML files:\n"
                "        (./config/ directory not found)"
            )
        yaml_files = sorted(config_dir.glob("*.yaml"))
        if not yaml_files:
            return (
                "        CONFIG from YAML files:\n"
                "        (no .yaml files found)"
            )
        try:
            import yaml

            all_vars = []
            for yaml_file in yaml_files:
                with open(yaml_file, "r") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    continue
                namespace = yaml_file.stem.upper()
                for key, value in data.items():
                    value_str = str(value)
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    all_vars.append(
                        f"        - CONFIG.{namespace}.{key} "
                        f"(from ./config/{yaml_file.name})\n"
                        f"            {value_str}"
                    )
            if all_vars:
                return "        CONFIG from YAML files:\n" + "\n".join(all_vars)
            return (
                "        CONFIG from YAML files:\n"
                "        (no variables found)"
            )
        except Exception:
            return (
                "        CONFIG from YAML files:\n"
                "        (unable to load at help-time, will be available "
                "at runtime)"
            )
    except Exception:
        return (
            "        CONFIG from YAML files:\n"
            "        (unable to check at help-time)"
        )


def _generate_short_form(param_name: str, used_short_forms: set) -> str:
    """Generate a short form for a parameter name avoiding conflicts.

    Parameters
    ----------
    param_name : str
        Full parameter name.
    used_short_forms : set
        Set of already-used short forms.

    Returns
    -------
    str or None
        Short form character/string, or ``None`` if no unique form
        can be generated.
    """
    # Strategy 1: try first letter.
    first_letter = param_name[0].lower()
    if first_letter not in used_short_forms:
        return first_letter

    # Strategy 2: try first letter of each word.
    words = param_name.replace("_", " ").replace("-", " ").split()
    if len(words) > 1:
        acronym = "".join(w[0].lower() for w in words)
        if len(acronym) == 1 and acronym not in used_short_forms:
            return acronym

    # Strategy 3: try first two letters.
    if len(param_name) >= 2:
        two_letters = param_name[:2].lower()
        if two_letters not in used_short_forms:
            return two_letters

    # Strategy 4: try each character in sequence.
    for char in param_name.lower():
        if char.isalnum() and char not in used_short_forms:
            return char

    return None


def _add_argument(
    parser: argparse.ArgumentParser,
    param_name: str,
    param: inspect.Parameter,
    type_hints: dict,
    short_form: str = None,
) -> None:
    """Add a single argument to ``parser`` derived from ``param``.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Parser to add the argument to.
    param_name : str
        Parameter name.
    param : inspect.Parameter
        Parameter object from ``inspect.signature``.
    type_hints : dict
        Type-hints dictionary (from ``typing.get_type_hints``).
    short_form : str, optional
        Optional short form (e.g. ``'a'`` for ``-a``).
    """
    from typing import Literal, get_args, get_origin

    param_type = type_hints.get(param_name, param.annotation)
    if param_type == inspect.Parameter.empty:
        param_type = str

    has_default = param.default != inspect.Parameter.empty
    default = param.default if has_default else None

    arg_name = f"--{param_name.replace('_', '-')}"
    arg_names = [arg_name]
    if short_form:
        arg_names.insert(0, f"-{short_form}")

    # Literal[...] → choices
    choices = None
    origin = get_origin(param_type)
    if origin is Literal:
        choices = list(get_args(param_type))
        param_type = type(choices[0]) if choices else str

    if param_type is bool:
        parser.add_argument(
            *arg_names,
            action="store_true" if not default else "store_false",
            default=default,
            help=f"(default: {default})",
        )
        return

    choices_str = f", choices: {choices}" if choices else ""
    kwargs = {
        "type": param_type,
        "help": (
            f"(default: {default}{choices_str})"
            if has_default
            else f"(required{choices_str})"
        ),
    }
    if choices:
        kwargs["choices"] = choices
    if has_default:
        kwargs["default"] = default
    else:
        kwargs["required"] = True

    parser.add_argument(*arg_names, **kwargs)


# EOF
