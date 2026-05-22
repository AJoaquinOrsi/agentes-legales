from datetime import datetime
from typing import List, Optional
import json as _json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import ChatMessage, ChatResponse
from ..services.claude_service import ClaudeService
from ..security import require_auth, chat_rate_limit
from ..models.models import ConversationSession

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(require_auth), Depends(chat_rate_limit)],
)


@router.post("/")
async def chat(payload: ChatMessage, db: Session = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    service = ClaudeService(db)
    try:
        return await service.chat(payload.mensaje, payload.conversation_history or [])
    except Exception as exc:
        logger.exception("Error en chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hubo un error procesando tu mensaje. Intentá de nuevo.",
        )


# ── Session schemas ───────────────────────────────────────────────────────────

class SessionSave(BaseModel):
    session_id: Optional[str] = None
    name: Optional[str] = None
    messages: List[dict] = []
    api_history: List[dict] = []


# ── Session endpoints (no rate limit — no AI calls) ──────────────────────────

@router.get("/sessions")
async def list_sessions(db: Session = Depends(get_db), username: str = Depends(require_auth)):
    sessions = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == username)
        .order_by(ConversationSession.updated_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for s in sessions:
        msgs = _json.loads(s.messages or "[]")
        preview = ""
        for m in reversed(msgs):
            if m.get("role") == "agent" and m.get("text"):
                preview = m["text"][:60]
                break
        result.append({
            "id": s.id,
            "name": s.name or "Conversación",
            "preview": preview,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        })
    return result


@router.post("/sessions")
async def save_session(
    payload: SessionSave,
    db: Session = Depends(get_db),
    username: str = Depends(require_auth),
):
    if payload.session_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.id == payload.session_id,
            ConversationSession.user_id == username,
        ).first()
        if session:
            if payload.name:
                session.name = payload.name
            session.messages = _json.dumps(payload.messages, ensure_ascii=False)
            session.api_history = _json.dumps(payload.api_history, ensure_ascii=False)
            session.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            return {"id": session.id, "name": session.name, "updated_at": session.updated_at.isoformat()}

    # Derive name from first user message
    name = payload.name
    if not name:
        for m in payload.messages:
            if m.get("role") == "user" and m.get("text"):
                name = m["text"][:60]
                break

    session = ConversationSession(
        user_id=username,
        name=name or "Nueva conversación",
        messages=_json.dumps(payload.messages, ensure_ascii=False),
        api_history=_json.dumps(payload.api_history, ensure_ascii=False),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "name": session.name, "updated_at": session.updated_at.isoformat()}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_auth),
):
    session = db.query(ConversationSession).filter(
        ConversationSession.id == session_id,
        ConversationSession.user_id == username,
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    return {
        "id": session.id,
        "name": session.name,
        "messages": session.messages,
        "api_history": session.api_history,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
    }


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    username: str = Depends(require_auth),
):
    session = db.query(ConversationSession).filter(
        ConversationSession.id == session_id,
        ConversationSession.user_id == username,
    ).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    db.delete(session)
    db.commit()
