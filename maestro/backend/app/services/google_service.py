"""
Servicio de integración con Google Drive y Google Calendar.

Usa una Service Account (el mismo credenciales.json del proyecto SCBA).
La cuenta de servicio debe tener acceso compartido a la carpeta de Drive y al calendario.

Docs:
- Drive: https://developers.google.com/drive/api/v3/reference
- Calendar: https://developers.google.com/calendar/api/v3/reference
"""
from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/calendar",
]

_MIME_FOLDER = "application/vnd.google-apps.folder"


def _get_credentials():
    """
    Devuelve credenciales de Google.
    Prioridad: OAuth personal → Service Account.
    """
    if settings.google_oauth_enabled:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GRequest
        creds = Credentials(
            token=None,
            refresh_token=settings.GOOGLE_OAUTH_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=_SCOPES,
        )
        creds.refresh(GRequest())
        return creds

    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(
        settings.GOOGLE_CREDENTIALS_PATH,
        scopes=_SCOPES,
    )


# ── Google Drive ──────────────────────────────────────────────────────────────

def get_or_create_project_folder(project_name: str) -> Optional[str]:
    """
    Busca o crea una subcarpeta con el nombre del proyecto dentro de GOOGLE_DRIVE_ROOT_FOLDER_ID.
    Devuelve el folder_id o None si la integración no está habilitada.
    """
    if not settings.google_enabled:
        return None

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        parent = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID or "root"

        # Buscar carpeta existente
        query = (
            f"name='{project_name}' and mimeType='{_MIME_FOLDER}' "
            f"and '{parent}' in parents and trashed=false"
        )
        resp = service.files().list(q=query, spaces="drive", fields="files(id,name)").execute()
        files = resp.get("files", [])
        if files:
            return files[0]["id"]

        # Crear nueva carpeta
        meta = {
            "name": project_name,
            "mimeType": _MIME_FOLDER,
            "parents": [parent],
        }
        folder = service.files().create(body=meta, fields="id").execute()
        folder_id = folder["id"]
        logger.info("Drive: carpeta '%s' creada — %s", project_name, folder_id)
        return folder_id

    except Exception as exc:
        logger.warning("Drive get_or_create_folder error: %s", exc)
        return None


def list_project_files(folder_id: str) -> list[dict]:
    """Lista los archivos dentro de una carpeta de proyecto en Drive."""
    if not settings.google_enabled or not folder_id:
        return []

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        query = f"'{folder_id}' in parents and trashed=false"
        resp = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name,mimeType,size,modifiedTime,webViewLink)",
        ).execute()
        return resp.get("files", [])

    except Exception as exc:
        logger.warning("Drive list_project_files error: %s", exc)
        return []


def get_folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"


# ── Google Calendar ───────────────────────────────────────────────────────────

def create_deadline_event(project_name: str, deadline: date, description: str = "") -> Optional[str]:
    """
    Crea un evento de un día en el calendario para el deadline del proyecto.
    Devuelve el event_id o None si la integración no está habilitada.
    """
    if not settings.google_enabled:
        return None

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        event = {
            "summary": f"[MAESTRO] Deadline: {project_name}",
            "description": description or f"Deadline del proyecto {project_name} en MAESTRO.",
            "start": {"date": deadline.isoformat()},
            "end": {"date": deadline.isoformat()},
            "colorId": "11",  # rojo
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60 * 24},  # 1 día antes
                    {"method": "popup", "minutes": 60 * 24 * 3},  # 3 días antes
                ],
            },
        }
        result = service.events().insert(
            calendarId=settings.GOOGLE_CALENDAR_ID, body=event
        ).execute()
        event_id = result["id"]
        logger.info("Calendar: evento creado para '%s' — %s", project_name, event_id)
        return event_id

    except Exception as exc:
        logger.warning("Calendar create_deadline_event error: %s", exc)
        return None


def update_deadline_event(event_id: str, project_name: str, new_deadline: date) -> bool:
    """Actualiza la fecha de un evento existente."""
    if not settings.google_enabled or not event_id:
        return False

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        event = service.events().get(
            calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id
        ).execute()
        event["start"] = {"date": new_deadline.isoformat()}
        event["end"] = {"date": new_deadline.isoformat()}
        event["summary"] = f"[MAESTRO] Deadline: {project_name}"
        service.events().update(
            calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id, body=event
        ).execute()
        return True

    except Exception as exc:
        logger.warning("Calendar update_deadline_event error: %s", exc)
        return False


def delete_event(event_id: str) -> bool:
    if not settings.google_enabled or not event_id:
        return False

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        service.events().delete(
            calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id
        ).execute()
        return True

    except Exception as exc:
        logger.warning("Calendar delete_event error: %s", exc)
        return False


def create_task_event(task_name: str, due_date: date, project_name: str, task_id: str = "") -> Optional[str]:
    """Crea un evento de un día en Calendar para el vencimiento de una tarea."""
    if not settings.google_enabled:
        return None
    try:
        from googleapiclient.discovery import build
        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = {
            "summary": f"[MAESTRO] Tarea: {task_name}",
            "description": f"Tarea del proyecto '{project_name}' en MAESTRO.",
            "start": {"date": due_date.isoformat()},
            "end": {"date": due_date.isoformat()},
            "colorId": "9",  # azul
            "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 60 * 24}]},
        }
        result = service.events().insert(calendarId=settings.GOOGLE_CALENDAR_ID, body=event).execute()
        return result["id"]
    except Exception as exc:
        logger.warning("Calendar create_task_event error: %s", exc)
        return None


def create_meeting_event(meeting_desc: str, meeting_date: date, meeting_with: str = "", project_name: str = "") -> Optional[str]:
    """Crea un evento en Calendar para una reunión."""
    if not settings.google_enabled:
        return None
    try:
        from googleapiclient.discovery import build
        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        summary = f"[MAESTRO] Reunión: {meeting_desc}"
        desc_parts = []
        if meeting_with:
            desc_parts.append(f"Con: {meeting_with}")
        if project_name:
            desc_parts.append(f"Proyecto: {project_name}")
        event = {
            "summary": summary,
            "description": "\n".join(desc_parts) if desc_parts else f"Reunión registrada en MAESTRO.",
            "start": {"date": meeting_date.isoformat()},
            "end": {"date": meeting_date.isoformat()},
            "colorId": "6",  # naranja
            "reminders": {"useDefault": False, "overrides": [
                {"method": "popup", "minutes": 60},
                {"method": "popup", "minutes": 60 * 24},
            ]},
        }
        result = service.events().insert(calendarId=settings.GOOGLE_CALENDAR_ID, body=event).execute()
        return result["id"]
    except Exception as exc:
        logger.warning("Calendar create_meeting_event error: %s", exc)
        return None


def get_upcoming_deadlines(days: int = 30) -> list[dict]:
    """Lista los eventos de MAESTRO en los próximos N días."""
    if not settings.google_enabled:
        return []

    try:
        from googleapiclient.discovery import build

        creds = _get_credentials()
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)

        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        resp = service.events().list(
            calendarId=settings.GOOGLE_CALENDAR_ID,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            q="[MAESTRO]",
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = []
        for e in resp.get("items", []):
            start = e.get("start", {})
            events.append({
                "id": e["id"],
                "titulo": e.get("summary", ""),
                "fecha": start.get("date") or start.get("dateTime", ""),
                "link": e.get("htmlLink", ""),
            })
        return events

    except Exception as exc:
        logger.warning("Calendar get_upcoming_deadlines error: %s", exc)
        return []
