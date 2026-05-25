---
name: scitex-session
description: `@session` decorator for reproducible experiment lifecycle. Wrap `def main(...)`; the decorator parses CLI args, loads `config/*.yaml`, configures matplotlib + logging, runs the function, and writes outputs to `script_out/<status>/<session_id>/`. The full SciTeX workflow contract in one decorator. Drop-in replacement for hand-rolled argparse + yaml.safe_load + logging.basicConfig + os.makedirs preambles.
primary_interface: python
interfaces:
  python: 3
  cli: 2
  mcp: 2
  skills: 2
  hook: 0
  http: 0
canonical-location: scitex-session/src/scitex_session/_skills/scitex-session/SKILL.md
tags: [scitex-session, scitex-package]
---

> **Interfaces:** Python ⭐⭐⭐ · CLI ⭐⭐ · MCP ⭐⭐ · Skills ⭐⭐ · Hook — · HTTP —

# scitex-session

`@session` decorator for reproducible experiment lifecycle. Wrap `def main(...)`; the decorator parses CLI args, loads `config/*.yaml`, configures matplotlib + logging, runs the function, and writes outputs to `script_out/<status>/<session_id>/`. The full SciTeX workflow contract in one decorator. Drop-in replacement for hand-rolled argparse + yaml.safe_load + logging.basicConfig + os.makedirs preambles.

## Index

- [01_installation.md](01_installation.md) — pip install, standalone vs umbrella, verify
- [02_quick-start.md](02_quick-start.md) — first `@session` in 30 seconds
- [03_python-api.md](03_python-api.md) — decorator, `start`/`close`, `SessionManager`, `INJECTED`
- [04_cli-reference.md](04_cli-reference.md) — `scitex-session-archive {compress,extract}`
- [05_mcp-tools.md](05_mcp-tools.md) — six FastMCP tools (4 archive helpers + skills envelope)
