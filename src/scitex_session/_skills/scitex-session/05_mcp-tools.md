---
description: |
  [TOPIC] MCP tools exposed by scitex-session
  [DETAILS] Six FastMCP tools — four archive helpers (archive_existing, restore_existing, archive_session_dir, restore_session_archive) plus the §5 skills envelope (skills_list, skills_get). Mounted under the `session_` namespace in the scitex umbrella.
tags: [scitex-session-mcp-tools]
---

# MCP Tools

`scitex-session` ships a single `FastMCP` instance at
`scitex_session._mcp_server.mcp` with six tools — four archive helpers
plus the `§5` skills-discovery envelope. The scitex umbrella mounts the
server under the `session_` namespace via `safe_mount`, so umbrella
clients see the tools as `session_archive_existing` etc.

## Server entry

```bash
# Stdio MCP server (default transport)
scitex-session-mcp
```

`scitex-session-mcp` is registered as a `[project.scripts]` entry in
`pyproject.toml`. The same module is importable for embedding:

```python
from scitex_session._mcp_server import mcp  # FastMCP instance
```

Install the optional dependency to enable the server:

```bash
pip install 'scitex-session[mcp]'
```

## Archive tools (mirror the Python API)

Each tool wraps the same-named function in
`scitex_session._lifecycle._archive` and returns a JSON-encoded string
matching the Python return value.

### `archive_existing`

Compress every session-shaped dir under `root` into a single archive
each. Dry-run by default.

```jsonc
// arguments
{
  "root": "script_out/FINISHED_SUCCESS",
  "older_than_days": 30,
  "format": "tar.gz",
  "dry_run": false
}
// returns (JSON string)
"{\"scanned\": 42, \"candidates\": 12, \"archived\": 12, \"skipped\": 0, \"failed\": 0, \"bytes_in\": 4194304, \"bytes_out\": 812345}"
```

### `restore_existing`

Inverse of `archive_existing`. Extracts every matching archive under
`root` back into a directory.

```jsonc
{
  "root": "script_out/FINISHED_SUCCESS",
  "pattern": "*.tar.gz",
  "remove_archive": false,
  "dry_run": false
}
```

Returns `{"scanned": N, "candidates": N, "restored": N, "skipped": N, "failed": N}`.

### `archive_session_dir`

Single-directory variant. Compresses `src_dir` into one archive file.

```jsonc
{
  "src_dir": "script_out/FINISHED_SUCCESS/2026-05-24-abc123",
  "format": "tar.gz",
  "remove_src": true
}
```

Returns `{"archive_path": "/.../2026-05-24-abc123.tar.gz"}`.

### `restore_session_archive`

Inverse of `archive_session_dir`. Extracts a single archive file back
into a directory.

```jsonc
{
  "archive_path": "/.../2026-05-24-abc123.tar.gz",
  "dest_dir": null,
  "remove_archive": false
}
```

Returns `{"dest_dir": "/.../2026-05-24-abc123"}`.

## Skills envelope (§5 mandate)

Every SciTeX MCP server exposes these two tools so agents can discover
the package's skill pages without filesystem walks.

### `skills_list`

Lists the available skill pages.

```jsonc
// arguments: none
// returns
"{\"skills\": [{\"name\": \"SKILL\", \"description\": \"…\"}, {\"name\": \"01_installation\", \"description\": \"…\"}, …]}"
```

### `skills_get`

Fetches the content of a skill page. `name=None` returns `SKILL.md`.

```jsonc
{
  "name": "04_cli-reference"
}
// returns
"{\"name\": \"04_cli-reference\", \"content\": \"---\\ndescription: …\"}"
```

## Umbrella naming (Convention A)

The standalone source uses **bare names** (`archive_existing`, not
`session_archive_existing`). The scitex umbrella bridge in
`scitex/_mcp_tools/session.py` calls
`safe_mount(mcp, sub_mcp, namespace="session")`, which prefixes every
tool name with `session_` at mount time. Final umbrella-visible names:

| Standalone (this package) | Umbrella                        |
|---------------------------|---------------------------------|
| `archive_existing`        | `session_archive_existing`      |
| `restore_existing`        | `session_restore_existing`      |
| `archive_session_dir`     | `session_archive_session_dir`   |
| `restore_session_archive` | `session_restore_session_archive` |
| `skills_list`             | `session_skills_list`           |
| `skills_get`              | `session_skills_get`            |

## See also

- [03_python-api.md](03_python-api.md) — the Python functions these
  tools wrap.
- [04_cli-reference.md](04_cli-reference.md) — the equivalent CLI.
