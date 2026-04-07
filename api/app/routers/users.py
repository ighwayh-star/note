from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models import User
from app.schemas import UserOut
from app.security import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
  return user

