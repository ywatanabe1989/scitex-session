---
description: |
  [TOPIC] First `@session` in 30 seconds
  [DETAILS] Wrap `main()` with the decorator; the lifecycle handles CLI parsing, config loading, matplotlib + logging setup, and writes outputs to `script_out/<status>/<session_id>/`.
tags: [scitex-session-quick-start]
---

# Quick Start

## The decorator

```python
import scitex_session as sess

@sess.session
def main(
    param1="default",          # Auto-CLI: --param1
    CONFIG=sess.INJECTED,      # Loaded from ./config/*.yaml
    plt=sess.INJECTED,         # Pre-configured matplotlib
    logger=sess.INJECTED,      # Session logger
    rngg=sess.INJECTED,        # Reproducible RandomStateManager
):
    """Docstring becomes --help."""
    logger.info("hi")
    return 0


if __name__ == "__main__":
    main()
```

Run it:

```bash
python my_script.py --param1 foo
```

## What the decorator does

1. Parses `def main(...)` parameters as CLI flags.
2. Loads `./config/*.yaml` into `CONFIG` (a `DotDict`).
3. Configures matplotlib (`plt`) and stdlib `logging` (`logger`).
4. Seeds a reproducible `RandomStateManager` (`rngg`).
5. Runs the wrapped function.
6. Writes outputs under `script_out/FINISHED_SUCCESS/<session_id>/`
   (or `FINISHED_FAILURE/` on exception).

## Manual lifecycle

If the decorator's contract doesn't fit, drive it yourself:

```python
import scitex_session as sess

CONFIG, plt, logger, rngg = sess.start()
try:
    ...
finally:
    sess.close()
```

## See also

- [03_python-api.md](03_python-api.md) — full Python surface
