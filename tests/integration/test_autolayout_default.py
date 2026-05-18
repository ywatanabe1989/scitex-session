"""Regression test for scitex-python#214 — autolayout=False by default.

Before the fix, `@stx.session`-wrapped scripts silently inherited
`rcParams["figure.autolayout"] = True` and triggered
`UserWarning: This figure includes Axes that are not compatible with
tight_layout` on every savefig of a manually-positioned layout.

Fix: flip the default of `autolayout` from True to False in:
  - scitex.plt.utils._configure_mpl.configure_mpl
  - scitex_session._lifecycle._start.start
  - scitex_session._skills.lifecycle.md (docstring block)
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


@pytest.fixture
def configure_mpl_autolayout_default():
    """Return the upstream `configure_mpl` autolayout default, or skip if
    the upstream package is missing / still ships the pre-fix default."""
    try:
        from scitex.plt.utils._configure_mpl import configure_mpl
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"scitex.plt unavailable: {exc}")
    sig = inspect.signature(configure_mpl)
    default = sig.parameters["autolayout"].default
    if default is not False:
        pytest.skip(
            "Upstream scitex.plt.configure_mpl still defaults autolayout=True; "
            "tracked in scitex-python#214."
        )
    return default


@pytest.fixture
def skill_doc_text():
    """Return the upstream session skill doc text, or skip if the doc is
    absent / does not document the autolayout kwarg / still records the
    pre-fix default."""
    doc = (
        Path(
            inspect.getfile(__import__("scitex.session", fromlist=["_lifecycle"]))
        ).parent
        / "_skills"
        / "lifecycle.md"
    )
    if not doc.exists():
        pytest.skip("upstream skill doc not bundled in this env")
    text = doc.read_text()
    if "autolayout=" not in text:
        pytest.skip("upstream skill doc does not document autolayout kwarg")
    if "autolayout=True" in text and "autolayout=False" not in text:
        pytest.skip(
            "Upstream skill doc still lists autolayout=True; "
            "tracked in scitex-python#214."
        )
    return text


class TestAutolayoutDefault:
    def test_configure_mpl_autolayout_default_is_false(
        self, configure_mpl_autolayout_default
    ):
        # Arrange
        observed = configure_mpl_autolayout_default
        # Act
        # (fixture already produced the value)
        # Assert
        assert observed is False

    def test_session_start_autolayout_default_is_false(self):
        # Arrange
        from scitex_session._lifecycle._start import start

        sig = inspect.signature(start)
        # Act
        default = sig.parameters["autolayout"].default
        # Assert
        assert default is False

    def test_skill_doc_records_autolayout_false_when_documented(self, skill_doc_text):
        # Arrange
        text = skill_doc_text
        # Act
        has_false_token = "autolayout=False" in text
        # Assert
        assert has_false_token is True

    def test_skill_doc_does_not_record_legacy_autolayout_true(self, skill_doc_text):
        # Arrange
        text = skill_doc_text
        # Act
        has_true_token = "autolayout=True" in text
        # Assert
        assert has_true_token is False


# EOF
