from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import types as sqltypes
from sqlalchemy.engine import url

from sqlalchemy_cubrid.dialect import CubridDialect


def _invoke_reflection(dialect, method_name, connection, *args, **kwargs):
    method = getattr(dialect, method_name)
    if hasattr(method, "__wrapped__"):
        return method.__wrapped__(dialect, connection, *args, **kwargs)
    return method(connection, *args, **kwargs)


class TestDialectBasics:
    def test_init_with_and_without_isolation_level(self):
        default_dialect = CubridDialect()
        assert default_dialect.isolation_level is None

        custom_dialect = CubridDialect(isolation_level="SERIALIZABLE")
        assert custom_dialect.isolation_level == "SERIALIZABLE"

    def test_import_dbapi_success(self):
        fake_module = types.ModuleType("CUBRIDdb")
        with patch.dict(sys.modules, {"CUBRIDdb": fake_module}):
            imported = CubridDialect.import_dbapi()
        assert imported is fake_module

    def test_import_dbapi_import_error(self):
        import builtins

        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "CUBRIDdb":
                raise ImportError("driver missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=_fake_import):
            with pytest.raises(ImportError, match="driver missing"):
                CubridDialect.import_dbapi()

    def test_legacy_dbapi_method_calls_import_dbapi(self):
        fake_module = object()
        with patch.object(CubridDialect, "import_dbapi", return_value=fake_module) as mocked:
            assert CubridDialect.dbapi() is fake_module
        mocked.assert_called_once_with()

    def test_create_connect_args_full_url(self):
        dialect = CubridDialect()
        parsed = url.make_url("cubrid://dba:pw@dbhost:33001/demodb")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ("CUBRID:dbhost:33001:demodb:::", "dba", "pw")
        assert kwargs == {}

    def test_create_connect_args_defaults(self):
        dialect = CubridDialect()
        parsed = url.make_url("cubrid://")

        args, kwargs = dialect.create_connect_args(parsed)

        assert args == ("CUBRID:localhost:33000::::", "", "")
        assert kwargs == {}

    def test_create_connect_args_none_url_raises(self):
        dialect = CubridDialect()
        none_url = cast(Any, None)
        with pytest.raises(ValueError, match="Unexpected database URL format"):
            dialect.create_connect_args(none_url)

    def test_on_connect_without_isolation_level(self):
        dialect = CubridDialect()
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        hook(dbapi_conn)

        dbapi_conn.set_autocommit.assert_called_once_with(False)
        dialect.set_isolation_level.assert_not_called()

    def test_on_connect_with_isolation_level(self):
        dialect = CubridDialect(isolation_level="SERIALIZABLE")
        dialect.set_isolation_level = MagicMock()

        dbapi_conn = MagicMock()
        hook = dialect.on_connect()
        hook(dbapi_conn)

        dbapi_conn.set_autocommit.assert_called_once_with(False)
        dialect.set_isolation_level.assert_called_once_with(dbapi_conn, "SERIALIZABLE")

    def test_server_version_info_match_and_non_match(self):
        dialect = CubridDialect()

        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = "11.2.9.0866"
        assert dialect._get_server_version_info(connection) == (11, 2, 9, 866)

        connection.execute.return_value.scalar.return_value = "not-a-version"
        assert dialect._get_server_version_info(connection) is None

    def test_get_default_schema_name(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = "dba"

        assert dialect._get_default_schema_name(connection) == "dba"

    def test_initialize_delegates_to_default_dialect(self):
        dialect = CubridDialect()
        connection = MagicMock()

        with patch("sqlalchemy.engine.default.DefaultDialect.initialize") as init_super:
            dialect.initialize(connection)

        init_super.assert_called_once_with(connection)


class TestIsolationLevelMethods:
    def test_get_isolation_level_string(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("SERIALIZABLE",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)

        assert level == "SERIALIZABLE"
        cursor.execute.assert_any_call("GET TRANSACTION ISOLATION LEVEL TO X")
        cursor.execute.assert_any_call("SELECT X")
        cursor.close.assert_called_once_with()

    def test_get_isolation_level_numeric(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (6,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "SERIALIZABLE"

    def test_get_isolation_level_unknown_numeric(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        cursor.fetchone.return_value = (99,)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        level = dialect.get_isolation_level(dbapi_conn)
        assert level == "99"

    def test_get_isolation_level_values(self):
        dialect = CubridDialect()
        levels = dialect.get_isolation_level_values()

        assert len(levels) == 9
        assert "SERIALIZABLE" in levels
        assert "READ COMMITTED" in levels
        assert "REPEATABLE READ" in levels

    def test_set_isolation_level_all_mapped_levels(self):
        """set_isolation_level works for every valid string level."""
        dialect = CubridDialect()
        expected_map = {
            "SERIALIZABLE": 6,
            "REPEATABLE READ": 5,
            "READ COMMITTED": 4,
            "CURSOR STABILITY": 4,
        }
        for level_name, expected_num in expected_map.items():
            cursor = MagicMock()
            dbapi_conn = MagicMock(spec=[])
            dbapi_conn.cursor = MagicMock(return_value=cursor)

            dialect.set_isolation_level(dbapi_conn, level_name)

            cursor.execute.assert_any_call(f"SET TRANSACTION ISOLATION LEVEL {expected_num}")
            cursor.execute.assert_any_call("COMMIT")
            cursor.close.assert_called_once_with()

    def test_set_isolation_level_with_plain_dbapi_class(self):
        dialect = CubridDialect()
        cursor = MagicMock()

        class PlainDBAPIConnection:
            def cursor(self):
                return cursor

        plain_conn = PlainDBAPIConnection()
        dialect.set_isolation_level(plain_conn, "SERIALIZABLE")

        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 6")
        cursor.execute.assert_any_call("COMMIT")
        cursor.close.assert_called_once_with()

    def test_set_isolation_level_invalid_raises(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        with pytest.raises(ValueError, match="Invalid isolation level"):
            dialect.set_isolation_level(dbapi_conn, "NONEXISTENT LEVEL")

    def test_reset_isolation_level(self):
        dialect = CubridDialect()
        cursor = MagicMock()
        # Use spec=[] to prevent MagicMock from auto-creating
        # a .connection attribute, which would cause set_isolation_level
        # to unwrap to a different mock object.
        dbapi_conn = MagicMock(spec=[])
        dbapi_conn.cursor = MagicMock(return_value=cursor)

        dialect.reset_isolation_level(dbapi_conn)
        # Should set to level 4 (READ COMMITTED)
        cursor.execute.assert_any_call("SET TRANSACTION ISOLATION LEVEL 4")


class TestExistenceChecks:
    def test_has_table_true_and_false(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "users") is True

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_table(connection, "users") is False

    def test_has_table_recognizes_views(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 1
        assert dialect.has_table(connection, "active_users") is True

    def test_has_index_true_false_and_exception(self):
        dialect = CubridDialect()
        connection = MagicMock()

        connection.execute.return_value.scalar.return_value = 2
        assert dialect.has_index(connection, "users", "ix_users_name") is True

        connection.execute.return_value.scalar.return_value = 0
        assert dialect.has_index(connection, "users", "ix_users_name") is False

        connection.execute.side_effect = RuntimeError("metadata unavailable")
        assert dialect.has_index(connection, "users", "ix_users_name") is False

    def test_has_sequence_always_false(self):
        dialect = CubridDialect()
        assert dialect.has_sequence(MagicMock(), "seq_users") is False


class TestReflectionMethods:
    def test_get_columns_covers_all_type_branches(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        rows = [
            ("char_col", "CHAR(3)", "YES", "", None, ""),
            ("varchar_col", "VARCHAR(100)", "YES", "", "v", ""),
            ("nchar_col", "NCHAR(10)", "NO", "", None, None),
            ("num_col", "NUMERIC(10,2)", "YES", "", "0", ""),
            ("dec_col", "DECIMAL", "NO", "", None, ""),
            ("int_col", "INTEGER", "NO", "", None, "auto_increment"),
            ("unknown_col", "MYSTERY", "YES", "", None, ""),
        ]
        comment_rows = [
            ("char_col", "char comment"),
            ("int_col", "int comment"),
            ("unknown_col", None),
        ]
        connection.execute.side_effect = [rows, comment_rows]

        with patch("sqlalchemy.sql.util.warn", create=True) as warn:
            columns = _invoke_reflection(dialect, "get_columns", connection, "sample_table")

        assert len(columns) == 7

        assert columns[0]["type"].__class__.__name__ == "CHAR"
        assert columns[0]["type"].length == 3

        assert columns[1]["type"].__class__.__name__ == "VARCHAR"
        assert columns[1]["type"].length == 100
        assert columns[1]["default"] == "v"

        assert columns[2]["type"].__class__.__name__ == "NCHAR"
        assert columns[2]["type"].length == 10
        assert columns[2]["nullable"] is False

        assert columns[3]["type"].__class__.__name__ == "NUMERIC"
        assert columns[3]["type"].precision == 10
        assert columns[3]["type"].scale == 2

        assert columns[4]["type"].__class__.__name__ == "DECIMAL"

        assert columns[5]["type"].__class__.__name__ == "INTEGER"
        assert columns[5]["autoincrement"] is True
        assert columns[5]["comment"] == "int comment"

        assert columns[6]["type"] is sqltypes.NULLTYPE
        assert columns[6]["comment"] is None
        warn.assert_called_once()

    def test_get_pk_constraint_with_primary_key_and_constraint_name(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_columns_rows = [
            ("id", "INTEGER", "NO", "PRI", None, "auto_increment"),
            ("name", "VARCHAR(50)", "YES", "", None, ""),
        ]
        constraint_result = MagicMock()
        constraint_result.fetchone.return_value = ("pk_users",)
        connection.execute.side_effect = [show_columns_rows, constraint_result]

        pk = _invoke_reflection(dialect, "get_pk_constraint", connection, "users")

        assert pk == {"name": "pk_users", "constrained_columns": ["id"]}

    def test_get_foreign_keys_success_and_exception(self):
        dialect = CubridDialect()

        success_conn = MagicMock()
        success_conn.info_cache = {}
        success_conn.dialect_options = {}
        success_conn.execute.return_value = [
            ("fk_order_user", "orders", "user_id", "users", "id"),
            ("fk_order_user", "orders", "tenant_id", "users", "tenant_id"),
            ("fk_no_ref_col", "orders", "legacy_id", "legacy", None),
        ]

        fks = _invoke_reflection(
            dialect,
            "get_foreign_keys",
            success_conn,
            "orders",
            schema="main",
        )

        assert len(fks) == 2
        first = next(item for item in fks if item["name"] == "fk_order_user")
        assert first["constrained_columns"] == ["user_id", "tenant_id"]
        assert first["referred_table"] == "users"
        assert first["referred_columns"] == ["id", "tenant_id"]
        assert first["referred_schema"] == "main"

        second = next(item for item in fks if item["name"] == "fk_no_ref_col")
        assert second["referred_columns"] == []

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        failed_conn.execute.side_effect = RuntimeError("fk lookup failed")

        assert _invoke_reflection(dialect, "get_foreign_keys", failed_conn, "orders") == []

    def test_get_table_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("users",), ("orders",)]

        assert _invoke_reflection(dialect, "get_table_names", connection, schema="main") == []
        assert _invoke_reflection(dialect, "get_table_names", connection, schema=None) == [
            "users",
            "orders",
        ]

    def test_get_view_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        connection.execute.return_value = [("active_users",), ("recent_orders",)]

        views = _invoke_reflection(dialect, "get_view_names", connection)
        assert views == ["active_users", "recent_orders"]

    def test_get_view_definition_with_and_without_row(self):
        dialect = CubridDialect()

        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        result = MagicMock()
        result.fetchone.return_value = ("view_name", "SELECT * FROM users")
        connection.execute.return_value = result
        assert (
            _invoke_reflection(dialect, "get_view_definition", connection, "user_view")
            == "SELECT * FROM users"
        )

        empty_result = MagicMock()
        empty_result.fetchone.return_value = None
        connection.execute.return_value = empty_result
        assert _invoke_reflection(dialect, "get_view_definition", connection, "user_view") is None

    def test_get_indexes_with_primary_key_and_exception_paths(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        # Batch PK query returns index_name, is_primary_key pairs
        pk_batch_result = [
            ("uq_name", 0),
            ("pk_users", 1),
            ("idx_email", 0),
        ]

        show_indexes_rows = [
            (None, 0, "uq_name", None, "first_name"),
            (None, 0, "uq_name", None, "last_name"),
            (None, 0, "pk_users", None, "id"),
            (None, 1, "idx_email", None, "email"),
        ]

        connection.execute.side_effect = [
            pk_batch_result,  # batch PK query
            show_indexes_rows,  # SHOW INDEXES
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "users")

        assert indexes == [
            {"name": "uq_name", "column_names": ["first_name", "last_name"], "unique": True},
            {"name": "idx_email", "column_names": ["email"], "unique": False},
        ]

    def test_get_indexes_batch_pk_query_failure(self):
        """When the batch PK catalog query fails, all indexes are returned."""
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}

        show_indexes_rows = [
            (None, 0, "uq_name", None, "first_name"),
            (None, 0, "pk_users", None, "id"),
        ]

        connection.execute.side_effect = [
            RuntimeError("catalog unavailable"),  # batch PK query fails
            show_indexes_rows,  # SHOW INDEXES
        ]

        indexes = _invoke_reflection(dialect, "get_indexes", connection, "users")

        # Both indexes returned since PK detection failed gracefully
        assert len(indexes) == 2
        assert indexes[0]["name"] == "uq_name"
        assert indexes[1]["name"] == "pk_users"

    def test_get_unique_constraints_success_and_exception(self):
        dialect = CubridDialect()

        success_conn = MagicMock()
        success_conn.info_cache = {}
        success_conn.dialect_options = {}
        success_conn.execute.return_value = [
            ("uq_users_email", "email"),
            ("uq_users_email", "tenant_id"),
            ("uq_users_name", "name"),
        ]

        unique_constraints = _invoke_reflection(
            dialect,
            "get_unique_constraints",
            success_conn,
            "users",
        )

        assert unique_constraints == [
            {"name": "uq_users_email", "column_names": ["email", "tenant_id"]},
            {"name": "uq_users_name", "column_names": ["name"]},
        ]

        failed_conn = MagicMock()
        failed_conn.info_cache = {}
        failed_conn.dialect_options = {}
        failed_conn.execute.side_effect = RuntimeError("uc lookup failed")

        assert _invoke_reflection(dialect, "get_unique_constraints", failed_conn, "users") == []

    def test_get_check_constraints_get_table_comment_and_schema_names(self):
        dialect = CubridDialect()
        connection = MagicMock()
        connection.info_cache = {}
        connection.dialect_options = {}
        table_comment_result = MagicMock()
        table_comment_result.fetchone.return_value = ("users table comment",)
        connection.execute.return_value = table_comment_result

        checks = _invoke_reflection(dialect, "get_check_constraints", connection, "users")
        comment = _invoke_reflection(dialect, "get_table_comment", connection, "users")

        assert checks == []
        assert comment == {"text": "users table comment"}
        assert dialect.get_schema_names(connection) == []


class TestDoReleaseSavepoint:
    def test_do_release_savepoint_is_noop(self):
        """CUBRID does not support RELEASE SAVEPOINT; method should be a no-op."""
        dialect = CubridDialect()
        connection = MagicMock()
        # Should not raise, should not call anything on connection
        result = dialect.do_release_savepoint(connection, "sp_test")
        assert result is None
        connection.execute.assert_not_called()


class TestIsDisconnect:
    """Tests for CubridDialect.is_disconnect() error detection."""

    @pytest.fixture()
    def dialect_with_dbapi(self):
        """Create a dialect with a mock dbapi module."""
        dialect = CubridDialect()

        # Build a mock dbapi module with CUBRIDdb's actual exception hierarchy:
        # Error (base) -> InterfaceError, DatabaseError, NotSupportedError
        dbapi = MagicMock()

        class Error(Exception):
            pass

        class InterfaceError(Error):
            pass

        class DatabaseError(Error):
            pass

        class NotSupportedError(Error):
            pass

        dbapi.Error = Error
        dbapi.InterfaceError = InterfaceError
        dbapi.DatabaseError = DatabaseError
        dbapi.NotSupportedError = NotSupportedError

        dialect.dbapi = dbapi
        return dialect, dbapi

    @pytest.mark.parametrize(
        "message",
        [
            "connection is closed",
            "Closed connection detected",
            "Lost connection to server",
            "server has gone away",
            "Connection Reset by peer",
            "Broken Pipe in socket",
            "Cannot communicate with the broker",
            "Received invalid packet from server",
            "Broker is not available right now",
            "Communication error during query",
            "Connection timed out after 30s",
            "Connection refused on port 33000",
            "connection was killed by admin",
            "Failed to connect to host",
        ],
    )
    def test_disconnect_message_patterns(self, dialect_with_dbapi, message):
        """is_disconnect() returns True for known disconnect messages."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(message)
        assert dialect.is_disconnect(exc, None, None) is True

    @pytest.mark.parametrize(
        "message",
        [
            "syntax error in SQL",
            "unique constraint violation",
            "table not found",
            "permission denied",
            "division by zero",
        ],
    )
    def test_non_disconnect_messages(self, dialect_with_dbapi, message):
        """is_disconnect() returns False for non-disconnect errors."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(message)
        assert dialect.is_disconnect(exc, None, None) is False

    @pytest.mark.parametrize(
        "error_code",
        [
            -21003,  # CAS_ER_COMMUNICATION
            -21005,  # CAS_ER_COMMUNICATION (alternate)
            -10005,  # ER_NET_CANT_CONNECT
            -10007,  # ER_NET_SERVER_COMM_ERROR
        ],
    )
    def test_disconnect_by_error_code(self, dialect_with_dbapi, error_code):
        """is_disconnect() returns True for known disconnect error codes."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError(error_code)
        assert dialect.is_disconnect(exc, None, None) is True

    def test_disconnect_with_interface_error(self, dialect_with_dbapi):
        """is_disconnect() works with InterfaceError subclass."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.InterfaceError("connection is closed")
        assert dialect.is_disconnect(exc, None, None) is True

    def test_non_dbapi_error_returns_false(self, dialect_with_dbapi):
        """is_disconnect() returns False for non-DBAPI exceptions."""
        dialect, _ = dialect_with_dbapi
        exc = RuntimeError("connection is closed")
        assert dialect.is_disconnect(exc, None, None) is False

    def test_disconnect_error_code_in_string_arg(self, dialect_with_dbapi):
        """is_disconnect() extracts numeric code from string like '-21003 msg'."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError("-21003 Cannot communicate with the broker")
        assert dialect.is_disconnect(exc, None, None) is True

    def test_disconnect_with_empty_args(self, dialect_with_dbapi):
        """is_disconnect() handles exception with no args gracefully."""
        dialect, dbapi = dialect_with_dbapi
        exc = dbapi.DatabaseError()
        assert dialect.is_disconnect(exc, None, None) is False


class TestExtractErrorCode:
    """Tests for CubridDialect._extract_error_code()."""

    def test_integer_arg(self):
        """Extracts integer error code from args[0]."""
        exc = Exception(-21003)
        assert CubridDialect._extract_error_code(exc) == -21003

    def test_string_with_embedded_code(self):
        """Extracts error code from string like '-21003 message'."""
        exc = Exception("-21003 Cannot communicate")
        assert CubridDialect._extract_error_code(exc) == -21003

    def test_string_without_code(self):
        """Returns None for string without leading number."""
        exc = Exception("some error message")
        assert CubridDialect._extract_error_code(exc) is None

    def test_empty_args(self):
        """Returns None for exception with no args."""
        exc = Exception()
        assert CubridDialect._extract_error_code(exc) is None

    def test_empty_string_arg(self):
        """Returns None for exception with empty string arg."""
        exc = Exception("")
        assert CubridDialect._extract_error_code(exc) is None

    def test_non_numeric_string_code(self):
        """Returns None when first token is not numeric."""
        exc = Exception("ERROR: connection lost")
        assert CubridDialect._extract_error_code(exc) is None

    def test_positive_integer(self):
        """Handles positive integer error codes."""
        exc = Exception(1234)
        assert CubridDialect._extract_error_code(exc) == 1234


class TestDoPing:
    """Tests for CubridDialect.do_ping()."""

    def test_ping_success(self):
        """do_ping() returns True when ping() succeeds."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.return_value = None

        result = dialect.do_ping(dbapi_conn)

        assert result is True
        dbapi_conn.ping.assert_called_once()

    def test_ping_propagates_exception(self):
        """do_ping() lets exceptions propagate (SA catches them)."""
        dialect = CubridDialect()
        dbapi_conn = MagicMock()
        dbapi_conn.ping.side_effect = RuntimeError("connection lost")

        with pytest.raises(RuntimeError, match="connection lost"):
            dialect.do_ping(dbapi_conn)


class TestPostfetchLastRowId:
    """Tests for postfetch_lastrowid flag and get_lastrowid behavior."""

    def test_postfetch_lastrowid_is_true(self):
        """CubridDialect sets postfetch_lastrowid = True."""
        dialect = CubridDialect()
        assert dialect.postfetch_lastrowid is True

    def test_get_lastrowid_via_driver_method(self):
        """get_lastrowid() uses raw connection's get_last_insert_id()."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)
        raw_conn = MagicMock()
        raw_conn.get_last_insert_id.return_value = 42

        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        assert ctx.get_lastrowid() == 42
        raw_conn.get_last_insert_id.assert_called_once()

    def test_get_lastrowid_fallback_to_sql(self):
        """get_lastrowid() falls back to SELECT LAST_INSERT_ID()."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        # Make the driver method unavailable
        raw_conn = MagicMock(spec=[])
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = (99,)
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() == 99
        cursor.execute.assert_called_once_with("SELECT LAST_INSERT_ID()")
        cursor.close.assert_called_once()

    def test_get_lastrowid_returns_none_when_no_result(self):
        """get_lastrowid() returns None if SELECT LAST_INSERT_ID() returns nothing."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        raw_conn = MagicMock(spec=[])
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = None
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() is None

    def test_get_lastrowid_exception_in_driver_method(self):
        """get_lastrowid() falls back if get_last_insert_id() raises."""
        from sqlalchemy_cubrid.base import CubridExecutionContext

        ctx = CubridExecutionContext.__new__(CubridExecutionContext)

        raw_conn = MagicMock()
        raw_conn.get_last_insert_id.side_effect = RuntimeError("driver error")
        connection = MagicMock()
        connection.connection.dbapi_connection = raw_conn
        ctx.root_connection = connection

        cursor = MagicMock()
        cursor.fetchone.return_value = (77,)
        ctx.create_server_side_cursor = MagicMock(return_value=cursor)

        assert ctx.get_lastrowid() == 77


class TestDisconnectMessages:
    """Ensure _disconnect_messages tuple is properly defined."""

    def test_disconnect_messages_is_tuple(self):
        assert isinstance(CubridDialect._disconnect_messages, tuple)

    def test_disconnect_messages_all_lowercase(self):
        """All patterns must be lowercase for case-insensitive matching."""
        for msg in CubridDialect._disconnect_messages:
            assert msg == msg.lower(), f"Pattern not lowercase: {msg!r}"

    def test_disconnect_messages_not_empty(self):
        assert len(CubridDialect._disconnect_messages) > 0
