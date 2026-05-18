"""Smoke test: every example script under examples/ runs to completion."""

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = list(Path(__file__).parent.parent.joinpath("examples").glob("*.py"))


def test_examples_directory_contains_at_least_one_script():
    # Arrange
    # Act
    count = len(EXAMPLES)
    # Assert
    assert count > 0, "No example scripts found under examples/"


@pytest.mark.parametrize(
    "example",
    EXAMPLES,
    ids=[e.name for e in EXAMPLES] if EXAMPLES else ["<none>"],
)
def test_example_script_exits_zero_when_run(example, tmp_path):
    # Arrange
    # Act
    r = subprocess.run(
        [sys.executable, str(example)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Assert
    assert r.returncode == 0, (
        f"{example.name} failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )
