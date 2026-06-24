"""Подключение к базе данных.

Используется SQLite (файл на диске) — не требует установки СУБД, Docker и т.п.
SQLAlchemy выбран намеренно: при переходе на PostgreSQL (как в архитектуре ВКР)
меняется только строка SQLALCHEMY_DATABASE_URL, прикладной код остаётся прежним.
"""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# backend/  (на уровень выше пакета app)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "nextburger.db"

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# check_same_thread=False — SQLite + многопоточный сервер uvicorn
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Включаем поддержку внешних ключей в SQLite (по умолчанию выключена)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Зависимость FastAPI: открывает сессию БД на время запроса и закрывает её."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
