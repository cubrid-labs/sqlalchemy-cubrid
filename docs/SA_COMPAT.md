# SQLAlchemy Private API Compatibility

This document inventories all SQLAlchemy internal/private API usages in
sqlalchemy-cubrid and outlines the plan for SA 2.2 compatibility.

## Why `sqlalchemy>=2.0,<2.2`?

sqlalchemy-cubrid depends on three SQLAlchemy compiler internals:
`_for_update_arg`, `_limit_clause`, and `_offset_clause`.
Earlier private dependencies for literal detection and typed bind recreation
have already been moved behind local helpers in `_compat.py`. The remaining
three attributes still have no stable public alternative as of the current
SQLAlchemy documentation. Therefore, SQLAlchemy 2.2+ compatibility is not
guaranteed without separate verification, and a conservative `<2.2` upper
bound is maintained.

## Private API Inventory

| API | File | Lines | Purpose |
|-----|------|-------|---------|
| `select._for_update_arg` | `compiler.py` | 93 | Access FOR UPDATE clause metadata (columns list for `OF`) |
| `select._limit_clause` | `compiler.py` | 104 | Get the LIMIT ClauseElement for custom CUBRID LIMIT syntax |
| `select._offset_clause` | `compiler.py` | 105 | Get the OFFSET ClauseElement for custom CUBRID LIMIT syntax |

## Detail

### `select._for_update_arg`

**What it does**: Returns the `ForUpdateArg` object containing the FOR UPDATE
options (columns, nowait, etc.).

**Why we use it**: CUBRID's FOR UPDATE supports `OF col1, col2` syntax, but
the public `Select.for_update` property only returns a boolean.  We need the
`.of` attribute to render column-specific locking.

**Risk**: Medium — this attribute has been stable across SA 2.0.x.

**Public alternative**: None known.  Other dialects (MySQL, Oracle) use the
same private attribute.

### `select._limit_clause` / `select._offset_clause`

**What they do**: Return the LIMIT and OFFSET as `ClauseElement` objects
(not raw ints, since SA 2.0).

**Why we use them**: CUBRID uses `LIMIT offset, count` syntax (offset-first),
which differs from standard `LIMIT count OFFSET offset`.  The base compiler's
`limit_clause()` doesn't support this order.

**Risk**: Medium — changed from int to ClauseElement in SA 2.0, but stable
since.

**Public alternative**: None.  This is the standard approach for dialects with
custom LIMIT syntax.

### Local compatibility helpers already removed from direct SA-private access

`is_literal_value()` and `bind_with_type()` now live in `_compat.py` and use
local logic / public constructors instead of calling private SQLAlchemy helpers
directly. They are still part of the compatibility story, but no longer count
as direct private API dependencies.

## SA 2.2 Readiness Plan

### Phase 1: Monitor (current)
- Track SA 2.2 pre-release changelogs for breaking changes
- Document current private API usage (this document)

### Phase 2: CI canary
- Add a tox environment that installs `sqlalchemy>=2.2.0a1` (allow failures)
- Run offline tests to detect breakage early

### Phase 3: Replace
- `_for_update_arg`, `_limit_clause`, `_offset_clause` → wait for public
  alternatives or match other dialects' approach to SA 2.2

### Phase 4: Release
- Remove upper pin: `sqlalchemy>=2.0`
- Update compatibility matrix and README
