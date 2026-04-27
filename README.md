# scitex-session

<!-- scitex-badges:start -->
[![PyPI](https://img.shields.io/pypi/v/scitex-session.svg)](https://pypi.org/project/scitex-session/)
[![Python](https://img.shields.io/pypi/pyversions/scitex-session.svg)](https://pypi.org/project/scitex-session/)
[![Tests](https://github.com/ywatanabe1989/scitex-session/actions/workflows/test.yml/badge.svg)](https://github.com/ywatanabe1989/scitex-session/actions/workflows/test.yml)
[![Install Test](https://github.com/ywatanabe1989/scitex-session/actions/workflows/install-test.yml/badge.svg)](https://github.com/ywatanabe1989/scitex-session/actions/workflows/install-test.yml)
[![Coverage](https://codecov.io/gh/ywatanabe1989/scitex-session/graph/badge.svg)](https://codecov.io/gh/ywatanabe1989/scitex-session)
[![Docs](https://readthedocs.org/projects/scitex-session/badge/?version=latest)](https://scitex-session.readthedocs.io/en/latest/)
[![License: AGPL v3](https://img.shields.io/badge/license-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
<!-- scitex-badges:end -->


`@session` decorator and lifecycle management (auto-CLI, output dir tree, randomstate, configs) extracted from the [SciTeX](https://github.com/ywatanabe1989/scitex-python) ecosystem as a standalone package.

## Install

```bash
pip install scitex-session
```

## API

```python
import scitex_session as sess

@sess.session
def main(
    param1="default",
    CONFIG=sess.INJECTED,
    plt=sess.INJECTED,
    logger=sess.INJECTED,
    rng=sess.INJECTED,
):
    """Docstring becomes --help."""
    logger.info("hi")
    return 0

# Manual lifecycle
sess.start(...) ; sess.close(...)
sess.SessionManager()
```

## Status

Standalone fork of `scitex.session`. Deps: matplotlib + scitex-dict / -logging
/ -repro / -str (already-standalone peer packages).

Decoupling notes:
- `scitex.dict.DotDict` → `scitex_dict.DotDict`
- `scitex.repro.RandomStateManager / gen_ID` → `scitex_repro.*`
- `scitex.str.clean_path / printc` → `scitex_str.*`
- `scitex.logging.getLogger` → stdlib `logging.getLogger`
- `scitex.plt.utils._configure_mpl` → optional via `try/except` with no-op
  fallback (matplotlib uses defaults if scitex umbrella isn't installed).
- `scitex.utils._notify` → optional via `try/except` (silent no-op fallback).

The umbrella package's `scitex.session` import path is preserved via a
`sys.modules`-alias bridge. 44/89 tests pass — same family as upstream
(48 fail there too, mostly jax/tf import issues unrelated to session).

## License

AGPL-3.0-only (see [LICENSE](./LICENSE)).
