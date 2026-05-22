from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import require_auth
from ..schemas import TaskCreate, TaskRead
from ..services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["tasks"], dependencies=[Depends(require_auth)])


@router.get("/{project_id}/tasks", response_model=List[TaskRead])
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.tasks


@router.post("/{project_id}/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(project_id: str, payload: TaskCreate, db: Session = Depends(get_db)):
    task = ProjectService.create_task(db, project_id, payload)
    if not task:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return task


@router.patch("/{project_id}/tasks/{task_id}/complete", response_model=TaskRead)
def complete_task(project_id: str, task_id: str, db: Session = Depends(get_db)):
    task = ProjectService.complete_task(db, project_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea o proyecto no encontrado")
    return task
