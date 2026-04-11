# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1을 위한 CUBRID 방언(Dialect)**

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-cubrid.svg)](https://pypi.org/project/sqlalchemy-cubrid/)
[![CI](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)](https://www.sqlalchemy.org/)
[![Coverage 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](DEVELOPMENT.md#code-coverage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 왜 sqlalchemy-cubrid인가?

CUBRID는 고성능 오픈소스 관계형 데이터베이스로, 한국 공공기관 및 기업 환경에서
널리 사용되고 있습니다. 그러나 지금까지 최신 SQLAlchemy 2.0–2.1 API를 지원하는
프로덕션 수준의 방언은 존재하지 않았습니다.

**sqlalchemy-cubrid**는 이 공백을 채웁니다:

- **쿼리 캐싱**과 **PEP 561 타입 지원**을 갖춘 완전한 SQLAlchemy 2.0–2.1 방언
- **427개 오프라인 테스트**, **99% 이상 코드 커버리지** — 데이터베이스 없이도 실행 가능
- **Python 3.10 -- 3.14**에서 **4개 CUBRID 버전**(10.2, 11.0, 11.2, 11.4) 통합 테스트 완료
- CUBRID 전용 DML 구문: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- Alembic 마이그레이션 기본 지원
- **두 가지 드라이버 옵션** — C 확장(`cubrid://`) 또는 순수 Python(`cubrid+pycubrid://`)

## 요구 사항

- Python 3.10+
- SQLAlchemy 2.0 – 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) (C 확장) **또는** [pycubrid](https://github.com/sqlalchemy-cubrid/pycubrid) (순수 Python)

## 설치

```bash
pip install sqlalchemy-cubrid
```

순수 Python 드라이버 사용 시 (C 빌드 불필요):

```bash
pip install "sqlalchemy-cubrid[pycubrid]"
```

Alembic 지원 포함:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## 빠른 시작

### Core (연결 수준)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (세션 수준)

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

## 주요 기능

- 완전한 타입 시스템 -- 숫자, 문자열, 날짜/시간, 비트, LOB, 컬렉션 타입
- SQL 컴파일 -- SELECT, JOIN, CAST, LIMIT/OFFSET, 서브쿼리, CTE, 윈도우 함수
- DML 확장 -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL 지원 -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- 스키마 리플렉션 -- 테이블, 뷰, 컬럼, 기본키, 외래키, 인덱스, 유니크 제약 조건, 코멘트
- `CubridImpl`을 통한 Alembic 마이그레이션 (자동 탐색 엔트리 포인트)
- CUBRID의 6가지 격리 수준 모두 지원 (이중 세분화: 클래스 수준 + 인스턴스 수준)

## 문서

| 가이드 | 설명 |
|---|---|
| [연결](CONNECTION.md) | 연결 문자열, URL 형식, 드라이버 설정, 커넥션 풀 튜닝 |
| [타입 매핑](TYPES.md) | 전체 타입 매핑, CUBRID 전용 타입, 컬렉션 타입 |
| [DML 확장](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, 쿼리 추적 |
| [격리 수준](ISOLATION_LEVELS.md) | CUBRID 6가지 격리 수준, 설정 방법 |
| [Alembic 마이그레이션](ALEMBIC.md) | 설정, 구성, 제한 사항, 배치 우회 방법 |
| [기능 지원](FEATURE_SUPPORT.md) | MySQL, PostgreSQL, SQLite와의 비교 |
| [ORM 활용 가이드](ORM_COOKBOOK.md) | 실용적인 ORM 예제, 관계, 쿼리 |
| [개발 가이드](DEVELOPMENT.md) | 개발 환경 설정, 테스트, Docker, 커버리지, CI/CD |
| [드라이버 호환성](DRIVER_COMPAT.md) | CUBRID-Python 드라이버 버전 및 알려진 이슈 |
| [문제 해결](TROUBLESHOOTING.md) | 일반적인 문제, 오류 해결, 디버깅 기법 |

## 호환성

| | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|:---:|:---:|:---:|:---:|
| **오프라인 테스트** | ✅ | ✅ | ✅ | ✅ |
| **CUBRID 11.4** | ✅ | -- | ✅ | -- |
| **CUBRID 11.2** | ✅ | -- | ✅ | -- |
| **CUBRID 11.0** | ✅ | -- | ✅ | -- |
| **CUBRID 10.2** | ✅ | -- | ✅ | -- |

## 기여하기

기여 가이드라인은 [CONTRIBUTING.md](../CONTRIBUTING.md)를, 개발 환경 설정은 [docs/DEVELOPMENT.md](DEVELOPMENT.md)를 참고하세요.

## 보안

보안 취약점은 이메일로 제보해 주세요 — 자세한 내용은 [SECURITY.md](../SECURITY.md)를 참고하세요. 보안 관련 사항은 공개 이슈로 등록하지 마세요.

## 라이선스

MIT — [LICENSE](../LICENSE) 참조.
