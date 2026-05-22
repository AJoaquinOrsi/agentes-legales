"""
Servicio de notificaciones in-app para MAESTRO.
Genera notificaciones automáticas basadas en:
  - Tareas vencidas (fecha_vencimiento < hoy, no completada)
  - Tareas próximas a vencer (en las próximas 48 horas)
  - Proyectos bloqueados
"""
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from ..models.models import Notification, Task, Project


# ── Generación automática ────────────────────────────────────────────────────

def _notif_key(tipo: str, ref_id: str) -> str:
    return f"{tipo}:{ref_id}"


def _already_notified(db: Session, tipo: str, ref_id: str, within_hours: int = 24) -> bool:
    """Evita duplicar notificaciones del mismo evento en las últimas N horas."""
    cutoff = datetime.utcnow() - timedelta(hours=within_hours)
    existing = (
        db.query(Notification)
        .filter(
            Notification.tipo == tipo,
            Notification.task_id == ref_id if "tarea" in tipo else Notification.project_id == ref_id,
            Notification.created_at >= cutoff,
        )
        .first()
    )
    return existing is not None


def generate_notifications(db: Session) -> int:
    """
    Genera notificaciones automáticas. Devuelve el número de nuevas notificaciones creadas.
    Se llama al cargar el endpoint GET /notifications.
    """
    today = date.today()
    soon = today + timedelta(days=2)
    created = 0

    # ── Tareas vencidas ──────────────────────────────────────────────────────
    overdue_tasks = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.fecha_vencimiento < today,
            Task.completada == False,
            Project.archived == False,
        )
        .all()
    )
    for t in overdue_tasks:
        if not _already_notified(db, "tarea_vencida", t.id, within_hours=24):
            proj = db.query(Project).filter(Project.id == t.project_id).first()
            notif = Notification(
                tipo="tarea_vencida",
                titulo=f"Tarea vencida: {t.descripcion[:60]}",
                mensaje=f"En proyecto «{proj.nombre}» — venció el {t.fecha_vencimiento}",
                project_id=t.project_id,
                task_id=t.id,
            )
            db.add(notif)
            created += 1

    # ── Tareas próximas a vencer (hoy o mañana) ──────────────────────────────
    upcoming_tasks = (
        db.query(Task)
        .join(Project, Task.project_id == Project.id)
        .filter(
            Task.fecha_vencimiento >= today,
            Task.fecha_vencimiento <= soon,
            Task.completada == False,
            Project.archived == False,
        )
        .all()
    )
    for t in upcoming_tasks:
        if not _already_notified(db, "tarea_proxima", t.id, within_hours=20):
            proj = db.query(Project).filter(Project.id == t.project_id).first()
            days_left = (t.fecha_vencimiento - today).days
            when = "hoy" if days_left == 0 else "mañana" if days_left == 1 else f"en {days_left} días"
            notif = Notification(
                tipo="tarea_proxima",
                titulo=f"Tarea vence {when}: {t.descripcion[:60]}",
                mensaje=f"Proyecto «{proj.nombre}»",
                project_id=t.project_id,
                task_id=t.id,
            )
            db.add(notif)
            created += 1

    # ── Proyectos bloqueados ──────────────────────────────────────────────────
    blocked_projects = (
        db.query(Project)
        .filter(Project.bloqueado == True, Project.archived == False)
        .all()
    )
    for p in blocked_projects:
        if not _already_notified(db, "proyecto_bloqueado", p.id, within_hours=12):
            notif = Notification(
                tipo="proyecto_bloqueado",
                titulo=f"Proyecto bloqueado: {p.nombre}",
                mensaje="Revisá los impedimentos activos.",
                project_id=p.id,
            )
            db.add(notif)
            created += 1

    if created:
        db.commit()
    return created


# ── CRUD ─────────────────────────────────────────────────────────────────────

def get_all(db: Session, limit: int = 50) -> list[Notification]:
    return (
        db.query(Notification)
        .order_by(Notification.leida.asc(), Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def count_unread(db: Session) -> int:
    return db.query(Notification).filter(Notification.leida == False).count()


def mark_read(db: Session, notif_id: str) -> bool:
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if not n:
        return False
    n.leida = True
    db.commit()
    return True


def mark_all_read(db: Session) -> int:
    updated = db.query(Notification).filter(Notification.leida == False).all()
    for n in updated:
        n.leida = True
    db.commit()
    return len(updated)


def delete_notification(db: Session, notif_id: str) -> bool:
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if not n:
        return False
    db.delete(n)
    db.commit()
    return True


def create_system_notification(db: Session, titulo: str, mensaje: str = "", project_id: str = None) -> Notification:
    """Crea una notificación de sistema manual."""
    n = Notification(tipo="sistema", titulo=titulo, mensaje=mensaje, project_id=project_id)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n
