from __future__ import annotations

import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
  model_config = SettingsConfigDict(env_file=".env", extra="ignore")

  database_url: str = "sqlite:///./app.db"
  jwt_secret: str = "dev-secret-change-me"
  jwt_algorithm: str = "HS256"
  access_token_exp_minutes: int = 60 * 24 * 7
  ai_mode: str = "rule"
  openai_api_key: str | None = None
  openai_model: str = "gpt-4o-mini"
  deepseek_api_key: str | None = None
  deepseek_base_url: str = "https://api.deepseek.com"
  deepseek_model: str = "deepseek-chat"
  cors_origins: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
  ]

  @field_validator("cors_origins", mode="before")
  @classmethod
  def _parse_cors_origins(cls, v):  # type: ignore[no-untyped-def]
    if v is None:
      return v
    if isinstance(v, str):
      s = v.strip()
      if not s:
        return []
      if s.startswith("["):
        try:
          parsed = json.loads(s)
          if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
          return []
      return [item.strip() for item in s.split(",") if item.strip()]
    return v


settings = Settings()

