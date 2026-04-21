sqlalchemy-cubrid
==================

CUBRID dialect for SQLAlchemy 2.0+.

This package provides a full-featured SQLAlchemy dialect for the `CUBRID <https://www.cubrid.org/>`_
relational database. It supports SQL compilation, type mapping, schema reflection,
DDL generation, DML extensions (``ON DUPLICATE KEY UPDATE``, ``MERGE``),
window functions, Alembic migrations, and more.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   sqlalchemy_cubrid


Quick Start
^^^^^^^^^^^

Install::

   pip install sqlalchemy-cubrid

Usage:

.. code-block:: python

   from sqlalchemy import create_engine, text

   engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

   with engine.connect() as conn:
       result = conn.execute(text("SELECT 1"))
       print(result.scalar())


Documentation
^^^^^^^^^^^^^

- `Connection Guide <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/CONNECTION.md>`_ — Connection strings, URL format, driver setup
- `Type Mapping <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/TYPES.md>`_ — Full type mapping, CUBRID-specific types, collection types
- `DML Extensions <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/DML_EXTENSIONS.md>`_ — ON DUPLICATE KEY UPDATE, MERGE, GROUP_CONCAT, TRUNCATE
- `Isolation Levels <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ISOLATION_LEVELS.md>`_ — All 6 CUBRID isolation levels, configuration
- `Alembic Migrations <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/ALEMBIC.md>`_ — Setup, configuration, limitations, workarounds
- `Feature Support Matrix <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/FEATURE_SUPPORT.md>`_ — Comparison with MySQL, PostgreSQL, SQLite
- `Development Guide <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/docs/DEVELOPMENT.md>`_ — Dev setup, testing, Docker, CI/CD


Links
^^^^^

- `GitHub Repository <https://github.com/cubrid-lab/sqlalchemy-cubrid>`_
- `Changelog <https://github.com/cubrid-lab/sqlalchemy-cubrid/blob/main/CHANGELOG.md>`_
- `CUBRID Documentation <https://www.cubrid.org/manual/en/11.2/>`_


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
