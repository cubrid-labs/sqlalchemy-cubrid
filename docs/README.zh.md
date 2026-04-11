# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1 的 CUBRID 数据库方言**

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-cubrid.svg)](https://pypi.org/project/sqlalchemy-cubrid/)
[![CI](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)](https://www.sqlalchemy.org/)
[![Coverage 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](DEVELOPMENT.md#code-coverage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 为什么选择 sqlalchemy-cubrid？

CUBRID 是一款高性能的开源关系型数据库，在韩国公共部门和企业应用中被广泛采用。
在此之前，还没有支持现代 SQLAlchemy 2.0–2.1 API 的生产级方言。

**sqlalchemy-cubrid** 填补了这一空白：

- 完整的 SQLAlchemy 2.0–2.1 方言，支持**语句缓存**和 **PEP 561 类型标注**
- **396 个离线测试**，**99.45% 代码覆盖率** — 无需数据库即可运行
- 在 **Python 3.10 -- 3.14** 上测试了 **4 个 CUBRID 版本**（10.2、11.0、11.2、11.4）
- CUBRID 特有的 DML 构造：`ON DUPLICATE KEY UPDATE`、`MERGE`、`REPLACE INTO`
- 开箱即用的 Alembic 迁移支持

## 环境要求

- Python 3.10+
- SQLAlchemy 2.0 -- 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) 驱动程序

## 安装

```bash
pip install sqlalchemy-cubrid
```

支持 Alembic：

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## 快速开始

### Core（连接级别）

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM（会话级别）

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

## 功能特性

- 完整的类型系统 -- 数值、字符串、日期/时间、位、LOB 和集合类型
- SQL 编译 -- SELECT、JOIN、CAST、LIMIT/OFFSET、子查询、CTE、窗口函数
- DML 扩展 -- `ON DUPLICATE KEY UPDATE`、`MERGE`、`REPLACE INTO`、`FOR UPDATE`、`TRUNCATE`
- DDL 支持 -- `COMMENT`、`IF NOT EXISTS` / `IF EXISTS`、`AUTO_INCREMENT`
- 模式反射 -- 表、视图、列、主键、外键、索引、唯一约束、注释
- 通过 `CubridImpl` 实现 Alembic 迁移（自动发现入口点）
- 全部 6 种 CUBRID 隔离级别（双粒度：类级别 + 实例级别）

## 文档

| 指南 | 描述 |
|---|---|
| [连接](CONNECTION.md) | 连接字符串、URL 格式、驱动设置、连接池调优 |
| [类型映射](TYPES.md) | 完整类型映射、CUBRID 特有类型、集合类型 |
| [DML 扩展](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE、MERGE、REPLACE INTO、查询跟踪 |
| [隔离级别](ISOLATION_LEVELS.md) | 全部 6 种 CUBRID 隔离级别、配置 |
| [Alembic 迁移](ALEMBIC.md) | 设置、配置、限制、批量解决方案 |
| [功能支持](FEATURE_SUPPORT.md) | 与 MySQL、PostgreSQL、SQLite 的对比 |
| [ORM 指南](ORM_COOKBOOK.md) | 实用 ORM 示例、关系、查询 |
| [开发指南](DEVELOPMENT.md) | 开发设置、测试、Docker、覆盖率、CI/CD |
| [驱动兼容性](DRIVER_COMPAT.md) | CUBRID-Python 驱动版本和已知问题 |
| [故障排除](TROUBLESHOOTING.md) | 常见问题、错误解决方案、调试技巧 |

## 兼容性

| | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|:---:|:---:|:---:|:---:|
| **离线测试** | ✅ | ✅ | ✅ | ✅ |
| **CUBRID 11.4** | ✅ | -- | ✅ | -- |
| **CUBRID 11.2** | ✅ | -- | ✅ | -- |
| **CUBRID 11.0** | ✅ | -- | ✅ | -- |
| **CUBRID 10.2** | ✅ | -- | ✅ | -- |

## 贡献

请参阅 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解贡献指南，以及 [docs/DEVELOPMENT.md](DEVELOPMENT.md) 了解开发环境设置。

## 安全

通过电子邮件报告漏洞 -- 详见 [SECURITY.md](../SECURITY.md)。请勿就安全问题创建公开 issue。

## 许可证

MIT -- 详见 [LICENSE](../LICENSE)。
