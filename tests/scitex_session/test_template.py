#!/usr/bin/env python3
# Time-stamp: "2026-05-18"
# File: ./tests/scitex_session/test_template.py

"""Tests for session template module.

`template.py` is an example script demonstrating @stx.session decorator
usage. These tests verify basic importability and structure.
"""

import pytest

# Required for scitex_session module
pytest.importorskip("natsort")
pytest.importorskip("h5py")
pytest.importorskip("zarr")


class TestTemplateModule:
    """Tests for session template module."""

    def test_template_module_imports_to_non_none_object(self):
        # Arrange
        # Act
        from scitex_session import template
        # Assert
        assert template is not None

    def test_template_module_exposes_main_attribute(self):
        # Arrange
        from scitex_session import template
        # Act
        has_main = hasattr(template, "main")
        # Assert
        assert has_main is True

    def test_template_main_attribute_is_callable(self):
        # Arrange
        from scitex_session import template
        # Act
        is_callable = callable(template.main)
        # Assert
        assert is_callable is True

    def test_template_main_exposes_session_wrapped_attr(self):
        # Arrange
        from scitex_session import template
        # Act
        has_attr = hasattr(template.main, "_is_session_wrapped")
        # Assert
        assert has_attr is True

    def test_template_main_session_wrapped_attr_is_true(self):
        # Arrange
        from scitex_session import template
        # Act
        flag = template.main._is_session_wrapped
        # Assert
        assert flag is True

    def test_template_main_exposes_original_function_attr(self):
        # Arrange
        from scitex_session import template
        # Act
        has_func_ref = hasattr(template.main, "_func")
        # Assert
        assert has_func_ref is True

    def test_template_main_original_function_is_callable(self):
        # Arrange
        from scitex_session import template
        # Act
        is_callable = callable(template.main._func)
        # Assert
        assert is_callable is True


class TestTemplateExecution:
    """Tests for template execution behavior."""

    def test_template_main_direct_call_returns_none(self):
        # Arrange
        from scitex_session import template
        # Act
        result = template.main(arg1="test", arg2="value")
        # Assert
        assert result is None


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# EOF
