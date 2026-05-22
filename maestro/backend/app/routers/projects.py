import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import ProjectCreate, ProjectRead, ProjectUpdate, ProjectStatusUpdate, TaskRead, TaskUpdate
from ..services.project_service import ProjectService
from ..security import require_auth
from ..models.models import Task

_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
_SUPABASE_BUCKET = "maestro-uploads"

# ── Magic bytes para validación real de tipo de archivo ──────────────────────
_IMAGE_MAGIC: list[tuple[bytes, str, str]] = [
    (b'\xff\xd8\xff', '.jpg', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', '.png', 'image/png'),
    (b'GIF87a', '.gif', 'image/gif'),
    (b'GIF89a', '.gif', 'image/gif'),
    (b'RIFF', '.webp', 'image/webp'),   # verificar offset 8 para 'WEBP'
]
_SVG_PREFIXES = (b'<svg', b'<?xml', b'\xef\xbb\xbf<')  # UTF-8 BOM + XML


def _detect_image_type(content: bytes) -> tuple[str, str] | None:
    """Devuelve (ext, content_type) si el contenido es una imagen válida, sino None."""
    for magic, ext, ct in _IMAGE_MAGIC:
        if content.startswith(magic):
            if ext == '.webp' and len(content) >= 12 and content[8:12] != b'WEBP':
                continue
            return ext, ct
    # SVG: verificar que sea XML/SVG válido sin scripts
    if any(content.lstrip().startswith(p) for p in _SVG_PREFIXES):
        text = content[:500].decode('utf-8', errors='ignore').lower()
        if '<svg' in text and '<script' not in text:
            return '.svg', 'image/svg+xml'
    return None

_DOC_MAGIC: list[tuple[bytes, list[str]]] = [
    (b'%PDF', ['.pdf']),
    (b'PK\x03\x04', ['.docx', '.pptx', '.xlsx']),          # ZIP-based Office
    (b'\xd0\xcf\x11\xe0', ['.doc', '.xls', '.ppt']),        # Legacy Office (OLE)
]

def _detect_doc_type(content: bytes, claimed_ext: str) -> bool:
    """Verifica que el contenido sea un documento válido para la extensión reclamada."""
    for magic, exts in _DOC_MAGIC:
        if content.startswith(magic):
            return claimed_ext in exts
    # txt/md: solo texto plano
    if claimed_ext in ('.txt', '.md'):
        try:
            content[:1024].decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False
    # Imágenes dentro de documentos (png/jpg)
    if claimed_ext in ('.png', '.jpg', '.jpeg'):
        return _detect_image_type(content) is not None
    return False

router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(require_auth)])


async def _upload_to_supabase(content: bytes, filename: str, content_type: str) -> str:
    """Sube un archivo a Supabase Storage y devuelve la URL pública."""
    import httpx
    from ..config import settings
    base = settings.SUPABASE_URL.rstrip("/")
    headers_auth = {"Authorization": f"Bearer {settings.SUPABASE_KEY}"}

    async with httpx.AsyncClient(timeout=20) as client:
        # Crear bucket si no existe (409 = ya existe, ignorar)
        await client.post(
            f"{base}/storage/v1/bucket",
            headers={**headers_auth, "Content-Type": "application/json"},
            json={"id": _SUPABASE_BUCKET, "name": _SUPABASE_BUCKET, "public": True},
        )
        # Subir archivo
        r = await client.put(
            f"{base}/storage/v1/object/{_SUPABASE_BUCKET}/{filename}",
            headers={**headers_auth, "Content-Type": content_type},
            content=content,
        )
        if r.status_code not in (200, 201):
            raise Exception(f"Supabase Storage error {r.status_code}: {r.text[:200]}")

    return f"{base}/storage/v1/object/public/{_SUPABASE_BUCKET}/{filename}"


