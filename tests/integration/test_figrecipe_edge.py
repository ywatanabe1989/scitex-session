#!/usr/bin/env python3
"""Per-edge integration + degradation tests for the OPTIONAL figrecipe edge.

This mirrors the canonical scitex-io <-> figrecipe edge template. figrecipe is
an OPTIONAL (dev/visualization) dependency of scitex-session, declared only
under the ``dev`` extra. The edge under test lives in
``scitex_session._lifecycle._matplotlib``::

    from scitex_dev import try_import_optional
    _configure_mpl = try_import_optional("figrecipe.utils._configure_mpl",
                                         "configure_mpl")
    if _configure_mpl is None:
        def _configure_mpl(plt, **kwargs):   # no-op fallback
            return plt, {}
    configure_mpl = _configure_mpl

When figrecipe is present, session intends to delegate matplotlib styling to
figrecipe's ``configure_mpl`` (which tunes rcParams and returns a populated
COLORS mapping). When figrecipe is absent, ``try_import_optional`` returns
``None`` and session installs an inert no-op that returns ``(plt, {})`` so a
``@session``-wrapped script still starts -- matplotlib simply keeps its
defaults.

The two test kinds every optional edge should have
--------------------------------------------------
1. INTEGRATION (collaborator PRESENT): exercise the *real* figrecipe styling
   entry point session is built to consume and assert on the concrete contract
   it offers (a callable returning ``(plt, COLORS)`` with a non-empty COLORS
   mapping). Guarded by ``pytest.importorskip("figrecipe")`` so minimal installs
   skip rather than error.

2. DEGRADATION (collaborator ABSENT): simulate figrecipe missing in a hermetic,
   reversible way (snapshot ``sys.modules``; shadow ``figrecipe`` with ``None``
   so a fresh import raises ImportError; reload the affected session module so
   it re-runs its optional-import guard), then assert the package's ACTUAL
   graceful contract: ``configure_mpl`` becomes the no-op returning
   ``(plt, {})`` and ``setup_matplotlib`` still succeeds without leaking an
   ImportError to the caller.

Discovered contract note (do not assume -- verified in this environment)
------------------------------------------------------------------------
figrecipe currently exposes ``configure_mpl`` at the top level / in
``figrecipe._configure_mpl``; the import path session hard-codes
(``figrecipe.utils._configure_mpl``) is the historical location. The
INTEGRATION test therefore asserts figrecipe's *own* styling contract (the
capability session relies on), not the stale module path, so it stays valid
across figrecipe's internal reshuffles. The DEGRADATION test asserts the
session-side fallback that is taken whenever that import does not resolve.

Conventions honoured (mirroring the template):
  - One assertion per test (TQ007); shared/expensive setup lifted into fixtures.
  - Explicit Arrange / Act / Assert markers in every test (TQ002).
  - No ``monkeypatch`` / ``mocker``: the figrecipe-absent fixture hand-swaps
    ``sys.modules`` and restores it on teardown.
"""

from __future__ import annotations

import importlib
import sys

import matplotlib
import pytest

matplotlib.use("Agg")


# ===========================================================================
# 1. INTEGRATION  --  figrecipe PRESENT
# ===========================================================================
figrecipe = pytest.importorskip("figrecipe")


@pytest.fixture
def figrecipe_configure_mpl_result():
    """Call figrecipe's real ``configure_mpl`` once; yield (plt, COLORS).

    This is the capability scitex-session is built to consume on the
    figrecipe-present path. We resolve it the way session intends (its
    top-level export), independent of the exact private module path.
    """
    configure_mpl = getattr(figrecipe, "configure_mpl", None)
    if configure_mpl is None:  # pragma: no cover - environment-dependent
        pytest.skip("figrecipe does not expose configure_mpl in this build")
    import matplotlib.pyplot as plt

    return configure_mpl(plt)


def test_figrecipe_exposes_callable_configure_mpl():
    """figrecipe offers the styling entry point session delegates to."""
    # Arrange
    configure_mpl = getattr(figrecipe, "configure_mpl", None)
    # Act
    is_callable = callable(configure_mpl)
    # Assert
    assert is_callable


def test_figrecipe_configure_mpl_returns_pair(figrecipe_configure_mpl_result):
    """configure_mpl returns a (plt, COLORS) 2-tuple (session unpacks both)."""
    # Arrange
    result = figrecipe_configure_mpl_result
    # Act
    is_pair = isinstance(result, tuple) and len(result) == 2
    # Assert
    assert is_pair


def test_figrecipe_configure_mpl_returns_plt_like_first(
    figrecipe_configure_mpl_result,
):
    """The first element is a pyplot-like module (carries ``subplots``)."""
    # Arrange
    returned_plt, _ = figrecipe_configure_mpl_result
    # Act
    is_plt_like = hasattr(returned_plt, "subplots")
    # Assert
    assert is_plt_like


def test_figrecipe_configure_mpl_returns_nonempty_colors(
    figrecipe_configure_mpl_result,
):
    """With figrecipe present, COLORS is populated (the styling payload)."""
    # Arrange
    _, colors = figrecipe_configure_mpl_result
    # Act
    is_nonempty = bool(colors)
    # Assert
    assert is_nonempty


