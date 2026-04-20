#!/usr/bin/env python3
"""Check Alembic revisions for multiple DDL operations (advisory).

Warns when a single revision contains multiple DDL calls, which is risky
with CUBRID's non-transactional DDL.

Usage:
    python scripts/alembic_safety_check.py alembic/versions/

Exit codes:
    0 — all revisions are safe (single DDL per function)
    0 — warnings found (advisory only, does not fail CI)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DDL_CALLS = {
    "create_table",
    "drop_table",
    "add_column",
    "drop_column",
    "create_index",
    "drop_index",
    "alter_column",
    "add_constraint",
    "drop_constraint",
}


def check_revision(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    warnings: list[str] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef) or func.name not in ("upgrade", "downgrade"):
            continue
        ddl_count = sum(
            1
            for node in ast.walk(func)
            if isinstance(node, ast.Attribute) and node.attr in DDL_CALLS
        )
        if ddl_count > 1:
            warnings.append(
                f"{path.name}:{func.name}() has {ddl_count} DDL operations "
                f"(recommended: 1 per revision for CUBRID)"
            )
    return warnings


def main() -> None:
    versions_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("alembic/versions")
    if not versions_dir.is_dir():
        print(f"Directory not found: {versions_dir}")
        sys.exit(1)

    all_warnings: list[str] = []
    for py_file in sorted(versions_dir.glob("*.py")):
        all_warnings.extend(check_revision(py_file))

    if all_warnings:
        print("\u26a0\ufe0f  Alembic safety warnings (advisory):")
        for w in all_warnings:
            print(f"  \u2022 {w}")
        print(f"\nTotal: {len(all_warnings)} warning(s)")
        print("Tip: Split multi-DDL revisions to avoid partial migration state.")
    else:
        print("\u2713 All revisions have single DDL operations per function.")


if __name__ == "__main__":
    main()
