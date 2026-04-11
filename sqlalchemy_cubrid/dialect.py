# sqlalchemy_cubrid/dialect.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""CUBRID dialect for SQLAlchemy 2.0."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional, Sequence, cast

from sqlalchemy import types as sqltypes
from sqlalchemy.engine import default, reflection
from sqlalchemy.engine.interfaces import (
    DBAPIConnection,
    DBAPIModule,
    ConnectArgsType,
    ReflectedCheckConstraint,
    ReflectedColumn,
    ReflectedForeignKeyConstraint,
    ReflectedIndex,
    ReflectedPrimaryKeyConstraint,
    ReflectedTableComment,
    ReflectedUniqueConstraint,
)
from sqlalchemy.engine.url import URL
from sqlalchemy.sql import text
from sqlalchemy.sql.compiler import IdentifierPreparer

from sqlalchemy_cubrid.base import CubridExecutionContext, CubridIdentifierPreparer
from sqlalchemy_cubrid.compiler import (
    CubridCompiler,
    CubridDDLCompiler,
    CubridTypeCompiler,
)
from sqlalchemy_cubrid.types import (
    BIGINT,
    BIT,
    BLOB,
    CHAR,
    CLOB,
    DECIMAL,
    DOUBLE,
    DOUBLE_PRECISION,
    FLOAT,
    MULTISET,
    NCHAR,
    NUMERIC,
    NVARCHAR,
    SEQUENCE,
    SET,
    SMALLINT,
    STRING,
    VARCHAR,
)

from sqlalchemy.types import (
    DATE,
    DATETIME,
    INTEGER,
    TIME,
    TIMESTAMP,
)

log = logging.getLogger(__name__)

# Pre-compiled patterns for column type parsing in get_columns().
# Avoids re-compilation on every reflection call.
_RE_TYPE_PARAMS = re.compile(r"\([\d,]+\)")
_RE_LENGTH = re.compile(r"\((\d+)\)")
_RE_PRECISION_SCALE = re.compile(r"\((\d+)(?:,\s*(\d+))?\)")


# -----------------------------------------------------------------------
# Column-spec and ischema_names mappings
# -----------------------------------------------------------------------

colspecs = {
    sqltypes.Numeric: NUMERIC,
    sqltypes.Float: FLOAT,
    sqltypes.Time: TIME,
}

# ischema_names maps CUBRID type names from SHOW COLUMNS to SA types.
# https://www.cubrid.org/manual/en/11.0/sql/datatype.html
ischema_names = {
    # Numeric
    "SHORT": SMALLINT,
    "SMALLINT": SMALLINT,
    "INTEGER": INTEGER,
    "BIGINT": BIGINT,
    "NUMERIC": NUMERIC,
    "DECIMAL": DECIMAL,
    "FLOAT": FLOAT,
    "DOUBLE": DOUBLE,
    "DOUBLE PRECISION": DOUBLE_PRECISION,
    # Date/Time
    "DATE": DATE,
    "TIME": TIME,
    "TIMESTAMP": TIMESTAMP,
    "DATETIME": DATETIME,
    # Bit Strings
    "BIT": BIT,
    "BIT VARYING": BIT,
    # Character Strings
    "CHAR": CHAR,
    "VARCHAR": VARCHAR,
    "NCHAR": NCHAR,
    "CHAR VARYING": NVARCHAR,
    "STRING": STRING,
    # LOB
    "BLOB": BLOB,
    "CLOB": CLOB,
    # Collection
    "SET": SET,
    "MULTISET": MULTISET,
    "SEQUENCE": SEQUENCE,
}


# -----------------------------------------------------------------------
# Dialect
# -----------------------------------------------------------------------


