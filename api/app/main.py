from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db import Base, engine, ensure_sqlite_schema
from app.routers import accounts, ai, auth, categories, stats, transactions, users


def create_app() -> FastAPI:
  app = FastAPI(title="Ledger MVP", docs_url="/api/docs", openapi_url="/api/openapi.json")

  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  app.include_router(auth.router, prefix="/api")
  app.include_router(users.router, prefix="/api")
  app.include_router(accounts.router, prefix="/api")
  app.include_router(categories.router, prefix="/api")
  app.include_router(transactions.router, prefix="/api")
  app.include_router(stats.router, prefix="/api")
  app.include_router(ai.router, prefix="/api")

  @app.get("/health")
  def health() -> dict[str, str]:
    return {"status": "ok"}

  return app


app = create_app()


@app.on_event("startup")
def _startup() -> None:
  Base.metadata.create_all(bind=engine)
  ensure_sqlite_schema(engine)

