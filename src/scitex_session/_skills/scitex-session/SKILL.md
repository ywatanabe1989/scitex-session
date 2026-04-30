---
name: scitex-session
description: `@session` decorator for reproducible experiment lifecycle. Wrap `def main(...)`; the decorator parses CLI args, loads `config/*.yaml`, configures matplotlib + logging, runs the function, and writes outputs to `script_out/<status>/<session_id>/`. The full SciTeX workflow contract in one decorator. Drop-in replacement for hand-rolled argparse + yaml.safe_load + logging.basicConfig + os.makedirs preambles.
primary_interface: python
interfaces:
  python: 3
  cli: 1
  mcp: 0
  skills: 2
  hook: 0
  http: 0
canonical-location: scitex-session/src/scitex_session/_skills/scitex-session/SKILL.md
tags: [scitex-session, scitex-package]
---

> **Interfaces:** Python ⭐⭐⭐ · CLI ⭐ · MCP — · Skills ⭐⭐ · Hook — · HTTP —

# scitex-session

`@session` decorator for reproducible experiment lifecycle. Wrap `def main(...)`; the decorator parses CLI args, loads `config/*.yaml`, configures matplotlib + logging, runs the function, and writes outputs to `script_out/<status>/<session_id>/`. The full SciTeX workflow contract in one decorator. Drop-in replacement for hand-rolled argparse + yaml.safe_load + logging.basicConfig + os.makedirs preambles.

See README.md and the package's public `__init__.py` for the full
function list. This skill leaf exists so agents discover the package
exists and roughly what shape it has — refer to the source for
signatures.
