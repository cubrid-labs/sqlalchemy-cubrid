# Roadmap

> **Last updated**: 2026-03-20
>
> This roadmap reflects current priorities. For the ecosystem-wide view, see the
> [CUBRID Labs Ecosystem Roadmap](https://github.com/cubrid-labs/.github/blob/main/ROADMAP.md).

## Links

- 📋 [GitHub Milestones](https://github.com/cubrid-labs/sqlalchemy-cubrid/milestones)
- 🗂️ [Org Project Board](https://github.com/orgs/cubrid-labs/projects/2)
- 🌐 [Ecosystem Roadmap](https://github.com/cubrid-labs/.github/blob/main/ROADMAP.md)

## Current Release Line — v1.4.x Beta — Stabilization & Polish

- Documentation accuracy and consistency across README / docs / AI-facing project files
- Continued SQLAlchemy 2.0–2.1 hardening while preparing for SA 2.2 validation
- Reflection/autogenerate polish and benchmark-driven performance tuning

## Next Minor — v1.5.x — Performance & Ecosystem

- Performance profiling and benchmark integration
- Ecosystem examples and cookbook expansion
- SQLAlchemy 2.2 readiness investigation

## Compatibility

Python 3.10+, SQLAlchemy 2.0–2.1, CUBRID 10.2–11.4

## Completed

### Async Dialect Support
- `cubrid+aiopycubrid://` URL scheme via `PyCubridAsyncDialect`
- Full `create_async_engine` / `AsyncSession` support
- Requires pycubrid >= 1.2.0,<2.0 with async module

### JSON Type Support
- Native JSON type with `JSON_EXTRACT`-based path expressions
- `col["key"]` and `col[("a", "b")]` indexing compiled to CUBRID SQL
- Full colspecs/ischema_names integration for reflection
