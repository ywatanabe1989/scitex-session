"""scitex-session quickstart: a minimal @session-decorated entry point.

The @session decorator wraps a function so that:
  - Function arguments are exposed as CLI flags
  - A reproducible run directory is created (under ./script_out/...)
  - CONFIG / plt / logger are auto-injected
  - Output is organized on success vs failure

This script invokes the wrapped function directly (with arguments) so it
runs synchronously, with no CLI parsing — perfect for a smoke test.
"""

from scitex_session import INJECTED, session


@session(verbose=False)
def run(
    n: int = 3,
    label: str = "demo",
    CONFIG=INJECTED,
    logger=INJECTED,
):
    """Squeeze out a few squared values, demonstrating injected globals."""
    # When called WITHOUT positional args from __main__, the decorator parses
    # CLI flags and injects CONFIG/logger. When called WITH explicit args,
    # the decorator passes them through; INJECTED placeholders may remain
    # as the sentinel — that's fine for this demo.
    squares = [i * i for i in range(n)]
    print(f"label={label!r}  squares(0..{n - 1})={squares}")
    return 0


def main():
    # Direct call form — bypasses CLI / session-dir creation.
    rc = run(n=5, label="quickstart")
    print("return code:", rc)
    assert rc == 0


if __name__ == "__main__":
    main()
