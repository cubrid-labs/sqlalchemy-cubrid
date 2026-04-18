from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.engine import url

from sqlalchemy_cubrid.aio_pycubrid_dialect import (
    AsyncAdapt_pycubrid_connection,
    AsyncAdapt_pycubrid_cursor,
    AsyncAdapt_pycubrid_dbapi,
    PyCubridAsyncDialect,
)


class TestPyCubridAsyncDialectBasics:
    def test_driver_name(self):
        dialect = PyCubridAsyncDialect()
        assert dialect.driver == "aiopycubrid"
        assert dialect.name == "cubrid"

    def test_is_async(self):
        dialect = PyCubridAsyncDialect()
        assert dialect.is_async is True

    def test_supports_statement_cache(self):
        dialect = PyCubridAsyncDialect()
        assert dialect.supports_statement_cache is True

    def test_inherits_cubrid_dialect_properties(self):
        dialect = PyCubridAsyncDialect()
        assert dialect.supports_native_boolean is False
        assert dialect.supports_sequences is False
        assert dialect.max_identifier_length == 254

    def test_default_paramstyle(self):
        dialect = PyCubridAsyncDialect()
        assert dialect.default_paramstyle == "qmark"


class TestPyCubridAsyncDialectImportDbapi:
    def test_import_dbapi_returns_async_adapt_module(self):
        fake_aio = types.ModuleType("pycubrid.aio")
        fake_sync = types.ModuleType("pycubrid")
        fake_sync.paramstyle = "qmark"  # type: ignore[attr-defined]
        for attr in [
            "Error",
            "OperationalError",
            "InterfaceError",
            "IntegrityError",
            "ProgrammingError",
            "DatabaseError",
            "InternalError",
            "DataError",
            "NotSupportedError",
            "Warning",
            "STRING",
            "BINARY",
            "NUMBER",
            "DATETIME",
            "ROWID",
        ]:
            setattr(fake_sync, attr, type(attr, (Exception,), {}))

        with patch.dict(sys.modules, {"pycubrid.aio": fake_aio, "pycubrid": fake_sync}):
            dbapi = PyCubridAsyncDialect.import_dbapi()

        assert isinstance(dbapi, AsyncAdapt_pycubrid_dbapi)


class TestPyCubridAsyncDialectConnectArgs:
    def test_create_connect_args(self):
        dialect = PyCubridAsyncDialect()
        u = url.make_url("cubrid+aiopycubrid://dba:pass@myhost:33000/mydb")
        args, kwargs = dialect.create_connect_args(u)
        assert args == ()
        assert kwargs["host"] == "myhost"
        assert kwargs["port"] == 33000
        assert kwargs["database"] == "mydb"
        assert kwargs["user"] == "dba"
        assert kwargs["password"] == "pass"

    def test_create_connect_args_defaults(self):
        dialect = PyCubridAsyncDialect()
        u = url.make_url("cubrid+aiopycubrid:///")
        args, kwargs = dialect.create_connect_args(u)
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 33000
        assert kwargs["user"] == "dba"
        assert kwargs["password"] == ""


class TestPyCubridAsyncDialectOnConnect:
    def test_on_connect_sets_autocommit_false(self):
        dialect = PyCubridAsyncDialect()
        callback = dialect.on_connect()
        assert callback is not None

        conn = MagicMock()
        callback(conn)
        assert conn.autocommit is False

    def test_on_connect_with_isolation_level(self):
        dialect = PyCubridAsyncDialect(isolation_level="SERIALIZABLE")
        callback = dialect.on_connect()
        assert callback is not None

        conn = MagicMock()
        with patch.object(dialect, "set_isolation_level") as mock_set:
            callback(conn)
        mock_set.assert_called_once_with(conn, "SERIALIZABLE")


class TestAsyncAdaptPycubridDbapi:
    def test_connect_calls_aio_connect(self):
        fake_aio = MagicMock()
        fake_sync = MagicMock()
        fake_sync.paramstyle = "qmark"

        with patch.dict(sys.modules, {"pycubrid": fake_sync}):
            dbapi = AsyncAdapt_pycubrid_dbapi(fake_aio)

        assert dbapi.paramstyle == "qmark"
        assert dbapi._aio_module is fake_aio

    def test_exception_classes_from_sync_module(self):
        fake_aio = MagicMock()
        fake_sync = MagicMock()
        fake_sync.paramstyle = "qmark"

        class FakeError(Exception):
            pass

        fake_sync.Error = FakeError

        with patch.dict(sys.modules, {"pycubrid": fake_sync}):
            dbapi = AsyncAdapt_pycubrid_dbapi(fake_aio)

        assert dbapi.Error is FakeError


class TestAsyncAdaptPycubridConnection:
    def test_autocommit_property_reads_underlying(self):
        mock_dbapi = MagicMock()
        mock_async_conn = MagicMock()
        mock_async_conn.autocommit = True

        conn = AsyncAdapt_pycubrid_connection(mock_dbapi, mock_async_conn)
        assert conn.autocommit is True

    def test_cursor_returns_adapted_cursor(self):
        mock_dbapi = MagicMock()
        mock_async_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_async_conn.cursor.return_value = mock_cursor

        conn = AsyncAdapt_pycubrid_connection(mock_dbapi, mock_async_conn)

        with patch.object(conn, "await_", side_effect=lambda x: mock_cursor):
            cur = conn.cursor()

        assert isinstance(cur, AsyncAdapt_pycubrid_cursor)


class TestAsyncAdaptPycubridCursor:
    def test_setinputsizes_is_noop(self):
        mock_conn = MagicMock(spec=AsyncAdapt_pycubrid_connection)
        mock_conn._connection = MagicMock()
        mock_async_cursor = MagicMock()
        mock_async_cursor.__aenter__ = AsyncMock(return_value=mock_async_cursor)
        mock_async_cursor.description = None
        mock_conn._connection.cursor.return_value = mock_async_cursor
        mock_conn.await_ = lambda x: mock_async_cursor
        mock_conn._execute_mutex = MagicMock()

        cur = AsyncAdapt_pycubrid_cursor(mock_conn)
        cur.setinputsizes(10, 20)

    def test_nextset_is_noop(self):
        mock_conn = MagicMock(spec=AsyncAdapt_pycubrid_connection)
        mock_conn._connection = MagicMock()
        mock_async_cursor = MagicMock()
        mock_async_cursor.__aenter__ = AsyncMock(return_value=mock_async_cursor)
        mock_conn._connection.cursor.return_value = mock_async_cursor
        mock_conn.await_ = lambda x: mock_async_cursor
        mock_conn._execute_mutex = MagicMock()

        cur = AsyncAdapt_pycubrid_cursor(mock_conn)
        cur.nextset()


class TestPyCubridAsyncDialectDoPing:
    def test_do_ping_executes_select_1(self):
        dialect = PyCubridAsyncDialect()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        result = dialect.do_ping(mock_conn)

        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.fetchone.assert_called_once()
        mock_cursor.close.assert_called_once()
        assert result is True
