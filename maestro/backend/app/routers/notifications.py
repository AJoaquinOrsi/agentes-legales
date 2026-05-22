"""
Router de notificaciones in-app para MAESTRO.
GET  /notifications          → lista + genera automáticas
GET  /notifications/count    → solo el conteo de no leídas
POST /notifications/{id}/read
POST /notifications/read-all
DELETE /notifications/{id}
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from ..database import get_db
from ..security import require_auth
from ..services import notification_service

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_auth)],
)


class NotificationOut(BaseModel):
    id: str
    tipo: str
    titulo: str
    mensaje: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    leida: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCount(BaseModel):
    unread: int


@router.get("", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db)):
    """Lista notificaciones y genera nuevas automáticamente."""
    notification_service.generate_notifications(db)
    return notification_service.get_all(db)


@router.get("/count", response_model=NotificationCount)
def unread_count(db: Session = Depends(get_db)):
    """Conteo rápido de no leídas (para el badge)."""
    notification_service.generate_notifications(db)
    return NotificationCount(unread=notification_service.count_unread(db))


@router.post("/{notif_id}/read")
def mark_as_read(notif_id: str, db: Session = Depends(get_db)):
    if not notification_service.mark_read(db, notif_id):
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"ok": True}


@router.post("/read-all")
def mark_all_as_read(db: Session = Depends(get_db)):
    count = notification_service.mark_all_read(db)
    return {"marked": count}


@router.delete("/{notif_id}")
def delete_notification(notif_id: str, db: Session = Depends(get_db)):
    if not notification_service.delete_notification(db, notif_id):
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return {"ok": True}
