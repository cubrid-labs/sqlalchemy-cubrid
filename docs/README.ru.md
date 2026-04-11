# sqlalchemy-cubrid

**Диалект CUBRID для SQLAlchemy 2.0–2.1**

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-cubrid.svg)](https://pypi.org/project/sqlalchemy-cubrid/)
[![CI](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)](https://www.sqlalchemy.org/)
[![Coverage 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](DEVELOPMENT.md#code-coverage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Почему sqlalchemy-cubrid?

CUBRID — это высокопроизводительная реляционная база данных с открытым исходным кодом,
широко используемая в корейском государственном секторе и корпоративных приложениях.
До сих пор не существовало готового к продакшену диалекта SQLAlchemy, поддерживающего
современный API версии 2.0–2.1.

**sqlalchemy-cubrid** восполняет этот пробел:

- Полноценный диалект SQLAlchemy 2.0–2.1 с **кэшированием выражений** и **типизацией PEP 561**
- **396 офлайн-тестов** с **99,45% покрытием кода** — для запуска не нужна база данных
- Протестирован с **4 версиями CUBRID** (10.2, 11.0, 11.2, 11.4) на **Python 3.10 -- 3.14**
- CUBRID-специфичные DML-конструкции: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Поддержка миграций Alembic из коробки

## Требования

- Python 3.10+
- SQLAlchemy 2.0 -- 2.1
- Драйвер [CUBRID-Python](https://github.com/CUBRID/cubrid-python)

## Установка

```bash
pip install sqlalchemy-cubrid
```

С поддержкой Alembic:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## Быстрый старт

### Core (уровень соединения)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (уровень сессии)

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

## Возможности

- Полная система типов -- числовые, строковые, дата/время, битовые, LOB и коллекции
- Компиляция SQL -- SELECT, JOIN, CAST, LIMIT/OFFSET, подзапросы, CTE, оконные функции
- DML-расширения -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL-поддержка -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- Рефлексия схемы -- таблицы, представления, столбцы, PK, FK, индексы, уникальные ограничения, комментарии
- Миграции Alembic через `CubridImpl` (автоматически обнаруживаемая точка входа)
- Все 6 уровней изоляции CUBRID (двойная гранулярность: уровень класса + уровень экземпляра)

## Документация

| Руководство | Описание |
|---|---|
| [Подключение](CONNECTION.md) | Строки подключения, формат URL, настройка драйвера, тюнинг пула |
| [Маппинг типов](TYPES.md) | Полный маппинг типов, CUBRID-специфичные типы, коллекции |
| [DML-расширения](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, трассировка запросов |
| [Уровни изоляции](ISOLATION_LEVELS.md) | Все 6 уровней изоляции CUBRID, конфигурация |
| [Миграции Alembic](ALEMBIC.md) | Настройка, конфигурация, ограничения, пакетные обходные пути |
| [Поддержка функций](FEATURE_SUPPORT.md) | Сравнение с MySQL, PostgreSQL, SQLite |
| [ORM-рецепты](ORM_COOKBOOK.md) | Практические примеры ORM, связи, запросы |
| [Разработка](DEVELOPMENT.md) | Настройка среды, тестирование, Docker, покрытие, CI/CD |
| [Совместимость драйверов](DRIVER_COMPAT.md) | Версии драйвера CUBRID-Python и известные проблемы |
| [Устранение неполадок](TROUBLESHOOTING.md) | Частые проблемы, решения ошибок, методы отладки |

## Совместимость

| | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|:---:|:---:|:---:|:---:|
| **Офлайн-тесты** | ✅ | ✅ | ✅ | ✅ |
| **CUBRID 11.4** | ✅ | -- | ✅ | -- |
| **CUBRID 11.2** | ✅ | -- | ✅ | -- |
| **CUBRID 11.0** | ✅ | -- | ✅ | -- |
| **CUBRID 10.2** | ✅ | -- | ✅ | -- |

## Участие в разработке

Ознакомьтесь с [CONTRIBUTING.md](../CONTRIBUTING.md) для руководства и [docs/DEVELOPMENT.md](DEVELOPMENT.md) для настройки среды разработки.

## Безопасность

Сообщайте об уязвимостях по электронной почте -- подробности в [SECURITY.md](../SECURITY.md). Не создавайте публичные issues по вопросам безопасности.

## Лицензия

MIT -- см. [LICENSE](../LICENSE).
