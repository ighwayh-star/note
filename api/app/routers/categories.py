from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, User
from app.schemas import CategoryCreateIn, CategoryOut
from app.security import get_current_user


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Category]:
  return list(
    db.scalars(
      select(Category)
      .where(Category.user_id == user.id)
      .order_by(Category.type.asc(), Category.id.desc())
    )
  )


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
  payload: CategoryCreateIn,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Category:
  category = Category(user_id=user.id, name=payload.name, type=payload.type)
  db.add(category)
  try:
    db.commit()
  except IntegrityError:
    db.rollback()
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")
  db.refresh(category)
  return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
  category_id: int,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Response:
  category = db.scalar(select(Category).where(Category.id == category_id, Category.user_id == user.id))
  if not category:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
  db.delete(category)
  db.commit()
  return Response(status_code=status.HTTP_204_NO_CONTENT)

