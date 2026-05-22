from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import require_auth
from ..schemas import NoteCreate, NoteRead
from ..services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["notes"], dependencies=[Depends(require_auth)])


@router.get("/{project_id}/notes", response_model=List[NoteRead])
def list_notes(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.notes


@router.post("/{project_id}/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def add_note(project_id: str, payload: NoteCreate, db: Session = Depends(get_db)):
    note = ProjectService.add_note(db, project_id, payload)
    if not note:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return note
