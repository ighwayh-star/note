from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
  pass


connect_args: dict[str, object] | None = None
if settings.database_url.startswith("sqlite"):
  connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args or {}, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def ensure_sqlite_schema(engine: Engine) -> None:
  if not settings.database_url.startswith("sqlite"):
    return
  with engine.begin() as conn:
    try:
      rows = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
    except Exception:
      return
    names = {r[1] for r in rows or []}
    if rows and "deleted_at" not in names:
      conn.execute(text("ALTER TABLE transactions ADD COLUMN deleted_at DATETIME"))


def get_db() -> Generator[Session, None, None]:
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

