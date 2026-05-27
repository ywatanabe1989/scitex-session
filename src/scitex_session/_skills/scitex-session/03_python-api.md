---
description: |
  [TOPIC] Public Python API of scitex-session
  [DETAILS] The `@session` decorator, manual `start()`/`close()`, the `SessionManager` class, the `INJECTED` sentinel, and `running2finished()`.
tags: [scitex-session-python-api]
---

# Python API

```python
import scitex_session as sess
```

## `@sess.session`

Decorator. Wraps `def main(...)`; turns parameters into CLI flags,
loads `config/*.yaml`, configures matplotlib + logging, seeds a
`RandomStateManager`, and writes outputs under `script_out/`.

```python
@sess.session
def main(param1="default",
         CONFIG=sess.INJECTED,
         plt=sess.INJECTED,
         logger=sess.INJECTED,
         rngg=sess.INJECTED):
    return 0
```

Parameters with `sess.INJECTED` as default are filled by the decorator.
Other parameters become CLI flags (`--param1`).

## `sess.INJECTED`

Sentinel sigil for parameters the decorator should fill. Distinct from
`None` so user-supplied `None` is preserved.

## `sess.start(...)` / `sess.close(...)`

Manual lifecycle when the decorator is too rigid:

```python
CONFIG, plt, logger, rngg = sess.start()
try:
    ...
finally:
    sess.close()
```

## `sess.SessionManager`

Class form of the lifecycle. Useful for nested or multi-phase runs:

```python
mgr = sess.SessionManager()
mgr.start()
...
mgr.close()
```

## `sess.run(...)`

Programmatic entry point — runs a callable with the session lifecycle
applied (no decorator, no `if __name__ == "__main__":` boilerplate).

## `sess.running2finished(...)`

Promotes a `script_out/RUNNING/<id>/` directory to
`script_out/FINISHED_SUCCESS/<id>/` (or `FINISHED_FAILURE/`). Called
automatically by `close()`; exposed for recovery scripts.

## See also

- [01_installation.md](01_installation.md)
- [02_quick-start.md](02_quick-start.md)
