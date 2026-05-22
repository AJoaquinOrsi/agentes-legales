from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from ..models.models import Project, ProjectStatusHistory, WorkHours, Task, Blocker, Note, ProjectStatus
from ..schemas.schemas import (
    ProjectCreate, ProjectUpdate, WorkHoursCreate,
    TaskCreate, BlockerCreate, NoteCreate,
)


class ProjectService:

    @staticmethod
    def get_all(db: Session) -> List[Project]:
        return db.query(Project).order_by(Project.updated_at.desc()).all()

    @staticmethod
    def get_by_id(db: Session, project_id: str) -> Optional[Project]:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_by_name(db: Session, nombre: str) -> Optional[Project]:
        return db.query(Project).filter(
            Project.nombre.ilike(nombre)
        ).first()

    @staticmethod
    def create(db: Session, payload: ProjectCreate) -> Project:
        project = Project(**payload.model_dump())
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def update(db: Session, project_id: str, payload: ProjectUpdate) -> Optional[Project]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(project, field, value)
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def change_status(
        db: Session, project_id: str, new_status: ProjectStatus, razon: Optional[str] = None
    ) -> Optional[Project]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        old_status = project.estado
        history = ProjectStatusHistory(
            project_id=project_id,
            estado_anterior=old_status,
            estado_nuevo=new_status,
            razon=razon,
        )
        db.add(history)
        project.estado = new_status
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return project

    @staticmethod
    def delete(db: Session, project_id: str) -> bool:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False
        db.delete(project)
        db.commit()
        return True

    @staticmethod
    def add_work_hours(db: Session, project_id: str, payload: WorkHoursCreate) -> Optional[WorkHours]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        entry = WorkHours(project_id=project_id, **payload.model_dump())
        db.add(entry)
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def create_task(db: Session, project_id: str, payload: TaskCreate) -> Optional[Task]:
        from ..config import settings
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        task = Task(project_id=project_id, **payload.model_dump())
        db.add(task)
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)

        # Auto-sync a Google Calendar si tiene fecha de vencimiento
        if settings.google_enabled and task.fecha_vencimiento:
            try:
                from . import google_service
                if task.task_type == "meeting":
                    event_id = google_service.create_meeting_event(
                        task.descripcion,
                        task.fecha_vencimiento,
                        meeting_with=task.meeting_with or "",
                        project_name=project.nombre,
                    )
                else:
                    event_id = google_service.create_task_event(
                        task.descripcion,
                        task.fecha_vencimiento,
                        project.nombre,
                        task.id,
                    )
                if event_id:
                    task.calendar_event_id = event_id
                    db.commit()
                    db.refresh(task)
            except Exception:
                pass  # No fallar la creación si Calendar falla

        return task

    @staticmethod
    def complete_task(db: Session, project_id: str, task_id: str) -> Optional[Task]:
        task = db.query(Task).filter(
            Task.id == task_id, Task.project_id == project_id
        ).first()
        if not task:
            return None
        task.completada = True
        task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def create_blocker(db: Session, project_id: str, payload: BlockerCreate) -> Optional[Blocker]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        blocker = Blocker(project_id=project_id, **payload.model_dump())
        db.add(blocker)
        project.bloqueado = True
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(blocker)
        return blocker

    @staticmethod
    def resolve_blocker(db: Session, project_id: str, blocker_id: str) -> Optional[Blocker]:
        blocker = db.query(Blocker).filter(
            Blocker.id == blocker_id, Blocker.project_id == project_id
        ).first()
        if not blocker:
            return None
        blocker.resuelto = True
        blocker.resolved_at = datetime.utcnow()
        # check if any other active blockers remain
        project = db.query(Project).filter(Project.id == project_id).first()
        remaining = db.query(Blocker).filter(
            Blocker.project_id == project_id,
            Blocker.resuelto == False,
            Blocker.id != blocker_id,
        ).count()
        if remaining == 0:
            project.bloqueado = False
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(blocker)
        return blocker

    @staticmethod
    def add_note(db: Session, project_id: str, payload: NoteCreate) -> Optional[Note]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None
        note = Note(project_id=project_id, **payload.model_dump())
        db.add(note)
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def get_projects_at_risk(db: Session) -> List[Project]:
        from datetime import date as date_type
        today = date_type.today()
        projects = db.query(Project).filter(
            Project.estado.notin_([ProjectStatus.listo, ProjectStatus.produccion])
        ).all()
        at_risk = []
        for p in projects:
            if (
                p.bloqueado
                or p.dias_en_estado_actual > 3
                or (p.deadline and p.deadline < today)
                or (p.estimated_hours and p.total_hours > p.estimated_hours * 1.5)
            ):
                at_risk.append(p)
        return at_risk

    @staticmethod
    def get_daily_summary(db: Session, target_date: date) -> dict:
        hours_today = db.query(WorkHours).filter(WorkHours.fecha == target_date).all()
        total_horas = sum(wh.horas for wh in hours_today)
        projects_touched = list({wh.project_id for wh in hours_today})

        tasks_completed = db.query(Task).filter(
            Task.completed_at >= datetime.combine(target_date, datetime.min.time()),
            Task.completed_at < datetime.combine(target_date, datetime.max.time()),
        ).count() if hasattr(datetime, 'combine') else 0

        active_blockers = db.query(Blocker).filter(Blocker.resuelto == False).count()

        project_names = []
        for pid in projects_touched:
            p = db.query(Project).filter(Project.id == pid).first()
            if p:
                project_names.append(p.nombre)

        at_risk = ProjectService.get_projects_at_risk(db)

        return {
            "fecha": target_date,
            "total_horas": total_horas,
            "tareas_completadas": tasks_completed,
            "proyectos_tocados": project_names,
            "proyectos_en_riesgo": [p.nombre for p in at_risk],
            "bloqueadores_activos": active_blockers,
        }
