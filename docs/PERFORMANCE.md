# Performance Guide

This guide covers observed performance for `sqlalchemy-cubrid` and practical optimization patterns.

---

## Table of Contents

- [Overview](#overview)
- [Benchmark Results](#benchmark-results)
- [Performance Characteristics](#performance-characteristics)
- [Optimization Tips](#optimization-tips)
- [Running Benchmarks](#running-benchmarks)

---

## Overview

`sqlalchemy-cubrid` adds SQLAlchemy Core/ORM behavior on top of the CUBRID Python driver.

```mermaid
flowchart LR
    App[Application / ORM Models] --> SA[SQLAlchemy Core / ORM]
    SA --> Dialect[sqlalchemy-cubrid Dialect]
    Dialect --> Driver[pycubrid DBAPI]
    Driver --> CAS[CAS Binary Protocol]
    CAS --> Server[(CUBRID Server)]
```

```mermaid
flowchart TD
    Query[ORM Query] --> Compile[SQL compilation]
    Compile --> Bind[Parameter binding]
    Bind --> Execute[DBAPI execute]
    Execute --> Fetch[Row fetch + object materialization]
    Fetch --> AppOut[Application objects]
```

---

## Benchmark Results

Source: [cubrid-benchmark](https://github.com/cubrid-labs/cubrid-benchmark)

Environment: Intel Core i5-9400F @ 2.90GHz, 6 cores, Linux x86_64, Docker containers.

Baseline driver workload: Python `pycubrid` vs `PyMySQL`, 10000 rows x 5 rounds.

| Scenario | CUBRID (pycubrid baseline) | MySQL (PyMySQL) | Ratio (CUBRID/MySQL) |
|---|---:|---:|---:|
| insert_sequential | 10.47s | 1.74s | 6.0x |
| select_by_pk | 15.99s | 3.52s | 4.5x |
| select_full_scan | 10.31s | 1.86s | 5.5x |
| update_indexed | 10.70s | 2.19s | 4.9x |
| delete_sequential | 10.75s | 2.10s | 5.1x |

Note: SQLAlchemy adds extra overhead for SQL compilation, ORM identity mapping, and object creation.

---

## Performance Characteristics

- The dialect inherits `pycubrid` transport behavior and CAS protocol costs.
- Core query compilation is fast but non-zero; repeated dynamic SQL can accumulate overhead.
- ORM paths add identity map and model materialization costs compared to raw DBAPI usage.
- Pool configuration strongly impacts latency under concurrency.
- Bulk APIs and Core statements generally outperform row-by-row ORM unit-of-work patterns.

---

## Optimization Tips

- Configure pooling explicitly (example: `pool_size`, `max_overflow`, `pool_pre_ping=True`).
- Use SQLAlchemy Core for high-volume bulk writes and large read pipelines.
- Use `executemany`-friendly patterns for insert/update bursts.
- Keep transactions explicit and avoid autocommit-style tiny transactions.
- Limit ORM object hydration when only scalar/tuple output is needed.

```mermaid
flowchart TD
    Start[Performance tuning] --> Pool{Pool saturated?}
    Pool -->|Yes| TunePool[Increase pool_size / max_overflow]
    Pool -->|No| ORM{Heavy ORM hydration?}
    ORM -->|Yes| CorePath[Switch hot path to Core statements]
    ORM -->|No| Batch{Batch operations possible?}
    Batch -->|Yes| Bulk[Use bulk operations / executemany]
    Batch -->|No| IndexCheck[Validate SQL plans and indexes]
```

---

## Running Benchmarks

1. Clone: `git clone https://github.com/cubrid-labs/cubrid-benchmark`.
2. Start the benchmark database containers per the benchmark documentation.
3. Run the Python benchmark suite to establish DBAPI baseline metrics.
4. Run SQLAlchemy-specific scenarios on the same host and dataset shape.
5. Compare driver baseline vs ORM/Core runs to isolate framework overhead.

Use the benchmark repository documentation for the exact command set and runner scripts.
