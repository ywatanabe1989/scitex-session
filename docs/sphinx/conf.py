"""Sphinx configuration for scitex-session."""

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "scitex-session"
copyright = "2026, Yusuke Watanabe"
author = "Yusuke Watanabe"

try:
    from scitex_session import __version__ as release
except ImportError:
    release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_theme",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
]

autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": False,
    "private-members": False,
    "exclude-members": "__weakref__,__init__,__dict__,__module__",
}

# Quiet "duplicate object description" warnings from the package's
# top-level re-exports (start/close/session/run/running2finished + the
# four archive helpers) which appear both in `scitex_session` and in
# their submodules. autodoc resolves both descriptions and -W treats
# this as an error in PR builds.
suppress_warnings = [
    "autodoc.duplicate_object_description",
    "ref.duplicate",
]

# Heavy/optional deps mocked so RTD can build without installing them.
autodoc_mock_imports = [""]

# `autosummary_generate = True` plus `automodule :members:` produced
# duplicate object descriptions for every top-level re-export (start,
# close, session, archive_* etc.) — both autodoc and autosummary
# generated entries for the same object. Disable autosummary; autodoc
# is enough for the small public API surface here.
autosummary_generate = False

napoleon_google_docstring = True
napoleon_numpy_docstring = True
# Render "Example:" sections as RST admonitions instead of inline
# paragraph + code blocks. This sidesteps the "Unexpected indentation"
# errors that arise when Google-style ``Example:`` is followed directly
# by indented code (as in `scitex_session._decorator.session`).
napoleon_use_admonition_for_examples = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "torch": ("https://pytorch.org/docs/stable/", None),
}
