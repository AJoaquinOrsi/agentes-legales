import json
from datetime import date, datetime
from typing import Any, Optional
import anthropic
from sqlalchemy.orm import Session

from ..config import settings
from ..models.models import ProjectStatus, Priority, BlockerType, NoteType
from ..schemas.schemas import (
    ProjectCreate, WorkHoursCreate, TaskCreate, BlockerCreate, NoteCreate, ProjectStatusUpdate
)
from .project_service import ProjectService
from ..prompts.agent_prompts import SYSTEM_PROMPT
from . import google_service, github_service

TOOLS: list[dict] = [
    {
        "name": "get_projects",
        "description": "Obtiene todos los proyectos activos con su estado, horas, bloqueadores y métricas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_completed": {
                    "type": "boolean",
                    "description": "Incluir proyectos en estado 'listo' o 'producción'. Default false.",
                }
            },
        },
    },
    {
        "name": "get_project_details",
        "description": "Obtiene todos los detalles de un proyecto: historial de estados, horas, tareas, bloqueadores y notas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto (puede ser parcial)"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "create_project",
        "description": "Crea un nuevo proyecto de automatización.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string"},
                "descripcion": {"type": "string"},
                "cliente_area": {"type": "string"},
                "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
                "deadline": {"type": "string", "description": "Fecha ISO YYYY-MM-DD (opcional)"},
                "estimated_hours": {"type": "number"},
                "tags": {"type": "string", "description": "Etiquetas separadas por coma (ej: RPA,API)"},
            },
            "required": ["nombre", "cliente_area"],
        },
    },
    {
        "name": "update_project_status",
        "description": "Cambia el estado de un proyecto. Estados válidos: en análisis, en desarrollo, testing, listo, producción.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto"},
                "nuevo_estado": {
                    "type": "string",
                    "enum": ["en análisis", "en desarrollo", "testing", "listo", "producción"],
                },
                "razon": {"type": "string", "description": "Razón del cambio (opcional)"},
            },
            "required": ["nombre", "nuevo_estado"],
        },
    },
    {
        "name": "add_work_hours",
        "description": "Registra horas trabajadas en un proyecto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto"},
                "horas": {"type": "number", "description": "Cantidad de horas (ej: 2.5)"},
                "fecha": {"type": "string", "description": "Fecha ISO YYYY-MM-DD. Si no se provee, usa hoy."},
                "descripcion": {"type": "string", "description": "Qué se hizo"},
            },
            "required": ["nombre", "horas"],
        },
    },
    {
        "name": "create_task",
        "description": "Crea una tarea pendiente en un proyecto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_proyecto": {"type": "string"},
                "descripcion": {"type": "string"},
                "prioridad": {"type": "string", "enum": ["alta", "media", "baja"]},
                "estimated_hours": {"type": "number"},
                "fecha_inicio": {"type": "string", "description": "Fecha de inicio ISO YYYY-MM-DD (opcional)"},
                "fecha_vencimiento": {"type": "string", "description": "Fecha de vencimiento ISO YYYY-MM-DD (opcional)"},
            },
            "required": ["nombre_proyecto", "descripcion"],
        },
    },
    {
        "name": "complete_task",
        "description": "Marca una tarea como completada dado el nombre del proyecto y descripción de la tarea.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_proyecto": {"type": "string"},
                "descripcion_tarea": {"type": "string", "description": "Descripción parcial o completa de la tarea"},
            },
            "required": ["nombre_proyecto", "descripcion_tarea"],
        },
    },
    {
        "name": "create_blocker",
        "description": "Registra un bloqueador que impide el avance de un proyecto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_proyecto": {"type": "string"},
                "descripcion": {"type": "string"},
                "tipo": {
                    "type": "string",
                    "enum": ["esperando cliente", "sin acceso", "técnico", "otro"],
                },
            },
            "required": ["nombre_proyecto", "descripcion"],
        },
    },
    {
        "name": "resolve_blocker",
        "description": "Resuelve un bloqueador activo de un proyecto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_proyecto": {"type": "string"},
                "descripcion_bloqueador": {
                    "type": "string",
                    "description": "Descripción parcial del bloqueador a resolver",
                },
            },
            "required": ["nombre_proyecto"],
        },
    },
    {
        "name": "add_note",
        "description": "Agrega una nota, learning o decisión a un proyecto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre_proyecto": {"type": "string"},
                "contenido": {"type": "string"},
                "tipo": {"type": "string", "enum": ["learning", "decision", "reflection", "otro"]},
            },
            "required": ["nombre_proyecto", "contenido"],
        },
    },
    {
        "name": "get_daily_summary",
        "description": "Obtiene el resumen del día: horas trabajadas, tareas completadas, proyectos tocados y proyectos en riesgo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {"type": "string", "description": "Fecha ISO YYYY-MM-DD. Default: hoy."},
            },
        },
    },
    {
        "name": "get_projects_at_risk",
        "description": "Lista los proyectos en riesgo: bloqueados, sin actividad >3 días, deadline pasado o horas >150% del estimado.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_github_info",
        "description": "Obtiene estadísticas del repositorio de GitHub de un proyecto: último commit, PRs abiertos, issues, lenguaje.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto en MAESTRO"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "sync_deadline_to_calendar",
        "description": "Crea o actualiza el evento de deadline del proyecto en Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "get_drive_files",
        "description": "Lista los archivos del proyecto en Google Drive. Crea la carpeta si no existe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre del proyecto"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "get_upcoming_deadlines",
        "description": "Lista todos los deadlines de proyectos de MAESTRO en Google Calendar para los próximos días.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dias": {"type": "integer", "description": "Cuántos días hacia adelante mirar. Default: 30."},
            },
        },
    },
]


