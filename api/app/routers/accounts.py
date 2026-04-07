from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Account, User
from app.schemas import AccountCreateIn, AccountOut
from app.security import get_current_user


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountOut])
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Account]:
  return list(db.scalars(select(Account).where(Account.user_id == user.id).order_by(Account.id.desc())))


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
  payload: AccountCreateIn,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Account:
  account = Account(user_id=user.id, name=payload.name, currency=payload.currency)
  db.add(account)
  try:
    db.commit()
  except IntegrityError:
    db.rollback()
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account name already exists")
  db.refresh(account)
  return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
  account_id: int,
  user: User = Depends(get_current_user),
  db: Session = Depends(get_db),
) -> Response:
  account = db.scalar(select(Account).where(Account.id == account_id, Account.user_id == user.id))
  if not account:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
  db.delete(account)
  db.commit()
  return Response(status_code=status.HTTP_204_NO_CONTENT)

