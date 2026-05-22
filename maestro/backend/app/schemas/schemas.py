from datetime import datetime, date
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from ..models.models import ProjectStatus, Priority, BlockerType, NoteType
from ..config import settings


# ─── Project ────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    cliente_area: str = Field(..., min_length=1, max_length=100)
    prioridad: Priority = Priority.media
    deadline: Optional[date] = None
    fecha_inicio: Optional[date] = None
    estimated_hours: Optional[float] = Field(default=None, ge=0, le=10000)
    tags: Optional[str] = Field(default=None, max_length=500)
    github_url: Optional[str] = Field(default=None, max_length=255)
    responsable: Optional[str] = Field(default=None, max_length=100)
    specs_text: Optional[str] = Field(default=None, max_length=20000)
    links_json: Optional[str] = Field(default=None, max_length=10000)
    structure_text: Optional[str] = Field(default=None, max_length=20000)
    structure_image_url: Optional[str] = Field(default=None, max_length=500)
    archived: bool = False
    tarifa_hora: Optional[float] = Field(default=None, ge=0)
    presupuesto: Optional[float] = Field(default=None, ge=0)


class ProjectUpdate(BaseModel):
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    cliente_area: Optional[str] = Field(default=None, max_length=100)
    prioridad: Optional[Priority] = None
    deadline: Optional[date] = None
    fecha_inicio: Optional[date] = None
    estimated_hours: Optional[float] = Field(default=None, ge=0, le=10000)
    tags: Optional[str] = Field(default=None, max_length=500)
    github_url: Optional[str] = Field(default=None, max_length=255)
    responsable: Optional[str] = Field(default=None, max_length=100)
    specs_text: Optional[str] = Field(default=None, max_length=20000)
    links_json: Optional[str] = Field(default=None, max_length=10000)
    structure_text: Optional[str] = Field(default=None, max_length=20000)
    structure_image_url: Optional[str] = Field(default=None, max_length=500)
    archived: Optional[bool] = None
    tarifa_hora: Optional[float] = Field(default=None, ge=0)
    presupuesto: Optional[float] = Field(default=None, ge=0)


class ProjectStatusUpdate(BaseModel):
    estado: ProjectStatus
    razon: Optional[str] = None


class StatusHistoryRead(BaseModel):
    id: str
    estado_anterior: Optional[str]
    estado_nuevo: str
    razon: Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class ProjectRead(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str]
    cliente_area: str
    prioridad: str
    estado: str
    deadline: Optional[date]
    fecha_inicio: Optional[date]
    estimated_hours: Optional[float]
    total_hours: float
    tags: Optional[str]
    bloqueado: bool
    dias_en_estado_actual: int
    created_at: datetime
    updated_at: datetime
    responsable: Optional[str] = None
    specs_text: Optional[str] = None
    github_url: Optional[str] = None
    links_json: Optional[str] = None
    structure_text: Optional[str] = None
    structure_image_url: Optional[str] = None
    archived: bool = False
    tarifa_hora: Optional[float] = None
    presupuesto: Optional[float] = None
    drive_folder_id: Optional[str] = None
    calendar_event_id: Optional[str] = None
    status_history: List[StatusHistoryRead] = []
    work_hours: List["WorkHoursRead"] = []
    tasks: List["TaskRead"] = []
    blockers: List["BlockerRead"] = []
    notes: List["NoteRead"] = []

    class Config:
        from_attributes = True


# ─── WorkHours ──────────────────────────────────────────────────────────────

class WorkHoursCreate(BaseModel):
    horas: float = Field(..., gt=0)
    fecha: date = Field(default_factory=date.today)
    descripcion: Optional[str] = None


class WorkHoursRead(BaseModel):
    id: str
    project_id: str
    horas: float
    fecha: date
    descripcion: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Task ───────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    descripcion: str = Field(..., min_length=1)
    prioridad: Priority = Priority.media
    estimated_hours: Optional[float] = None
    fecha_inicio: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    task_type: str = "task"
    meeting_with: Optional[str] = None


