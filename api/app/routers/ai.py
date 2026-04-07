from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.actions import cancel_action, confirm_action, undo_last_ai_transaction_action
from app.ai.schemas import AIChatIn, AIChatOut, AIConfirmIn, AIConfirmOut
from app.ai.service import run_chat
from app.core.config import settings
from app.db import get_db
from app.models import User
from app.security import get_current_user


router = APIRouter(prefix="/ai", tags=["ai"])

def _module_available(name: str) -> bool:
  try:
    __import__(name)
    return True
  except Exception:
    return False


@router.get("/status")
def ai_status(user: User = Depends(get_current_user)) -> dict[str, object]:
  mode = (settings.ai_mode or "rule").lower()
  langchain_installed = _module_available("langchain_core") and _module_available("langchain_openai")
  provider_configured = bool(settings.openai_api_key) if mode != "deepseek" else bool(settings.deepseek_api_key)
  openai_ready = provider_configured and langchain_installed
  provider = "deepseek" if mode == "deepseek" else "openai"
  model = settings.deepseek_model if mode == "deepseek" else settings.openai_model
  base_url = settings.deepseek_base_url if mode == "deepseek" else None
  return {
    "mode": mode,
    "provider": provider,
    "model": model,
    "base_url": base_url,
    "provider_configured": provider_configured,
    "langchain_installed": langchain_installed,
    "llm_ready": openai_ready,
    "user_id": user.id,
  }



@router.post("/chat", response_model=AIChatOut)
def chat(payload: AIChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AIChatOut:
  try:
    return run_chat(message=payload.message, user=user, db=db, conversation_id=payload.conversation_id)
  except RuntimeError as e:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/confirm", response_model=AIConfirmOut)
def confirm(payload: AIConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AIConfirmOut:
  try:
    audit_id, entity_id = confirm_action(db=db, user=user, action_id=payload.action_id)
    return AIConfirmOut(ok=True, audit_id=audit_id, entity_id=entity_id)
  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/cancel", response_model=AIConfirmOut)
def cancel(payload: AIConfirmIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AIConfirmOut:
  ok = cancel_action(db=db, user=user, action_id=payload.action_id)
  if not ok:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired action")
  return AIConfirmOut(ok=True)


@router.post("/undo-last", response_model=AIConfirmOut)
def undo_last(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AIConfirmOut:
  ok = undo_last_ai_transaction_action(db=db, user=user)
  if not ok:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to undo")
  return AIConfirmOut(ok=True)
