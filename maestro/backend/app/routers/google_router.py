"""
Router para integración con Google Calendar y Google Drive.
Todos los endpoints requieren autenticación JWT.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from ..database import get_db
from ..security import require_auth
from ..config import settings

router = APIRouter(prefix="/google", tags=["google"], dependencies=[Depends(require_auth)])


# ── Schemas de respuesta ──────────────────────────────────────────────────────

class GoogleStatus(BaseModel):
    enabled: bool
    oauth_enabled: bool
    calendar_configured: bool
    drive_configured: bool


class CalendarEvent(BaseModel):
    id: str
    titulo: str
    fecha: str
    link: str


class DriveFolder(BaseModel):
    project_id: str
    folder_id: Optional[str]
    folder_url: Optional[str]


class DriveFile(BaseModel):
    id: str
    name: str
    mimeType: str
    size: Optional[str] = None
    modifiedTime: Optional[str] = None
    webViewLink: Optional[str] = None


class SyncCalendarRequest(BaseModel):
    project_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=GoogleStatus)
def google_status():
    """Devuelve el estado de la integración con Google."""
    return GoogleStatus(
        enabled=settings.google_enabled,
        oauth_enabled=settings.google_oauth_enabled,
        calendar_configured=bool(settings.GOOGLE_CALENDAR_ID),
        drive_configured=bool(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID),
    )


@router.get("/calendar/upcoming", response_model=List[CalendarEvent])
def upcoming_deadlines(days: int = 30):
    """Lista los eventos [MAESTRO] en el calendario para los próximos N días."""
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Google no está configurado")
    from ..services.google_service import get_upcoming_deadlines
    events = get_upcoming_deadlines(days=days)
    return [CalendarEvent(**e) for e in events]


@router.post("/calendar/sync/{project_id}")
def sync_project_to_calendar(project_id: str, db: Session = Depends(get_db)):
    """
    Sincroniza el deadline del proyecto con Google Calendar.
    Crea el evento si no existe, lo actualiza si ya existe.
    """
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Google no está configurado")

    from ..models.models import Project
    from ..services.google_service import (
        create_deadline_event, update_deadline_event
    )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if not project.deadline:
        raise HTTPException(status_code=400, detail="El proyecto no tiene deadline definido")

    if project.calendar_event_id:
        # Actualizar evento existente
        ok = update_deadline_event(
            project.calendar_event_id,
            project.nombre,
            project.deadline,
        )
        if not ok:
            # Si falla la actualización, crear uno nuevo
            event_id = create_deadline_event(project.nombre, project.deadline)
            if event_id:
                project.calendar_event_id = event_id
                db.commit()
        return {"event_id": project.calendar_event_id, "action": "updated"}
    else:
        # Crear nuevo evento
        event_id = create_deadline_event(project.nombre, project.deadline)
        if not event_id:
            raise HTTPException(status_code=500, detail="No se pudo crear el evento en Calendar")
        project.calendar_event_id = event_id
        db.commit()
        return {"event_id": event_id, "action": "created"}


@router.delete("/calendar/event/{event_id}")
def delete_calendar_event(event_id: str, project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Elimina un evento del calendario y desvincula el proyecto si se indica."""
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Google no está configurado")

    from ..services.google_service import delete_event
    from ..models.models import Project

    ok = delete_event(event_id)
    if project_id:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.calendar_event_id = None
            db.commit()

    return {"deleted": ok}


@router.get("/drive/folder/{project_id}", response_model=DriveFolder)
def get_project_drive_folder(project_id: str, db: Session = Depends(get_db)):
    """
    Obtiene o crea la carpeta de Drive para el proyecto.
    """
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Google no está configurado")

    from ..models.models import Project
    from ..services.google_service import get_or_create_project_folder, get_folder_url

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    # Usar folder_id existente o crear uno nuevo
    folder_id = project.drive_folder_id
    if not folder_id:
        folder_id = get_or_create_project_folder(project.nombre)
        if folder_id:
            project.drive_folder_id = folder_id
            db.commit()

    return DriveFolder(
        project_id=project_id,
        folder_id=folder_id,
        folder_url=get_folder_url(folder_id) if folder_id else None,
    )


@router.get("/drive/files/{project_id}", response_model=List[DriveFile])
def list_project_drive_files(project_id: str, db: Session = Depends(get_db)):
    """Lista los archivos en la carpeta de Drive del proyecto."""
    if not settings.google_enabled:
        raise HTTPException(status_code=503, detail="Google no está configurado")

    from ..models.models import Project
    from ..services.google_service import list_project_files, get_or_create_project_folder

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    folder_id = project.drive_folder_id
    if not folder_id:
        folder_id = get_or_create_project_folder(project.nombre)
        if folder_id:
            project.drive_folder_id = folder_id
            db.commit()

    if not folder_id:
        return []

    files = list_project_files(folder_id)
    return [DriveFile(**f) for f in files]
