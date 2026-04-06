# Architecture

## Design Objectives
sqlalchemy-cubrid is designed to provide a robust, modern interface between SQLAlchemy and the CUBRID database. Its core design goals include:

*   Full SQLAlchemy 2.0 dialect implementation
*   Dual-driver support (C-extension CUBRIDdb + pure Python pycubrid)
*   Schema reflection (tables, columns, constraints, indexes, comments)
*   Custom DML extensions (ON DUPLICATE KEY UPDATE, MERGE, REPLACE)
*   Alembic migration support
*   PEP 561 typed

## High-Level Flow

### Phase 1: Engine Creation & Connection
This phase covers how SQLAlchemy discovers the CUBRID dialect and establishes a physical connection to the CUBRID Server.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy
    participant Registry as Dialect Registry
    participant Dialect as CubridDialect
    participant Driver as pycubrid / CUBRIDdb
    participant DB as CUBRID Server

    App->>SA: create_engine("cubrid+pycubrid://dba@host:33000/testdb")
    rect rgb(230, 245, 255)
      note over SA, Registry: Phase 1 — Dialect Discovery
      SA->>Registry: Lookup "cubrid.pycubrid" entry point
      Registry-->>SA: PyCubridDialect class
      SA->>Dialect: Instantiate dialect
      Dialect->>Driver: import_dbapi() → import pycubrid
    end
    
    App->>SA: engine.connect()
    rect rgb(230, 255, 230)
      note over SA, DB: Phase 2 — Physical Connection
      SA->>Dialect: create_connect_args(url)
      Dialect-->>SA: (host, port, database, user, password)
      SA->>Driver: pycubrid.connect(host, port, database, user, password)
      Driver->>DB: CAS handshake + OpenDatabase
      DB-->>Driver: Session established
      Driver-->>SA: Connection object
      Dialect->>Driver: on_connect() → set autocommit=False
    end
    SA-->>App: Connection
```

### Phase 2: SQL Compilation
This phase describes the transformation of SQLAlchemy Expression Language constructs into CUBRID-compatible SQL strings and their subsequent execution.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy Core
    participant Compiler as CubridSQLCompiler
    participant TypeCompiler as CubridTypeCompiler
    participant Driver as pycubrid
    participant CAS as CAS Process
    
    App->>SA: conn.execute(select(users).where(users.c.id == 1))
    rect rgb(255, 245, 230)
      note over SA, TypeCompiler: SQL Compilation
      SA->>Compiler: process(select_statement)
      Compiler->>Compiler: visit_select() → column clause
      Compiler->>Compiler: limit_clause() → LIMIT/OFFSET (no FETCH FIRST)
      Compiler->>Compiler: for_update_clause()
      Compiler->>TypeCompiler: process column types
      TypeCompiler-->>Compiler: CUBRID SQL type strings
      Compiler-->>SA: "SELECT users.id, ... FROM users WHERE users.id = ?"
    end
    rect rgb(230, 255, 230)
      note over SA, CAS: Execution
      SA->>Driver: cursor.execute(sql, params)
      Driver->>CAS: PrepareAndExecute packet
      CAS-->>Driver: Result rows
      Driver-->>SA: DB-API cursor with results
    end
    SA-->>App: CursorResult
```

## Schema Reflection
The reflection process allows SQLAlchemy to inspect an existing CUBRID database and reconstruct Table objects automatically.

```mermaid
sequenceDiagram
    participant App
    participant SA as SQLAlchemy
    participant Dialect as CubridDialect
    participant CAS as CAS Process
    
    App->>SA: metadata.reflect(engine)
    SA->>Dialect: get_table_names(connection)
    Dialect->>CAS: SHOW TABLES
    CAS-->>Dialect: Table list
    
    loop For each table
      SA->>Dialect: get_columns(connection, table_name)
      Dialect->>CAS: SHOW COLUMNS IN "table_name"
      CAS-->>Dialect: Column definitions
      
      SA->>Dialect: get_pk_constraint(connection, table_name)
      Dialect->>CAS: SHOW INDEX IN "table_name" (filter PRIMARY)
      CAS-->>Dialect: PK constraint info
      
      SA->>Dialect: get_foreign_keys(connection, table_name)
      Dialect->>CAS: SELECT from db_constraint
      CAS-->>Dialect: FK constraints
      
      SA->>Dialect: get_indexes(connection, table_name)
      Dialect->>CAS: SHOW INDEX IN "table_name"
      CAS-->>Dialect: Index definitions
    end
    
    SA-->>App: MetaData with reflected tables
```

