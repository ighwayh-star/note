from __future__ import annotations

import datetime as dt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
  return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
  return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user: User) -> str:
  expire_at = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=settings.access_token_exp_minutes)
  payload = {
    "sub": str(user.id),
    "email": user.email,
    "exp": expire_at,
  }
  return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid authentication credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  try:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    sub = payload.get("sub")
    if not sub:
      raise credentials_exception
    user_id = int(sub)
  except (JWTError, ValueError):
    raise credentials_exception

  user = db.scalar(select(User).where(User.id == user_id))
  if not user:
    raise credentials_exception
  return user

