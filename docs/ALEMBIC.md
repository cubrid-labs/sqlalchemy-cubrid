# Alembic Migration Support

Guide for using [Alembic](https://alembic.sqlalchemy.org/) database migrations with the CUBRID dialect.

---

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Running Migrations](#running-migrations)
- [CUBRID-Specific Behavior](#cubrid-specific-behavior)
- [Limitations & Workarounds](#limitations--workarounds)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Installation

Install sqlalchemy-cubrid with the `alembic` extra:

```bash
pip install sqlalchemy-cubrid[alembic]
```

This pulls in Alembic ≥ 1.7 as a dependency. The CUBRID Alembic implementation
(`CubridImpl`) is registered automatically via the `alembic.ddl` entry point —
no manual configuration is needed.

> **Note**: If you install Alembic separately (`pip install alembic`), it will
> still auto-discover the CUBRID implementation as long as `sqlalchemy-cubrid`
> is installed in the same environment.

---

## Configuration

### Initialize Alembic

```bash
alembic init alembic
```

This creates an `alembic/` directory and an `alembic.ini` configuration file.

### Set the Database URL

Edit `alembic.ini`:

```ini
[alembic]
sqlalchemy.url = cubrid://dba:password@localhost:33000/demodb
```

Or set it dynamically in `alembic/env.py`:

```python
from sqlalchemy import create_engine

def run_migrations_online():
    connectable = create_engine("cubrid://dba:password@localhost:33000/demodb")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()
```

### env.py Setup

The standard Alembic `env.py` works without modification. The `CubridImpl`
class is auto-discovered when the connection URL uses the `cubrid://` scheme.

A minimal `env.py` for online migrations:

```python
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# Import your models' metadata
from myapp.models import Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

---

## Running Migrations

### Create a Migration

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "add users table"

# Create an empty migration
alembic revision -m "custom migration"
```

### Apply Migrations

```bash
# Upgrade to the latest version
alembic upgrade head

# Upgrade to a specific revision
alembic upgrade abc123

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

---

## CUBRID-Specific Behavior

### DDL Auto-Commit

CUBRID implicitly commits every DDL statement. The `CubridImpl` sets
`transactional_ddl = False`, which tells Alembic:

- **No transaction wrapping** around DDL statements
- Each `CREATE TABLE`, `ALTER TABLE`, `DROP TABLE` commits immediately
- A failed migration may leave the database in a partially-migrated state

**Implication**: If a migration with multiple DDL operations fails halfway
through, you cannot simply roll back — the earlier operations have already
been committed. Write migrations with small, atomic steps.

### Auto-Discovery

The dialect registers `CubridImpl` via the `alembic.ddl` entry point in
`pyproject.toml`:

```toml
[project.entry-points."alembic.ddl"]
cubrid = "sqlalchemy_cubrid.alembic_impl:CubridImpl"
```

When Alembic detects a `cubrid://` connection URL, it automatically loads
`CubridImpl`. No imports or configuration are required in your migration files.

### Implementation Details

```python
class CubridImpl(DefaultImpl):
    __dialect__ = "cubrid"
    transactional_ddl = False
```

The implementation inherits all standard Alembic operations from `DefaultImpl`:
- `add_column`, `drop_column`
- `add_constraint`, `drop_constraint`
- `create_table`, `drop_table`
- `create_index`, `drop_index`
- `alter_column` (with limitations — see below)
- `bulk_insert`

---

## Limitations & Workarounds

### ❌ No ALTER COLUMN TYPE

CUBRID does not support changing a column's data type:

```sql
-- This will FAIL:
ALTER TABLE users MODIFY COLUMN name BIGINT;
```

**In Alembic**, `alter_column(type_=...)` will raise an error.

**Workaround** — use `batch_alter_table` (table recreate):

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.BigInteger())
```

This creates a new table with the desired schema, copies data, drops the
original, and renames the new table.

### ❌ No RENAME COLUMN

CUBRID ≤ 11.x does not support renaming columns:

```sql
-- This will FAIL:
ALTER TABLE users RENAME COLUMN old_name TO new_name;
```

**In Alembic**, `alter_column(new_column_name=...)` will raise an error.

**Workaround** — use `batch_alter_table`:

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("old_name", new_column_name="new_name")
```

### ⚠️ DDL Auto-Commit

As noted above, DDL is auto-committed. Be aware:

- Keep migrations small (one logical change per migration)
- Test migrations against a staging database before production
- Maintain database backups before running migrations

### Summary

| Operation | Supported | Workaround |
|---|:---:|---|
| `create_table` | ✅ | — |
| `drop_table` | ✅ | — |
| `add_column` | ✅ | — |
| `drop_column` | ✅ | — |
| `alter_column` (nullable) | ✅ | — |
| `alter_column` (default) | ✅ | — |
| `alter_column` (type) | ❌ | `batch_alter_table` |
| `alter_column` (rename) | ❌ | `batch_alter_table` |
| `create_index` | ✅ | — |
| `drop_index` | ✅ | — |
| `add_constraint` | ✅ | — |
| `drop_constraint` | ✅ | — |
| `bulk_insert` | ✅ | — |
| Transactional DDL | ❌ | Small atomic migrations |

---

## Examples

### Create a Table

```python
"""create users table

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(200), unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"])


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
```

### Add a Column

```python
def upgrade():
    op.add_column("users", sa.Column("is_active", sa.SmallInteger(), server_default="1"))


def downgrade():
    op.drop_column("users", "is_active")
```

### Change Column Type (via batch)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(500))


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", type_=sa.String(100))
```

### Rename Column (via batch)

```python
def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("name", new_column_name="full_name")


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("full_name", new_column_name="name")
```

---

## Troubleshooting

### "No implementation found for dialect 'cubrid'"

**Cause**: `sqlalchemy-cubrid` is not installed, or not installed with the
`alembic` extra.

**Fix**:

```bash
pip install sqlalchemy-cubrid[alembic]
```

### "Alembic is required for migration support"

**Cause**: The `alembic_impl` module was imported directly without Alembic
installed.

**Fix**:

```bash
pip install alembic>=1.7
```

### Migration partially applied

**Cause**: A migration with multiple DDL statements failed partway through.
Because CUBRID auto-commits DDL, some statements already took effect.

**Fix**:
1. Manually inspect the database state
2. Either complete the remaining operations manually, or reverse the
   completed ones
3. Stamp the revision to the correct state: `alembic stamp <revision>`

### `alter_column` raises NotImplementedError

**Cause**: Attempting to change column type or rename column directly.

**Fix**: Use `batch_alter_table` — see [Limitations & Workarounds](#limitations--workarounds).

---

## Migration Safety Checklist

!!! warning "DDL is not transactional"
    CUBRID auto-commits DDL. A failed migration can leave partial schema changes applied.
    Prefer small revisions with one logical schema change each.

!!! warning "Type changes and rename require batch operations"
    Direct `alter_column(type_=...)` and `alter_column(new_column_name=...)` are not portable for CUBRID.
    Use `op.batch_alter_table()` with tested downgrade steps.

!!! tip "Always test upgrade + downgrade on staging"
    Validate full forward and backward migration chains before production rollout.

!!! tip "Create backups for destructive operations"
    Back up data before `drop_column`, `drop_table`, or multi-step restructuring migrations.

Recommended pre-deploy sequence:

1. `alembic upgrade head` on a staging copy.
2. Run smoke tests and critical queries.
3. `alembic downgrade -1` and `alembic upgrade head` to verify reversibility.
4. Deploy during a maintenance window for high-impact schema changes.

---

*See also: [Connection Guide](CONNECTION.md) · [Type Mapping](TYPES.md) · [Feature Support](FEATURE_SUPPORT.md)*
