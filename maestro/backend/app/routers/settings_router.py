"""
Router de configuración del sistema — lee y escribe variables en .env.

GET  /settings/integrations → devuelve config actual (secrets enmascarados)
POST /settings/integrations → actualiza variables en .env (requiere restart para aplicar)
POST /settings/test/{service} → verifica conectividad de un servicio
"""
import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import set_key

from ..config import settings
from ..security import require_auth
from .auth import require_admin

router = APIRouter(prefix="/settings", tags=["settings"])

# Ruta absoluta del .env (relativa a este archivo, no a CWD)
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
_ENV_EXAMPLE = Path(__file__).resolve().parent.parent.parent / ".env.example"


_PLACEHOLDER_PATTERNS = (
    "[project-ref]", "[ref]", "...", "xxxxxxx", "XXXXXXXX",
    "eyJ...", "ghp_...", "EAAxxxxxxx", "1234567890",
    "ACxxxxxxx", "change-me",
)


def _is_placeholder(value: str) -> bool:
    """Detecta si un valor es un placeholder de ejemplo, no un valor real."""
    if not value:
        return True
    v = value.strip()
    for pat in _PLACEHOLDER_PATTERNS:
        if pat.lower() in v.lower():
            return True
    return False


def _real_value(value: str) -> bool:
    """True si el valor existe y no es un placeholder."""
    return bool(value) and not _is_placeholder(value)


def _mask(value: str) -> str:
    """Enmascara un secreto mostrando solo los primeros y últimos 4 chars."""
    if not value or _is_placeholder(value):
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return value[:4] + "•••" + value[-4:]


def _is_masked(value: str) -> bool:
    """Detecta si un valor enviado desde el frontend es la versión enmascarada (no cambió)."""
    return "•••" in value


def _ensure_env_file():
    """Crea .env desde .env.example si no existe."""
    if not _ENV_PATH.exists():
        if _ENV_EXAMPLE.exists():
            shutil.copy(_ENV_EXAMPLE, _ENV_PATH)
        else:
            _ENV_PATH.touch()
    return _ENV_PATH


# ── Schemas ───────────────────────────────────────────────────────────────────

_OAUTH_REDIRECT_URI = "http://2.24.108.79:8000/settings/google/callback"
_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar.events",
]


class IntegrationsUpdate(BaseModel):
    # Anthropic
    anthropic_api_key: Optional[str] = None
    # Supabase
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    # Google OAuth
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    # Google general
    google_credentials_path: Optional[str] = None
    google_drive_folder_id: Optional[str] = None
    google_calendar_id: Optional[str] = None
    # GitHub
    github_token: Optional[str] = None
    # WhatsApp
    whatsapp_provider: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from: Optional[str] = None
    meta_token: Optional[str] = None
    meta_phone_id: Optional[str] = None
    meta_verify_token: Optional[str] = None
    # Claude
    claude_model: Optional[str] = None
    # DB
    database_url: Optional[str] = None


_FIELD_TO_ENV: dict[str, str] = {
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "supabase_url": "SUPABASE_URL",
    "supabase_key": "SUPABASE_KEY",
    "google_oauth_client_id": "GOOGLE_OAUTH_CLIENT_ID",
    "google_oauth_client_secret": "GOOGLE_OAUTH_CLIENT_SECRET",
    "google_credentials_path": "GOOGLE_CREDENTIALS_PATH",
    "google_drive_folder_id": "GOOGLE_DRIVE_ROOT_FOLDER_ID",
    "google_calendar_id": "GOOGLE_CALENDAR_ID",
    "github_token": "GITHUB_TOKEN",
    "whatsapp_provider": "WHATSAPP_PROVIDER",
    "twilio_account_sid": "TWILIO_ACCOUNT_SID",
    "twilio_auth_token": "TWILIO_AUTH_TOKEN",
    "twilio_from": "TWILIO_WHATSAPP_FROM",
    "meta_token": "META_WHATSAPP_TOKEN",
    "meta_phone_id": "META_WHATSAPP_PHONE_ID",
    "meta_verify_token": "META_WEBHOOK_VERIFY_TOKEN",
    "claude_model": "CLAUDE_MODEL",
    "database_url": "DATABASE_URL",
}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/google-service-account-email", dependencies=[Depends(require_admin)])
def get_google_service_account_email():
    """Lee el email de la service account del credentials JSON configurado."""
    import json
    path = settings.GOOGLE_CREDENTIALS_PATH
    if not path or not Path(path).exists():
        return {"email": None, "error": "Archivo no encontrado"}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return {"email": data.get("client_email", ""), "project_id": data.get("project_id", "")}
    except Exception as e:
        return {"email": None, "error": str(e)}


