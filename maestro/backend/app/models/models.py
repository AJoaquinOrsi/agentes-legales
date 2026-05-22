import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Integer, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(120), nullable=True, unique=True)
    hashed_password = Column(String(128), nullable=False)
    display_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

import enum


class ProjectStatus(str, enum.Enum):
    en_analisis = "en análisis"
    en_desarrollo = "en desarrollo"
    testing = "testing"
    listo = "listo"
    produccion = "producción"


class Priority(str, enum.Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class BlockerType(str, enum.Enum):
    esperando_cliente = "esperando cliente"
    sin_acceso = "sin acceso"
    tecnico = "técnico"
    otro = "otro"


class NoteType(str, enum.Enum):
    learning = "learning"
    decision = "decision"
    reflection = "reflection"
    otro = "otro"


def _uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_uuid)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text, nullable=True)
    cliente_area = Column(String(100), nullable=False)
    prioridad = Column(SAEnum(Priority), default=Priority.media, nullable=False)
    estado = Column(SAEnum(ProjectStatus), default=ProjectStatus.en_analisis, nullable=False)
    deadline = Column(Date, nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    tags = Column(String(200), nullable=True)  # comma-separated
    bloqueado = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    responsable = Column(String(100), nullable=True)
    specs_text = Column(Text, nullable=True)
    links_json = Column(Text, nullable=True)
    structure_text = Column(Text, nullable=True)
    structure_image_url = Column(String(500), nullable=True)
    archived = Column(Boolean, default=False, nullable=False)
    tarifa_hora = Column(Float, nullable=True)
    presupuesto = Column(Float, nullable=True)

    # ── Integraciones externas ────────────────────────────────────────────────
    github_url = Column(String(255), nullable=True)
    drive_folder_id = Column(String(100), nullable=True)
    calendar_event_id = Column(String(200), nullable=True)

    status_history = relationship("ProjectStatusHistory", back_populates="project", cascade="all, delete-orphan")
    work_hours = relationship("WorkHours", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    blockers = relationship("Blocker", back_populates="project", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="project", cascade="all, delete-orphan")

    @property
    def total_hours(self) -> float:
        return sum(wh.horas for wh in self.work_hours)

    @property
    def dias_en_estado_actual(self) -> int:
        if not self.status_history:
            delta = datetime.utcnow() - self.created_at
            return delta.days
        last = max(self.status_history, key=lambda h: h.changed_at)
        return (datetime.utcnow() - last.changed_at).days

    @property
    def active_blockers(self):
        return [b for b in self.blockers if not b.resuelto]


class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    estado_anterior = Column(SAEnum(ProjectStatus), nullable=True)
    estado_nuevo = Column(SAEnum(ProjectStatus), nullable=False)
    razon = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="status_history")


class WorkHours(Base):
    __tablename__ = "work_hours"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    horas = Column(Float, nullable=False)
    fecha = Column(Date, default=date.today, nullable=False)
    descripcion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="work_hours")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    descripcion = Column(Text, nullable=False)
    prioridad = Column(SAEnum(Priority), default=Priority.media, nullable=False)
    estimated_hours = Column(Float, nullable=True)
    completada = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_vencimiento = Column(Date, nullable=True)
    subtareas_json = Column(Text, nullable=True)
    elapsed_seconds = Column(Integer, default=0, nullable=False)
    timer_started_at = Column(DateTime, nullable=True)
    task_type = Column(String(20), default="task", nullable=False)
    meeting_with = Column(String(200), nullable=True)
    meeting_prep_url = Column(String(500), nullable=True)
    meeting_prep_filename = Column(String(200), nullable=True)
    calendar_event_id = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="tasks")


class Blocker(Base):
    __tablename__ = "blockers"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    descripcion = Column(Text, nullable=False)
    tipo = Column(SAEnum(BlockerType), default=BlockerType.otro, nullable=False)
    resuelto = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="blockers")

    @property
    def dias_sin_resolver(self) -> int:
        if self.resuelto:
            return 0
        return (datetime.utcnow() - self.created_at).days


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    contenido = Column(Text, nullable=False)
    tipo = Column(SAEnum(NoteType), default=NoteType.otro, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="notes")


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    messages = Column(Text, nullable=False, default="[]")      # JSON: UI message list
    api_history = Column(Text, nullable=False, default="[]")   # JSON: Claude API history
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ── Notifications ─────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=_uuid)
    # tipo: tarea_vencida | tarea_proxima | proyecto_bloqueado | sistema
    tipo = Column(String(30), nullable=False, default="sistema")
    titulo = Column(String(200), nullable=False)
    mensaje = Column(Text, nullable=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(String, nullable=True)
    leida = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
