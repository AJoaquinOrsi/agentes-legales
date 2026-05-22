from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..security import require_auth
from ..schemas import BlockerCreate, BlockerRead
from ..services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["blockers"], dependencies=[Depends(require_auth)])


@router.get("/{project_id}/blockers", response_model=List[BlockerRead])
def list_blockers(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project.blockers


@router.post("/{project_id}/blockers", response_model=BlockerRead, status_code=status.HTTP_201_CREATED)
def create_blocker(project_id: str, payload: BlockerCreate, db: Session = Depends(get_db)):
    blocker = ProjectService.create_blocker(db, project_id, payload)
    if not blocker:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return blocker


@router.patch("/{project_id}/blockers/{blocker_id}/resolve", response_model=BlockerRead)
def resolve_blocker(project_id: str, blocker_id: str, db: Session = Depends(get_db)):
    blocker = ProjectService.resolve_blocker(db, project_id, blocker_id)
    if not blocker:
        raise HTTPException(status_code=404, detail="Bloqueador o proyecto no encontrado")
    return blocker