@router.get("/google/auth-url", dependencies=[Depends(require_admin)])
def get_google_auth_url():
    """Genera la URL de autorización OAuth de Google."""
    import urllib.parse
    if not _real_value(settings.GOOGLE_OAUTH_CLIENT_ID) or not _real_value(settings.GOOGLE_OAUTH_CLIENT_SECRET):
        raise HTTPException(400, "Guardá primero el Client ID y Client Secret antes de conectar.")
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": _OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return {"url": url}


@router.get("/google/callback")
def google_oauth_callback(code: str = None, error: str = None):
    """Recibe el código OAuth de Google, intercambia por refresh token y lo guarda en .env."""
    import urllib.request, urllib.parse, json as _json

    _fail = lambda msg: HTMLResponse(f"""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:40px;text-align:center">
<h2 style="color:#dc2626">Error al conectar con Google</h2><p>{msg}</p>
<p>Cerrá esta ventana y volvé a intentarlo.</p></body></html>""")

    if error:
        return _fail(error)
    if not code:
        return _fail("No se recibió código de autorización.")

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": _OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            tokens = _json.loads(resp.read())
    except Exception as e:
        return _fail(f"Error al obtener tokens: {e}")

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        return _fail(
            "Google no envió refresh token. "
            "Revocá el acceso de MAESTRO en "
            "<a href='https://myaccount.google.com/permissions' target='_blank'>myaccount.google.com/permissions</a> "
            "y volvé a conectar."
        )

    env_path = _ensure_env_file()
    set_key(str(env_path), "GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token)
    object.__setattr__(settings, "GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token)

    return HTMLResponse("""<!DOCTYPE html><html>
<body style="font-family:sans-serif;padding:40px;text-align:center;background:#f0fdf4">
<h2 style="color:#16a34a">&#10003; Conectado con Google</h2>
<p>Tu Drive y Calendar personal están vinculados a MAESTRO.</p>
<p style="color:#6b7280;font-size:14px">Esta ventana se cerrará automáticamente...</p>
<script>
  window.opener && window.opener.postMessage({type:"maestro:google-connected"},"*");
  setTimeout(() => window.close(), 2000);
</script>
</body></html>""")


@router.post("/google/disconnect", dependencies=[Depends(require_admin)])
def google_disconnect():
    """Elimina el refresh token de OAuth (desconecta la cuenta personal)."""
    env_path = _ensure_env_file()
    set_key(str(env_path), "GOOGLE_OAUTH_REFRESH_TOKEN", "")
    object.__setattr__(settings, "GOOGLE_OAUTH_REFRESH_TOKEN", "")
    return {"success": True}


@router.get("/integrations", dependencies=[Depends(require_admin)])
def get_integrations():
    """Devuelve el estado actual de todas las integraciones con secretos enmascarados."""
    import os
    google_oauth_ok = bool(
        _real_value(settings.GOOGLE_OAUTH_CLIENT_ID) and
        _real_value(settings.GOOGLE_OAUTH_CLIENT_SECRET) and
        _real_value(settings.GOOGLE_OAUTH_REFRESH_TOKEN)
    )
    google_sa_ok = bool(
        _real_value(settings.GOOGLE_CREDENTIALS_PATH) and
        os.path.exists(settings.GOOGLE_CREDENTIALS_PATH)
    )
    return {
        "env_file_exists": _ENV_PATH.exists(),
        "supabase": {
            "url": settings.SUPABASE_URL if _real_value(settings.SUPABASE_URL) else "",
            "key": _mask(settings.SUPABASE_KEY),
            "enabled": _real_value(settings.SUPABASE_URL) and _real_value(settings.SUPABASE_KEY),
        },
        "google": {
            "oauth_client_id": _mask(settings.GOOGLE_OAUTH_CLIENT_ID),
            "oauth_client_secret": _mask(settings.GOOGLE_OAUTH_CLIENT_SECRET),
            "oauth_connected": google_oauth_ok,
            "credentials_path": settings.GOOGLE_CREDENTIALS_PATH if _real_value(settings.GOOGLE_CREDENTIALS_PATH) else "",
            "drive_folder_id": settings.GOOGLE_DRIVE_ROOT_FOLDER_ID if _real_value(settings.GOOGLE_DRIVE_ROOT_FOLDER_ID) else "",
            "calendar_id": settings.GOOGLE_CALENDAR_ID,
            "enabled": google_oauth_ok or google_sa_ok,
        },
        "github": {
            "token": _mask(settings.GITHUB_TOKEN),
            "enabled": _real_value(settings.GITHUB_TOKEN),
        },
        "whatsapp": {
            "provider": settings.WHATSAPP_PROVIDER,
            "twilio_account_sid": settings.TWILIO_ACCOUNT_SID if _real_value(settings.TWILIO_ACCOUNT_SID) else "",
            "twilio_auth_token": _mask(settings.TWILIO_AUTH_TOKEN),
            "twilio_from": settings.TWILIO_WHATSAPP_FROM if _real_value(settings.TWILIO_WHATSAPP_FROM) else "",
            "meta_token": _mask(settings.META_WHATSAPP_TOKEN),
            "meta_phone_id": settings.META_WHATSAPP_PHONE_ID if _real_value(settings.META_WHATSAPP_PHONE_ID) else "",
            "verify_token": settings.META_WEBHOOK_VERIFY_TOKEN,
            "enabled": (
                (_real_value(settings.TWILIO_ACCOUNT_SID) and _real_value(settings.TWILIO_AUTH_TOKEN))
                if settings.WHATSAPP_PROVIDER == "twilio"
                else (_real_value(settings.META_WHATSAPP_TOKEN) and _real_value(settings.META_WHATSAPP_PHONE_ID))
            ),
        },
        "claude": {
            "model": settings.CLAUDE_MODEL,
            "api_key": _mask(settings.ANTHROPIC_API_KEY),
            "enabled": _real_value(settings.ANTHROPIC_API_KEY),
        },
        "database": {
            "url_type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
            "enabled": True,
        },
    }


@router.post("/integrations", dependencies=[Depends(require_admin)])
def update_integrations(payload: IntegrationsUpdate):
    """
    Escribe las variables provistas en el archivo .env.
    Los valores enmascarados (contienen •••) se ignoran automáticamente.
    Requiere reiniciar el servidor para que los cambios surtan efecto.
    """
    env_path = _ensure_env_file()
    updated: list[str] = []
    skipped: list[str] = []

    data = payload.model_dump(exclude_none=True)
    for field, env_key in _FIELD_TO_ENV.items():
        if field not in data:
            continue
        value = data[field]
        # Ignorar valores enmascarados (el usuario no los cambió)
        if isinstance(value, str) and _is_masked(value):
            skipped.append(env_key)
            continue
        # No sobreescribir con string vacío si ya tiene valor
        if value == "" and os.getenv(env_key):
            skipped.append(env_key)
            continue
        set_key(str(env_path), env_key, value or "")
        updated.append(env_key)

    return {
        "success": True,
        "updated": updated,
        "skipped": skipped,
        "requires_restart": len(updated) > 0,
        "message": (
            f"✓ {len(updated)} variable(s) guardadas en .env."
            + (" Reiniciá el servidor para aplicar los cambios." if updated else "")
        ) if updated else "No hubo cambios que guardar.",
    }


@router.post("/test/{service}", dependencies=[Depends(require_admin)])
async def test_service(service: str):
    """Prueba la conectividad de un servicio configurado."""
    if service == "google":
        if not settings.google_enabled:
            return {"ok": False, "message": "Credenciales de Google no configuradas"}
        try:
            from ..services.google_service import _get_credentials
            creds = _get_credentials()
            return {"ok": True, "message": f"Service account autenticado · {creds.service_account_email}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    elif service == "github":
        if not settings.github_enabled:
            return {"ok": False, "message": "GITHUB_TOKEN no configurado"}
        try:
            import httpx
            r = httpx.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                         "Accept": "application/vnd.github+json"},
                timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                return {"ok": True, "message": f"Conectado como @{data.get('login', '?')} · {data.get('public_repos', 0)} repos"}
            return {"ok": False, "message": f"GitHub respondió {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    elif service == "claude":
        if not settings.ANTHROPIC_API_KEY:
            return {"ok": False, "message": "ANTHROPIC_API_KEY no configurada"}
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            r = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "ok"}],
            )
            return {"ok": True, "message": f"API activa · modelo {settings.CLAUDE_MODEL}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    elif service == "supabase":
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            return {"ok": False, "message": "SUPABASE_URL o SUPABASE_KEY no configurados"}
        try:
            import httpx
            base = settings.SUPABASE_URL.rstrip("/")
            headers = {"Authorization": f"Bearer {settings.SUPABASE_KEY}"}
            # Test: listar buckets de Storage
            r = httpx.get(f"{base}/storage/v1/bucket", headers=headers, timeout=8)
            if r.status_code == 200:
                buckets = [b.get("id") for b in r.json()]
                return {"ok": True, "message": f"Supabase Storage OK · buckets: {buckets or 'ninguno aún'}"}
            # Fallback: test REST API
            r2 = httpx.get(f"{base}/rest/v1/", headers={"apikey": settings.SUPABASE_KEY}, timeout=8)
            if r2.status_code in (200, 404):
                return {"ok": True, "message": "Supabase accesible (REST)"}
            return {"ok": False, "message": f"Supabase respondió {r.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    elif service == "whatsapp":
        if not settings.whatsapp_enabled:
            return {"ok": False, "message": "WhatsApp no configurado"}
        return {"ok": True, "message": f"Proveedor: {settings.WHATSAPP_PROVIDER} · credenciales presentes"}

    return {"ok": False, "message": f"Servicio desconocido: {service}"}
