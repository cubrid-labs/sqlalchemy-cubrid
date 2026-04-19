# test/test_alembic.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Tests for Alembic migration support (sqlalchemy_cubrid.alembic_impl).

These tests verify that the CubridImpl class is correctly configured and
can be discovered by Alembic via the entry-point mechanism.
"""

from __future__ import annotations

import importlib
import sys
from unittest import mock

import pytest
import sqlalchemy as sa

from sqlalchemy_cubrid import types as cubrid_types

if sys.version_info >= (3, 11):
    import tomllib as toml_mod
else:
    import tomli as toml_mod


def _load_pyproject():
    """Load pyproject.toml."""
    import pathlib

    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        return toml_mod.load(f)


class _AutogenContext:
    def __init__(self):
        self.imports: set[str] = set()


class TestCubridImpl:
    """Tests for the CubridImpl Alembic implementation class."""

    def test_import(self):
        """CubridImpl can be imported from the alembic_impl module."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl is not None

    def test_dialect_name(self):
        """CubridImpl.__dialect__ is set to 'cubrid'."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl.__dialect__ == "cubrid"

    def test_transactional_ddl_false(self):
        """CUBRID auto-commits DDL, so transactional_ddl must be False."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert CubridImpl.transactional_ddl is False

    def test_subclass_of_default_impl(self):
        """CubridImpl inherits from alembic.ddl.impl.DefaultImpl."""
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        assert issubclass(CubridImpl, DefaultImpl)

    def test_class_registered_in_impl_registry(self):
        """Alembic's DefaultImpl registry should know about 'cubrid'."""
        from alembic.ddl.impl import _impls

        # Import triggers class registration via metaclass
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        # _impls is the internal registry keyed by dialect name
        assert "cubrid" in _impls
        assert _impls["cubrid"] is CubridImpl

    def test_entry_point_registered(self):
        """Verify the entry point is declared in pyproject.toml."""
        config = _load_pyproject()

        entry_points = config["project"]["entry-points"]
        assert "alembic.ddl" in entry_points
        assert entry_points["alembic.ddl"]["cubrid"] == (
            "sqlalchemy_cubrid.alembic_impl:CubridImpl"
        )

    def test_optional_dependency_declared(self):
        """Verify the [alembic] optional dependency is declared in pyproject.toml."""
        config = _load_pyproject()

        optional_deps = config["project"]["optional-dependencies"]
        assert "alembic" in optional_deps
        assert any("alembic" in dep for dep in optional_deps["alembic"])


class TestAlembicImportError:
    """Test that a clear error is raised when alembic is not installed."""

    def test_import_error_without_alembic(self):
        """If alembic is not installed, importing alembic_impl raises ImportError."""
        # Remove alembic_impl from cache so we can re-import it
        module_key = "sqlalchemy_cubrid.alembic_impl"
        saved = sys.modules.pop(module_key, None)

        try:
            with mock.patch.dict(
                sys.modules,
                {"alembic": None, "alembic.ddl": None, "alembic.ddl.impl": None},
            ):
                # Force re-import
                if module_key in sys.modules:
                    del sys.modules[module_key]
                with pytest.raises(ImportError, match="Alembic is required"):
                    importlib.import_module(module_key)
        finally:
            # Restore
            if saved is not None:
                sys.modules[module_key] = saved
            elif module_key in sys.modules:
                del sys.modules[module_key]