## Module Boundaries
The package is organized into specialized modules, each handling a specific aspect of the dialect's functionality.

```mermaid
flowchart TD
    init["__init__.py<br/>Public API: types, insert(), merge()"]
    dialect["dialect.py<br/>CubridDialect: reflection, connection, isolation"]
    pycubrid_d["pycubrid_dialect.py<br/>PyCubridDialect: pure Python variant"]
    compiler["compiler.py<br/>SQL, DDL, Type compilers"]
    base["base.py<br/>ExecutionContext, IdentifierPreparer"]
    dml["dml.py<br/>ODKU, MERGE, REPLACE constructs"]
    types["types.py<br/>CUBRID type system"]
    req["requirements.py<br/>SA test requirement flags"]
    alembic_mod["alembic_impl.py<br/>CubridImpl DDL operations"]
    
    init --> types
    init --> dml
    dialect --> base
    dialect --> compiler
    dialect --> types
    pycubrid_d --> dialect
    compiler --> types
    compiler --> base
    
    %% External dependencies
    sa["SQLAlchemy 2.0"]
    pycubrid_pkg["pycubrid (driver)"]
    alembic_pkg["Alembic"]
    
    dialect -.-> sa
    pycubrid_d -.-> pycubrid_pkg
    compiler -.-> sa
    alembic_mod -.-> alembic_pkg
    req -.-> sa
```

### Module Descriptions

#### `__init__.py`
Defines the public API boundary, exporting CUBRID-specific types and DML extensions like `insert()`, `merge()`, and `replace()`. It serves as the primary entry point for users of the dialect.

#### `dialect.py`
Contains the base `CubridDialect` class, implementing core logic for schema reflection, connection management, and transaction isolation levels. It defaults to the C-extension driver `CUBRIDdb`.

#### `pycubrid_dialect.py`
Implements the `PyCubridDialect` variant, which uses the pure Python `pycubrid` driver. It overrides connection argument parsing and connection-time initialization logic.

#### `compiler.py`
Houses the SQL, DDL, and Type compilers. It translates SQLAlchemy's abstract syntax trees into CUBRID-specific SQL dialects, handling nuances like LIMIT/OFFSET and FOR UPDATE clauses.

#### `base.py`
Provides the `CubridExecutionContext` for statement execution state and the `CubridIdentifierPreparer` for handling CUBRID's lowercase identifier folding and quoting rules.

#### `dml.py`
Defines custom DML constructs for CUBRID-specific features such as `ON DUPLICATE KEY UPDATE` (ODKU), `MERGE INTO`, and `REPLACE INTO`.

#### `types.py`
Implements the CUBRID-specific type system, mapping SQLAlchemy's generic types to CUBRID's internal types like `SET`, `MULTISET`, and `BIT`.

#### `requirements.py`
Defines feature flags used by the SQLAlchemy test suite to determine which behavioral tests should be executed against a CUBRID backend.

#### `alembic_impl.py`
Provides the `CubridImpl` class for Alembic, enabling DDL migration support and defining CUBRID's lack of transactional DDL capabilities.

## Dialect Discovery
SQLAlchemy uses entry points to discover and load the appropriate dialect class based on the provided connection URL.

```mermaid
flowchart TD
    url["Connection URL<br/>cubrid+pycubrid://dba@host:33000/db"]
    parse["SQLAlchemy URL Parser<br/>backend=cubrid, driver=pycubrid"]
    entry["Entry Point Lookup<br/>sqlalchemy.dialects → cubrid.pycubrid"]
    
    url --> parse
    parse --> entry
    
    entry -->|"cubrid://"| cubrid_dialect["CubridDialect<br/>(C-extension CUBRIDdb)"]
    entry -->|"cubrid.cubrid://"| cubrid_dialect
    entry -->|"cubrid+pycubrid://"| pycubrid_dialect["PyCubridDialect<br/>(Pure Python pycubrid)"]
    
    cubrid_dialect --> import_c["import CUBRIDdb"]
    pycubrid_dialect --> import_py["import pycubrid"]
    
    alembic_entry["Entry Point: alembic.ddl → cubrid"]
    alembic_entry --> alembic_impl["CubridImpl<br/>transactional_ddl = False"]
```

