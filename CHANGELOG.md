# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.3] - 2026-04-19

### Fixed

- **Re-release of 1.2.2** from current `main` HEAD. The `v1.2.2` git tag
  unintentionally pointed to an older commit (pre-async-dialect, pre-#120 fix),
  so the PyPI 1.2.2 artifact shipped without the #120 fix and was missing the
  `cubrid.pycubrid` and `cubrid.aiopycubrid` entry points. **PyPI 1.2.2 has been
  yanked**; please upgrade to 1.2.3.
- No source code changes vs. `main` — same fixes as listed under [1.2.2] below,
  now actually shipped to PyPI.

## [1.2.2] - 2026-04-19

### Fixed

- **Alembic autogenerate false-positive diffs** (#120):
  - `get_indexes()` now filters out the implicit indexes that CUBRID auto-creates
    for every primary-key and foreign-key constraint.  These auto-indexes
    previously caused Alembic to emit spurious `op.drop_index` /
    `op.create_index` operations on every `alembic check` / `revision --autogenerate`
    run.  The dialect now batch-queries `_db_index.is_primary_key` and
    `_db_index.is_foreign_key` (single round trip) and excludes flagged indexes
    from the reflection result.
  - `get_foreign_keys()` rewritten to parse `SHOW CREATE TABLE` output.  The
    previous implementation queried the `db_constraint` view, which is **not**
    queryable in CUBRID 11.x (despite older docs referencing it) and silently
    returned an empty list — leaving Alembic blind to every existing FK and
    causing it to schedule recreation on every run.
  - `get_unique_constraints()` rewritten to parse `SHOW CREATE TABLE` output
    for the same reason as `get_foreign_keys()`.
- **`compare_type` for unbounded VARCHAR**: `CubridImpl.compare_type()` now
  treats CUBRID's `VARCHAR(1073741823)` (the physical storage for `STRING`,
  `CLOB`, `TEXT`, and `String` without a length) as equivalent to SQLAlchemy's
  `Text()`, `CLOB()`, and `String()` (no length), eliminating false-positive
  type-change diffs in Alembic autogenerate.

## [1.2.1] - 2026-04-19

### Fixed

- **Async dialect**: Add missing `get_pool_class()` override returning
  `AsyncAdaptedQueuePool` — `create_async_engine()` now works correctly (#116)
- **JSON serialization**: Initialize `_json_serializer` / `_json_deserializer`
  attributes in `CubridDialect.__init__()` — ORM `JSON` column inserts no
  longer raise `AttributeError` (#117)

### Added

- 16 async E2E integration tests (`test/test_aio_integration.py`)
- Async usage sample (`samples/async_basic.py`)

## [1.2.0] - 2026-04-18

### Added

- **JSON type support** (CUBRID 10.2+)
  - `JSON` type class subclassing `sqltypes.JSON`
  - `JSONIndexType` and `JSONPathType` for path expression formatting
    (with embedded-quote escaping per CUBRID JSON path grammar)
  - `visit_JSON` type compiler emitting `JSON` DDL
  - JSON path expressions via `JSON_EXTRACT` (`col["key"]`, `col[("a", "b")]`)
  - Typed access via `as_boolean`, `as_integer`, `as_numeric`, `as_float`, `as_string`
    using CASE / CAST / `JSON_UNQUOTE` as appropriate
  - JSON null → SQL NULL handling with CASE expressions for typed access
  - `colspecs` mapping: generic `sa.JSON` → dialect `JSON`
  - `ischema_names` mapping: `"JSON"` → `JSON` for reflection
  - 47 offline tests (`test/test_json.py`)

### Fixed

- Version consistency: synchronized `__version__` in `sqlalchemy_cubrid/__init__.py`
  with `pyproject.toml` (was 1.0.0 vs 1.1.0)
- Removed unused imports flagged by `ruff` in `aio_pycubrid_dialect.py` and
  `test/test_aio_pycubrid_dialect.py`

## [1.1.0] - 2026-04-18

### Added

- **Async dialect** via `cubrid+aiopycubrid://` URL scheme
  - `PyCubridAsyncDialect` (`is_async=True`) using SQLAlchemy's `AsyncAdapt_dbapi_*` base classes
  - `AsyncAdapt_pycubrid_dbapi` wraps `pycubrid.aio` module
  - `AsyncAdapt_pycubrid_connection` bridges autocommit via greenlet `await_only`
  - `AsyncAdapt_pycubrid_cursor` with full async cursor adaptation
  - `cubrid.aiopycubrid` entry point auto-discovered by SQLAlchemy
- 17 new async dialect offline tests (`test/test_aio_pycubrid_dialect.py`)

## [1.0.0] - 2026-04-11

### Stability Guarantee

This release marks the first stable version of sqlalchemy-cubrid. The public API is frozen:
breaking changes will only occur in major version bumps (2.0+).

### Supported Environments

- **Python**: 3.10, 3.11, 3.12, 3.13, 3.14
- **CUBRID**: 10.2, 11.0, 11.2, 11.4
- **SQLAlchemy**: 2.0–2.1 (`>=2.0,<2.2`)
- **Alembic**: >=1.7

### Known Limitations

- `RETURNING` clauses not supported (CUBRID limitation)
- No `Sequence` support (CUBRID uses `AUTO_INCREMENT`)
- Native `BOOLEAN` not available (mapped to `SMALLINT`)
- Lateral joins and writable CTEs not supported
- `RELEASE SAVEPOINT` is a no-op

### Fixed
- `visit_join` signature: added missing `from_linter` parameter to match SQLAlchemy base class
- `sqlalchemy.sql.util.warn`: replaced with correct `sqlalchemy.util.warn` API

### Added
- Full type annotations across all 8 source modules (mypy errors: 280 → 0)
- Compatibility Matrix in README (Python, CUBRID, SQLAlchemy, Alembic versions)

### Changed
- Development Status classifier updated from "Beta" to "Production/Stable"
- pycubrid optional dependency updated from `>=0.6.0` to `>=1.0,<2.0`
- All documentation updated to explicitly state "SQLAlchemy 2.0–2.1" support
- Version bumped to 1.0.0

## [0.8.0] - 2026-04-04

### Added
- `docs/SUPPORT_MATRIX.md`: Comprehensive support matrix documenting SQLAlchemy versions,
  Python versions, CUBRID versions, driver compatibility, feature support, type mappings,
  and known limitations — defines the 1.0 support boundary
- Documents private SQLAlchemy API usages that require the `<2.2` version pin
- Clarified public documentation to state SQLAlchemy 2.0–2.1 support explicitly

### Changed
- **pycubrid dependency**: Pin optional `pycubrid` dependency to `>=0.6.0` — required for
  tuple-based `fetchall()` return type introduced in pycubrid v0.6.0 (#72)
- Version bumped to 0.8.0 (stabilization release on path to 1.0)

## [0.7.1] - 2026-03-13

### Fixed
- **`visit_utc_timestamp_func`**: Compile `func.utc_timestamp()` to `UTC_TIMESTAMP()` instead of `UTC_TIME()`, returning a full datetime value instead of time-only (#53).
- **`get_indexes()`**: Fix PK index filtering — read `is_primary_key` from column 0 of the single-column query result instead of unreachable column 6, so primary-key indexes are properly excluded (#54).
- **`has_table()`**: Recognize views as existing objects by accepting `class_type IN ('CLASS', 'VCLASS')` instead of only `'CLASS'` (#55).


## [0.7.0] - 2026-03-12

### Added
- **pycubrid dialect variant**: New `PyCubridDialect` class (`cubrid+pycubrid://` URL scheme)
  for using the [pycubrid](https://github.com/sqlalchemy-cubrid/pycubrid) pure Python DB-API 2.0
  driver. Subclasses `CubridDialect` — inherits all SQL compilation, type mapping, and schema
  reflection. Overrides only driver-specific methods: `import_dbapi()`, `create_connect_args()`,
  `on_connect()`, `do_ping()`.
- **`PyCubridExecutionContext`**: Execution context that uses pycubrid's native `cursor.lastrowid`
  (returns `int | None` directly) with SQL `LAST_INSERT_ID()` fallback.
- **`cubrid.pycubrid` entry point**: Registered in `pyproject.toml` so SQLAlchemy auto-discovers
  the pycubrid dialect via `create_engine("cubrid+pycubrid://...")`.
- **`pycubrid` optional dependency**: `pip install "sqlalchemy-cubrid[pycubrid]"` installs pycubrid.
- **30 new offline tests**: `test/test_pycubrid_dialect.py` covering driver basics, connect args,
  on_connect, do_ping, execution context, entry point registration, isolation levels, and
  misc methods.
- **Documentation**: Updated `docs/CONNECTION.md` and `README.md` with pycubrid driver information.

### Changed
- Version bumped to 0.7.0.


## [0.6.0] - 2026-03-12

### Added
- **`MONETARY` type class**: New `TypeEngine` subclass for CUBRID's monetary data type.
  Stores monetary values with currency — internally represented as DOUBLE with currency code.
- **`OBJECT` type class**: New `TypeEngine` subclass for CUBRID's OID reference type.
  Represents a reference to another CUBRID class instance.
- **Alembic autogenerate support**: `CubridImpl` now implements `render_type()` and
  `compare_type()` for CUBRID collection types (SET, MULTISET, SEQUENCE).
  Collection type comparison uses semantic equality (unordered for SET/MULTISET,
  ordered for SEQUENCE). CUBRID type imports are auto-added to migration scripts.
- **`merge()` factory function docstring**: Comprehensive docstring documenting all
  chaining methods (`.using()`, `.on()`, `.when_matched_then_update()`,
  `.when_not_matched_then_insert()`) with usage examples.
- **GitHub issue templates**: Bug report and feature request forms (`.github/ISSUE_TEMPLATE/`).
- **ORM Cookbook**: `docs/ORM_COOKBOOK.md` — practical ORM usage examples with CUBRID-specific
  patterns, collection types, DML extensions, and gotchas.
- **10 new offline tests**: MONETARY/OBJECT type tests (4), Alembic autogenerate tests (6).
  Total: 396 offline tests, 99.45% coverage.

### Changed
- `alembic_impl.py`: Expanded from 69 lines to 141 lines with full autogenerate support.
- `types.py`: Added MONETARY and OBJECT classes (319 → 349 lines).
- `__init__.py`: Exported MONETARY and OBJECT types.
- Version bumped to 0.6.0.

### Investigated (Blocked)
- **SQLAlchemy 2.1 compatibility**: SA 2.1 does not exist yet (latest: 2.0.48).
  All 396 tests pass with SA 2.0.48 — readiness confirmed.
- **Async DBAPI support**: CUBRID Python driver has no async support — blocked.


## [0.5.0] - 2026-03-12

### Added
- **`REPLACE INTO` statement**: New `Replace` DML construct and `replace()` factory function.
  `replace(table).values(...)` generates `REPLACE INTO table (...) VALUES (...)` syntax.
  Exported from `sqlalchemy_cubrid` top-level package.
- **ODKU with subquery values**: `on_duplicate_key_update()` now accepts subquery and
  expression values (e.g., `val=(select(func.max(t.c.val)))`).
  Note: CUBRID does not support the `VALUES()` function in ODKU — use literal/subquery values.
- **Recursive CTE support**: Verified `WITH RECURSIVE` works in CUBRID 11.x+.
  SQLAlchemy's base compiler generates correct syntax — 3 offline tests added.
- **Query trace utility**: New `trace_query(connection, statement)` function in `trace.py`.
  Uses CUBRID's `SET TRACE ON` / `SHOW TRACE` mechanism instead of standard `EXPLAIN`.
  Exported from `sqlalchemy_cubrid` top-level package.
- **Integration tests**: `REPLACE INTO`, recursive CTE, and `trace_query()` integration
  tests against live CUBRID Docker instance.
- **21 new offline tests**: `TestReplaceCompilation` (7), `TestRecursiveCTECompilation` (3),
  ODKU subquery tests (2), `test_trace.py` (7), ODKU expression test (1), ODKU literal test (1).

### Investigated (Not Supported)
- **Lateral joins**: CUBRID does not support `LATERAL` subqueries — syntax error in 11.2.
- **Full-text search**: CUBRID has no `MATCH … AGAINST` syntax or full-text index support.

### Changed
- `docs/FEATURE_SUPPORT.md`: Added recursive CTE, lateral joins, full-text search, query trace,
  and REPLACE INTO rows. Updated Known Limitations & Roadmap section.
- `docs/DML_EXTENSIONS.md`: Added REPLACE INTO, ODKU subquery values, and Query Trace sections.
- Version bumped to 0.5.0.


## [0.4.0] - 2026-03-12

### Added
- **Error code mapping**: `is_disconnect()` detects dropped connections via string-based message
  matching (14 patterns) and numeric CUBRID CCI error codes (-21003, -21005, -10005, -10007).
- **`_extract_error_code()`**: Extracts numeric error codes from CUBRID DBAPI exceptions
  (supports both integer args and string-embedded codes like "-21003 message").
- **`do_ping()`**: Connection liveness check using CUBRID Python driver's native `ping()`
  method — enables SQLAlchemy's `pool_pre_ping` feature.
- **Connection pool tuning guide**: `docs/CONNECTION.md` expanded with pool configuration
  recommendations (`pool_size`, `pool_recycle`, `pool_pre_ping`), CUBRID broker timeout
  interaction, disconnect detection, and error code mapping documentation.
- **CUBRID-Python driver compatibility matrix**: `docs/DRIVER_COMPAT.md` documenting tested
  driver versions, CUBRID server compatibility, and known issues.
- **Python 3.14 support**: Added to CI matrix and `pyproject.toml` classifiers.
- **44 new offline tests**: Comprehensive coverage for `is_disconnect()` (14 message patterns,
  4 error codes, edge cases), `_extract_error_code()` (7 tests), `do_ping()` (2 tests),
  `postfetch_lastrowid` validation (5 tests), and disconnect message integrity (3 tests).

### Changed
- CI integration test matrix expanded: Python {3.10, 3.12, 3.14} × CUBRID {11.4, 11.2, 11.0, 10.2}.
- `pyproject.toml`: Added `Programming Language :: Python :: 3.14` classifier.


## [0.3.2] - 2026-03-12

### Added
- `docs/CONNECTION.md`: Connection guide — URL format, driver setup, troubleshooting.
- `docs/TYPES.md`: Type mapping reference — standard types, CUBRID-specific types, collection types, boolean handling.
- `docs/ISOLATION_LEVELS.md`: Isolation level guide — all 6 CUBRID levels, dual-granularity model, configuration.
- `docs/DML_EXTENSIONS.md`: DML extensions reference — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE, FOR UPDATE, index hints.
- `docs/ALEMBIC.md`: Alembic migration guide — setup, configuration, limitations, batch workarounds.
- `docs/DEVELOPMENT.md`: Development guide — setup, testing, Docker, coverage, CI/CD pipeline.

### Changed
- `README.md`: Rewritten as a concise landing page (~80 lines); all detailed content moved to `docs/` files.
- `docs/source/index.rst`: Added links to all new documentation files.
- `docs/FEATURE_SUPPORT.md`: Updated version reference from v0.3.0 to v0.3.2.


## [0.3.1] - 2026-03-12

### Fixed
- README: Fixed lint badge referencing deleted `pre-commit.yml` workflow — now points to `ci.yml`.
- SECURITY.md: Added v0.2.x and v0.3.x to supported versions table.
- `docs/source/index.rst`: Replaced Sphinx quickstart boilerplate with proper project documentation.
- `docs/source/conf.py`: Updated version to 0.3.0, added `viewcode` and `intersphinx` extensions.
- `docs/source/sqlalchemy_cubrid.rst`: Added `dml` and `alembic_impl` module autodoc sections.
- `samples/create_engine.py`: Modernized to SA 2.0 API (`text()`, context manager).
- `samples/cubrid_datatypes.py`: Modernized to SA 2.0 API (`metadata.create_all`, CUBRID types).
- `samples/env.sample`: Replaced hardcoded external IP with `localhost`.

### Removed
- Removed legacy files superseded by `pyproject.toml`: `setup.py`, `setup.cfg`, `CHANGES.rst`, `requirements.txt`, `requirements-dev.txt`, `install_cubrid_python.sh`.
- Removed duplicate `pre-commit.yml` GitHub Actions workflow (functionality covered by `ci.yml`).
## [0.3.0] - 2026-03-12

### Added
- Alembic migration support via `CubridImpl` (`alembic.ddl` entry-point).
  Install with `pip install sqlalchemy-cubrid[alembic]`.
- `test/test_alembic.py`: 8 tests covering import, registry, entry-point, and import-error scenarios.

### Changed
- Edge-case tests added for compiler.py, dml.py, and dialect.py — coverage raised from 97% to 99% (306 → 314 tests).
- `docs/FEATURE_SUPPORT.md`: Alembic row updated from ❌ to ✅.

## [0.2.0] - 2026-03-12

### Added
- `FOR UPDATE` clause support (`SELECT … FOR UPDATE [OF col1, col2]`).
- `INSERT … DEFAULT VALUES` and empty INSERT support.
- Window functions (`ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `LAG`, `LEAD`, etc.) with `OVER()` clause.
- `NULLS FIRST` / `NULLS LAST` ordering in ORDER BY.
- Table and column `COMMENT` support — inline DDL, `ALTER` statements, and schema reflection.
- `IF NOT EXISTS` / `IF EXISTS` DDL support for `CREATE TABLE` and `DROP TABLE`.
- `ON DUPLICATE KEY UPDATE` via CUBRID-specific `sqlalchemy_cubrid.insert()` construct (MySQL-compatible syntax).
- `MERGE` statement via `sqlalchemy_cubrid.merge()` with full `WHEN MATCHED` / `WHEN NOT MATCHED` clause support.
- `GROUP_CONCAT` aggregate function compilation.
- `TRUNCATE TABLE` autocommit detection.
- Index hint documentation (`USING INDEX`, `USE INDEX`, `FORCE INDEX`, `IGNORE INDEX` via SQLAlchemy’s built-in `with_hint()` / `suffix_with()`).
- `docs/FEATURE_SUPPORT.md`: Comprehensive feature support matrix updated with all new capabilities.

## [0.1.0] - 2026-03-12

### Changed
- **BREAKING**: Minimum Python version raised from 3.6 to 3.10.
- **BREAKING**: Minimum SQLAlchemy version raised from 1.3 to 2.0.
- Complete rewrite of all dialect modules for SQLAlchemy 2.0 compatibility.
- Modernized project infrastructure (`pyproject.toml`, ruff linting, GitHub Actions CI).

### Fixed
- `compiler.py`: Fixed `visit_cast` missing space before `AS` keyword (`CAST(exprAS type)` → `CAST(expr AS type)`).
- `compiler.py`: Fixed `visit_CHAR` missing closing parenthesis.
- `compiler.py`: Fixed `visit_list` using Python 2 `basestring` — crashes on Python 3.
- `compiler.py`: Fixed `limit_clause` using `sql.literal()` without importing `sql` module.
- `compiler.py`: Fixed `limit_clause` for SA 2.0 (`_limit_clause` / `_offset_clause` are now ClauseElements).
- `types.py`: Fixed `REAL.__init__` calling `super(FLOAT, self)` instead of `super(REAL, self)`.
- `types.py`: Fixed `_StringType.__repr__` using `inspect.getargspec` removed in Python 3.11+.
- `dialect.py`: Fixed `get_pk_constraint` using string literal instead of f-string and missing `text()`.
- `dialect.py`: Fixed `get_indexes` shadowing outer `result` variable inside loop.
- `dialect.py`: Fixed `has_table` SQL injection via f-string interpolation — now uses parameterized query.
- `dialect.py`: Fixed `get_foreign_keys` empty stub — now queries `db_constraint` system table.
- `dialect.py`: Fixed `postfetch_lastrowid = False` → `True` so SA can retrieve auto-generated keys.
- `dialect.py`: Fixed CUBRID driver defaulting to `autocommit=True` — `on_connect()` now calls `conn.set_autocommit(False)`.
- `dialect.py`: Removed unused `from cmd import IDENTCHARS` import.
- `base.py`: Implemented `CubridExecutionContext.get_lastrowid()` using `conn.get_last_insert_id()` with `SELECT LAST_INSERT_ID()` fallback.
- All files: Modernized `super(ClassName, self).__init__()` to `super().__init__()`.

### Added
- `dialect.py`: `import_dbapi()` classmethod (SA 2.0 API).
- `dialect.py`: `supports_statement_cache = True` for SA 2.0 query caching.
- `dialect.py`: `supports_comments`, `supports_is_distinct_from`, `insert_returning`, `update_returning`, `delete_returning` flags.
- `dialect.py`: `get_schema_names()`, `get_table_comment()`, `get_check_constraints()`, `has_sequence()` methods.
- `dialect.py`: `get_unique_constraints()` now queries `db_constraint` system table.
- `dialect.py`: `get_isolation_level_values()` method (SA 2.0 API).
- `dialect.py`: `do_release_savepoint()` no-op override — CUBRID does not support `RELEASE SAVEPOINT`.
- `compiler.py`: `CubridDDLCompiler.get_column_specification()` for proper `AUTO_INCREMENT` DDL emission.
- `requirements.py`: Comprehensive SA 2.0 test requirement flags (40+ properties), including binary, LOB, identifier quoting, and FOR UPDATE skip markers.
- `test/test_compiler.py`: 70 offline SQL compilation tests.
- `test/test_types.py`: 48 offline type system tests.
- `test/test_requirements.py`: 46 parametrized requirement flag tests.
- `test/test_dialect_offline.py`: 24 offline dialect tests (reflection, connection, isolation, savepoint).
- `test/test_base.py`: 15 base module tests.
- `test/test_integration.py`: 20 integration tests against live CUBRID Docker instances.
- `.github/workflows/ci.yml`: Full CI/CD pipeline with Python × CUBRID version matrix.
- `CHANGELOG.md`: This file.
- `docs/PRD.md`: Product requirements document.
- `docs/FEATURE_SUPPORT.md`: Feature-by-feature comparison with MySQL, PostgreSQL, and SQLite.

### Removed
- `.pre-commit-config.yaml`: Replaced by ruff configuration in `pyproject.toml`.

## [0.0.1] - 2022-01-01

### Added
- Initial release with basic CUBRID dialect for SQLAlchemy 1.3.
