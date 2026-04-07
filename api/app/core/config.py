from __future__ import annotations

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


settings = Settings()

