# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1 dialect for the CUBRID database** — Python ORM, schema reflection, Alembic migrations, and full type system support.

[🇰🇷 한국어](docs/README.ko.md) · [🇺🇸 English](README.md) · [🇨🇳 中文](docs/README.zh.md) · [🇮🇳 हिन्दी](docs/README.hi.md) · [🇩🇪 Deutsch](docs/README.de.md) · [🇷🇺 Русский](docs/README.ru.md)

<!-- BADGES:START -->
[![PyPI version](https://img.shields.io/pypi/v/sqlalchemy-cubrid)](https://pypi.org/project/sqlalchemy-cubrid)
[![python version](https://img.shields.io/pypi/pyversions/sqlalchemy-cubrid)](https://www.python.org)
[![ci workflow](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![coverage](https://codecov.io/gh/cubrid-labs/sqlalchemy-cubrid/branch/main/graph/badge.svg)](https://codecov.io/gh/cubrid-labs/sqlalchemy-cubrid)
[![license](https://img.shields.io/github/license/cubrid-labs/sqlalchemy-cubrid)](https://github.com/cubrid-labs/sqlalchemy-cubrid/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/cubrid-labs/sqlalchemy-cubrid)](https://github.com/cubrid-labs/sqlalchemy-cubrid)
[![docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://cubrid-labs.github.io/sqlalchemy-cubrid/)
<!-- BADGES:END -->

---

## Why sqlalchemy-cubrid?

CUBRID is a high-performance open-source relational database, widely adopted in
Korean public-sector and enterprise applications. Until now, there was no
production-ready SQLAlchemy dialect that supports the modern 2.0–2.1 API.

**sqlalchemy-cubrid** bridges that gap:

- Full SQLAlchemy 2.0–2.1 dialect with **statement caching** and **PEP 561 typing**
- **426 offline tests** with **99%+ code coverage** — no database required to run them
- Tested against **4 CUBRID versions** (10.2, 11.0, 11.2, 11.4) across **Python 3.10 -- 3.14**
- CUBRID-specific DML constructs: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic migration support out of the box
- **Three driver options** — C-extension (`cubrid://`), pure Python (`cubrid+pycubrid://`), or async pure Python (`cubrid+aiopycubrid://`)

## Architecture

```mermaid
flowchart TD
    app["Application"] --> sa["SQLAlchemy Core/ORM"]
    sa --> dialect["CubridDialect"]
    dialect --> pycubrid["pycubrid driver"]
    dialect --> cext["CUBRIDdb driver"]
    dialect --> aio["pycubrid.aio async driver"]
    pycubrid --> server["CUBRID Server"]
    cext --> server
    aio --> server
```

```mermaid
flowchart TD
    expr["SQL Expression"] --> compiler["CubridSQLCompiler"] --> sql["SQL String"]
```

## Requirements

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C-extension) **or** [pycubrid](https://github.com/sqlalchemy-cubrid/pycubrid) (pure Python)

## Installation

```bash
pip install sqlalchemy-cubrid
```

With the pure Python driver (no C build needed):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

With Alembic support:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## Quick Start

### Core (Connection-Level)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (Session-Level)

```python
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)


engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
Base.metadata.create_all(engine)

with Session(engine) as session:
    user = User(name="Alice", email="alice@example.com")
    session.add(user)
    session.commit()
```

### Async

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

engine = create_async_engine("cubrid+aiopycubrid://dba:password@localhost:33000/demodb")

async with AsyncSession(engine) as session:
    result = await session.execute(text("SELECT 1"))
    print(result.scalar())
```

## Features

- Complete type system -- numeric, string, date/time, bit, LOB, and collection types
- SQL compilation -- SELECT, JOIN, CAST, LIMIT/OFFSET, subqueries, CTEs, window functions
- DML extensions -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL support -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Schema reflection -- tables, views, columns, PKs, FKs, indexes, unique constraints, comments
- Alembic migrations via `CubridImpl` (auto-discovered entry point)
- All 6 CUBRID isolation levels (dual-granularity: class-level + instance-level)
- Async support — `create_async_engine("cubrid+aiopycubrid://...")` via pycubrid.aio

## Documentation

| Guide | Description |
|---|---|
| [Connection](docs/CONNECTION.md) | Connection strings, URL format, driver setup, pool tuning |
| [Type Mapping](docs/TYPES.md) | Full type mapping, CUBRID-specific types, collection types |
| [DML Extensions](docs/DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, query trace |
| [Isolation Levels](docs/ISOLATION_LEVELS.md) | All 6 CUBRID isolation levels, configuration |
| [Alembic Migrations](docs/ALEMBIC.md) | Setup, configuration, limitations, batch workarounds |
| [Feature Support](docs/FEATURE_SUPPORT.md) | Comparison with MySQL, PostgreSQL, SQLite |
| [ORM Cookbook](docs/ORM_COOKBOOK.md) | Practical ORM examples, relationships, queries |
| [Development](docs/DEVELOPMENT.md) | Dev setup, testing, Docker, coverage, CI/CD |
| [Driver Compatibility](docs/DRIVER_COMPAT.md) | CUBRID-Python driver versions and known issues |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues, error solutions, debugging techniques |
| [Async Connection](docs/CONNECTION.md#async-connection) | Async engine setup with `cubrid+aiopycubrid://` |

## Compatibility Matrix

| Component | Supported versions |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13, 3.14 |
| CUBRID | 10.2, 11.0, 11.2, 11.4 |
| SQLAlchemy | 2.0–2.1 |
| Alembic | >=1.7 |

## FAQ

### How do I connect to CUBRID with SQLAlchemy?

```python
from sqlalchemy import create_engine
engine = create_engine("cubrid://dba:password@localhost:33000/demodb")
```

For the pure Python driver (no C build needed): `create_engine("cubrid+pycubrid://dba@localhost:33000/demodb")`

### Does sqlalchemy-cubrid support SQLAlchemy 2.0–2.1?

Yes. sqlalchemy-cubrid is built for SQLAlchemy 2.0–2.1 and supports the 2.0-style API including `Session.execute()`, typed `Mapped[]` columns, and statement caching.

### Does sqlalchemy-cubrid support Alembic migrations?

Yes. Install with `pip install "sqlalchemy-cubrid[alembic]"`. The dialect auto-registers via entry point. Note that CUBRID auto-commits DDL, so migrations are not transactional.

### What Python versions are supported?

Python 3.10, 3.11, 3.12, 3.13, and 3.14.

### Does CUBRID support RETURNING clauses?

No. CUBRID does not support `INSERT ... RETURNING` or `UPDATE ... RETURNING`. Use `cursor.lastrowid` or `SELECT LAST_INSERT_ID()` instead.

### How do I use ON DUPLICATE KEY UPDATE with CUBRID?

```python
from sqlalchemy_cubrid import insert
stmt = insert(users).values(name="Alice").on_duplicate_key_update(name="Alice Updated")
```

### What's the difference between `cubrid://` and `cubrid+pycubrid://`?

`cubrid://` uses the C-extension driver (CUBRIDdb) which requires compilation. `cubrid+pycubrid://` uses the pure Python driver which installs with pip alone — no build tools needed. `cubrid+aiopycubrid://` uses the async variant of the pure Python driver for use with `create_async_engine` and `AsyncSession`.

### Does sqlalchemy-cubrid support async?

Yes. Use `create_async_engine("cubrid+aiopycubrid://...")` with the pycubrid async driver. Requires `pycubrid>=1.1.0`. All Core and ORM features work with `AsyncSession`.


## Related Projects

- [pycubrid](https://github.com/cubrid-labs/pycubrid) — Pure Python DB-API 2.0 driver for CUBRID
- [cubrid-python-cookbook](https://github.com/cubrid-labs/cubrid-python-cookbook) — Production-ready Python examples for CUBRID

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for this project's direction and next milestones.

For the ecosystem-wide view, see the [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-labs/.github/blob/main/ROADMAP.md) and [Project Board](https://github.com/orgs/cubrid-labs/projects/2).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup.

## Security

Report vulnerabilities via email -- see [SECURITY.md](SECURITY.md). Do not open public issues for security concerns.

## License

MIT -- see [LICENSE](LICENSE).