class TaskUpdate(BaseModel):
    descripcion: Optional[str] = None
    prioridad: Optional[Priority] = None
    estimated_hours: Optional[float] = None
    fecha_vencimiento: Optional[date] = None
    subtareas_json: Optional[str] = None
    task_type: Optional[str] = None
    meeting_with: Optional[str] = None
    meeting_prep_url: Optional[str] = None
    meeting_prep_filename: Optional[str] = None


class TaskRead(BaseModel):
    id: str
    project_id: str
    descripcion: str
    prioridad: str
    estimated_hours: Optional[float]
    completada: bool
    completed_at: Optional[datetime]
    fecha_inicio: Optional[date]
    fecha_vencimiento: Optional[date]
    subtareas_json: Optional[str] = None
    elapsed_seconds: int = 0
    timer_started_at: Optional[datetime] = None
    task_type: str = "task"
    meeting_with: Optional[str] = None
    meeting_prep_url: Optional[str] = None
    meeting_prep_filename: Optional[str] = None
    calendar_event_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Blocker ────────────────────────────────────────────────────────────────

class BlockerCreate(BaseModel):
    descripcion: str = Field(..., min_length=1)
    tipo: BlockerType = BlockerType.otro


class BlockerRead(BaseModel):
    id: str
    project_id: str
    descripcion: str
    tipo: BlockerType
    resuelto: bool
    resolved_at: Optional[datetime]
    dias_sin_resolver: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Note ───────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    contenido: str = Field(..., min_length=1)
    tipo: NoteType = NoteType.otro


class NoteRead(BaseModel):
    id: str
    project_id: str
    contenido: str
    tipo: NoteType
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Chat ───────────────────────────────────────────────────────────────────

_ALLOWED_HISTORY_ROLES = {"user", "assistant"}
_ALLOWED_CONTENT_TYPES = {"text", "tool_use", "tool_result"}


class ChatMessage(BaseModel):
    mensaje: str = Field(..., min_length=1, max_length=4000)
    conversation_history: Optional[List[dict]] = Field(default_factory=list, max_length=100)

    @field_validator("mensaje")
    @classmethod
    def strip_mensaje(cls, v: str) -> str:
        return v.strip()

    @field_validator("conversation_history")
    @classmethod
    def sanitize_history(cls, history: Optional[List[dict]]) -> List[dict]:
        if not history:
            return []

        clean: List[dict] = []
        max_turns = settings.CHAT_MAX_HISTORY_TURNS * 2  # user + assistant per turn

        for turn in history[-max_turns:]:
            if not isinstance(turn, dict):
                continue
            role = turn.get("role")
            if role not in _ALLOWED_HISTORY_ROLES:
                continue  # drop injected system messages
            content = turn.get("content")
            if isinstance(content, str):
                # Truncate overly long history messages
                clean.append({"role": role, "content": content[:2000]})
            elif isinstance(content, list):
                # Tool use/result blocks — only allow known types, strip unknown keys
                safe_blocks = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype not in _ALLOWED_CONTENT_TYPES:
                        continue
                    if btype == "text":
                        safe_blocks.append({"type": "text", "text": str(block.get("text", ""))[:2000]})
                    elif btype == "tool_use":
                        safe_blocks.append({
                            "type": "tool_use",
                            "id": str(block.get("id", ""))[:64],
                            "name": str(block.get("name", ""))[:64],
                            "input": block.get("input", {}),
                        })
                    elif btype == "tool_result":
                        safe_blocks.append({
                            "type": "tool_result",
                            "tool_use_id": str(block.get("tool_use_id", ""))[:64],
                            "content": str(block.get("content", ""))[:2000],
                        })
                if safe_blocks:
                    clean.append({"role": role, "content": safe_blocks})
        return clean


class ChatResponse(BaseModel):
    respuesta: str
    tool_calls_executed: List[str] = []
    conversation_history: List[dict] = []


# ─── Summary ────────────────────────────────────────────────────────────────

class DailySummary(BaseModel):
    fecha: date
    total_horas: float
    tareas_completadas: int
    proyectos_tocados: List[str]
    proyectos_en_riesgo: List[str]
    bloqueadores_activos: int