@router.get("/", response_model=List[ProjectRead])
def list_projects(db: Session = Depends(get_db)):
    return ProjectService.get_all(db)


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    return ProjectService.create(db, payload)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = ProjectService.update(db, project_id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.patch("/{project_id}/status", response_model=ProjectRead)
def change_status(project_id: str, payload: ProjectStatusUpdate, db: Session = Depends(get_db)):
    project = ProjectService.change_status(db, project_id, payload.estado, payload.razon)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project


@router.post("/{project_id}/structure-image", response_model=ProjectRead)
async def upload_structure_image(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    from ..config import settings
    project = ProjectService.get_by_id(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 5 MB")
    # Validar por magic bytes (no solo extensión)
    detected = _detect_image_type(content)
    if not detected:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido. Solo imágenes (JPG, PNG, GIF, WebP, SVG).")
    ext, ct = detected
    filename = f"struct_{project_id}_{uuid.uuid4().hex[:8]}{ext}"
    if settings.supabase_storage_enabled:
        image_url = await _upload_to_supabase(content, filename, ct)
    else:
        _UPLOADS_DIR.mkdir(exist_ok=True)
        (_UPLOADS_DIR / filename).write_bytes(content)
        image_url = f"/uploads/{filename}"
    payload = ProjectUpdate(structure_image_url=image_url)
    return ProjectService.update(db, project_id, payload)


@router.patch("/{project_id}/tasks/{task_id}", response_model=TaskRead)
def update_task(project_id: str, task_id: str, payload: TaskUpdate, db: Session = Depends(get_db)):
    from ..models.models import Task, Project
    from ..config import settings
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    updates = payload.model_dump(exclude_unset=True)
    old_fecha = task.fecha_vencimiento

    for field, value in updates.items():
        setattr(task, field, value)

    # Auto-sync a Google Calendar si Google está habilitado
    if settings.google_enabled:
        from ..services import google_service
        new_fecha = task.fecha_vencimiento
        project = db.query(Project).filter(Project.id == project_id).first()
        project_name = project.nombre if project else ""

        # Tarea con fecha de vencimiento nueva o cambiada
        if new_fecha and new_fecha != old_fecha:
            if task.calendar_event_id:
                google_service.update_deadline_event(task.calendar_event_id, task.descripcion, new_fecha)
            else:
                if task.task_type == "meeting":
                    event_id = google_service.create_meeting_event(
                        task.descripcion, new_fecha,
                        meeting_with=task.meeting_with or "",
                        project_name=project_name,
                    )
                else:
                    event_id = google_service.create_task_event(
                        task.descripcion, new_fecha, project_name, task.id
                    )
                if event_id:
                    task.calendar_event_id = event_id

        # Si se elimina la fecha, borrar evento de Calendar
        if "fecha_vencimiento" in updates and not new_fecha and task.calendar_event_id:
            google_service.delete_event(task.calendar_event_id)
            task.calendar_event_id = None

    db.commit()
    db.refresh(task)
    return task


@router.post("/{project_id}/tasks/{task_id}/prep-file", response_model=TaskRead)
async def upload_task_prep_file(project_id: str, task_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    from ..models.models import Task
    from ..config import settings
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    ext = Path(file.filename).suffix.lower() if file.filename else ".pdf"
    allowed = (".pdf", ".doc", ".docx", ".txt", ".md", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg")
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 10 MB")
    # Validar contenido real vs extensión declarada
    if not _detect_doc_type(content, ext):
        raise HTTPException(status_code=400, detail="El contenido del archivo no coincide con la extensión declarada.")
    orig_name = Path(file.filename).stem[:40] if file.filename else "prep"
    # Sanitizar nombre: solo caracteres seguros
    import re as _re
    orig_name = _re.sub(r'[^a-zA-Z0-9_\-]', '_', orig_name)
    filename = f"prep_{task_id}_{orig_name}{ext}"
    if settings.supabase_storage_enabled:
        ct = file.content_type or "application/octet-stream"
        prep_url = await _upload_to_supabase(content, filename, ct)
    else:
        _UPLOADS_DIR.mkdir(exist_ok=True)
        (_UPLOADS_DIR / filename).write_bytes(content)
        prep_url = f"/uploads/{filename}"
    task.meeting_prep_url = prep_url
    task.meeting_prep_filename = file.filename or filename
    db.commit()
    db.refresh(task)
    return task


@router.post("/{project_id}/tasks/{task_id}/timer/start", response_model=TaskRead)
def start_timer(project_id: str, task_id: str, db: Session = Depends(get_db)):
    from ..models.models import Task
    from datetime import datetime
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    task.timer_started_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.post("/{project_id}/tasks/{task_id}/timer/pause", response_model=TaskRead)
def pause_timer(project_id: str, task_id: str, db: Session = Depends(get_db)):
    from ..models.models import Task, WorkHours
    from datetime import datetime, date
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if task.timer_started_at:
        elapsed = int((datetime.utcnow() - task.timer_started_at).total_seconds())
        task.elapsed_seconds = (task.elapsed_seconds or 0) + elapsed
        task.timer_started_at = None
        # Registrar horas automáticamente si el timer estuvo activo >= 1 minuto
        if elapsed >= 60:
            horas = round(elapsed / 3600, 2)
            wh = WorkHours(
                project_id=project_id,
                horas=horas,
                fecha=date.today(),
                descripcion=f"Timer: {task.descripcion[:60]}",
            )
            db.add(wh)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{project_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(project_id: str, task_id: str, db: Session = Depends(get_db), _=Depends(require_auth)):
    task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    # Borrar evento de Calendar si existe
    if task.calendar_event_id:
        try:
            from ..services import google_service
            google_service.delete_event(task.calendar_event_id)
        except Exception:
            pass
    db.delete(task)
    db.commit()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    if not ProjectService.delete(db, project_id):
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