class CubridDialect(default.DefaultDialect):
    """SQLAlchemy dialect for CUBRID."""

    name = "cubrid"
    driver = "cubrid"

    # SA 2.0 statement caching
    supports_statement_cache = True

    # Compiler classes
    statement_compiler = CubridCompiler
    ddl_compiler = CubridDDLCompiler
    type_compiler = CubridTypeCompiler
    preparer: type[IdentifierPreparer] = CubridIdentifierPreparer
    execution_ctx_cls = CubridExecutionContext

    # DBAPI
    # https://www.cubrid.org/manual/en/11.0/api/python.html
    default_paramstyle = "qmark"

    # Type mappings
    colspecs = colspecs  # pyright: ignore[reportAssignmentType]
    ischema_names = ischema_names

    # Identifiers
    # https://www.cubrid.org/manual/en/11.0/sql/identifier.html
    max_identifier_length = 254
    max_index_name_length = 254
    max_constraint_name_length = 254

    requires_name_normalize = True

    # Data type support
    supports_native_enum = False
    supports_native_boolean = False  # CUBRID uses SMALLINT for booleans
    supports_native_decimal = True

    # Column options
    supports_sequences = False

    # DDL
    supports_alter = True
    supports_comments = True
    inline_comments = True

    # DML
    supports_default_values = True
    supports_default_metavalue = True
    supports_empty_insert = True
    supports_multivalues_insert = True
    supports_is_distinct_from = False

    # RETURNING
    insert_returning = False
    update_returning = False
    delete_returning = False

    postfetch_lastrowid = True

    def __init__(self, isolation_level: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.isolation_level = isolation_level

    @classmethod
    def import_dbapi(cls) -> DBAPIModule:
        """Import and return the CUBRID DBAPI module (SA 2.0 API)."""
        try:
            import CUBRIDdb as cubrid_dbapi  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
        except ImportError as e:
            raise e
        return cast(DBAPIModule, cubrid_dbapi)  # pyright: ignore[reportInvalidCast]

    # Keep legacy dbapi() for SA 1.x compat if needed
    @classmethod
    def dbapi(cls) -> DBAPIModule:  # type: ignore[override]
        return cls.import_dbapi()

    def create_connect_args(self, url: URL) -> ConnectArgsType:
        """Build DB-API connection arguments for CUBRID.

        CUBRID connection string format::

            CUBRID:host:port:db_name:::
        """
        if url is None:
            raise ValueError("Unexpected database URL format")

        opts = url.translate_connect_args(username="user", database="database")
        host = opts.get("host", "localhost")
        port = opts.get("port", 33000)
        database = opts.get("database", "")
        username = opts.get("user", "")
        password = opts.get("password", "")

        connect_url = f"CUBRID:{host}:{port}:{database}:::"
        args = (connect_url, username, password)
        return args, {}

    def initialize(self, connection: Any) -> None:
        super().initialize(connection)

    # ----- Reflection methods -----

    @reflection.cache
    def get_columns(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedColumn]:
        """Return column information for *table_name*.

        Uses ``SHOW COLUMNS IN <table>`` which is available since CUBRID 9.x.
        """
        columns: list[ReflectedColumn] = []
        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
        for row in result:
            colname = row[0]
            coltype_raw = row[1]
            nullable = row[2] == "YES"
            default_val = row[4]
            autoincrement = "auto_increment" in row[5] if row[5] else False

            # Strip length/precision from type string for lookup
            coltype_key = _RE_TYPE_PARAMS.sub("", coltype_raw).strip()

            if coltype_key in ("CHAR", "VARCHAR", "NCHAR", "CHAR VARYING"):
                length_match = _RE_LENGTH.search(coltype_raw)
                length = int(length_match.group(1)) if length_match else None
                coltype = self.ischema_names[coltype_key](length)  # pyright: ignore[reportCallIssue, reportArgumentType]
            elif coltype_key in ("NUMERIC", "DECIMAL"):
                params_match = _RE_PRECISION_SCALE.search(coltype_raw)
                if params_match:
                    precision = int(params_match.group(1))
                    scale = int(params_match.group(2)) if params_match.group(2) else None
                    coltype = self.ischema_names[coltype_key](precision=precision, scale=scale)  # pyright: ignore[reportCallIssue]
                else:
                    coltype = self.ischema_names[coltype_key]()
            else:
                try:
                    coltype_cls = self.ischema_names[coltype_key]
                    # Some ischema entries are classes, some are instances
                    coltype = coltype_cls() if callable(coltype_cls) else coltype_cls
                except KeyError:
                    from sqlalchemy import util

                    util.warn("Did not recognize type '%s' of column '%s'" % (coltype_raw, colname))
                    coltype = sqltypes.NULLTYPE

            columns.append(
                {
                    "name": colname,
                    "type": coltype,
                    "nullable": nullable,
                    "default": default_val,
                    "autoincrement": autoincrement,
                }
            )

        try:
            comment_result = connection.execute(
                text(
                    "SELECT attr_name, comment FROM _db_attribute "
                    "WHERE class_name = :name ORDER BY def_order"
                ),
                {"name": table_name},
            )
            comment_map = {row[0]: row[1] for row in comment_result}
        except Exception:
            comment_map = {}

        for column in columns:
            column["comment"] = comment_map.get(column["name"])

        return columns

    @reflection.cache
    def get_pk_constraint(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> ReflectedPrimaryKeyConstraint:
        """Return the primary key constraint for *table_name*."""
        constraint_name = None
        constrained_columns: list[str] = []

        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW COLUMNS IN {quoted}"))
        for row in result:
            if row[3] == "PRI":
                constrained_columns.append(row[0])

        # Try to find constraint name from db_constraint
        if constrained_columns:
            try:
                constraint_result = connection.execute(
                    text(
                        "SELECT index_name FROM db_constraint "
                        "WHERE class_name = :table AND type = 0"
                    ),
                    {"table": table_name},
                )
                row = constraint_result.fetchone()
                if row:
                    constraint_name = row[0]
            except Exception:  # nosec B110 — constraint name is optional metadata
                pass

        return {
            "name": constraint_name,
            "constrained_columns": constrained_columns,
        }

    @reflection.cache
    def get_foreign_keys(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedForeignKeyConstraint]:
        """Return foreign key information for *table_name*.

        Uses ``db_constraint`` system table to retrieve FK constraints.
        """
        foreign_keys: list[ReflectedForeignKeyConstraint] = []
        try:
            result = connection.execute(
                text(
                    "SELECT c.constraint_name, c.class_name, "
                    "a.attr_name, c.ref_class_name, ra.attr_name "
                    "FROM db_constraint c "
                    "JOIN _db_index_key a ON c.index_name = a.index_name "
                    "LEFT JOIN db_constraint rc ON c.ref_class_name = rc.class_name "
                    "  AND rc.type = 0 "
                    "LEFT JOIN _db_index_key ra ON rc.index_name = ra.index_name "
                    "  AND a.key_order = ra.key_order "
                    "WHERE c.class_name = :table AND c.type = 3 "
                    "ORDER BY c.constraint_name, a.key_order"
                ),
                {"table": table_name},
            )

            fk_dict: dict[str, ReflectedForeignKeyConstraint] = {}
            for row in result:
                name = row[0]
                if name not in fk_dict:
                    fk_dict[name] = {
                        "name": name,
                        "constrained_columns": [],
                        "referred_schema": schema,
                        "referred_table": row[3],
                        "referred_columns": [],
                    }
                fk_dict[name]["constrained_columns"].append(row[2])
                if row[4]:
                    fk_dict[name]["referred_columns"].append(row[4])

            foreign_keys = list(fk_dict.values())
        except Exception:  # nosec B110 — graceful fallback when FK info unavailable
            pass

        return foreign_keys

    @reflection.cache
    def get_table_names(
        self,
        connection: Any,
        schema: str | None = None,
        **kw: Any,
    ) -> list[str]:
        """Return a list of table names for *schema*."""
        if schema is not None:
            return []
        result = connection.execute(
            text(
                "SELECT class_name FROM db_class "
                "WHERE class_type = 'CLASS' AND is_system_class = 'NO'"
            )
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_names(
        self,
        connection: Any,
        schema: str | None = None,
        **kw: Any,
    ) -> list[str]:
        """Return a list of view names."""
        result = connection.execute(
            text("SELECT class_name FROM db_class WHERE class_type = 'VCLASS'")
        )
        return [row[0] for row in result]

    @reflection.cache
    def get_view_definition(self, connection: Any, view_name: str, schema: str | None = None, **kw: Any) -> str | None:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the CREATE VIEW definition."""
        quoted = self.identifier_preparer.quote_identifier(view_name)
        result = connection.execute(text(f"SHOW CREATE VIEW {quoted}"))
        row = result.fetchone()
        return row[1] if row else None

    @reflection.cache
    def get_indexes(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedIndex]:
        """Return index information for *table_name*."""
        idict: dict[str, ReflectedIndex] = {}

        # Batch-fetch primary key flags for all indexes on this table
        # instead of issuing one query per index (N+1 → 1+1).
        pk_indexes: set[str] = set()
        try:
            pk_result = connection.execute(
                text(
                    "SELECT index_name, is_primary_key FROM _db_index "
                    "WHERE class_of.class_name = :table"
                ),
                {"table": table_name},
            )
            for pk_row in pk_result:
                if pk_row[1]:
                    pk_indexes.add(pk_row[0])
        except Exception:
            # Fallback: if catalog query fails, pk_indexes stays empty
            # so no indexes will be wrongly excluded.
            log.debug("Batch PK query failed for table %s, falling back", table_name)

        quoted = self.identifier_preparer.quote_identifier(table_name)
        result = connection.execute(text(f"SHOW INDEXES IN {quoted}"))
        for row in result:
            index_name = row[2]

            if index_name not in pk_indexes:
                if index_name in idict:
                    idict[index_name]["column_names"].append(row[4])
                else:
                    idict[index_name] = {
                        "name": index_name,
                        "column_names": [row[4]],
                        "unique": row[1] == 0,
                    }

        return list(idict.values())

    @reflection.cache
    def get_unique_constraints(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedUniqueConstraint]:
        """Return unique constraints for *table_name*."""
        unique_constraints: list[ReflectedUniqueConstraint] = []
        try:
            result = connection.execute(
                text(
                    "SELECT c.constraint_name, a.attr_name "
                    "FROM db_constraint c "
                    "JOIN _db_index_key a ON c.index_name = a.index_name "
                    "WHERE c.class_name = :table AND c.type = 1 "
                    "ORDER BY c.constraint_name, a.key_order"
                ),
                {"table": table_name},
            )
            uc_dict: dict[str, ReflectedUniqueConstraint] = {}
            for row in result:
                name = row[0]
                if name not in uc_dict:
                    uc_dict[name] = {"name": name, "column_names": []}
                uc_dict[name]["column_names"].append(row[1])
            unique_constraints = list(uc_dict.values())
        except Exception:  # nosec B110 — graceful fallback when UC info unavailable
            pass
        return unique_constraints

    @reflection.cache
    def get_check_constraints(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> list[ReflectedCheckConstraint]:
        """Return check constraints for *table_name*."""
        # CUBRID does not expose check constraint expressions easily
        return []

    @reflection.cache
    def get_table_comment(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> ReflectedTableComment:
        """Return table comment from CUBRID system catalog."""
        result = connection.execute(
            text("SELECT comment FROM db_class WHERE class_name = :name"),
            {"name": table_name},
        )
        row = result.fetchone()
        return {"text": row[0] if row and row[0] else None}

    def get_schema_names(self, connection: Any, **kw: Any) -> list[str]:
        """Return schema names.  CUBRID does not support schemas."""
        return []

    def has_table(
        self,
        connection: Any,
        table_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if *table_name* exists."""
        result = connection.execute(
            text(
                "SELECT COUNT(*) FROM db_class "
                "WHERE class_type IN ('CLASS', 'VCLASS') "
                "AND is_system_class = 'NO' "
                "AND class_name = :name"
            ),
            {"name": table_name},
        )
        return bool(result.scalar())

    def has_index(
        self,
        connection: Any,
        table_name: str,
        index_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """Check if an index exists on *table_name*."""
        try:
            result = connection.execute(
                text("SELECT COUNT(*) FROM _db_index WHERE index_name = :name"),
                {"name": index_name},
            )
            return bool(result.scalar())
        except Exception:
            return False

    def has_sequence(
        self,
        connection: Any,
        sequence_name: str,
        schema: str | None = None,
        **kw: Any,
    ) -> bool:
        """CUBRID does not support sequences."""
        return False

    # ----- Connection lifecycle -----

    def on_connect(self) -> Callable[[Any], None] | None:
        """Return a callable to set up a new DBAPI connection.

        Disables autocommit on the CUBRID driver so that
        SQLAlchemy can manage transactions properly.
        """
        isolation_level = self.isolation_level

        def connect(conn: Any) -> None:
            # CUBRID Python driver defaults to autocommit=True;
            # SA manages transactions, so we turn it off.
            conn.set_autocommit(False)
            if isolation_level is not None:
                self.set_isolation_level(conn, isolation_level)

        return connect

    def _get_server_version_info(self, connection: Any) -> tuple[int, int, int, int] | None:
        """Return server version as a tuple of ints."""
        versions = connection.execute(text("SELECT VERSION()")).scalar()
        m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", versions)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
        return None

    def _get_default_schema_name(self, connection: Any) -> str:
        """Return the default schema name."""
        return str(connection.execute(text("SELECT SCHEMA()")).scalar())

    # ----- Isolation level -----

    # CUBRID isolation level mapping
    # https://www.cubrid.org/manual/en/11.0/sql/transaction.html
    _ISOLATION_LEVEL_MAP: dict[str, int] = {
        "SERIALIZABLE": 6,
        "REPEATABLE READ": 5,
        "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES": 5,
        "READ COMMITTED": 4,
        "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES": 4,
        "CURSOR STABILITY": 4,
        "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES": 3,
        "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES": 2,
        "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES": 1,
    }

    _ISOLATION_LEVEL_REVERSE: dict[int, str] = {
        6: "SERIALIZABLE",
        5: "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES",
        4: "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES",
        3: "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES",
        2: "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES",
        1: "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES",
    }

    def get_isolation_level(self, dbapi_connection: DBAPIConnection) -> str:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the current isolation level for *dbapi_conn*."""
        # https://www.cubrid.org/manual/en/11.0/sql/transaction.html
        cursor = dbapi_connection.cursor()
        cursor.execute("GET TRANSACTION ISOLATION LEVEL TO X")
        cursor.execute("SELECT X")
        row = cursor.fetchone()
        if row is None:
            return "READ COMMITTED"
        val = row[0]
        cursor.close()
        # CUBRID returns numeric level; map to string for SA
        if isinstance(val, int):
            return self._ISOLATION_LEVEL_REVERSE.get(val, str(val))
        return str(val)

    def get_isolation_level_values(self, dbapi_conn: DBAPIConnection | None = None) -> Sequence[str]:  # type: ignore[override]  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the list of valid isolation level values."""
        del dbapi_conn
        return [
            "SERIALIZABLE",
            "REPEATABLE READ",
            "REPEATABLE READ SCHEMA, REPEATABLE READ INSTANCES",
            "READ COMMITTED",
            "REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES",
            "CURSOR STABILITY",
            "REPEATABLE READ SCHEMA, READ UNCOMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ COMMITTED INSTANCES",
            "READ COMMITTED SCHEMA, READ UNCOMMITTED INSTANCES",
        ]

    def set_isolation_level(self, dbapi_connection: DBAPIConnection, level: str) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Set the isolation level for *dbapi_conn*."""
        # Note: do NOT unwrap dbapi_conn.connection — the inner C-level
        # _cubrid.connection cursor cannot handle SET TRANSACTION SQL.
        # SA already passes the correct Python-level CUBRIDdb.connections.Connection.
        # Map string level to numeric
        numeric_level = self._ISOLATION_LEVEL_MAP.get(level.upper())
        if numeric_level is None:
            raise ValueError(
                f"Invalid isolation level: {level!r}. "
                f"Valid values: {list(self._ISOLATION_LEVEL_MAP.keys())}"
            )
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {numeric_level}")
        cursor.execute("COMMIT")
        cursor.close()

    def reset_isolation_level(self, dbapi_conn: DBAPIConnection) -> None:
        """Revert isolation level to the default."""
        # CUBRID server default is typically level 4
        # (REPEATABLE READ SCHEMA, READ COMMITTED INSTANCES)
        self.set_isolation_level(dbapi_conn, "READ COMMITTED")

    def do_release_savepoint(self, connection: Any, name: str) -> None:
        """CUBRID does not support RELEASE SAVEPOINT; no-op."""
        pass

    # ----- Error handling & connection health -----

    # Disconnect message patterns (lowercase) for is_disconnect().
    # Modeled after psycopg2's string-based approach since CUBRIDdb has
    # only Error, InterfaceError, DatabaseError, and NotSupportedError.
    _disconnect_messages = (
        "connection is closed",
        "closed connection",
        "lost connection",
        "server has gone away",
        "connection reset",
        "broken pipe",
        "cannot communicate with the broker",
        "received invalid packet",
        "broker is not available",
        "communication error",
        "connection timed out",
        "connection refused",
        "connection was killed",
        "failed to connect",
    )

    def is_disconnect(self, e: Exception, connection: Any, cursor: Any) -> bool:
        """Return True if *e* indicates a dropped connection.

        CUBRID's Python driver exposes a limited exception hierarchy:
        ``Error``, ``InterfaceError``, ``DatabaseError``, and
        ``NotSupportedError``.  There is no ``OperationalError`` class,
        so we rely primarily on string-based message matching (similar
        to psycopg2) supplemented by known numeric error codes.
        """
        dbapi_module = getattr(self, "dbapi", None)
        if dbapi_module is None or not hasattr(dbapi_module, "Error"):
            try:
                dbapi_module = self.import_dbapi()
            except ImportError:
                dbapi_module = None

        if dbapi_module is not None and isinstance(e, dbapi_module.Error):
            msg = str(e).lower()
            for pattern in self._disconnect_messages:
                if pattern in msg:
                    return True

            # Check numeric error code for known disconnect codes
            error_code = self._extract_error_code(e)
            if error_code is not None and error_code in (
                -21003,  # CAS_ER_COMMUNICATION
                -21005,  # CAS_ER_COMMUNICATION (alternate)
                -10005,  # ER_NET_CANT_CONNECT
                -10007,  # ER_NET_SERVER_COMM_ERROR
            ):
                return True
        return False

    @staticmethod
    def _extract_error_code(exception: Exception) -> Optional[int]:
        """Extract a numeric error code from a CUBRID DBAPI exception.

        CUBRIDdb stores the error code in ``exception.args[0]``.
        Returns ``None`` if no numeric code can be extracted.
        """
        if exception.args:
            first_arg = exception.args[0]
            if isinstance(first_arg, int):
                return first_arg
            # Some errors embed the code at the start: "-21003 ..."
            if isinstance(first_arg, str):
                parts = first_arg.split(None, 1)
                if parts:
                    try:
                        return int(parts[0])
                    except (ValueError, IndexError):
                        pass
        return None

    def do_ping(self, dbapi_connection: DBAPIConnection) -> bool:
        """Ping the server to check connection liveness.

        Used by SQLAlchemy's ``pool_pre_ping`` feature.  The CUBRID
        Python driver exposes a ``ping()`` method on the connection
        that delegates to the C-level CCI ping.
        """
        dbapi_connection.ping()
        return True


dialect = CubridDialect
