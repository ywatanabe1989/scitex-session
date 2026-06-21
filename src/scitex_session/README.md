<!--
# scitex-session

`@session` decorator + lifecycle (auto-CLI, output dir tree, randomstate, configs).
-->

# scitex-session

Experiment session management for reproducible scientific computing.

## Overview

`scitex-session` provides a `@session` decorator and manual lifecycle
(`start()`/`close()`) for reproducible experiment orchestration:

- Auto-CLI from `def main(...)` signature
- Loads `./config/*.yaml` into a `DotDict` CONFIG
- Configures matplotlib + stdlib logging
- Seeds a `RandomStateManager` for reproducibility
- Writes outputs under `script_out/<status>/<session_id>/`

## Quick Start

```python
import scitex_session as sess

@sess.session
def main(
    CONFIG=sess.INJECTED,
    plt=sess.INJECTED,
    COLORS=sess.INJECTED,
    rngg=sess.INJECTED,
):
    """Args injected by @sess.session decorator"""
    print(f"Session ID: {CONFIG['ID']}")

if __name__ == "__main__":
    main()
```

## Core Functions

### `@sess.session` Decorator

The recommended way to use `scitex-session` is through the `@sess.session`
decorator, which automatically handles session initialization and cleanup.

```python
import scitex_session as sess

@sess.session
def main(
    CONFIG=sess.INJECTED,
    plt=sess.INJECTED,
    COLORS=sess.INJECTED,
    rngg=sess.INJECTED,
):
    """Args injected by @sess.session decorator"""
    print(f"Session ID: {CONFIG['ID']}")

if __name__ == "__main__":
    main()
```

The decorator automatically injects the following parameters:
- `CONFIG`: Configuration dictionary with session metadata
- `plt`: Configured matplotlib.pyplot module
- `COLORS`: Color cycle dictionary
- `rngg`: RandomStateManager instance

Using `sess.INJECTED` as default values makes it explicit that these
parameters are injected by the decorator.

Decorator parameters:
- `file`: Script file path (auto-detected if None)
- `sdir`: Save directory (auto-generated if None)
- `sdir_suffix`: Suffix appended to the auto-generated save directory
- `seed`: Random seed for reproducibility (default: 42)
- `agg`: Use matplotlib Agg backend (default: False)
- `verbose`: Print detailed information (default: True)
- `fig_size_mm`, `fig_scale`, `dpi_display`, `dpi_save`, `fontsize`,
  `autolayout`, `hide_top_right_spines`, `alpha`, `line_width`:
  Matplotlib figure defaults
- `clear_logs`: Clear existing log directory before starting
- `show_execution_flow`: Print code-flow analysis at startup

### `sess.start()` (Advanced)

Initialize experiment session with reproducibility settings. Note: The
decorator approach is recommended over direct `start()`/`close()` calls.

Parameters:
- `sys`: Python sys module for I/O redirection
- `plt`: Matplotlib pyplot module
- `file`: Script file path (auto-detected if None)
- `sdir`: Save directory (auto-generated if None)
- `sdir_suffix`: Suffix for save directory name
- `seed`: Random seed for reproducibility (default: 42)
- `agg`: Use matplotlib Agg backend (default: False)
- `verbose`: Print detailed information (default: True)

Returns:
- `CONFIGS`: Configuration dictionary with session metadata
- `stdout`, `stderr`: Redirected output streams
- `plt`: Configured matplotlib.pyplot module
- `COLORS`: Color cycle dictionary
- `rng`: RandomStateManager instance

### `sess.close()` (Advanced)

Close experiment session and finalize logging. The decorator handles this
automatically.

Parameters:
- `CONFIG`: Configuration dictionary from `start()`
- `message`: Completion message (default: `':)'`)
- `notify`: Send notification (default: False)
- `verbose`: Print verbose output (default: True)
- `exit_status`: 0=success, 1=error, None=finished

### `sess.SessionManager`

Class-style lifecycle manager for multi-phase or nested runs:

```python
from scitex_session import SessionManager

manager = SessionManager()
manager.create_session(...)
active = manager.get_active_sessions()
info = manager.get_session(session_id)
```

### `sess.run(func, **session_kwargs)`

Programmatic entry point — runs a callable with the full session lifecycle
applied. No decorator, no `if __name__ == "__main__":` boilerplate.

### `sess.running2finished(CONFIG, exit_status=None, ...)`

Promotes a `script_out/RUNNING/<id>/` directory to
`script_out/FINISHED_SUCCESS/<id>/` (or `FINISHED_ERROR/`). Called
automatically by `close()`; exposed for recovery scripts.

## Features

### Automatic Logging

