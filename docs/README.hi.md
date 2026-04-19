# sqlalchemy-cubrid

**SQLAlchemy 2.0–2.1 के लिए CUBRID डायलेक्ट**

[🇰🇷 한국어](README.ko.md) · [🇺🇸 English](../README.md) · [🇨🇳 中文](README.zh.md) · [🇮🇳 हिन्दी](README.hi.md) · [🇩🇪 Deutsch](README.de.md) · [🇷🇺 Русский](README.ru.md)

[![PyPI](https://img.shields.io/pypi/v/sqlalchemy-cubrid.svg)](https://pypi.org/project/sqlalchemy-cubrid/)
[![CI](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml/badge.svg)](https://github.com/cubrid-labs/sqlalchemy-cubrid/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-green.svg)](https://www.sqlalchemy.org/)
[![Coverage 99%](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](DEVELOPMENT.md#code-coverage)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## sqlalchemy-cubrid क्यों?

CUBRID एक उच्च-प्रदर्शन ओपन-सोर्स रिलेशनल डेटाबेस है, जो कोरियाई सार्वजनिक क्षेत्र
और एंटरप्राइज़ अनुप्रयोगों में व्यापक रूप से अपनाया गया है। अब तक, कोई भी
प्रोडक्शन-रेडी SQLAlchemy डायलेक्ट नहीं था जो आधुनिक 2.0–2.1 API को सपोर्ट करता हो।

**sqlalchemy-cubrid** इस कमी को पूरा करता है:

- **स्टेटमेंट कैशिंग** और **PEP 561 टाइपिंग** के साथ पूर्ण SQLAlchemy 2.0–2.1 डायलेक्ट
- **577 ऑफ़लाइन टेस्ट** और **99%+ कोड कवरेज** — चलाने के लिए डेटाबेस की आवश्यकता नहीं
- **Python 3.10 -- 3.14** पर **4 CUBRID संस्करणों** (10.2, 11.0, 11.2, 11.4) के खिलाफ परीक्षित
- CUBRID-विशिष्ट DML कंस्ट्रक्ट: `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`
- बॉक्स से बाहर Alembic माइग्रेशन सपोर्ट

## आवश्यकताएँ

- Python 3.10+
- SQLAlchemy 2.0 -- 2.1
- [CUBRID-Python](https://github.com/CUBRID/cubrid-python) ड्राइवर

## इंस्टॉलेशन

```bash
pip install sqlalchemy-cubrid
```

Alembic सपोर्ट के साथ:

```bash
pip install "sqlalchemy-cubrid[alembic]"
```

## त्वरित शुरुआत

### Core (कनेक्शन-स्तर)

```python
from sqlalchemy import create_engine, text

engine = create_engine("cubrid://dba:password@localhost:33000/demodb")

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print(result.scalar())
```

### ORM (सेशन-स्तर)

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

## विशेषताएँ

- पूर्ण टाइप सिस्टम -- न्यूमेरिक, स्ट्रिंग, दिनांक/समय, बिट, LOB, और कलेक्शन टाइप
- SQL कम्पाइलेशन -- SELECT, JOIN, CAST, LIMIT/OFFSET, सबक्वेरी, CTE, विंडो फ़ंक्शन
- DML एक्सटेंशन -- `ON DUPLICATE KEY UPDATE`, `MERGE`, `REPLACE INTO`, `FOR UPDATE`, `TRUNCATE`
- DDL सपोर्ट -- `COMMENT`, `IF NOT EXISTS` / `IF EXISTS`, `AUTO_INCREMENT`
- स्कीमा रिफ्लेक्शन -- टेबल, व्यू, कॉलम, PK, FK, इंडेक्स, यूनीक कंस्ट्रेंट, कमेंट
- `CubridImpl` के माध्यम से Alembic माइग्रेशन (ऑटो-डिस्कवर्ड एंट्री पॉइंट)
- सभी 6 CUBRID आइसोलेशन लेवल (दोहरी ग्रैन्युलैरिटी: क्लास-स्तर + इंस्टेंस-स्तर)

## दस्तावेज़ीकरण

| गाइड | विवरण |
|---|---|
| [कनेक्शन](CONNECTION.md) | कनेक्शन स्ट्रिंग, URL प्रारूप, ड्राइवर सेटअप, पूल ट्यूनिंग |
| [टाइप मैपिंग](TYPES.md) | पूर्ण टाइप मैपिंग, CUBRID-विशिष्ट टाइप, कलेक्शन टाइप |
| [DML एक्सटेंशन](DML_EXTENSIONS.md) | ON DUPLICATE KEY UPDATE, MERGE, REPLACE INTO, क्वेरी ट्रेस |
| [आइसोलेशन लेवल](ISOLATION_LEVELS.md) | सभी 6 CUBRID आइसोलेशन लेवल, कॉन्फ़िगरेशन |
| [Alembic माइग्रेशन](ALEMBIC.md) | सेटअप, कॉन्फ़िगरेशन, सीमाएँ, बैच वर्कअराउंड |
| [फ़ीचर सपोर्ट](FEATURE_SUPPORT.md) | MySQL, PostgreSQL, SQLite से तुलना |
| [ORM कुकबुक](ORM_COOKBOOK.md) | व्यावहारिक ORM उदाहरण, रिलेशनशिप, क्वेरी |
| [डेवलपमेंट](DEVELOPMENT.md) | डेव सेटअप, टेस्टिंग, Docker, कवरेज, CI/CD |
| [ड्राइवर अनुकूलता](DRIVER_COMPAT.md) | CUBRID-Python ड्राइवर संस्करण और ज्ञात समस्याएँ |
| [समस्या निवारण](TROUBLESHOOTING.md) | सामान्य समस्याएँ, त्रुटि समाधान, डिबगिंग तकनीकें |

## अनुकूलता

| | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|:---:|:---:|:---:|:---:|
| **ऑफ़लाइन टेस्ट** | ✅ | ✅ | ✅ | ✅ |
| **CUBRID 11.4** | ✅ | -- | ✅ | -- |
| **CUBRID 11.2** | ✅ | -- | ✅ | -- |
| **CUBRID 11.0** | ✅ | -- | ✅ | -- |
| **CUBRID 10.2** | ✅ | -- | ✅ | -- |

## योगदान

दिशानिर्देशों के लिए [CONTRIBUTING.md](../CONTRIBUTING.md) और डेवलपमेंट सेटअप के लिए [docs/DEVELOPMENT.md](DEVELOPMENT.md) देखें।

## सुरक्षा

ईमेल के माध्यम से कमज़ोरियों की रिपोर्ट करें -- विवरण के लिए [SECURITY.md](../SECURITY.md) देखें। सुरक्षा चिंताओं के लिए सार्वजनिक issue न खोलें।

## लाइसेंस

MIT -- [LICENSE](../LICENSE) देखें।
