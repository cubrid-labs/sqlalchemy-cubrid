# test/test_aio_integration.py
# Copyright (C) 2021-2026 by sqlalchemy-cubrid authors and contributors
# <see AUTHORS file>
#
# This module is part of sqlalchemy-cubrid and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Async integration tests against a live CUBRID instance.

These tests require a running CUBRID database.  They are skipped
automatically when no CUBRID connection is available.

Set the environment variable ``CUBRID_TEST_URL`` to the **sync**
connection URL.  The async URL is derived automatically::

    export CUBRID_TEST_URL="cubrid://dba@localhost:33000/testdb"

The async dialect uses ``cubrid+aiopycubrid://`` as scheme.
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, MetaData, String, Table, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DEFAULT_SYNC_URL = "cubrid://dba@localhost:33000/testdb"


def _async_url() -> str:
    """Derive the async URL from the sync one."""
    sync = os.environ.get("CUBRID_TEST_URL", _DEFAULT_SYNC_URL)
    return sync.replace("cubrid://", "cubrid+aiopycubrid://", 1)


def _can_connect_async() -> bool:
    """Return True if a CUBRID instance is reachable via async."""
    try:
        engine = create_async_engine(_async_url())

        async def _probe() -> bool:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            return True

        return asyncio.get_event_loop().run_until_complete(_probe())
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(
        not _can_connect_async(),
        reason="CUBRID async instance not available (set CUBRID_TEST_URL)",
    ),
    pytest.mark.asyncio,
]


@pytest_asyncio.fixture(scope="module")
def event_loop():
    """Create a single event loop for the module."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def engine():
    eng = create_async_engine(_async_url(), echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="module")
async def metadata(engine):
    meta = MetaData()
    Table(
        "aio_test_users",
        meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("name", String(100), nullable=False),
        Column("value", Integer),
    )
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS aio_test_users"))
        await conn.run_sync(meta.create_all)
    yield meta
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS aio_test_users"))


# ---------------------------------------------------------------------------
# Phase 2: Async CRUD + Transaction
# ---------------------------------------------------------------------------


class TestAsyncCRUD:
    """Async CRUD round-trip tests."""

    async def test_connect(self, engine):
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.fetchone() == (1,)

    async def test_insert_and_select(self, engine, metadata):
        users = metadata.tables["aio_test_users"]
        async with engine.begin() as conn:
            await conn.execute(
                users.insert(),
                [{"name": "alice", "value": 10}, {"name": "bob", "value": 20}],
            )
        async with engine.connect() as conn:
            result = await conn.execute(users.select())
            rows = result.fetchall()
            assert len(rows) >= 2

    async def test_update(self, engine, metadata):
        users = metadata.tables["aio_test_users"]
        async with engine.begin() as conn:
            await conn.execute(
                users.update().where(users.c.name == "alice").values(value=100)
            )
        async with engine.connect() as conn:
            result = await conn.execute(
                users.select().where(users.c.name == "alice")
            )
            row = result.fetchone()
            assert row is not None and row.value == 100

    async def test_delete(self, engine, metadata):
        users = metadata.tables["aio_test_users"]
        async with engine.begin() as conn:
            await conn.execute(users.delete().where(users.c.name == "bob"))
        async with engine.connect() as conn:
            result = await conn.execute(
                users.select().where(users.c.name == "bob")
            )
            assert result.fetchone() is None

    async def test_transaction_rollback(self, engine, metadata):
        users = metadata.tables["aio_test_users"]
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    users.insert().values(name="will_rollback", value=999)
                )
                raise RuntimeError("force rollback")
        except RuntimeError:
            pass

        async with engine.connect() as conn:
            result = await conn.execute(
                users.select().where(users.c.name == "will_rollback")
            )
            assert result.fetchone() is None

    async def test_concurrent_pool(self, engine):
        async def worker(i: int) -> int:
            async with engine.connect() as conn:
                r = await conn.execute(text(f"SELECT {i}"))
                return r.scalar()

        results = await asyncio.gather(*[worker(i) for i in range(5)])
        assert sorted(results) == [0, 1, 2, 3, 4]

    async def test_bad_sql_raises(self, engine):
        with pytest.raises(Exception):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT * FROM nonexistent_xyz"))

    async def test_autocommit_toggle(self, engine):
        async with engine.connect() as conn:
            raw = await conn.get_raw_connection()
            raw.autocommit = True
            raw.autocommit = False


# ---------------------------------------------------------------------------
# Phase 3: JSON
# ---------------------------------------------------------------------------


class TestAsyncJSON:
    """JSON type round-trip tests."""

    @pytest_asyncio.fixture(autouse=True)
    async def _json_table(self, engine):
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS aio_test_json"))
            await conn.execute(
                text(
                    "CREATE TABLE aio_test_json ("
                    "  id INT AUTO_INCREMENT PRIMARY KEY,"
                    "  payload JSON"
                    ")"
                )
            )
        yield
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS aio_test_json"))

    async def _insert_json(self, engine, value):
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO aio_test_json (payload) VALUES (:p)"),
                {"p": json.dumps(value) if value is not None else None},
            )

    async def _last_json(self, engine):
        async with engine.connect() as conn:
            r = await conn.execute(
                text("SELECT payload FROM aio_test_json ORDER BY id DESC LIMIT 1")
            )
            raw = r.scalar()
            return json.loads(raw) if isinstance(raw, str) else raw

    async def test_dict_roundtrip(self, engine):
        d = {"key": "value", "n": 42}
        await self._insert_json(engine, d)
        assert await self._last_json(engine) == d

    async def test_list_roundtrip(self, engine):
        lst = [1, "two", 3.0, None]
        await self._insert_json(engine, lst)
        assert await self._last_json(engine) == lst

    async def test_nested_roundtrip(self, engine):
        nested = {"a": {"b": [1, {"c": True}]}}
        await self._insert_json(engine, nested)
        assert await self._last_json(engine) == nested

    async def test_null_json(self, engine):
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO aio_test_json (payload) VALUES (NULL)")
            )
        assert await self._last_json(engine) is None

    async def test_empty_object(self, engine):
        await self._insert_json(engine, {})
        assert await self._last_json(engine) == {}

    async def test_empty_array(self, engine):
        await self._insert_json(engine, [])
        assert await self._last_json(engine) == []

    async def test_json_extract(self, engine):
        async with engine.connect() as conn:
            r = await conn.execute(
                text("SELECT JSON_EXTRACT('{\"a\": 1}', '$.a')")
            )
            assert r.scalar() is not None

    async def test_orm_json_type(self, engine):
        from sqlalchemy_cubrid.types import JSON as CubridJSON

        meta = MetaData()
        t = Table(
            "aio_test_json_orm",
            meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("data", CubridJSON),
        )
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS aio_test_json_orm"))
            await conn.run_sync(meta.create_all)

        test_data = {"items": [1, 2, 3]}
        async with engine.begin() as conn:
            await conn.execute(t.insert().values(data=test_data))

        async with engine.connect() as conn:
            r = await conn.execute(t.select())
            row = r.fetchone()
            val = row.data
            if isinstance(val, str):
                val = json.loads(val)
            assert val == test_data

        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS aio_test_json_orm"))
