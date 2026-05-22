import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .database import init_db
from .routers import auth, projects, hours, tasks, blockers, notes, chat, whatsapp
from .routers import settings_router, google_router, notifications
from .security import add_security_headers

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"

app = FastAPI(
    title="MAESTRO — Sistema de Gestión de Proyectos",
    description="API para tracking de automatizaciones con agente IA integrado",
    version="1.0.0",
    # Deshabilitar docs interactivos en producción
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Security headers en todas las respuestas
app.add_middleware(BaseHTTPMiddleware, dispatch=add_security_headers)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    max_age=600,
)


@app.on_event("startup")
def startup():
    init_db()
    _enforce_jwt_secret()


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _enforce_jwt_secret():
    """Auto-generates a secure JWT_SECRET if the default placeholder is detected."""
    if settings.JWT_SECRET != "change-me-in-production":
        import hashlib
        fp = hashlib.sha256(settings.JWT_SECRET.encode()).hexdigest()[:8]
        print(f"JWT_SECRET: ...{fp} (estable)")
        return
    import secrets as _secrets
    from dotenv import set_key
    new_secret = _secrets.token_hex(32)
    try:
        set_key(str(_ENV_FILE), "JWT_SECRET", new_secret)
        object.__setattr__(settings, "JWT_SECRET", new_secret)
        print("JWT_SECRET auto-generado y guardado en .env")
    except Exception as e:
        print(f"No se pudo escribir JWT_SECRET en .env: {e}")


app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(hours.router)
app.include_router(tasks.router)
app.include_router(blockers.router)
app.include_router(notes.router)
app.include_router(chat.router)
app.include_router(whatsapp.router)
app.include_router(settings_router.router)
app.include_router(google_router.router)
app.include_router(notifications.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def serve_index():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    from fastapi.responses import JSONResponse
    return JSONResponse({"error": f"Frontend no encontrado en: {FRONTEND_DIR}"}, status_code=503)


# Serve uploaded files (structure images)
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Serve frontend static files — mount after API routes
_frontend_abs = str(FRONTEND_DIR)
if FRONTEND_DIR.is_dir():
    app.mount("/app", StaticFiles(directory=_frontend_abs, html=True), name="frontend")