def _serialize(obj: Any) -> Any:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return {k: _serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


class ClaudeService:
    def __init__(self, db: Session):
        self.db = db
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ── tool dispatcher ──────────────────────────────────────────────────────

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> dict:
        db = self.db

        if tool_name == "get_projects":
            include_done = tool_input.get("include_completed", False)
            projects = ProjectService.get_all(db)
            if not include_done:
                projects = [
                    p for p in projects
                    if p.estado not in (ProjectStatus.listo, ProjectStatus.produccion)
                ]
            result = []
            for p in projects:
                result.append({
                    "id": p.id,
                    "nombre": p.nombre,
                    "estado": p.estado.value,
                    "prioridad": p.prioridad.value,
                    "dias_en_estado": p.dias_en_estado_actual,
                    "horas_estimadas": p.estimated_hours,
                    "horas_reales": p.total_hours,
                    "bloqueado": p.bloqueado,
                    "deadline": p.deadline.isoformat() if p.deadline else None,
                    "bloqueadores_activos": len(p.active_blockers),
                    "tareas_pendientes": sum(1 for t in p.tasks if not t.completada),
                })
            return {"proyectos": result, "total": len(result)}

        elif tool_name == "get_project_details":
            nombre = tool_input["nombre"]
            project = self._find_project(nombre)
            if not project:
                return {"error": f"Proyecto '{nombre}' no encontrado"}
            return {
                "id": project.id,
                "nombre": project.nombre,
                "descripcion": project.descripcion,
                "cliente_area": project.cliente_area,
                "prioridad": project.prioridad.value,
                "estado": project.estado.value,
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "estimated_hours": project.estimated_hours,
                "total_hours": project.total_hours,
                "tags": project.tags,
                "bloqueado": project.bloqueado,
                "dias_en_estado": project.dias_en_estado_actual,
                "created_at": project.created_at.isoformat(),
                "status_history": [
                    {
                        "de": h.estado_anterior.value if h.estado_anterior else None,
                        "a": h.estado_nuevo.value,
                        "razon": h.razon,
                        "fecha": h.changed_at.isoformat(),
                    }
                    for h in sorted(project.status_history, key=lambda x: x.changed_at)
                ],
                "horas_por_dia": [
                    {"fecha": wh.fecha.isoformat(), "horas": wh.horas, "descripcion": wh.descripcion}
                    for wh in sorted(project.work_hours, key=lambda x: x.fecha)
                ],
                "tareas": [
                    {
                        "descripcion": t.descripcion,
                        "prioridad": t.prioridad.value,
                        "completada": t.completada,
                        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    }
                    for t in project.tasks
                ],
                "bloqueadores": [
                    {
                        "id": b.id,
                        "descripcion": b.descripcion,
                        "tipo": b.tipo.value,
                        "resuelto": b.resuelto,
                        "dias_sin_resolver": b.dias_sin_resolver,
                    }
                    for b in project.blockers
                ],
                "notas": [
                    {"tipo": n.tipo.value, "contenido": n.contenido, "fecha": n.created_at.isoformat()}
                    for n in project.notes
                ],
            }

        elif tool_name == "create_project":
            deadline = None
            if tool_input.get("deadline"):
                deadline = date.fromisoformat(tool_input["deadline"])
            payload = ProjectCreate(
                nombre=tool_input["nombre"],
                descripcion=tool_input.get("descripcion"),
                cliente_area=tool_input["cliente_area"],
                prioridad=Priority(tool_input.get("prioridad", "media")),
                deadline=deadline,
                estimated_hours=tool_input.get("estimated_hours"),
                tags=tool_input.get("tags"),
            )
            project = ProjectService.create(db, payload)
            return {"success": True, "id": project.id, "nombre": project.nombre, "estado": project.estado.value}

        elif tool_name == "update_project_status":
            project = self._find_project(tool_input["nombre"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre']}' no encontrado"}
            nuevo = ProjectStatus(tool_input["nuevo_estado"])
            updated = ProjectService.change_status(db, project.id, nuevo, tool_input.get("razon"))
            return {
                "success": True,
                "nombre": updated.nombre,
                "estado_anterior": tool_input["nuevo_estado"],
                "estado_nuevo": updated.estado.value,
                "dias_en_estado_anterior": updated.dias_en_estado_actual,
            }

        elif tool_name == "add_work_hours":
            project = self._find_project(tool_input["nombre"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre']}' no encontrado"}
            target_date = date.fromisoformat(tool_input["fecha"]) if tool_input.get("fecha") else date.today()
            payload = WorkHoursCreate(
                horas=tool_input["horas"],
                fecha=target_date,
                descripcion=tool_input.get("descripcion"),
            )
            ProjectService.add_work_hours(db, project.id, payload)
            db.refresh(project)
            return {
                "success": True,
                "nombre": project.nombre,
                "horas_agregadas": tool_input["horas"],
                "total_horas": project.total_hours,
                "horas_estimadas": project.estimated_hours,
            }

        elif tool_name == "create_task":
            project = self._find_project(tool_input["nombre_proyecto"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre_proyecto']}' no encontrado"}
            fecha_inicio = date.fromisoformat(tool_input["fecha_inicio"]) if tool_input.get("fecha_inicio") else None
            fecha_vencimiento = date.fromisoformat(tool_input["fecha_vencimiento"]) if tool_input.get("fecha_vencimiento") else None
            payload = TaskCreate(
                descripcion=tool_input["descripcion"],
                prioridad=Priority(tool_input.get("prioridad", "media")),
                estimated_hours=tool_input.get("estimated_hours"),
                fecha_inicio=fecha_inicio,
                fecha_vencimiento=fecha_vencimiento,
            )
            task = ProjectService.create_task(db, project.id, payload)
            return {
                "success": True, "id": task.id, "descripcion": task.descripcion, "prioridad": task.prioridad.value,
                "fecha_inicio": task.fecha_inicio.isoformat() if task.fecha_inicio else None,
                "fecha_vencimiento": task.fecha_vencimiento.isoformat() if task.fecha_vencimiento else None,
            }

        elif tool_name == "complete_task":
            project = self._find_project(tool_input["nombre_proyecto"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre_proyecto']}' no encontrado"}
            desc = tool_input["descripcion_tarea"].lower()
            task = next(
                (t for t in project.tasks if not t.completada and desc in t.descripcion.lower()),
                None,
            )
            if not task:
                return {"error": f"Tarea no encontrada en {project.nombre}"}
            updated = ProjectService.complete_task(db, project.id, task.id)
            return {"success": True, "descripcion": updated.descripcion, "completed_at": updated.completed_at.isoformat()}

        elif tool_name == "create_blocker":
            project = self._find_project(tool_input["nombre_proyecto"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre_proyecto']}' no encontrado"}
            payload = BlockerCreate(
                descripcion=tool_input["descripcion"],
                tipo=BlockerType(tool_input.get("tipo", "otro")),
            )
            blocker = ProjectService.create_blocker(db, project.id, payload)
            return {"success": True, "id": blocker.id, "descripcion": blocker.descripcion, "proyecto_bloqueado": True}

        elif tool_name == "resolve_blocker":
            project = self._find_project(tool_input["nombre_proyecto"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre_proyecto']}' no encontrado"}
            desc = (tool_input.get("descripcion_bloqueador") or "").lower()
            blocker = next(
                (b for b in project.blockers if not b.resuelto and (not desc or desc in b.descripcion.lower())),
                None,
            )
            if not blocker:
                return {"error": f"No hay bloqueadores activos en {project.nombre}"}
            updated = ProjectService.resolve_blocker(db, project.id, blocker.id)
            db.refresh(project)
            return {
                "success": True,
                "descripcion": updated.descripcion,
                "proyecto_aun_bloqueado": project.bloqueado,
            }

        elif tool_name == "add_note":
            project = self._find_project(tool_input["nombre_proyecto"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre_proyecto']}' no encontrado"}
            payload = NoteCreate(
                contenido=tool_input["contenido"],
                tipo=NoteType(tool_input.get("tipo", "otro")),
            )
            note = ProjectService.add_note(db, project.id, payload)
            return {"success": True, "id": note.id, "tipo": note.tipo.value}

        elif tool_name == "get_daily_summary":
            target = date.fromisoformat(tool_input["fecha"]) if tool_input.get("fecha") else date.today()
            return ProjectService.get_daily_summary(self.db, target)

        elif tool_name == "get_projects_at_risk":
            at_risk = ProjectService.get_projects_at_risk(db)
            return {
                "proyectos_en_riesgo": [
                    {
                        "nombre": p.nombre,
                        "estado": p.estado.value,
                        "bloqueado": p.bloqueado,
                        "dias_en_estado": p.dias_en_estado_actual,
                        "horas_estimadas": p.estimated_hours,
                        "horas_reales": p.total_hours,
                        "deadline": p.deadline.isoformat() if p.deadline else None,
                        "bloqueadores_activos": [
                            {"descripcion": b.descripcion, "dias": b.dias_sin_resolver}
                            for b in p.active_blockers
                        ],
                    }
                    for p in at_risk
                ],
                "total": len(at_risk),
            }

        elif tool_name == "get_github_info":
            project = self._find_project(tool_input["nombre"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre']}' no encontrado"}
            if not project.github_url:
                return {"error": f"El proyecto '{project.nombre}' no tiene URL de GitHub configurada."}
            stats = github_service.get_repo_stats(project.github_url)
            return {"proyecto": project.nombre, "github": stats}

        elif tool_name == "sync_deadline_to_calendar":
            project = self._find_project(tool_input["nombre"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre']}' no encontrado"}
            if not settings.google_enabled:
                return {"error": "Integración con Google Calendar no configurada. Verificá GOOGLE_CREDENTIALS_PATH en .env"}
            if not project.deadline:
                return {"error": f"El proyecto '{project.nombre}' no tiene deadline configurado"}
            if project.calendar_event_id:
                ok = google_service.update_deadline_event(
                    project.calendar_event_id, project.nombre, project.deadline
                )
                if ok:
                    return {"success": True, "accion": "actualizado", "deadline": project.deadline.isoformat()}
            event_id = google_service.create_deadline_event(
                project.nombre, project.deadline,
                description=project.descripcion or ""
            )
            if event_id:
                project.calendar_event_id = event_id
                self.db.commit()
                return {"success": True, "accion": "creado", "event_id": event_id, "deadline": project.deadline.isoformat()}
            return {"error": "No se pudo crear el evento en Google Calendar"}

        elif tool_name == "get_drive_files":
            project = self._find_project(tool_input["nombre"])
            if not project:
                return {"error": f"Proyecto '{tool_input['nombre']}' no encontrado"}
            if not settings.google_enabled:
                return {"error": "Integración con Google Drive no configurada. Verificá GOOGLE_CREDENTIALS_PATH en .env"}
            if not project.drive_folder_id:
                folder_id = google_service.get_or_create_project_folder(project.nombre)
                if folder_id:
                    project.drive_folder_id = folder_id
                    self.db.commit()
                else:
                    return {"error": "No se pudo crear la carpeta en Google Drive"}
            files = google_service.list_project_files(project.drive_folder_id)
            return {
                "proyecto": project.nombre,
                "carpeta_id": project.drive_folder_id,
                "carpeta_url": google_service.get_folder_url(project.drive_folder_id),
                "archivos": files,
                "total": len(files),
            }

        elif tool_name == "get_upcoming_deadlines":
            if not settings.google_enabled:
                return {"error": "Integración con Google Calendar no configurada"}
            dias = tool_input.get("dias", 30)
            events = google_service.get_upcoming_deadlines(days=dias)
            return {"proximos_deadlines": events, "total": len(events), "dias": dias}

        return {"error": f"Herramienta desconocida: {tool_name}"}

    def _find_project(self, nombre: str):
        all_projects = ProjectService.get_all(self.db)
        nombre_lower = nombre.lower()
        # exact match first
        for p in all_projects:
            if p.nombre.lower() == nombre_lower:
                return p
        # partial match
        for p in all_projects:
            if nombre_lower in p.nombre.lower() or p.nombre.lower() in nombre_lower:
                return p
        return None

    # ── agentic loop ─────────────────────────────────────────────────────────

    async def chat(self, mensaje: str, history: list) -> dict:
        today = date.today().isoformat()
        system = SYSTEM_PROMPT.replace("{{fecha_hoy}}", today)

        messages = list(history) + [{"role": "user", "content": mensaje}]
        tools_executed: list[str] = []

        while True:
            response = self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            # append assistant turn
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text = next(
                    (block.text for block in response.content if hasattr(block, "text")), ""
                )
                return {
                    "respuesta": text,
                    "tool_calls_executed": tools_executed,
                    "conversation_history": messages,
                }

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    result = self._dispatch_tool(block.name, block.input)
                    tools_executed.append(block.name)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str, ensure_ascii=False),
                    })
                messages.append({"role": "user", "content": tool_results})
                continue

            # unexpected stop reason
            break

        return {
            "respuesta": "No se pudo procesar la respuesta.",
            "tool_calls_executed": tools_executed,
            "conversation_history": messages,
        }
