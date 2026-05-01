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

<p align="center">
  <a href="https://scitex.ai">
    <img src="docs/scitex-logo-blue-cropped.png" alt="SciTeX" width="400">
  </a>
</p>

<p align="center"><b>`@session` decorator + lifecycle (auto-CLI, output dir tree, randomstate, configs).</b></p>

<p align="center">
  <a href="https://scitex-session.readthedocs.io/">Full Documentation</a> · <code>pip install scitex-session</code>
</p>

---

## Installation

```bash
pip install scitex-session
```

## Quick Start

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
```

## 1 Interfaces

<details>
<summary><strong>Python API</strong></summary>

<br>

```python
import scitex_session as sess

# Decorator — wraps main() with auto-CLI, output dir, configs, RNG.
@sess.session
def main(CONFIG=sess.INJECTED, logger=sess.INJECTED, rng=sess.INJECTED):
    ...

# Manual lifecycle
sess.start(...)
sess.close(...)

# Class-style manager
mgr = sess.SessionManager()
```

</details>

## Status

Standalone fork of `scitex.session`. Deps: matplotlib + scitex-dict /
-logging / -repro / -str (already-standalone peer packages).

Decoupling notes:
- `scitex.dict.DotDict` → `scitex_dict.DotDict`
- `scitex.repro.RandomStateManager / gen_ID` → `scitex_repro.*`
- `scitex.str.clean_path / printc` → `scitex_str.*`
- `scitex.logging.getLogger` → stdlib `logging.getLogger`
- `scitex.plt.utils._configure_mpl` → optional via `try/except` with no-op
  fallback (matplotlib uses defaults if scitex umbrella isn't installed).
- `scitex.utils._notify` → optional via `try/except` (silent no-op fallback).

The umbrella package's `scitex.session` import path is preserved via a
`sys.modules`-alias bridge.

## Part of SciTeX

`scitex-session` is part of [**SciTeX**](https://scitex.ai).

>Four Freedoms for Research
>
>0. The freedom to **run** your research anywhere — your machine, your terms.
>1. The freedom to **study** how every step works — from raw data to final manuscript.
>2. The freedom to **redistribute** your workflows, not just your papers.
>3. The freedom to **modify** any module and share improvements with the community.
>
>AGPL-3.0 — because we believe research infrastructure deserves the same freedoms as the software it runs on.

## License

AGPL-3.0-only (see [LICENSE](./LICENSE)).

---

<p align="center">
  <a href="https://scitex.ai" target="_blank"><img src="docs/scitex-icon-navy-inverted.png" alt="SciTeX" width="40"/></a>
</p>
