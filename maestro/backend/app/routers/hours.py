from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import require_auth
from ..schemas import WorkHoursCreate, WorkHoursRead
from ..services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["hours"], dependencies=[Depends(require_auth)])


@router.get("/{project_id}/hours", response_model=List[WorkHoursRead])
def list_hours(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.work_hours


@router.post("/{project_id}/hours", response_model=WorkHoursRead, status_code=status.HTTP_201_CREATED)
def add_hours(project_id: str, payload: WorkHoursCreate, db: Session = Depends(get_db)):
    entry = ProjectService.add_work_hours(db, project_id, payload)
    if not entry:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return entry
