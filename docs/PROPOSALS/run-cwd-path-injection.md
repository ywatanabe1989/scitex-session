# PROPOSAL: project-root injection into `sys.path` for `@scitex_session.session` users

Status: DRAFT — pending owner review (ywatanabe)
Author: proj-neurovista (relayed from operator, 2026-06-06)
Affects: `scitex_session._decorator._run.run()` and the `@scitex_session.session` decorator path.

---

## 1. Motivation

A user runs a research script that lives at `./scripts/foo/bar.py`, decorated with `@scitex_session.session`. The script imports a sibling helper:

```python
# ./scripts/foo/bar.py
from scripts.utils._date_parsing import parse_session_date
```

Invocation forms behave differently:

| Form                                                           | Works? | Why                                                                |
|----------------------------------------------------------------|--------|--------------------------------------------------------------------|
| `python -m scripts.foo.bar`                                    | ✅      | `sys.path[0]` is `''` (cwd), `scripts` resolves                     |
| `python ./scripts/foo/bar.py`                                  | ❌      | `sys.path[0]` is `./scripts/foo/`, `scripts` not on path            |
| `./scripts/foo/bar.py` (shebang)                               | ❌      | Same as above                                                       |
| `bash submit.sh` where `submit.sh` shebang-runs the script     | ❌      | Same as above; observed in production                               |

This bit neurovista on 2026-06-06: the SLE PAC SLURM driver shebang-executed `./scripts/pac/stats/calc_pac_stats.py`, which crashed on `from scripts.io import load_pac` with `ModuleNotFoundError: No module named 'scripts'`. pac_db was written by an earlier script that happened not to cross-import; only the downstream stats sidecars vanished silently. External fix: `export PYTHONPATH="$PROJECT_DIR"` in the driver. See neurovista PR #57.

The operator's mental model — `pwd` is always on `PYTHONPATH` — only holds for `python -c`, `python -m`, and the REPL. New users (and AIs) hit this regularly. A library that already wraps user entry can repair the user's `sys.path` *before* their import block runs.

## 2. Current behaviour

`scitex_session/_decorator/_run.py:230-248`:

```python
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
```

`caller_file` is already captured. No `sys.path` or `PYTHONPATH` manipulation happens before `start()`. By the time `start()` returns, the user's import block at the top of their script has already executed (the `import` statements run at module-load time, *before* `if __name__ == '__main__': stx.session.run(main)` ever fires).

→ Injecting at `_run.py:run()` is **too late** for the import errors we want to fix. The hook must run **before module load**, which means at `import scitex_session` time. See §3.3.

## 3. Proposed change

Add an opt-in, project-root-aware `sys.path` injection that runs **at scitex_session import time**, gated on a sentinel-file heuristic.

### 3.1 Detection

