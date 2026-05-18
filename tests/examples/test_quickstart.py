#!/usr/bin/env python3
"""Compile-only smoke test for examples/quickstart.py."""

import py_compile
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "quickstart.py"


def test_quickstart_example_file_exists_on_disk():
    # Arrange
    # Act
    is_file = EXAMPLE.is_file()
    # Assert
    assert is_file, f"missing example: {EXAMPLE}"


def test_quickstart_example_compiles_without_error():
    # Arrange
    # Act
    py_compile.compile(str(EXAMPLE), doraise=True)
    # Assert
    assert True  # no PyCompileError raised


# EOF