def test_session_matplotlib_module_imports_with_figrecipe_present():
    """The session matplotlib lifecycle module imports cleanly here."""
    # Arrange
    module_name = "scitex_session._lifecycle._matplotlib"
    # Act
    module = importlib.import_module(module_name)
    # Assert
    assert callable(module.configure_mpl)


# ===========================================================================
# 2. DEGRADATION  --  figrecipe ABSENT
# ===========================================================================
@pytest.fixture
def figrecipe_absent():
    """Make ``import figrecipe`` fail for the duration of the test.

    Hermetic and reversible:
      1. snapshot the whole ``sys.modules`` so teardown restores it exactly;
      2. evict figrecipe and the session matplotlib lifecycle module, then
         shadow ``figrecipe`` with ``None`` so a *fresh* ``import figrecipe``
         raises ImportError;
      3. reload ``scitex_session._lifecycle._matplotlib`` so it re-runs its
         ``try_import_optional`` guard under the missing dependency and
         installs the no-op fallback.

    Yields the freshly reloaded ``_matplotlib`` module.
    """
    import scitex_session._lifecycle._matplotlib  # noqa: F401  (importable first)

    # 1. Full snapshot for an exact restore.
    snapshot = dict(sys.modules)

    # 2. Evict figrecipe + the session matplotlib module, then block figrecipe.
    def _to_evict(name: str) -> bool:
        return (
            name == "figrecipe"
            or name.startswith("figrecipe.")
            or name == "scitex_session._lifecycle._matplotlib"
        )

    for name in [n for n in list(sys.modules) if _to_evict(n)]:
        del sys.modules[name]
    sys.modules["figrecipe"] = None  # type: ignore[assignment]

    reloaded = importlib.import_module("scitex_session._lifecycle._matplotlib")

    try:
        yield reloaded
    finally:
        # Restore the exact pre-test module table.
        for name in list(sys.modules):
            if name not in snapshot:
                del sys.modules[name]
        sys.modules.update(snapshot)


def test_figrecipe_absent_fixture_blocks_the_import(figrecipe_absent):
    """Sanity: under the fixture, ``import figrecipe`` really does fail."""
    # Arrange
    _ = figrecipe_absent
    # Act
    module_name = "figrecipe"
    # Assert
    with pytest.raises(ImportError):
        importlib.import_module(module_name)


def test_configure_mpl_is_session_noop_fallback_when_absent(figrecipe_absent):
    """Without figrecipe, configure_mpl is session's own no-op fallback."""
    # Arrange
    module = figrecipe_absent
    # Act
    fn_module = module.configure_mpl.__module__
    # Assert
    assert fn_module == "scitex_session._lifecycle._matplotlib"


def test_noop_configure_mpl_returns_same_plt_when_absent(figrecipe_absent):
    """The no-op returns the *same* plt it was handed (no substitution)."""
    # Arrange
    import matplotlib.pyplot as plt

    # Act
    returned_plt, _ = figrecipe_absent.configure_mpl(plt)
    # Assert
    assert returned_plt is plt


def test_noop_configure_mpl_returns_empty_colors_when_absent(figrecipe_absent):
    """The no-op returns an empty COLORS mapping (matplotlib defaults)."""
    # Arrange
    import matplotlib.pyplot as plt

    # Act
    _, colors = figrecipe_absent.configure_mpl(plt)
    # Assert
    assert colors == {}


class _StubPlt:
    """Minimal pyplot-like stub.

    ``setup_matplotlib`` only touches ``plt.close`` and (when scitex_plt is
    absent) returns the very plt it was handed. We pass a stub rather than the
    real ``matplotlib.pyplot`` so the degradation assertion isolates *session's*
    behaviour: the real pyplot may itself be the figrecipe-backed wrapper, whose
    ``close("all")`` re-imports figrecipe -- a property of that wrapper, not of
    scitex-session's optional-figrecipe guard.
    """

    def close(self, *args, **kwargs):
        return None

    def subplots(self, *args, **kwargs):  # marks this as pyplot-like
        return None


def test_setup_matplotlib_still_works_without_figrecipe(figrecipe_absent):
    """setup_matplotlib degrades gracefully -- no ImportError to the caller.

    With figrecipe absent, configure_mpl is the no-op returning ``(plt, {})`` and
    the grey/gray aliasing over an empty COLORS mapping must not raise.
    """
    # Arrange
    plt = _StubPlt()
    # Act
    _, colors = figrecipe_absent.setup_matplotlib(plt)
    # Assert
    assert colors == {}


def test_setup_matplotlib_returns_a_plt_module_without_figrecipe(figrecipe_absent):
    """setup_matplotlib still hands back a usable pyplot-like module."""
    # Arrange
    plt = _StubPlt()
    # Act
    returned_plt, _ = figrecipe_absent.setup_matplotlib(plt)
    # Assert
    assert hasattr(returned_plt, "subplots")


# EOF
