from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db import Base, get_db
from app.main import create_app
from app import models


@pytest.fixture()
def client() -> TestClient:
  settings.ai_mode = "rule"
  settings.openai_api_key = None
  settings.deepseek_api_key = None

  engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
  )
  TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
  Base.metadata.create_all(bind=engine)

  def override_get_db():
    db: Session = TestingSessionLocal()
    try:
      yield db
    finally:
      db.close()

  app = create_app()
  app.dependency_overrides[get_db] = override_get_db
  return TestClient(app)