class TestCubridImplAutogenerate:
    def test_render_type_set_multiset_sequence_with_strings(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        set_render = impl.render_type(cubrid_types.SET("A", "b"), autogen_context)
        multiset_render = impl.render_type(cubrid_types.MULTISET("x", "y"), autogen_context)
        sequence_render = impl.render_type(cubrid_types.SEQUENCE("f", "s"), autogen_context)

        assert set_render == "cubrid_types.SET('A', 'b')"
        assert multiset_render == "cubrid_types.MULTISET('x', 'y')"
        assert sequence_render == "cubrid_types.SEQUENCE('f', 's')"
        assert autogen_context.imports == {
            "from sqlalchemy_cubrid import types as cubrid_types",
        }

    def test_render_type_collection_with_typeengine_values(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        rendered = impl.render_type(cubrid_types.SET(sa.String(), sa.Integer()), autogen_context)

        assert rendered == "cubrid_types.SET(String, Integer)"
        assert "from sqlalchemy_cubrid import types as cubrid_types" in autogen_context.imports

    def test_render_type_non_cubrid_type_returns_false(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        assert impl.render_type(sa.String(), autogen_context) is False
        assert autogen_context.imports == set()

    def test_compare_type_set_same_values_different_order(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET(" A ", "B"))
        metadata_column = sa.Column("v", cubrid_types.SET("b", "a"))

        assert impl.compare_type(inspector_column, metadata_column) is False

    def test_compare_type_set_different_values(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.SET("a", "c"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_sequence_order_matters(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SEQUENCE("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.SEQUENCE("b", "a"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_delegates_to_super_for_non_collection(self):
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", sa.String())
        metadata_column = sa.Column("v", sa.String())

        with mock.patch.object(DefaultImpl, "compare_type", return_value=True) as mock_super:
            result = impl.compare_type(inspector_column, metadata_column)

        assert result is True
        mock_super.assert_called_once_with(inspector_column, metadata_column)

    def test_normalize_collection_value_typeengine(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        result = CubridImpl._normalize_collection_value(sa.String())
        assert result == "string"

    def test_normalize_collection_value_non_string_non_type(self):
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        result = CubridImpl._normalize_collection_value(42)
        assert result == "42"

    def test_render_type_cubrid_non_collection_returns_false(self):
        """CUBRID types that are NOT collections (e.g., MONETARY) return False."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        assert impl.render_type(cubrid_types.MONETARY(), autogen_context) is False
        assert autogen_context.imports == set()

    def test_render_type_collection_with_non_string_non_type_values(self):
        """Values that are neither str nor TypeEngine use repr()."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        autogen_context = _AutogenContext()

        rendered = impl.render_type(cubrid_types.SET(42, 3.14), autogen_context)
        assert rendered == "cubrid_types.SET(42, 3.14)"

    def test_compare_type_collection_vs_non_collection(self):
        """When one type is collection and the other is not, they differ."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a"))
        metadata_column = sa.Column("v", sa.String())

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_different_collection_names(self):
        """SET vs MULTISET with same values should still differ."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.SET("a", "b"))
        metadata_column = sa.Column("v", cubrid_types.MULTISET("a", "b"))

        assert impl.compare_type(inspector_column, metadata_column) is True

    def test_compare_type_text_vs_varchar_max_no_diff(self):
        """Text() vs VARCHAR(1073741823) must NOT be reported as a type change.

        See cubrid-labs/sqlalchemy-cubrid#120 — CUBRID stores Text/CLOB/STRING
        as VARCHAR(1073741823) so reflection round-trips trip Alembic's
        default compare_type.
        """
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(1073741823))
        for metadata_type in (sa.Text(), cubrid_types.CLOB(), cubrid_types.STRING()):
            metadata_column = sa.Column("v", metadata_type)
            assert impl.compare_type(inspector_column, metadata_column) is False
            # Reverse direction must also hold.
            assert impl.compare_type(metadata_column, inspector_column) is False

    def test_compare_type_varchar_max_vs_string_no_length_no_diff(self):
        """Plain String() (no length) maps to VARCHAR(max) on CUBRID."""
        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(1073741823))
        metadata_column = sa.Column("v", sa.String())
        assert impl.compare_type(inspector_column, metadata_column) is False

    def test_compare_type_varchar_bounded_still_compared(self):
        """VARCHAR(100) vs Text() must still be detected as a real diff."""
        from alembic.ddl.impl import DefaultImpl

        from sqlalchemy_cubrid.alembic_impl import CubridImpl

        impl = object.__new__(CubridImpl)
        inspector_column = sa.Column("v", cubrid_types.VARCHAR(100))
        metadata_column = sa.Column("v", sa.Text())
        with mock.patch.object(DefaultImpl, "compare_type", return_value=True) as m:
            result = impl.compare_type(inspector_column, metadata_column)
        assert result is True
        m.assert_called_once()