## Two-Driver Architecture
The dialect supports both the legacy C-extension driver and the modern pure Python driver through a hierarchical class structure.

```mermaid
flowchart TD
    sa_default["sqlalchemy.engine.default<br/>DefaultDialect"]
    cubrid_base["CubridDialect<br/>dialect.py<br/>• reflection<br/>• isolation levels<br/>• type mapping<br/>• import_dbapi() → CUBRIDdb"]
    pycubrid_variant["PyCubridDialect<br/>pycubrid_dialect.py<br/>• import_dbapi() → pycubrid<br/>• create_connect_args()<br/>• on_connect()<br/>• do_ping()"]
    
    sa_default --> cubrid_base
    cubrid_base --> pycubrid_variant
    
    cubrid_base -.->|"loads"| cci["CUBRIDdb<br/>(C-extension driver)"]
    pycubrid_variant -.->|"loads"| pure["pycubrid<br/>(Pure Python driver)"]
```

## Key Design Decisions

*   **SQLAlchemy < 2.2 pin**: Uses private SA APIs (`select._limit_clause`, `select._offset_clause`, `select._for_update_arg`, `coercions._is_literal`, `BindParameter._with_binary_element_type`) at compiler.py:71, 81-82, 144, 150-151 — requires version pinning until public alternatives exist.
*   **BOOLEAN → SMALLINT mapping**: CUBRID has no native BOOLEAN — dialect maps to `SMALLINT` (0/1).
*   **No JSON type mapping (yet)**: CUBRID 10.2+ supports JSON natively, but the dialect doesn't map it yet — JSON columns can still be used via raw SQL.
*   **`transactional_ddl = False`**: CUBRID auto-commits DDL statements — Alembic cannot roll back failed migrations.
*   **`supports_statement_cache = True`**: Required for SA 2.0 performance — dialect is cache-safe.
*   **Lowercase identifier folding**: CUBRID folds to lowercase (not SQL-standard uppercase) — `CubridIdentifierPreparer` handles this.
*   **No RELEASE SAVEPOINT**: CUBRID doesn't support it — `do_release_savepoint()` is a no-op.

## Public API Boundary

```python
# DML Extensions
insert()    # Insert with .on_duplicate_key_update()
merge()     # MERGE INTO ... USING ... ON ... WHEN MATCHED/NOT MATCHED
replace()   # REPLACE INTO
trace_query() # Query tracing utility

# Types (CUBRID-specific)
STRING, BIT, CLOB, BLOB, SET, MULTISET, SEQUENCE, MONETARY, OBJECT
NCHAR, NVARCHAR, DOUBLE_PRECISION, REAL

# Types (standard, re-exported)
SMALLINT, INTEGER, BIGINT, NUMERIC, DECIMAL, FLOAT, DOUBLE
CHAR, VARCHAR, DATE, TIME, TIMESTAMP, DATETIME

# Entry Points (registered via pyproject.toml)
cubrid://          → CubridDialect
cubrid.cubrid://   → CubridDialect  
cubrid+pycubrid:// → PyCubridDialect
cubrid (alembic)   → CubridImpl
```

## What This Package Owns / Does Not Own

### Owns
*   SQLAlchemy dialect for CUBRID
*   SQL compilation (SELECT/INSERT/UPDATE/DELETE with CUBRID syntax)
*   DDL compilation
*   Type mapping
*   Schema reflection
*   DML extensions (ODKU, MERGE, REPLACE)
*   Alembic DDL support
*   Identifier quoting

### Does Not Own
*   The CUBRID driver itself (use pycubrid or CUBRIDdb)
*   Connection pooling (SQLAlchemy handles this)
*   ORM model definitions (user code)
*   The CAS wire protocol (pycubrid handles this)
*   Query optimization (CUBRID server handles this)

## Related Documents
*   [Connection Guide](CONNECTION.md)
*   [Type System](TYPES.md)
*   [Isolation Levels](ISOLATION_LEVELS.md)
*   [DML Extensions](DML_EXTENSIONS.md)
*   [Alembic Guide](ALEMBIC.md)
*   [Feature Support](FEATURE_SUPPORT.md)
*   [Support Matrix](SUPPORT_MATRIX.md)
*   [Driver Compatibility](DRIVER_COMPAT.md)