- Redirects `sys.stdout`/`sys.stderr` to log files via `scitex_logging.tee`
- Saves logs to `script_out/*/<id>/logs/{stdout,stderr}.log`
- Removes ANSI escape codes from log files on close
- Captures all print statements

### Reproducibility

- Fixed random seeds via `RandomStateManager`
- Supports `os`, `random`, `numpy`, `torch`
- Records all configuration parameters
- Timestamps and session IDs

### Session Tracking

- Unique session IDs (4 alphanumeric characters)
- Process ID (PID) tracking
- Start/end timestamps via `datetime`
- Runtime calculation (HH:MM:SS)

### Directory Management

- Auto-generates save directories from script path
- `RUNNING/` for active sessions
- `FINISHED_SUCCESS/` / `FINISHED_ERROR/` / `FINISHED/` on completion

### Configuration Management

- Saves CONFIG as `.pkl` and `.yaml` under `CONFIGS/`
- Includes all session metadata
- Command-line arguments captured in `ARGS`
- Path objects and strings supported

## Advanced Usage

### Custom Save Directory

```python
@sess.session(sdir="/custom/path/")
def main():
    pass
```

### Debug Mode

Set `IS_DEBUG: true` in `./config/IS_DEBUG.yaml` — session IDs will be
prefixed with `"DEBUG_"`.

### Manual Lifecycle

```python
import scitex_session as sess

CONFIG, plt, logger, rng = sess.start()
try:
    ...
finally:
    sess.close(exit_status=0)
```

## Directory Structure

```
/path/to/script.py
/path/to/script_out/
├── RUNNING/
│   └── XXXX/              # Session ID
│       ├── logs/
│       │   ├── stdout.log
│       │   └── stderr.log
│       └── CONFIGS/
│           ├── CONFIG.pkl
│           └── CONFIG.yaml
├── FINISHED_SUCCESS/
├── FINISHED_ERROR/
└── FINISHED/
```

## Configuration Object (CONFIG)

| Key             | Type       | Description                         |
|-----------------|------------|-------------------------------------|
| `ID`            | str        | Session identifier                  |
| `PID`           | int        | Process ID                          |
| `START_DATETIME`| datetime   | Session start timestamp             |
| `END_DATETIME`  | datetime   | Session end timestamp               |
| `RUN_DURATION`  | str        | Formatted runtime (HH:MM:SS)        |
| `FILE`          | Path       | Script file path                    |
| `SDIR_OUT`      | Path       | Base output directory               |
| `SDIR_RUN`      | Path       | Current session directory           |
| `ARGS`          | dict       | Command-line arguments              |
| `EXIT_STATUS`   | int/None   | Exit code (0=success, 1=error)      |

## Matplotlib Integration

```python
import scitex_session as sess

@sess.session(
    fig_size_mm=(160, 100),
    dpi_save=300,
    hide_top_right_spines=True,
    alpha=0.9
)
def main(plt=sess.INJECTED, COLORS=sess.INJECTED):
    plt.plot([1, 2, 3], color=COLORS[0])
```

- `plt` and `COLORS` are injected by the decorator
- When available, `scitex_plt` replaces `matplotlib.pyplot` for enhanced
  functionality (optional dep — falls back to plain pyplot)
- Automatic style configuration via `figrecipe` (optional dep)

## Random State Management

```python
@sess.session(seed=42)
def main(rngg=sess.INJECTED):
    arr = rngg.random((10, 10))
```

- `rngg` is a `RandomStateManager` instance
- Automatically fixes seeds for `os`, `random`, `numpy`, `torch`
- Reproducible across runs with the same seed

## Standalone vs Umbrella

`scitex-session` is a standalone package; it is also part of the
[scitex umbrella](https://pypi.org/project/scitex/). The same module
is reachable via two import paths:

```python
# Standalone — pip install scitex-session
import scitex_session as sess

# Umbrella — pip install scitex
import scitex
sess = scitex.session
```

`pip install scitex-session` alone does **not** expose the `scitex`
namespace. To get both paths, install both:
`pip install scitex scitex-session` (or `pip install scitex[session]`).

## Part of SciTeX

`scitex-session` is part of [**SciTeX**](https://scitex.ai).

> Four Freedoms for Research
>
> 0. The freedom to **run** your research anywhere — your machine, your terms.
> 1. The freedom to **study** how every step works — from raw data to final manuscript.
> 2. The freedom to **redistribute** your workflows, not just your papers.
> 3. The freedom to **modify** any module and share improvements with the community.
>
> AGPL-3.0 — because we believe research infrastructure deserves the same freedoms as the software it runs on.

<!-- EOF -->