Walk upward from `os.getcwd()` (NOT `caller_file`'s dir — the user explicitly chose where to invoke) looking for the first directory containing any of, in priority order:

1. `pyproject.toml`
2. `setup.py` / `setup.cfg`
3. `.git/`
4. `config/PATH.yaml` (scitex / research-project convention)

Cap the walk at 8 levels. If found and not already on `sys.path`, `sys.path.insert(1, str(project_root))` (index 1 so the script's own dir at index 0 still wins for local-name collisions).

### 3.2 Opt-out / opt-in env vars

Three escape hatches, checked in order:

- env `SCITEX_NO_PATH_INJECT=1` → skip entirely
- env `SCITEX_PROJECT_ROOT=<path>` → use that, skip detection
- no project-root marker found within 8 levels → silently no-op

### 3.3 Where to put the call

Three candidate sites; pick one:

**(A)** Module-level in `scitex_session/__init__.py`. Runs at every `import scitex_session`. Most aggressive; fixes the failing-import case because it runs before *any* of the user's other imports if the user does `import scitex_session` early. **Downside**: imported transitively by *anything* depending on scitex_session (every research script in the umbrella), so global state mutation happens implicitly. Hard to undo.

**(B)** Inside `start()` and inside `run()` (both pre-arg-parse). Caller has to have already executed their own import block, so this fixes only *runtime* lookups, not module-load `import` failures. Insufficient on its own.

**(C)** Module-level in `scitex_session/__init__.py`, gated by a `SCITEX_ENABLE_PATH_INJECT=1` opt-IN env var. Same coverage as (A), opt-in. **Recommended**: avoids the surprise of (A) for existing users; new users who hit the trap can enable it once and forget.

### 3.4a Companion linter rule (proactive detection)

Even with the runtime hook, users running outside scitex_session won't get the fix. A static lint rule catches the trap before the script ever runs. Proposed:

- **ID**: `STX-S006` (next free in the structural `S` namespace; engine-shipped `S001`–`S005` already exist)
- **Owner package**: `scitex-dev` for now (engine-shipped, like the other `S*` rules) — or migrate into `scitex_session` once it ships a `_linter_plugin.py`.
- **Severity**: `warning`
- **Trigger** (AST visitor):
  1. File path matches `**/scripts/**/*.py` (configurable via `linter.scripts_dirs`)
  2. File contains a top-level `from scripts.<...> import <...>` or `import scripts.<...>` statement
  3. File EITHER has a `#!` shebang on line 1 OR is marked executable in the index
- **Message**: `Cross-package import 'from scripts.X import …' in a script under ./scripts/ — will fail with ModuleNotFoundError under 'python ./scripts/foo.py' or shebang invocation unless PYTHONPATH points to the project root.`
- **Suggestion**: `Invoke as 'python -m scripts.foo.bar' (Makefile / SLURM driver / CI), OR prepend 'export PYTHONPATH="$PROJECT_DIR"' in the wrapper, OR set 'SCITEX_ENABLE_PATH_INJECT=1' once §3 lands.`
- **Auto-fix** (optional, low-priority): emit a CI-only printable patch suggesting the PYTHONPATH export at the top of any `*.sh` driver in the same repo that invokes the offending script — heuristic, off by default.

Tests for the rule live in the owning package (`tests/test_linter_s006.py`), following the per-package layout in [`general/01_ecosystem/08_linter-plugins.md`](https://gitlab/scitex/general/01_ecosystem/08_linter-plugins.md). Snippet contexts (notebooks, README code blocks) are skipped automatically — `S*` rules already opt out of snippet linting.

Open question: should the rule extend beyond `scripts/` and fire on any `*.py` file outside the installable `src/<pkg>/` tree that does cross-package imports? Probably yes — `examples/`, `notebooks/`, `analyses/`, and `experiments/` all share the same trap. Recommendation: match a configurable list of "non-installable script dirs" (default: `scripts`, `examples`, `notebooks`, `analyses`, `experiments`).

### 3.4 Default ON or default OFF?

Strong opinions both ways:

- **Default ON** (operator's preference, judging from "pwd がいつも PYTHONPATH に入るものだと思ってました"): matches the naive mental model, fixes the trap by default, kills the most common new-user/agent footgun.
- **Default OFF**: silent `sys.path` mutation is dangerous in mixed-tooling environments (CI runners, pytest, sphinx), and is exactly the kind of "convenience" that downstream maintainers (pylint, ruff, mypy plugins) will object to.

Recommendation: **default OFF, with site (C) opt-in** for the first minor version. Document the env var and the failure pattern (already added to the scitex general skills tree at `scitex/general/02_package/03_project-structure-scripts.md` on 2026-06-06). Reassess after one minor version of real-world usage.

## 4. Rejected alternatives

- **Always inject `os.getcwd()` unconditionally.** Breaks when the user `cd`s into a subdir, breaks for tools that intentionally run from `/tmp`. Aggressive and surprising.
- **Always inject `Path(caller_file).parent`.** This is what CPython already does. No fix.
- **Require user to `sys.path.insert(0, …)` at the top of their script.** Status quo. The whole point of `@scitex_session.session` is to remove boilerplate; this is more boilerplate.
- **Detect via `__main__` package context.** Doesn't help when the user invokes by file path (the failing case).
- **A `--add-project-root` argparse flag.** scitex_session.run already builds argparse from the user's function signature; injecting framework flags pollutes the user's CLI.
- **Standalone `scitex run <script>` CLI subcommand.** Solves a different problem; many users want the decorator form, not a wrapper command. Out of scope here.

## 5. Open questions

- What counts as a "project root" if multiple sentinel files are present at different levels (e.g. `.git/` at `~/proj/foo/` but `pyproject.toml` at `~/proj/foo/sub/`)? Recommendation: stop at the first hit in the priority list, regardless of depth. Document explicitly.
- Should we also export `PYTHONPATH` for child processes the user might spawn (e.g. `subprocess.run([sys.executable, '...'])`)? Probably yes, but consider the security implications of mutating env vars on import.
- Interaction with `pytest` collection: pytest already does its own rootdir/sys.path manipulation. Do we conflict? Add a guard: if `PYTEST_CURRENT_TEST` is in env, skip injection.
- Interaction with `jupyter`: notebooks have a different `__file__` semantics. Should we treat notebook callers specially? Probably skip injection when the caller frame is a notebook kernel.
- Interaction with `runpy.run_path` / `runpy.run_module` callers (e.g. `python -m`). Verify the hook is idempotent (re-running it after `cwd` is already on `sys.path` should be a no-op).

## 6. Implementation sketch (not for merge — discussion only)

```python
# scitex_session/_path_inject.py
import os
import sys
from pathlib import Path

_ROOT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", ".git", "config/PATH.yaml")
_MAX_DEPTH = 8


def _detect_project_root(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(_MAX_DEPTH):
        for marker in _ROOT_MARKERS:
            if (cur / marker).exists():
                return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def maybe_inject_project_root() -> Path | None:
    if os.environ.get("SCITEX_NO_PATH_INJECT") == "1":
        return None
    explicit = os.environ.get("SCITEX_PROJECT_ROOT")
    if explicit:
        root = Path(explicit).resolve()
    else:
        if os.environ.get("PYTEST_CURRENT_TEST"):  # pytest handles its own
            return None
        root = _detect_project_root(Path.cwd())
    if root and str(root) not in sys.path:
        sys.path.insert(1, str(root))
    return root
```

Call site per §3.3 recommendation (opt-in C):

```python
# scitex_session/__init__.py — at very top
import os
if os.environ.get("SCITEX_ENABLE_PATH_INJECT") == "1":
    from ._path_inject import maybe_inject_project_root
    maybe_inject_project_root()
```

## 7. Testing plan (when implementing)

- `tests/scitex_session/test_path_inject.py`:
  - Detects `pyproject.toml`, prefers it over `.git`, stops at first hit.
  - Respects `SCITEX_NO_PATH_INJECT=1`.
  - Honours explicit `SCITEX_PROJECT_ROOT`.
  - Idempotent (does nothing if root already on `sys.path`).
  - Skips when `PYTEST_CURRENT_TEST` is set.
  - Walk depth capped at 8.
- E2E: a `scripts/foo/bar.py` script that imports from `scripts.utils.*`, invoked four ways (file path, shebang, `-m`, `-c`), with and without the env var. Assert `ImportError` shape changes only as documented.

## 8. Out of scope

- A standalone `scitex run <script>` CLI subcommand. None currently exists; `scitex_session.run()` is Python-API only. Adding a CLI is a separate proposal.
- Auto-injecting other paths (parent dirs, sibling packages). This proposal is scoped to a single path: the project root as detected by sentinel files.
