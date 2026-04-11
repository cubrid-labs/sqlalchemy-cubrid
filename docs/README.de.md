# sqlalchemy-cubrid

**CUBRID-Dialekt für SQLAlchemy 2.0–2.1**

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-cubrid.svg)](https://pypi.org/project/sqlalchemy-cubrid/)
[![CI](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)](https://www.sqlalchemy.org/)
[![Coverage 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](DEVELOPMENT.md#code-coverage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Warum sqlalchemy-cubrid?

CUBRID ist eine leistungsstarke relationale Open-Source-Datenbank, die in koreanischen
Behörden und Unternehmensanwendungen weit verbreitet ist. Bisher gab es keinen
produktionsreifen SQLAlchemy-Dialekt, der die moderne 2.0–2.1-API unterstützt.

**sqlalchemy-cubrid** schließt diese Lücke:

- Vollständiger SQLAlchemy 2.0–2.1 Dialekt mit **Statement-Caching** und **PEP 561 Typisierung**
- **396 Offline-Tests** mit **99,45% Codeabdeckung** — keine Datenbank zum Ausführen erforderlich
- Getestet mit **4 CUBRID-Versionen** (10.2, 11.0, 11.2, 11.4) auf **Python 3.10 -- 3.14**
- CUBRID-spezifische DML-Konstrukte: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic-Migrationsunterstützung direkt einsatzbereit

## Voraussetzungen

- Python 3.10+
- SQLAlchemy 2.0 -- 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) Treiber

## Installation

```bash
pip install sqlalchemy-cubrid
```

Mit Alembic-Unterstützung:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## Schnellstart

### Core (Verbindungsebene)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (Sitzungsebene)

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

## Funktionen

- Vollständiges Typsystem -- numerisch, Zeichenketten, Datum/Zeit, Bit, LOB und Sammlungstypen
- SQL-Kompilierung -- SELECT, JOIN, CAST, LIMIT/OFFSET, Unterabfragen, CTEs, Fensterfunktionen
- DML-Erweiterungen -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL-Unterstützung -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Schema-Reflexion -- Tabellen, Views, Spalten, PKs, FKs, Indizes, Unique-Constraints, Kommentare
- Alembic-Migrationen über `CubridImpl` (automatisch erkannter Entry-Point)
- Alle 6 CUBRID-Isolationsstufen (duale Granularität: Klassen- + Instanzebene)

## Dokumentation

| Leitfaden | Beschreibung |
|---|---|
| [Verbindung](CONNECTION.md) | Verbindungszeichenfolgen, URL-Format, Treibereinrichtung, Pool-Tuning |
| [Typzuordnung](TYPES.md) | Vollständige Typzuordnung, CUBRID-spezifische Typen, Sammlungstypen |
| [DML-Erweiterungen](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, Query-Trace |
| [Isolationsstufen](ISOLATION_LEVELS.md) | Alle 6 CUBRID-Isolationsstufen, Konfiguration |
| [Alembic-Migrationen](ALEMBIC.md) | Einrichtung, Konfiguration, Einschränkungen, Batch-Workarounds |
| [Feature-Unterstützung](FEATURE_SUPPORT.md) | Vergleich mit MySQL, PostgreSQL, SQLite |
| [ORM-Kochbuch](ORM_COOKBOOK.md) | Praktische ORM-Beispiele, Beziehungen, Abfragen |
| [Entwicklung](DEVELOPMENT.md) | Entwicklungsumgebung, Tests, Docker, Abdeckung, CI/CD |
| [Treiberkompatibilität](DRIVER_COMPAT.md) | CUBRID-Python Treiberversionen und bekannte Probleme |
| [Fehlerbehebung](TROUBLESHOOTING.md) | Häufige Probleme, Fehlerlösungen, Debugging-Techniken |

## Kompatibilität

| | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|:---:|:---:|:---:|:---:|
| **Offline-Tests** | ✅ | ✅ | ✅ | ✅ |
| **CUBRID 11.4** | ✅ | -- | ✅ | -- |
| **CUBRID 11.2** | ✅ | -- | ✅ | -- |
| **CUBRID 11.0** | ✅ | -- | ✅ | -- |
| **CUBRID 10.2** | ✅ | -- | ✅ | -- |

## Mitwirken

Richtlinien finden Sie in [CONTRIBUTING.md](../CONTRIBUTING.md) und die Einrichtung der Entwicklungsumgebung in [docs/DEVELOPMENT.md](DEVELOPMENT.md).

## Sicherheit

Melden Sie Schwachstellen per E-Mail -- siehe [SECURITY.md](../SECURITY.md). Erstellen Sie keine öffentlichen Issues für Sicherheitsbedenken.

## Lizenz

MIT -- siehe [LICENSE](../LICENSE).
