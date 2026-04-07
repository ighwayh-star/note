from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> User:
  user = User(email=str(payload.email).lower(), password_hash=hash_password(payload.password))
  db.add(user)
  try:
    db.commit()
  except IntegrityError:
    db.rollback()
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
  db.refresh(user)
  return user


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
  user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
  if not user or not verify_password(payload.password, user.password_hash):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
  return TokenOut(access_token=create_access_token(user))

