"""
Foliar — Agente de formularios (Flask backend)
Ejecutar: python app.py  →  http://localhost:5000
"""
import os, re, json, uuid, tempfile, threading, queue, time, io, zipfile
import urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ── Cargar variables de entorno desde .env (si existe) ───────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv no instalado → solo variables del sistema
from flask import Flask, request, send_file, send_from_directory, jsonify, render_template, Response, stream_with_context, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import anthropic
import pdfplumber
from pypdf import PdfReader, PdfWriter

import combo_templates as ct

# Generación de telegrama PDF y escrito DOCX (combo)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

# ── Entorno ───────────────────────────────────────────────────────────────────
_IS_PROD = bool(
    os.environ.get("RAILWAY_ENVIRONMENT") or
    os.environ.get("PRODUCTION") or
    os.environ.get("FOLIAR_ENV", "").lower() == "production"
)

# ── ProxyFix: necesario cuando Flask corre detrás de Nginx ───────────────────
# Hace que Flask confíe en X-Forwarded-Proto para detectar HTTPS correctamente.
if _IS_PROD:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ── Secret key: env var (VPS) → archivo .secret_key (local) → generada ───────
_secret_from_env = os.environ.get("FLASK_SECRET_KEY", "").strip()
if _secret_from_env:
    app.config["SECRET_KEY"] = _secret_from_env.encode("utf-8")
else:
    _key_file = Path(__file__).parent / ".secret_key"
    if _key_file.exists():
        app.config["SECRET_KEY"] = _key_file.read_bytes()
    else:
        _secret = os.urandom(32)
        _key_file.write_bytes(_secret)
        app.config["SECRET_KEY"] = _secret

# ── Cookies de sesión seguras ─────────────────────────────────────────────────
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=_IS_PROD,   # solo HTTPS en producción
    PERMANENT_SESSION_LIFETIME=86400 * 7,
)

# ── Base de datos ────────────────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(Path(__file__).parent / "foliar.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],          # sin límite global por defecto
    storage_uri="memory://",
)

# ── Login manager ────────────────────────────────────────────────────────────
login_manager = LoginManager(app)
login_manager.login_view = "auth_login"
login_manager.login_message = "Iniciá sesión para continuar."
login_manager.login_message_category = "info"

# ── Headers de seguridad ──────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    # Prevenir que el browser interprete el MIME incorrecto
    response.headers["X-Content-Type-Options"] = "nosniff"
    # No permitir que la app se cargue en iframes de otros sitios
    response.headers["X-Frame-Options"] = "DENY"
    # Política de referrer
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Deshabilitar permisos innecesarios del browser
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "frame-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp
    if _IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# ── Modelo de usuario ────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    username       = db.Column(db.String(80),  unique=True, nullable=False)
    email          = db.Column(db.String(120), unique=True, nullable=False)
    password_hash  = db.Column(db.String(256), nullable=False)
    password_plain = db.Column(db.String(256), nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    rol            = db.Column(db.String(20), default="Editor")  # Admin / Editor / Visor
    last_seen      = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash  = generate_password_hash(password)
        self.password_plain = password

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AuditLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actor_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    actor_name = db.Column(db.String(80), nullable=False)
    accion     = db.Column(db.String(50), nullable=False)   # user_created / role_changed / user_deleted / password_changed
    target     = db.Column(db.String(120), nullable=True)   # nombre del usuario afectado
    detalle    = db.Column(db.String(200), nullable=True)   # ej: "Editor → Admin"

    def to_dict(self):
        delta = datetime.utcnow() - self.created_at
        if delta.total_seconds() < 60:
            t = "ahora"
        elif delta.total_seconds() < 3600:
            t = f"hace {int(delta.total_seconds() / 60)} min"
        elif delta.total_seconds() < 86400:
            t = f"hace {int(delta.total_seconds() / 3600)} h"
        elif delta.days < 7:
            t = f"hace {delta.days} d"
        else:
            t = self.created_at.strftime("%d %b")
        return {"id": self.id, "t": t, "actor": self.actor_name,
                "accion": self.accion, "target": self.target, "detalle": self.detalle}


def _audit(accion, target=None, detalle=None):
    """Registra un evento de auditoría con el usuario actual como actor."""
    try:
        actor_name = current_user.username if current_user.is_authenticated else "sistema"
        actor_id   = current_user.id if current_user.is_authenticated else None
        log = AuditLog(actor_id=actor_id, actor_name=actor_name,
                       accion=accion, target=target, detalle=detalle)
        db.session.add(log)
    except Exception:
        pass  # el log nunca debe interrumpir la operación principal


class Tramite(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    codigo      = db.Column(db.String(20), unique=True, nullable=False)  # TR-XXXX
    producto    = db.Column(db.String(20), nullable=False)               # formulario / telegrama / escrito / combo
    titulo      = db.Column(db.String(200), nullable=False)
    estado      = db.Column(db.String(30), default="Borrador")           # Borrador / En revisión / Despachado / Presentado
    conf        = db.Column(db.Float, default=0.9)
    campos      = db.Column(db.String(60), default="")                    # ej: "46/46" o "CD 88421"
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    user        = db.relationship("User", backref="tramites")

    def to_dict(self):
        delta = datetime.utcnow() - self.created_at
        if delta.total_seconds() < 60:
            t = "ahora"
        elif delta.total_seconds() < 3600:
            t = f"hace {int(delta.total_seconds() / 60)} min"
        elif delta.total_seconds() < 86400:
            t = f"hace {int(delta.total_seconds() / 3600)} h"
        elif delta.days < 7:
            t = f"hace {delta.days} d"
        else:
            t = self.created_at.strftime("%d %b")
        return {
            "id": self.codigo,
            "producto": self.producto,
            "titulo": self.titulo,
            "estado": self.estado,
            "conf": self.conf,
            "campos": self.campos,
            "t": t,
            "autor": self.user.username if self.user else "",
        }


def _ensure_user_columns():
    """Agrega columnas faltantes a la tabla user si la BD ya existe y promueve al primer usuario a Admin."""
    try:
        from sqlalchemy import text, inspect
        insp = inspect(db.engine)
        cols = {c["name"] for c in insp.get_columns("user")}
        if "rol" not in cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN rol VARCHAR(20) DEFAULT 'Editor'"))
        if "last_seen" not in cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN last_seen DATETIME"))
        if "password_plain" not in cols:
            db.session.execute(text("ALTER TABLE user ADD COLUMN password_plain VARCHAR(256)"))
        # Crear tabla audit_log si no existe (BD antigua sin ella)
        tables = inspect(db.engine).get_table_names()
        if "audit_log" not in tables:
            db.create_all()
        db.session.commit()
        # Si no hay ningún Admin, promover al usuario más antiguo
        if not User.query.filter_by(rol="Admin").first():
            first = User.query.order_by(User.created_at.asc()).first()
            if first:
                first.rol = "Admin"
                db.session.commit()
    except Exception:
        db.session.rollback()


def _next_tramite_codigo() -> str:
    last = Tramite.query.order_by(Tramite.id.desc()).first()
    n = (last.id + 1) if last else 1
    return f"TR-{2600 + n:04d}"


def _visor_blocked():
    """Retorna respuesta 403 si el usuario tiene rol Visor. Usar al inicio de rutas de escritura."""
    if getattr(current_user, "rol", "Editor") == "Visor":
        return jsonify({"error": "Los usuarios Visor no pueden realizar esta acción."}), 403
    return None


def require_role(*roles):
    """Decorador que restringe una ruta a los roles indicados.
    Jerarquía: Admin > Editor > Visor.
    Uso: @require_role("Admin") o @require_role("Admin", "Editor")
    """
    import functools
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            user_rol = getattr(current_user, "rol", "Editor") or "Editor"
            if user_rol not in roles:
                return jsonify({"ok": False, "error": "No tenés permiso para realizar esta acción."}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Sesión expirada. Volvé a iniciar sesión."}), 401
    return redirect(url_for("auth_login"))

# ── Rutas & paths ────────────────────────────────────────────────────────────
_ASSETS_DIR = Path(__file__).parent / "assets"
# Versión reparada del PDF (campos "Nombre y Apellido" trabajador y letrado separados)
FORM_PDF        = str(_ASSETS_DIR / "anexo_i_base.pdf")
FIELD_INFO_JSON = str(_ASSETS_DIR / "field_info.json")
# Fallback: si no están en assets/, buscarlos en el Escritorio (ubicación legacy)
if not Path(FORM_PDF).exists():
    FORM_PDF = str(Path(__file__).parent.parent / "anexo_i_-_incapacidad.pdf")
if not Path(FIELD_INFO_JSON).exists():
    FIELD_INFO_JSON = str(Path(__file__).parent.parent / "field_info.json")
TELEGRAMA_PDF   = str(Path(__file__).parent / "MODELO AMPLIACION.pdf")
_CONFIG_FILE    = Path(__file__).parent / "config.json"

def _load_config() -> dict:
    """Lee configuración con esta prioridad:
    1. Variables de entorno (ANTHROPIC_API_KEY, FOLIAR_MODEL, FOLIAR_ESTUDIO)
    2. config.json (guardado desde la UI)
    3. Valores por defecto
    """
    defaults = {
        "anthropic_api_key": "",
        "model":             "claude-sonnet-4-6",
        "estudio_nombre":    "Estudio Arrechea",
    }
    # Leer config.json como base (puede ser sobreescrito por env vars)
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in data.items():
                if v:
                    defaults[k] = v
        except Exception:
            pass
    # Las variables de entorno tienen MÁXIMA PRIORIDAD — no se pueden sobreescribir
    # desde la UI. Esto protege las credenciales en el VPS.
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        defaults["anthropic_api_key"] = env_key
    env_model = os.environ.get("FOLIAR_MODEL", "").strip()
    if env_model:
        defaults["model"] = env_model
    env_estudio = os.environ.get("FOLIAR_ESTUDIO", "").strip()
    if env_estudio:
        defaults["estudio_nombre"] = env_estudio
    return defaults


def _save_config(updates: dict) -> dict:
    """Guarda cambios en config.json. Solo Admin puede llamar esto."""
    ALLOWED = {"anthropic_api_key", "model", "estudio_nombre"}
    MODELS  = {"claude-sonnet-4-6", "claude-haiku-4-5", "claude-opus-4-5"}
    cfg = {}
    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    saved, errors = [], []
    for k, v in updates.items():
        if k not in ALLOWED:
            errors.append(f"Campo no permitido: {k}"); continue
        v = str(v).strip() if v else ""
        if not v:
            continue  # vacío = no modificar
        if k == "model" and v not in MODELS:
            errors.append(f"Modelo no válido: {v}"); continue
        if k == "anthropic_api_key":
            # Si viene de env var, no permitir cambio desde la UI
            if os.environ.get("ANTHROPIC_API_KEY", "").strip():
                errors.append("La API key está fijada por variable de entorno del servidor y no se puede cambiar desde aquí.")
                continue
            if not v.startswith("sk-ant-"):
                errors.append("La API key debe empezar con 'sk-ant-'"); continue
        cfg[k] = v
        saved.append(k)
    if saved:
        _CONFIG_FILE.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return {"ok": True, "saved": saved, "errors": errors}


def _load_api_key() -> str:
    env_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if env_key:
        return env_key
    key = _load_config().get("anthropic_api_key", "").strip()
    if key and not key.startswith("sk-ant-PONE"):
        return key
    raise RuntimeError("Falta la API key. Configurala desde el panel de Configuración (Admin).")


def _get_model() -> str:
    """Retorna el modelo Claude activo según config."""
    return _load_config().get("model", "claude-sonnet-4-6")

_sessions: dict = {}   # token -> {queue, path?, fields?, status, created_at}

# ── Limpieza automática de sesiones viejas (cada hora) ───────────────────────
def _session_cleanup_worker():
    while True:
        time.sleep(3600)
        cutoff = time.time() - 3600 * 6   # eliminar con más de 6 horas
        to_del = [k for k, v in list(_sessions.items()) if v.get("created_at", 0) < cutoff]
        for k in to_del:
            session = _sessions.pop(k, None)
            if session:
                path = session.get("path")
                if path:
                    try: os.unlink(path)
                    except OSError: pass

threading.Thread(target=_session_cleanup_worker, daemon=True).start()

# ── Validación de PDF por magic bytes ────────────────────────────────────────
def _is_valid_pdf(file_storage) -> bool:
    header = file_storage.read(4)
    file_storage.seek(0)
    return header == b"%PDF"

# ── Modelos y límites permitidos para /api/chat ───────────────────────────────
_ALLOWED_MODELS = {"claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-7"}
_MAX_TOKENS_CAP = 4000

# ── Datos fijos del letrado ───────────────────────────────────────────────────
_LETRADO_CUIT      = "20348263812"
_LETRADO_MATRICULA = "T° 129 F° 33 / CASI T° LII F° 52"

# ── Base de datos de ARTs ─────────────────────────────────────────────────────
_ART_DATABASE = [
    {"nombre": "Berkley International A.R.T. S.A.",                          "cuit": "30-68589307-6", "keywords": ["berkley", "berkeley"]},
    {"nombre": "Prevención Aseguradora de Riesgos del Trabajo S.A.",          "cuit": "30-68436191-7", "keywords": ["prevención", "prevencion", "prev art"]},
    {"nombre": "EXPERTA ASEGURADORA DE RIESGOS DEL TRABAJO S.A.",             "cuit": "30-68715616-8", "keywords": ["experta"]},
    {"nombre": "Inca Aseguradora de Riesgos del Trabajo S.A.",                "cuit": "30-68833640-2", "keywords": ["inca"]},
    {"nombre": "Provincia Aseguradora de Riesgos del Trabajo S.A.",           "cuit": "30-68825409-0", "keywords": ["provincia art", "provincia aseguradora"]},
    {"nombre": "La Segunda Aseguradora de Riesgos del Trabajo S.A.",          "cuit": "30-68913348-3", "keywords": ["la segunda", "segunda art"]},
    {"nombre": "Aseguradora de Riesgos de Trabajo Interacción S.A.",          "cuit": "33-68717056-9", "keywords": ["interacción", "interaccion"]},
    {"nombre": "Federación Patronal Seguros S.A.U.",                          "cuit": "33-70736658-9", "keywords": ["federación patronal", "federacion patronal"]},
    {"nombre": "Sul America A.R.T. S.A.",                                     "cuit": "30-68825294-2", "keywords": ["sul america", "sulamerica"]},
    {"nombre": "Responsabilidad Patronal Aseguradora de Riesgos del Trabajo S.A.", "cuit": "33-68804343-9", "keywords": ["responsabilidad patronal"]},
    {"nombre": "MAPFRE ARGENTINA ART S.A.",                                   "cuit": "30-68649089-7", "keywords": ["mapfre"]},
    {"nombre": "SWISS MEDICAL ART S.A.U.",                                    "cuit": "33-68626286-9", "keywords": ["swiss medical", "swiss"]},
    {"nombre": "QBE Aseguradora de Riesgos del Trabajo S.A.",                 "cuit": "30-68727613-9", "keywords": ["qbe"]},
    {"nombre": "ASOCIART SA ASEGURADORA DE RIESGOS DEL TRABAJO",              "cuit": "30-68627333-0", "keywords": ["asociart"]},
    {"nombre": "SMG Aseguradora de Riesgos del Trabajo S.A.",                 "cuit": "30-71095695-9", "keywords": ["smg"]},
    {"nombre": "ASEGURADORA DE RIESGOS DEL TRABAJO LIDERAR S.A.",             "cuit": "30-71122767-5", "keywords": ["liderar"]},
    {"nombre": "Caminos Protegidos Aseguradora de Riesgos del Trabajo S.A.U.","cuit": "33-71105830-9", "keywords": ["caminos protegidos"]},
    {"nombre": "SERENA ASEGURADORA DE RIESGOS DEL TRABAJO S.A.U.",            "cuit": "30-71234180-3", "keywords": ["serena"]},
    {"nombre": "ANDINA ART S.A.",                                             "cuit": "33-71699299-9", "keywords": ["andina"]},
    {"nombre": "PARANA ASEGURADORA DE RIESGOS DEL TRABAJO SA",                "cuit": "30-71856742-0", "keywords": ["parana", "paraná"]},
    {"nombre": "Solart Aseguradora de Riesgos del Trabajo S.A.",              "cuit": "30-68591441-3", "keywords": ["solart"]},
    {"nombre": "Reconquista A.R.T. S.A.",                                     "cuit": "30-63278185-3", "keywords": ["reconquista"]},
    {"nombre": "Luz Aseg. de Riesgos del Trabajo S.A.",                       "cuit": "33-68627616-9", "keywords": ["luz art", "luz aseg"]},
    {"nombre": "MUTUAL DE EMPLEADOS Y OBREROS PETROLEROS PRIVADOS ART MUTUAL","cuit": "30-71500295-3", "keywords": ["petroleros privados", "obreros petroleros"]},
    {"nombre": "ART MUTUAL RURAL DE SEGUROS DE RIESGOS DEL TRABAJO",          "cuit": "30-71621143-2", "keywords": ["mutual rural", "art mutual rural"]},
    {"nombre": "ART MUTUAL DE EMPLEADOS MECANICOS Y AFINES DEL TRANSPORTE AUTOMOTOR SAN FRANCISC", "cuit": "30-71721658-6", "keywords": ["mecanicos", "mecánicos", "transporte automotor san"]},
    {"nombre": "La Ibero Platense Compañía de Seguros S.A.",                  "cuit": "30-50004892-8", "keywords": ["ibero platense"]},
    {"nombre": "La Meridional Compañía Argentina de Seguros S.A.",            "cuit": "30-50005116-3", "keywords": ["meridional"]},
    {"nombre": "Cenit Seguros",                                               "cuit": "30-50005673-4", "keywords": ["cenit"]},
    {"nombre": "Compañía Argentina de Seguros Latitud Sur S.A.",              "cuit": "30-50006638-1", "keywords": ["latitud sur"]},
    {"nombre": "Copan Cooperativa de Seguros Ltda.",                          "cuit": "30-50005192-9", "keywords": ["copan"]},
]

def _lookup_art(nombre_pdf: str) -> dict | None:
    """Busca la ART por nombre aproximado usando keywords y solapamiento de palabras."""
    if not nombre_pdf:
        return None
    nombre_lower = nombre_pdf.lower().strip()
    # Primero por keywords exactas
    for art in _ART_DATABASE:
        for kw in art["keywords"]:
            if kw in nombre_lower:
                return art
    # Fallback: solapamiento de palabras significativas
    stopwords = {"de", "del", "la", "el", "los", "las", "y", "a", "sa", "srl",
                 "art", "aseguradora", "riesgos", "trabajo", "s.a.", "s.a.u.",
                 "compañía", "argentina", "seguros"}
    words = {w.strip(".,") for w in nombre_lower.split()} - stopwords
    best, best_score = None, 0
    for art in _ART_DATABASE:
        art_words = {w.strip(".,") for w in art["nombre"].lower().split()} - stopwords
        score = len(words & art_words)
        if score > best_score:
            best_score, best = score, art
    return best if best_score >= 1 else None

# ── Claude API retry helper ──────────────────────────────────────────────────

def _claude_call_with_retry(fn, max_tries: int = 3, step_name: str = "Claude"):
    """
    Llama a fn() con reintentos ante errores transitorios de la API de Anthropic.
    Espera 5s, 15s, 30s entre intentos (backoff progresivo).
    Lanza la excepción original si se agotan todos los intentos.
    """
    WAIT = [5, 15, 30]
    TRANSIENT_KEYWORDS = (
        "overloaded", "529", "timeout", "timed out", "connection",
        "rate_limit", "429", "500", "502", "503", "504",
        "remote end closed", "read timed out",
    )
    last_err = None
    for attempt in range(max_tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            is_transient = any(k in msg for k in TRANSIENT_KEYWORDS)
            if attempt < max_tries - 1 and is_transient:
                wait = WAIT[min(attempt, len(WAIT) - 1)]
                app.logger.warning(
                    f"[retry] {step_name} falló (intento {attempt+1}/{max_tries}): "
                    f"{str(e)[:120]} — reintentando en {wait}s"
                )
                time.sleep(wait)
                last_err = e
            else:
                raise
    raise last_err


# ── Text extraction ──────────────────────────────────────────────────────────

def extract_text(path: str) -> str:
    """Extrae texto del PDF con tres intentos en cascada:
    1. pdfplumber  2. pymupdf  3. Claude Vision (para PDFs con texto vectorizado)."""
    MIN_CHARS = 80

    # ── Intento 1: pdfplumber ────────────────────────────────────────────────
    text = ""
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                t = page.extract_text()
                if t:
                    text += f"\n--- PÁGINA {i+1} ---\n{t}"
        text = text.strip()
    except Exception:
        text = ""

    if len(text) >= MIN_CHARS:
        return text

    # ── Intento 2: pymupdf ───────────────────────────────────────────────────
    text_fitz = ""
    try:
        import fitz
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            t = page.get_text("text")
            if t and t.strip():
                text_fitz += f"\n--- PÁGINA {i+1} ---\n{t.strip()}"
        doc.close()
        text_fitz = text_fitz.strip()
    except Exception:
        text_fitz = ""

    best = text_fitz if len(text_fitz) > len(text) else text
    if len(best) >= MIN_CHARS:
        return best

    # ── Intento 3: Claude Vision (PDF con texto vectorizado / curvas) ────────
    return _extract_text_via_vision(path)


def _extract_text_via_vision(path: str) -> str:
    """Renderiza cada página del PDF como imagen y usa Claude para leer el texto.
    Necesario cuando el PDF tiene texto convertido a curvas vectoriales."""
    import fitz, base64 as _b64
    try:
        api_key = _load_api_key()
    except RuntimeError:
        return ""
    try:
        doc = fitz.open(path)
        content = []
        for i, page in enumerate(doc):
            mat = fitz.Matrix(150 / 72, 150 / 72)   # 150 DPI — buena calidad sin exceder tokens
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            img_b64 = _b64.b64encode(pix.tobytes("png")).decode()
            content.append({"type": "text", "text": f"--- PÁGINA {i+1} ---"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
            })
        doc.close()
        content.append({
            "type": "text",
            "text": (
                "Transcribí completamente todo el texto visible en estas páginas. "
                "Mantené el orden, estructura y todos los datos. No omitas nada."
            ),
        })
        client = anthropic.Anthropic(api_key=api_key)
        msg = _claude_call_with_retry(
            lambda: client.messages.create(
                model=_get_model(),
                max_tokens=4000,
                messages=[{"role": "user", "content": content}],
            ),
            step_name="Vision OCR",
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception:
        return ""

# ── Claude prompt ────────────────────────────────────────────────────────────

def build_prompt(text: str) -> str:
    return (
        "Eres un asistente especializado en extraer datos de documentos legales argentinos "
        "para completar formularios de ART (Aseguradoras de Riesgos del Trabajo).\n\n"
        "TAREA: Analiza el documento y extrae SOLO los campos indicados.\n\n"
        "FORMATO DE SALIDA OBLIGATORIO: Emite SOLO líneas JSON, una por campo detectado. "
        "No emitas nada más — ni texto, ni markdown, ni explicaciones.\n"
        'Formato: {"field": "FIELD_ID", "value": "valor", "confidence": 0.95}\n\n'
        "CAMPOS A EXTRAER (usa el FIELD_ID exactamente como aparece aquí):\n"
        "0.  Nombre y Apellido → Apellido y nombre del TRABAJADOR (formato 'APELLIDO, Nombre' en mayúsculas/minúsculas naturales)\n"
        "1.  CUIL → CUIL del trabajador (formato XX-XXXXXXXX-X). SOLO el CUIL.\n"
        "2.  NombreRazón Social → Nombre o razón social del EMPLEADOR\n"
        "3.  CUIT → CUIT del empleador\n"
        "4.  Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta → Dirección del lugar de trabajo\n"
        "5.  Localidad → Localidad del lugar de trabajo\n"
        "6.  Provincia → Provincia del lugar de trabajo (si no figura, usar 'BUENOS AIRES')\n"
        "7.  art_nombre → Nombre completo de la ART mencionada en el documento\n"
        "8.  tipo_contingencia → SOLO uno de: accidente_trabajo, accidente_in_itinere, enfermedad_profesional\n"
        "9.  fecha_accidente → Fecha del accidente/siniestro en formato DD/MM/YYYY\n"
        "10. Detalle accidente o enfermedad profesional → Descripción del accidente tal como figura en el documento\n"
        "11. Detallá la o las afecciones o diagnósticos derivados de la contingencia → Lo que figura como 'Daños Sufridos' en el documento\n"
        "12. prueba_medica → Buscá en el documento cualquier sección llamada 'Tratamiento Recibido', 'Tratamiento médico', 'Tratamientos', 'Atención recibida', 'Estudios realizados' o similar. Copiá su contenido completo. Si no encontrás una sección específica, extraé cualquier información sobre tratamientos, estudios o atención médica que figure en el documento.\n\n"
        "REGLAS:\n"
        "- Emite SOLO los campos que encuentres en el documento\n"
        "- NO inventes datos que no estén en el documento\n"
        "- confidence entre 0 y 1\n"
        "- Transcribe el nombre de la ART (art_nombre) exactamente como aparece\n"
        "- Sin markdown, comentarios ni texto adicional\n\n"
        "DOCUMENTO:\n"
        f"{text}\n\n"
        "Emití las líneas JSON ahora:"
    )

# ── Form filling ─────────────────────────────────────────────────────────────

def build_field_values(extracted: dict, field_info: list) -> list:
    tipo  = extracted.get("tipo_contingencia", {}).get("value", "")
    fecha = extracted.get("fecha_accidente", {}).get("value", "")

    # Lookup ART por nombre extraído del PDF
    art_data = _lookup_art(extracted.get("art_nombre", {}).get("value", ""))

    # Checkboxes: tipo contingencia depende del PDF; resto son valores fijos
    checkbox_map = {
        # Tipo contingencia (pág 1) — extraído del PDF
        "undefined":   tipo == "accidente_trabajo",
        "undefined_2": tipo == "accidente_in_itinere",
        "undefined_3": tipo == "enfermedad_profesional",
        # Atención médica — valores FIJOS
        "Sí":   True,   # ¿Recibiste atención de la ART? → siempre Sí
        "No":   False,
        "Sí_2": True,   # ¿Recibiste alta médica? → siempre Sí
        "No_2": False,
        "Sí_3": False,  # ¿Atención Obra Social/Prepaga? → siempre No
        "No_3": True,
        "Sí_4": False,  # ¿Estudios Obra Social/Prepaga? → siempre No
        "No_4": True,
        # Preexistencias, Sí_5/No_5 y Opción de competencia: NO se tocan
    }

    # Valores de texto fijos (letrado + ART lookup + fechas)
    fixed_text: dict = {
        "CUIT / Domcilio electrónico": _LETRADO_CUIT,
        "Matrícula - Jurisdicción":    _LETRADO_MATRICULA,
    }
    if art_data:
        fixed_text["DenominaciónRazón Social"]    = art_data["nombre"]
        fixed_text["CUIT En caso de empleadores"] = art_data["cuit"]
    if fecha:
        fixed_text["Fecha de la denuncia_af_date"]              = fecha
        fixed_text["Fecha de baja laboral_af_date"]             = fecha
        fixed_text["Fecha de ocurrencia o diagnóstico_af_date"] = fecha

    # prueba_medica (virtual) → campo largo del formulario
    prueba = extracted.get("prueba_medica", {}).get("value", "")
    if prueba:
        fixed_text["Las partes deber\u00e1n ofrecer en su primera presentaci\u00f3n toda la prueba de la que intenten valerse acompa\u00f1ando en"] = prueba

    # Campos de texto extraídos del PDF
    pdf_text_fields = {
        "Nombre y Apellido",  # nombre del trabajador
        "CUIL",
        "NombreRazón Social",
        "CUIT",
        "Establecimiento del lugar de efectiva prestación de servicios o donde habitualmente reporta",
        "Localidad",
        "Provincia",
        "Detalle accidente o enfermedad profesional",
        "Detallá la o las afecciones o diagnósticos derivados de la contingencia",
    }

    # El nombre del letrado se reusa del nombre del trabajador? NO: el letrado siempre es ARRECHEA.
    # Se llena automáticamente con el dato fijo del estudio.
    fixed_text["Nombre y Apellido Letrado"] = "ARRECHEA, Leandro"
    fixed_text["Aclaración"]   = ""
    fixed_text["Aclaración_2"] = ""

    field_values = []
    for field in field_info:
        fid   = field["field_id"]
        ftype = field["type"]
        page  = field["page"]

        if ftype == "checkbox" and fid in checkbox_map:
            checked = checkbox_map[fid]
            field_values.append({"field_id": fid, "page": page,
                                  "value": field["checked_value"] if checked else field["unchecked_value"]})
        elif ftype == "text":
            if fid in fixed_text:
                field_values.append({"field_id": fid, "page": page, "value": fixed_text[fid]})
            elif fid in pdf_text_fields:
                ext = extracted.get(fid)
                if ext and ext.get("value"):
                    field_values.append({"field_id": fid, "page": page, "value": str(ext["value"])})
    return field_values


def _solidify_checkbox_ap(doc, widget):
    """Reemplaza la apariencia del casillero marcado con un rectángulo relleno sólido negro."""
    import fitz
    r = widget.rect
    w, h = r.width, r.height
    pad = max(0.8, min(w, h) * 0.12)
    stream = f"q 0 0 0 rg {pad:.2f} {pad:.2f} {w - 2*pad:.2f} {h - 2*pad:.2f} re f Q".encode()
    try:
        ann_obj = doc.xref_object(widget.xref, compressed=False)
        for pat in [r'/On\s+(\d+)\s+0\s+R', r'/N\s+(\d+)\s+0\s+R']:
            hit = re.search(pat, ann_obj)
            if hit:
                doc.update_stream(int(hit.group(1)), stream)
                return
    except Exception:
        pass


def fill_form(field_values: list, output_path: str):
    import fitz  # pymupdf

    RICHTEXT_BIT = 1 << 22
    MULTILINE_BIT = 1 << 12

    val_map = {fv["field_id"]: fv["value"] for fv in field_values}

    doc = fitz.open(FORM_PDF)
    for page in doc:
        for widget in page.widgets():
            name = widget.field_name
            if name not in val_map:
                continue
            value = val_map[name]
            if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                is_checked = (value == "On")
                widget.field_value = is_checked
                widget.update()
                if is_checked:
                    _solidify_checkbox_ap(doc, widget)
            else:
                if widget.field_flags & RICHTEXT_BIT:
                    widget.field_flags = (widget.field_flags & ~RICHTEXT_BIT) | MULTILINE_BIT
                widget.field_value = value
                widget.update()

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

# ── Worker thread ─────────────────────────────────────────────────────────────

def _extract_combo_vars(api_key: str, text: str) -> dict:
    """Extrae todas las variables que necesitan telegrama y escrito en una sola llamada a Claude.
    Devuelve un dict (puede tener strings vacíos si el PDF no traía el dato)."""
    client = anthropic.Anthropic(api_key=api_key)
    msg = _claude_call_with_retry(
        lambda: client.messages.create(
            model=_get_model(),
            max_tokens=2500,
            system=ct.PROMPT_EXTRACCION,
            messages=[{"role": "user", "content": f"Antecedentes del trabajador:\n\n{text[:15000]}"}],
        ),
        step_name="Extracción combo vars",
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    # Limpiar markdown fence si vino
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip("` \n")
    # Buscar el primer objeto JSON balanceado
    start = raw.find("{")
    if start == -1:
        return {}
    depth, in_str, esc, end = 0, False, False, -1
    for i, ch in enumerate(raw[start:]):
        if esc:
            esc = False; continue
        if ch == "\\" and in_str:
            esc = True; continue
        if ch == '"':
            in_str = not in_str; continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = start + i; break
    if end == -1:
        return {}
    try:
        return json.loads(raw[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return {}


def _generate_telegrama_data(api_key: str, text: str, prefetched: dict | None = None) -> dict:
    """Devuelve la estructura completa del telegrama lista para renderizar."""
    vars_ = prefetched if prefetched is not None else _extract_combo_vars(api_key, text)
    return ct.compose_telegrama(vars_)


def _generate_escrito_blocks(api_key: str, text: str, prefetched: dict | None = None) -> list:
    """Devuelve la lista de bloques del escrito lista para renderizar."""
    vars_ = prefetched if prefetched is not None else _extract_combo_vars(api_key, text)
    return ct.compose_escrito(vars_)


TELEGRAMA_BASE_PDF = Path(__file__).parent / "TELEGRAMA_BASE.pdf"

# Coordenadas extraídas de las líneas reales del PDF base (subrayados de cada campo).
# Los subrayados están en y=724.5 / 695.5 / 666.9 / 638.1 (col izq y der).
# El texto se asienta ~2pt por encima del subrayado.
# Página A4 = 595 x 842 pt
_TG_LAYOUT = {
    # DESTINATARIO  (línea x=31-283, ancho 252)
    "dest_razon":     ( 35, 727, 245),
    "dest_ramo":      ( 35, 698, 245),
    "dest_domicilio": ( 35, 669, 145),
    "dest_cp":        (190, 669,  90),
    "dest_localidad": ( 35, 640, 130),
    "dest_provincia": (180, 640, 100),
    # REMITENTE     (línea x=311-564, ancho 253)
    "rem_nombre":     (315, 727, 245),
    "rem_dni":        (315, 698, 130),
    "rem_fecha":      (455, 698, 105),
    "rem_domicilio":  (315, 669, 145),
    "rem_cp":         (470, 669,  90),
    "rem_localidad":  (315, 640, 130),
    "rem_provincia":  (455, 640, 105),
    # Cuerpo: caja del telegrama (lavanda) detectada entre y=590 (top) y y=127 (bottom),
    # x=58-1180 px → x=28-566 pt. Padding interior ~10pt para que el texto no toque los bordes.
    "body_top":       ( 40, 575, 515),  # baseline primera línea
    "body_line_h":    13,
    "body_y_min":     140,  # margen de seguridad arriba del borde inferior (y=127)
}


def _render_telegrama_pdf(data: dict, out_path: str) -> None:
    """Rellena el telegrama base con los datos provistos.
    `data` viene de ct.compose_telegrama(). El PDF base es TELEGRAMA_BASE.pdf."""
    if not _HAS_REPORTLAB or not TELEGRAMA_BASE_PDF.exists():
        # Fallback: texto plano
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(_telegrama_to_text(data))
        return

    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.lib.pagesizes import A4 as A4SIZE
    from reportlab.platypus import Frame, Paragraph
    from reportlab.lib.styles import ParagraphStyle as PS
    from reportlab.lib.enums import TA_JUSTIFY

    overlay_path = out_path + ".overlay"
    c = rl_canvas.Canvas(overlay_path, pagesize=A4SIZE)
    c.setFillColorRGB(0, 0, 0)

    def draw_value(key: str, value: str, font="Helvetica-Bold", size=10):
        if not value:
            return
        x, y, w = _TG_LAYOUT[key]
        sz = size
        while pdfmetrics.stringWidth(value, font, sz) > w and sz > 7:
            sz -= 0.5
        c.setFont(font, sz)
        c.drawString(x, y, value)

    dest = data["destinatario"]
    rem  = data["remitente"]

    draw_value("dest_razon",     dest["razon"])
    draw_value("dest_ramo",      dest["ramo"], font="Helvetica", size=9)
    draw_value("dest_domicilio", dest["domicilio"])
    draw_value("dest_cp",        dest["cp"])
    draw_value("dest_localidad", dest["localidad"])
    draw_value("dest_provincia", dest["provincia"])

    draw_value("rem_nombre",     rem["nombre"])
    draw_value("rem_dni",        rem["dni"])
    draw_value("rem_fecha",      rem["fecha"])
    draw_value("rem_domicilio",  rem["domicilio"])
    draw_value("rem_cp",         rem["cp"])
    draw_value("rem_localidad",  rem["localidad"])
    draw_value("rem_provincia",  rem["provincia"])

    # ── Cuerpo: 3 párrafos justificados dentro de una Frame ──────────────────
    bx, by, bw = _TG_LAYOUT["body_top"]
    by_min = _TG_LAYOUT["body_y_min"]
    body_h = by - by_min  # alto disponible

    body_style = PS(
        "body", fontName="Helvetica", fontSize=10, leading=13.5,
        alignment=TA_JUSTIFY, spaceAfter=8, firstLineIndent=0,
    )

    def _esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    paragraphs = [Paragraph(_esc(p.strip()), body_style) for p in data["cuerpo"] if p and p.strip()]

    # Frame con altura desde by_min hasta by (la baseline del primer renglón cae cerca de by)
    frame = Frame(bx, by_min, bw, body_h,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                  showBoundary=0)
    frame.addFromList(paragraphs, c)

    # Si quedó algo sin renderizar (texto muy largo) lo emitimos en otra página
    if paragraphs:
        c.showPage()
        from reportlab.lib.pagesizes import A4 as _A4
        frame2 = Frame(40, 60, _A4[0] - 80, _A4[1] - 120,
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                       showBoundary=0)
        frame2.addFromList(paragraphs, c)

    c.save()

    # Mergear overlay con el PDF base
    base = PdfReader(str(TELEGRAMA_BASE_PDF))
    over = PdfReader(overlay_path)
    writer = PdfWriter(clone_from=base)
    writer.pages[0].merge_page(over.pages[0])
    # Si el overlay tiene más páginas (cuerpo extenso), agregarlas
    for extra in over.pages[1:]:
        writer.add_page(extra)
    with open(out_path, "wb") as f:
        writer.write(f)
    try:
        os.unlink(overlay_path)
    except OSError:
        pass


def _telegrama_to_text(data: dict) -> str:
    """Fallback en texto plano si reportlab no está disponible."""
    lines = ["TELEGRAMA LEY N° 23.789", "Más de 30 palabras", "=" * 60, "",
             "DESTINATARIO", "-" * 12]
    for k in ("razon", "ramo", "domicilio", "cp", "localidad", "provincia"):
        lines.append(f"  {k.upper()}: {data['destinatario'][k]}")
    lines += ["", "REMITENTE", "-" * 9]
    for k in ("nombre", "dni", "domicilio", "cp", "localidad", "provincia", "fecha"):
        lines.append(f"  {k.upper()}: {data['remitente'][k]}")
    lines += ["", "CUERPO", "-" * 6]
    for p in data["cuerpo"]:
        lines += [p, ""]
    return "\n".join(lines)


def _render_escrito_pdf(blocks: list, out_path: str) -> None:
    """Renderiza el escrito en PDF emulando el estilo del estudio Arrechea:
    - Helvetica (≈ Arial) 9pt
    - Títulos centrados subrayados+negrita
    - Headings de sección (I.-, II.-, III.-, etc.) subrayados+negrita
    - Sub-headings (III. A), III.B.-, "En cumplimiento...") solo negrita
    - Negritas inline embebidas vía <b>...</b> en las plantillas
    - Párrafos justificados, sangría primer renglón
    `blocks` es lista de (tipo, texto) de ct.compose_escrito."""
    if not _HAS_REPORTLAB:
        with open(out_path, "w", encoding="utf-8") as f:
            for _, txt in blocks:
                # quitar markup HTML para fallback texto plano
                import re as _re
                clean = _re.sub(r"<[^>]+>", "", txt)
                f.write(clean + "\n\n")
        return

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2.0 * cm,
        title="Escrito judicial — Estudio Arrechea",
        author=ct.LETRADO["nombre"],
    )

    title_style = ParagraphStyle("title",
        fontName="Helvetica-Bold", fontSize=9, leading=14,
        alignment=TA_CENTER, spaceAfter=22, underlineWidth=0.6)
    # Heading principal con subrayado (I.-, II.-, ..., Señor Superintendente:)
    h_under_style = ParagraphStyle("h_under",
        fontName="Helvetica-Bold", fontSize=9, leading=14,
        alignment=TA_LEFT, spaceBefore=12, spaceAfter=8)
    # Sub-heading (sin subrayado, solo bold) — III. A), III.B.-, "En cumplimiento...", etc.
    h_bold_style = ParagraphStyle("h_bold",
        fontName="Helvetica-Bold", fontSize=9, leading=14,
        alignment=TA_LEFT, spaceBefore=10, spaceAfter=8)
    body_style = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9, leading=14,
        alignment=TA_JUSTIFY, firstLineIndent=24, spaceAfter=10)
    list_style = ParagraphStyle("list",
        fontName="Helvetica", fontSize=9, leading=14,
        alignment=TA_JUSTIFY, leftIndent=18, firstLineIndent=18, spaceAfter=8)
    sign_style = ParagraphStyle("sign",
        fontName="Helvetica-Bold", fontSize=9, leading=14,
        alignment=2, spaceBefore=28)

    # Patrones para clasificar cada subpárrafo
    # Match para headings con subrayado (secciones I a VII y "Señor Superintendente")
    HEADER_UNDERLINE = (
        "I.- ", "II.- ", "III.- ", "IV.- ", "V.- ", "VI.- ", "VII.- ",
        "Señor Superintendente",
    )
    # Match para sub-headings (solo negrita, sin subrayado)
    HEADER_BOLD = (
        "III. A)", "III.B.-", "III.A.-",
        "En cumplimiento con la Res", "a).- ", "b.- ", "b).- ",
    )
    # Match para listados numerados: "1.-", "2.-", "3.-", "4.-", ...
    import re as _re
    LIST_RE = _re.compile(r"^\d+\.\-\s")

    def classify(plain: str) -> str:
        """Quita el markup HTML inline para clasificar el subpárrafo."""
        bare = _re.sub(r"<[^>]+>", "", plain).lstrip()
        if bare.startswith(HEADER_UNDERLINE):
            return "h_under"
        if bare.startswith(HEADER_BOLD):
            return "h_bold"
        if LIST_RE.match(bare):
            return "list"
        return "body"

    def wrap_underline(html: str) -> str:
        """Envuelve un párrafo entero en <u>...</u> para subrayar todo el bloque."""
        return f"<u>{html}</u>"

    story = []
    for tipo, texto in blocks:
        if tipo == "titulo":
            story.append(Paragraph(wrap_underline(f"<b>{texto}</b>"), title_style))
            continue
        for sub in [s for s in texto.split("\n\n") if s.strip()]:
            sub = sub.strip()
            kind = classify(sub)
            html = sub.replace("\n", "<br/>")
            if kind == "h_under":
                # bold + underline
                story.append(Paragraph(wrap_underline(f"<b>{html}</b>"), h_under_style))
            elif kind == "h_bold":
                story.append(Paragraph(f"<b>{html}</b>", h_bold_style))
            elif kind == "list":
                story.append(Paragraph(html, list_style))
            else:
                story.append(Paragraph(html, body_style))

    # Firma
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        f"{ct.LETRADO['nombre']}<br/>{ct.LETRADO['matricula']}",
        sign_style,
    ))

    doc.build(story)


def process_worker(token: str, pdf_path: str, api_key: str):
    q: queue.Queue = _sessions[token]["queue"]
    combo_products = _sessions[token].get("combo_products") or []
    try:
        q.put({"type": "progress", "pct": 0.05, "stage": "Leyendo páginas y extrayendo texto"})
        text = extract_text(pdf_path)
        if not text:
            q.put({"type": "error", "message": "No se pudo extraer texto del PDF. Verificá que no sea una imagen escaneada."})
            return

        q.put({"type": "progress", "pct": 0.18, "stage": "Detectando secciones y campos"})
        time.sleep(0.4)
        q.put({"type": "progress", "pct": 0.26, "stage": "Mapeando datos al formulario"})

        client    = anthropic.Anthropic(api_key=api_key)
        extracted = {}
        pct       = 0.28

        def _do_stream():
            with client.messages.stream(
                model=_get_model(),
                max_tokens=3000,
                messages=[{"role": "user", "content": build_prompt(text)}],
            ) as stream:
                return stream.get_final_text()

        raw = _claude_call_with_retry(_do_stream, step_name="Extracción de campos")

        # Parser robusto: extrae objetos JSON aunque estén en múltiples líneas
        buf = raw
        while buf:
            start = buf.find("{")
            if start == -1:
                break
            buf = buf[start:]
            depth, in_str, esc, end = 0, False, False, -1
            for i, ch in enumerate(buf):
                if esc:
                    esc = False; continue
                if ch == "\\" and in_str:
                    esc = True; continue
                if ch == '"':
                    in_str = not in_str; continue
                if in_str:
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i; break
            if end == -1:
                break
            candidate = buf[:end + 1]
            buf = buf[end + 1:]
            try:
                d    = json.loads(candidate)
                fid  = str(d.get("field", "")).strip()
                val  = d.get("value")
                conf = float(d.get("confidence", 0.9))
                if fid and val is not None and str(val) not in ("", "null", "None"):
                    extracted[fid] = {"value": str(val), "confidence": conf}
                    pct = min(pct + 0.019, 0.88)
                    q.put({"type": "field", "field": fid, "value": str(val),
                           "confidence": conf, "pct": pct})
            except (json.JSONDecodeError, ValueError):
                pass

        q.put({"type": "progress", "pct": 0.92, "stage": "Validando y verificando coherencia"})
        time.sleep(0.3)
        q.put({"type": "progress", "pct": 0.96, "stage": "Armando documento firmable"})

        with open(FIELD_INFO_JSON, encoding="utf-8") as f:
            field_info = json.load(f)

        field_values = build_field_values(extracted, field_info)
        out_path = os.path.join(tempfile.gettempdir(), f"foliar_{token}.pdf")
        fill_form(field_values, out_path)

        _sessions[token].update({"path": out_path, "fields": extracted, "status": "done"})

        # ── Combo: generar telegrama y/o escrito si fueron solicitados ──
        combo_paths = {"formulario": out_path}
        combo_vars = None
        if combo_products:
            try:
                q.put({"type": "combo_progress", "doc": "shared", "stage": "Extrayendo variables del expediente"})
                combo_vars = _extract_combo_vars(api_key, text)
            except Exception as e:
                q.put({"type": "combo_error", "doc": "shared", "message": str(e)})
                combo_vars = {}

        if "telegrama" in combo_products:
            try:
                q.put({"type": "combo_progress", "doc": "telegrama", "stage": "Redactando telegrama"})
                tel_data = ct.compose_telegrama(combo_vars or {})
                tel_ext = "pdf" if _HAS_REPORTLAB else "txt"
                tel_path = os.path.join(tempfile.gettempdir(), f"foliar_{token}_telegrama.{tel_ext}")
                _render_telegrama_pdf(tel_data, tel_path)
                combo_paths["telegrama"] = tel_path
                q.put({"type": "combo_done", "doc": "telegrama"})
            except Exception as e:
                q.put({"type": "combo_error", "doc": "telegrama", "message": str(e)})
        if "escrito" in combo_products:
            try:
                q.put({"type": "combo_progress", "doc": "escrito", "stage": "Redactando escrito"})
                esc_blocks = ct.compose_escrito(combo_vars or {})
                esc_ext = "pdf" if _HAS_REPORTLAB else "txt"
                esc_path = os.path.join(tempfile.gettempdir(), f"foliar_{token}_escrito.{esc_ext}")
                _render_escrito_pdf(esc_blocks, esc_path)
                combo_paths["escrito"] = esc_path
                q.put({"type": "combo_done", "doc": "escrito"})
            except Exception as e:
                q.put({"type": "combo_error", "doc": "escrito", "message": str(e)})

        _sessions[token]["combo_paths"] = combo_paths
        _sessions[token]["combo_vars"]  = combo_vars or {}

        # Registrar el trámite en historial
        try:
            uid = _sessions[token].get("user_id")
            pdf_name = _sessions[token].get("pdf_name", "Formulario")
            if uid:
                with app.app_context():
                    if extracted:
                        confs = [float(v.get("confidence", 0.9)) for v in extracted.values()]
                        avg = sum(confs) / len(confs) if confs else 0.9
                    else:
                        avg = 0.9
                    # Determinar tipo de producto correcto
                    _prods_raw = _sessions[token].get("products_raw", "formulario")
                    _plist = [p.strip() for p in _prods_raw.split(",") if p.strip()]
                    _has_form = "formulario" in _plist
                    _has_tel  = "telegrama" in _plist
                    _has_esc  = "escrito" in _plist
                    if (_has_form and (_has_tel or _has_esc)) or (_has_tel and _has_esc):
                        _tipo = "combo"
                    elif _has_tel:
                        _tipo = "telegrama"
                    elif _has_esc:
                        _tipo = "escrito"
                    else:
                        _tipo = "formulario"
                    t = Tramite(
                        user_id  = uid,
                        codigo   = _next_tramite_codigo(),
                        producto = _tipo,
                        titulo   = pdf_name[:200],
                        estado   = "En revisión",
                        conf     = avg,
                        campos   = f"{len(extracted)}/{len(extracted)}",
                    )
                    db.session.add(t)
                    db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
        q.put({"type": "done", "token": token, "fields": extracted})

    except anthropic.AuthenticationError:
        err = "API Key inválida. Verificá tu clave en la pantalla de login."
        _sessions[token]["status"] = "error"
        _sessions[token]["error_message"] = err
        q.put({"type": "error", "message": err})
    except Exception as e:
        err = str(e)
        _sessions[token]["status"] = "error"
        _sessions[token]["error_message"] = err
        q.put({"type": "error", "message": err})
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass
        q.put(None)  # sentinel

# ── Rutas de autenticación ───────────────────────────────────────────────────

@app.route("/auth/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 30 per hour", methods=["POST"])
def auth_login():
    if request.method == "POST":
        if current_user.is_authenticated:
            return jsonify({"ok": True})
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        if not identifier or not password:
            return jsonify({"error": "Completá todos los campos."}), 400
        if len(identifier) > 120 or len(password) > 256:
            return jsonify({"error": "Datos inválidos."}), 400
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()
        if user and user.check_password(password):
            remember = request.form.get("remember") == "1"
            login_user(user, remember=remember)
            return jsonify({"ok": True, "username": user.username})
        time.sleep(0.5)   # pequeño delay para dificultar enumeración
        return jsonify({"error": "Usuario o contraseña incorrectos."}), 401
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return render_template("auth.html", mode="login", error=None)


@app.route("/auth/register")
def auth_register():
    # El registro es solo por manage.py — no hay pantalla pública
    return redirect(url_for("auth_login"))


@app.route("/auth/logout")
@login_required
def auth_logout():
    logout_user()
    return redirect(url_for("auth_login"))


@app.route("/api/me")
def api_me():
    """Verifica si el usuario tiene una sesión activa válida."""
    if current_user.is_authenticated:
        # Actualizar last_seen
        try:
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({"ok": True, "username": current_user.username, "rol": getattr(current_user, "rol", "Editor")})
    return jsonify({"ok": False}), 401


# ── Historial ────────────────────────────────────────────────────────────────
@app.route("/api/historial")
@login_required
def api_historial():
    # Admins ven todo; el resto solo lo suyo
    rol = getattr(current_user, "rol", None) or "Editor"
    q = Tramite.query
    if rol != "Admin":
        q = q.filter_by(user_id=current_user.id)
    items = q.order_by(Tramite.created_at.desc()).limit(200).all()
    return jsonify({"ok": True, "items": [t.to_dict() for t in items], "scope": "all" if rol == "Admin" else "mine"})


@app.route("/api/historial", methods=["POST"])
@login_required
@require_role("Admin", "Editor")
def api_historial_create():
    data = request.get_json(silent=True) or {}
    producto = (data.get("producto") or "").strip().lower()
    titulo   = (data.get("titulo")   or "").strip()
    if producto not in ("formulario", "telegrama", "escrito", "combo") or not titulo:
        return jsonify({"ok": False, "error": "datos inválidos"}), 400
    t = Tramite(
        user_id  = current_user.id,
        codigo   = _next_tramite_codigo(),
        producto = producto,
        titulo   = titulo[:200],
        estado   = (data.get("estado") or "Borrador")[:30],
        conf     = float(data.get("conf") or 0.9),
        campos   = (data.get("campos") or "")[:60],
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "item": t.to_dict()})


# ── Estadísticas ─────────────────────────────────────────────────────────────
@app.route("/api/stats")
@login_required
@require_role("Admin")
def api_stats():
    """Estadísticas completas: totales, por tipo, por estado, actividad diaria 30d, usuarios."""
    try:
        from datetime import date as _date, timedelta as _td
        from sqlalchemy import func as _func
        rol   = getattr(current_user, "rol", "Editor")
        today = _date.today()

        def base_q():
            q = Tramite.query
            if rol != "Admin":
                q = q.filter_by(user_id=current_user.id)
            return q

        # ── Totales ──
        total = base_q().count()
        hoy   = base_q().filter(
            Tramite.created_at >= datetime(today.year, today.month, today.day)
        ).count()

        # Esta semana (últimos 7 días)
        sem_start = datetime(today.year, today.month, today.day) - _td(days=6)
        esta_sem  = base_q().filter(Tramite.created_at >= sem_start).count()

        # Este mes / mes anterior
        mes_start = datetime(today.year, today.month, 1)
        este_mes  = base_q().filter(Tramite.created_at >= mes_start).count()
        prev_month_end   = mes_start - _td(seconds=1)
        prev_month_start = datetime(prev_month_end.year, prev_month_end.month, 1)
        mes_anterior = base_q().filter(
            Tramite.created_at >= prev_month_start,
            Tramite.created_at <= prev_month_end
        ).count()

        # ── Actividad diaria — últimos 30 días ──
        daily = {}
        for i in range(29, -1, -1):
            d     = today - _td(days=i)
            label = d.strftime("%d/%m")
            start = datetime(d.year, d.month, d.day, 0, 0, 0)
            end   = datetime(d.year, d.month, d.day, 23, 59, 59)
            daily[label] = base_q().filter(
                Tramite.created_at >= start,
                Tramite.created_at <= end
            ).count()

        # ── Por tipo de producto ──
        productos = ["formulario", "telegrama", "escrito", "combo"]
        by_product = {p: base_q().filter_by(producto=p).count() for p in productos}

        # ── Por estado ──
        estados = ["Borrador", "En revisión", "Despachado", "Presentado"]
        by_estado = {e: base_q().filter_by(estado=e).count() for e in estados}

        # ── Confianza promedio ──
        avg_conf_row = db.session.query(_func.avg(Tramite.conf))
        if rol != "Admin":
            avg_conf_row = avg_conf_row.filter(Tramite.user_id == current_user.id)
        avg_conf_val = avg_conf_row.scalar()
        avg_conf = round((avg_conf_val or 0) * 100, 1)

        # ── Por usuario (Admin only) ──
        by_user = []
        if rol == "Admin":
            palette = ['#9C5A2E','#1E3A5F','#3A6B40','#6B4E8A','#8A7318','#9C988F','#3F6675']
            users = User.query.order_by(User.created_at.asc()).all()
            for u in users:
                count = Tramite.query.filter_by(user_id=u.id).count()
                by_user.append({
                    "name":  u.username,
                    "count": count,
                    "color": palette[u.id % len(palette)],
                    "rol":   u.rol,
                })
            by_user.sort(key=lambda x: x["count"], reverse=True)

        return jsonify({
            "ok":          True,
            "total":       total,
            "hoy":         hoy,
            "esta_sem":    esta_sem,
            "este_mes":    este_mes,
            "mes_anterior":mes_anterior,
            "avg_conf":    avg_conf,
            "daily":       daily,
            "by_product":  by_product,
            "by_estado":   by_estado,
            "by_user":     by_user,
        })
    except Exception as e:
        app.logger.error(f"[api_stats] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/historial/export")
@login_required
def api_historial_export():
    """Descarga el historial como CSV."""
    import csv as _csv, io as _io
    rol = getattr(current_user, "rol", "Editor")
    q = Tramite.query
    if rol != "Admin":
        q = q.filter_by(user_id=current_user.id)
    items = q.order_by(Tramite.created_at.desc()).all()

    buf = _io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(["ID", "Producto", "Título", "Estado", "Confianza", "Campos", "Fecha", "Autor"])
    for t in items:
        d = t.to_dict()
        writer.writerow([d.get("id",""), d.get("producto",""), d.get("titulo",""),
                         d.get("estado",""), f"{round((d.get('conf') or 0)*100)}%",
                         d.get("campos",""), d.get("t",""), d.get("autor","")])

    output = buf.getvalue().encode("utf-8-sig")  # BOM para Excel
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=historial_foliar.csv",
                 "Content-Type": "text/csv; charset=utf-8-sig"},
    )


# ── Equipo ───────────────────────────────────────────────────────────────────
def _user_to_member(u: "User") -> dict:
    last = u.last_seen or u.created_at or datetime.utcnow()
    delta = datetime.utcnow() - last
    if delta.total_seconds() < 300:
        activa = "ahora"
    elif delta.total_seconds() < 3600:
        activa = f"hace {int(delta.total_seconds() / 60)} min"
    elif delta.total_seconds() < 86400:
        activa = f"hace {int(delta.total_seconds() / 3600)} h"
    elif delta.days < 7:
        activa = f"hace {delta.days} d"
    else:
        activa = last.strftime("%d %b")
    # Color determinístico por id
    palette = ['#9C5A2E', '#1E3A5F', '#3A6B40', '#6B4E8A', '#8A7318', '#9C988F', '#3F6675']
    tramites = Tramite.query.filter_by(user_id=u.id).count()
    return {
        "id": u.id,
        "n": u.username,
        "email": u.email,
        "rol": getattr(u, "rol", "Editor") or "Editor",
        "activa": activa,
        "tramites": tramites,
        "color": palette[u.id % len(palette)],
        "estado": "activa",
    }


@app.route("/api/equipo")
@login_required
def api_equipo():
    users = User.query.order_by(User.created_at.asc()).all()
    return jsonify({"ok": True, "items": [_user_to_member(u) for u in users]})


@app.route("/api/equipo/audit")
@login_required
@require_role("Admin")
def api_equipo_audit():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
    return jsonify({"ok": True, "items": [l.to_dict() for l in logs]})


@app.route("/api/equipo/invite", methods=["POST"])
@login_required
@require_role("Admin")
def api_equipo_invite():
    data = request.get_json(silent=True) or {}
    nombre   = (data.get("nombre") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    rol      = (data.get("rol") or "Editor").strip()
    password = data.get("password") or ""
    if not nombre or not email or len(password) < 8 or rol not in ("Admin", "Editor", "Visor"):
        return jsonify({"ok": False, "error": "datos inválidos"}), 400
    if User.query.filter((User.email == email) | (User.username == nombre)).first():
        return jsonify({"ok": False, "error": "El usuario ya existe."}), 409
    u = User(username=nombre[:80], email=email[:120], rol=rol)
    u.set_password(password)
    db.session.add(u)
    _audit("user_created", target=nombre, detalle=f"rol: {rol}")
    db.session.commit()
    return jsonify({"ok": True, "member": _user_to_member(u)})


@app.route("/api/equipo/<int:user_id>", methods=["PATCH"])
@login_required
@require_role("Admin")
def api_equipo_update(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "Miembro no encontrado."}), 404
    data = request.get_json(silent=True) or {}

    nombre = (data.get("nombre") or "").strip()
    email  = (data.get("email") or "").strip().lower()
    rol    = (data.get("rol") or "").strip()
    pwd    = data.get("password") or ""

    if nombre:
        if User.query.filter(User.username == nombre, User.id != u.id).first():
            return jsonify({"ok": False, "error": "El nombre ya está en uso."}), 409
        u.username = nombre[:80]
    if email:
        if User.query.filter(User.email == email, User.id != u.id).first():
            return jsonify({"ok": False, "error": "El email ya está en uso."}), 409
        u.email = email[:120]
    if rol:
        if rol not in ("Admin", "Editor", "Visor"):
            return jsonify({"ok": False, "error": "Rol inválido."}), 400
        # No permitir quedarse sin Admins
        if u.rol == "Admin" and rol != "Admin":
            other_admins = User.query.filter(User.rol == "Admin", User.id != u.id).count()
            if other_admins == 0:
                return jsonify({"ok": False, "error": "No puede quedar el estudio sin administradores."}), 400
        if u.rol != rol:
            _audit("role_changed", target=u.username, detalle=f"{u.rol} → {rol}")
        u.rol = rol
    if pwd:
        if len(pwd) < 8:
            return jsonify({"ok": False, "error": "La contraseña debe tener al menos 8 caracteres."}), 400
        u.set_password(pwd)
        _audit("password_changed", target=u.username, detalle="por administrador")

    db.session.commit()
    return jsonify({"ok": True, "member": _user_to_member(u)})


@app.route("/api/equipo/<int:user_id>/password")
@login_required
@require_role("Admin")
def api_equipo_get_password(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "Miembro no encontrado."}), 404
    return jsonify({"ok": True, "password": u.password_plain or "(no disponible)"})


@app.route("/api/equipo/<int:user_id>", methods=["DELETE"])
@login_required
@require_role("Admin")
def api_equipo_delete(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({"ok": False, "error": "Miembro no encontrado."}), 404
    if u.id == current_user.id:
        return jsonify({"ok": False, "error": "No podés eliminar tu propia cuenta."}), 400
    if u.rol == "Admin":
        other_admins = User.query.filter(User.rol == "Admin", User.id != u.id).count()
        if other_admins == 0:
            return jsonify({"ok": False, "error": "No puede quedar el estudio sin administradores."}), 400
    # Reasignar trámites a NULL para preservarlos? Acá los borramos junto con el user para mantenerlo simple.
    nombre_eliminado = u.username
    Tramite.query.filter_by(user_id=u.id).delete()
    db.session.delete(u)
    _audit("user_deleted", target=nombre_eliminado)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    """Cierra la sesión desde el frontend SPA."""
    logout_user()
    return jsonify({"ok": True})


# ── Rutas principales ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file(Path(__file__).parent / "templates" / "index.html")


@app.route("/api/start", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
@require_role("Admin", "Editor")
def api_start():
    pdf_file = request.files.get("pdf")
    if not pdf_file:
        return jsonify({"error": "Se requiere un archivo PDF"}), 400
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "El archivo debe ser un PDF"}), 400
    if not _is_valid_pdf(pdf_file):
        return jsonify({"error": "El archivo no es un PDF válido"}), 400
    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    token = str(uuid.uuid4())
    q     = queue.Queue()
    # Si vino con products=formulario,telegrama,escrito → flujo combo
    products_raw = request.form.get("products", "formulario")
    combo_products = [p.strip() for p in products_raw.split(",") if p.strip() in ("telegrama", "escrito")]
    _sessions[token] = {
        "queue": q,
        "status": "processing",
        "created_at": time.time(),
        "user_id": current_user.id,
        "pdf_name": pdf_file.filename,
        "combo_products": combo_products,
        "products_raw": products_raw,
    }

    threading.Thread(target=process_worker, args=(token, tmp_path, api_key), daemon=True).start()
    return jsonify({"token": token})


@app.route("/api/stream/<token>")
@login_required
def api_stream(token):
    session = _sessions.get(token)
    if not session:
        return jsonify({"error": "Sesión no encontrada"}), 404
    # Verificar que la sesión pertenece al usuario que la creó
    if session.get("user_id") and session["user_id"] != current_user.id:
        return jsonify({"error": "No autorizado"}), 403

    def generate():
        q = session["queue"]

        # ── Reconexión: si la sesión ya terminó, re-enviar resultado ────────
        status = session.get("status")
        if status == "done":
            fields = session.get("fields", {})
            combo_paths = session.get("combo_paths", {})
            yield f"data: {json.dumps({'type': 'progress', 'pct': 1.0, 'stage': 'Completado'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'fields': fields, 'combo_paths': {k: bool(v) for k,v in combo_paths.items()}}, ensure_ascii=False)}\n\n"
            return
        if status == "error":
            err_msg = session.get("error_message", "Error durante el procesamiento.")
            yield f"data: {json.dumps({'type': 'error', 'message': err_msg}, ensure_ascii=False)}\n\n"
            return

        while True:
            try:
                msg = q.get(timeout=180)   # 3 minutos — suficiente para PDFs pesados
                if msg is None:
                    break
                # Guardar error para posibles reconexiones futuras
                if msg.get("type") == "error":
                    session["status"] = "error"
                    session["error_message"] = msg.get("message", "Error")
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/apply_edits/<token>", methods=["POST"])
@login_required
@require_role("Admin", "Editor")
def api_apply_edits(token):
    """Aplica las ediciones del usuario y regenera el formulario PDF."""
    session = _sessions.get(token)
    if not session or "fields" not in session:
        return jsonify({"error": "Sesión no encontrada"}), 404
    if session.get("user_id") and session["user_id"] != current_user.id:
        return jsonify({"error": "No autorizado"}), 403

    edits = request.get_json(silent=True) or {}
    if not edits:
        return jsonify({"ok": True})  # sin ediciones, nada que hacer

    # Fusionar ediciones sobre los campos extraídos
    extracted = dict(session["fields"])
    for key, value in edits.items():
        extracted[key] = {"value": value, "confidence": 1.0}

    try:
        with open(FIELD_INFO_JSON, encoding="utf-8") as f:
            field_info = json.load(f)
        field_values = build_field_values(extracted, field_info)
        out_path = session["path"]
        fill_form(field_values, out_path)
        # Actualizar campos en sesión
        session["fields"] = extracted
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<token>")
@login_required
def api_download(token):
    session = _sessions.get(token)
    if not session or "path" not in session:
        return "Archivo no encontrado o expirado", 404
    if session.get("user_id") and session["user_id"] != current_user.id:
        return "No autorizado", 403
    return send_file(session["path"], as_attachment=True,
                     download_name="anexo_i_rellenado.pdf", mimetype="application/pdf")


@app.route("/api/combo/download/<token>/<doc>")
@login_required
def api_combo_download(token, doc):
    """Descarga un documento individual del combo (formulario|telegrama|escrito)."""
    session = _sessions.get(token)
    if not session:
        return "Sesión no encontrada", 404
    if session.get("user_id") and session["user_id"] != current_user.id:
        return "No autorizado", 403
    paths = session.get("combo_paths") or {}
    # formulario también puede vivir en session["path"] si no es combo
    if doc == "formulario" and not paths.get("formulario"):
        paths["formulario"] = session.get("path")
    fpath = paths.get(doc)
    if not fpath or not os.path.exists(fpath):
        return f"Documento {doc} no encontrado", 404
    ext = os.path.splitext(fpath)[1].lower().lstrip(".") or "bin"
    mime_map = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt":  "text/plain",
    }
    name_map = {
        "formulario": "anexo_i_rellenado",
        "telegrama":  "telegrama",
        "escrito":    "escrito",
    }
    base = name_map.get(doc)
    if not base:
        return "Documento inválido", 400
    return send_file(fpath, as_attachment=True,
                     download_name=f"{base}.{ext}",
                     mimetype=mime_map.get(ext, "application/octet-stream"))


@app.route("/api/combo/download/<token>/zip")
@login_required
def api_combo_download_zip(token):
    """Empaqueta los documentos generados en un ZIP descargable."""
    session = _sessions.get(token)
    if not session:
        return "Sesión no encontrada", 404
    if session.get("user_id") and session["user_id"] != current_user.id:
        return "No autorizado", 403
    paths = dict(session.get("combo_paths") or {})
    if "formulario" not in paths and session.get("path"):
        paths["formulario"] = session["path"]
    if not paths:
        return "Sin documentos para empaquetar", 404

    name_map = {
        "formulario": "anexo_i_rellenado",
        "telegrama":  "telegrama",
        "escrito":    "escrito",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for k, p in paths.items():
            if p and os.path.exists(p):
                ext = os.path.splitext(p)[1].lower().lstrip(".") or "bin"
                base = name_map.get(k, k)
                zf.write(p, arcname=f"{base}.{ext}")
    buf.seek(0)
    return send_file(buf, as_attachment=True,
                     download_name=f"foliar_tramite_{token[:8]}.zip",
                     mimetype="application/zip")


# ── Telegrama Ley 23.789 ─────────────────────────────────────────────────────

@app.route("/telegrama")
@login_required
def telegrama():
    return send_file(Path(__file__).parent / "templates" / "telegrama.html")


@app.route("/escrito")
@login_required
def escrito():
    return send_file(Path(__file__).parent / "templates" / "telegrama_escrito.html")


@app.route("/calibrar")
@login_required
def calibrar():
    return send_file(Path(__file__).parent / "templates" / "telegrama_calibrar.html")


@app.route("/static/<path:filename>")
@login_required
def static_files(filename):
    return send_from_directory(Path(__file__).parent / "static", filename)


@app.route("/api/extract_docs", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
@require_role("Admin", "Editor")
def api_extract_docs():
    """Extrae datos para telegrama y escrito desde un PDF."""
    import base64
    pdf_file = request.files.get("pdf")
    if not pdf_file:
        return jsonify({"error": "Se requiere PDF"}), 400
    if not _is_valid_pdf(pdf_file):
        return jsonify({"error": "PDF inválido"}), 400
    pdf_b64 = base64.b64encode(pdf_file.read()).decode()
    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    art_list = "\n".join(
        f"{a['nombre']} — {a['cuit']}"
        for a in _ART_DATABASE
    )
    system_prompt = (
        "Sos un agente jurídico especializado en accidentes de trabajo bajo la Ley 24.557 y Ley 23.789 (Argentina). "
        "Extraé datos del expediente PDF y devolvé ÚNICAMENTE un JSON válido sin texto extra ni bloques de código.\n\n"
        f"LISTADO DE ARTs (Nombre — CUIT):\n{art_list}\n\n"
        "ESTRUCTURA JSON REQUERIDA:\n"
        '{"destNombre":"","destDomicilio":"","destCP":"","destLocalidad":"","destProvincia":"",'
        '"remNombre":"","remDNI":"","remFecha":"",'
        '"cuerpo":"",'
        '"escritoCliente":"","escritoART":"","escritoEmpleador":"","escritoHechos":""}\n\n'
        "REGLAS:\n"
        "- destNombre: nombre completo de la ART\n"
        "- destDomicilio/CP/localidad/provincia: domicilio legal de la ART según el listado\n"
        "- remNombre: APELLIDO Y NOMBRE del trabajador en mayúsculas\n"
        "- remDNI: DNI con puntos, ej: 28.345.678\n"
        "- remFecha: fecha del accidente en formato YYYY-MM-DD\n"
        "- escritoCliente: solo apellido y nombre, ej: PERALTA, Claudia\n"
        "- escritoART: solo nombre de la ART\n"
        "- escritoEmpleador: solo nombre del empleador\n"
        "- escritoHechos: relato en tercera persona de lo ocurrido\n"
        "- vacío si no figura en el documento"
    )
    user_prompt = (
        "Analizá el expediente y completá el JSON. "
        "Para el campo 'cuerpo' usá esta estructura de 3 párrafos separados por \\n\\n:\n\n"
        "1) 'Me dirijo a ustedes a fin de ampliar la denuncia oportunamente presentada con motivo del accidente de trabajo ocurrido el día [fecha en letras].'\n\n"
        "2) 'Como consecuencia del hecho sufrí [lesiones principales], [síntomas: dolor crónico, limitación funcional, etc.], afectación psicológica. "
        "Asimismo solicito la realización de los siguientes estudios y tratamientos médicos: [estudios según zonas].'\n\n"
        "3) 'Solicito se tenga por ampliada la denuncia inicial, se reconozcan la totalidad de las secuelas físicas y se disponga la cobertura médica integral "
        "conforme a la Ley N° 24.557. Esta parte impugna expresamente los estudios médicos practicados por [NOMBRE ART]. "
        "Sin otro particular, saludo atentamente.'"
    )
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 4000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
            {"type": "text", "text": user_prompt}
        ]}]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "pdfs-2024-09-25",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        texto = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        clean = texto.replace("```json", "").replace("```", "").strip()
        campos = json.loads(clean)
        return jsonify(campos)
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, mimetype="application/json")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/fill_telegrama", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
@require_role("Admin", "Editor")
def api_fill_telegrama():
    """Llena el PDF oficial del telegrama y lo devuelve para descarga."""
    body = request.get_json(force=True, silent=True)
    if not body:
        return jsonify({"error": "Body vacío"}), 400
    try:
        reader = PdfReader(TELEGRAMA_PDF)
        writer = PdfWriter(clone_from=reader)
        fields = {
            "Apellido y nombre o razón social": body.get("destNombre", ""),
            "Ramo o actividad principal":       "Aseguradora de Riesgos del Trabajo",
            "Domicilio laboral":                body.get("destDomicilio", ""),
            "CP":                               body.get("destCP", ""),
            "Localidad":                        body.get("destLocalidad", ""),
            "Provincia":                        body.get("destProvincia", ""),
            "Apellido y nombre REMITENTE":      body.get("remNombre", ""),
            "N° DNI REMITENTE":                 body.get("remDNI", ""),
            "Fecha":                            body.get("fecha", ""),
            "Campo de texto":                   body.get("cuerpo", ""),
        }
        writer.update_page_form_field_values(writer.pages[0], fields, auto_regenerate=False)
        writer.set_need_appearances_writer(True)
        out_path = os.path.join(tempfile.gettempdir(), f"telegrama_{uuid.uuid4().hex}.pdf")
        with open(out_path, "wb") as f:
            writer.write(f)
        return send_file(out_path, as_attachment=True,
                         download_name="telegrama_ampliacion.pdf", mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
@require_role("Admin", "Editor")
def api_chat():
    try:
        body = request.get_json(force=True, silent=True)
        if not body or not isinstance(body, dict):
            return jsonify({"error": "Body vacío o inválido"}), 400

        # Validar y sanitizar el modelo
        model = body.get("model", "claude-sonnet-4-6")
        if model not in _ALLOWED_MODELS:
            model = "claude-sonnet-4-6"

        # Cap de tokens para evitar abuso de costos
        max_tokens = min(int(body.get("max_tokens", 4000)), _MAX_TOKENS_CAP)

        # Validar estructura de mensajes
        messages = body.get("messages", [])
        if not isinstance(messages, list) or len(messages) > 20:
            return jsonify({"error": "Estructura de mensajes inválida"}), 400

        system = str(body.get("system", ""))[:8000]   # cap del system prompt

        api_key = _load_api_key()
        payload = {
            "model":      model,
            "max_tokens": max_tokens,
            "system":     system,
            "messages":   messages,
        }
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta":    "pdfs-2024-09-25",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            return Response(resp.read(), status=200, mimetype="application/json")
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, mimetype="application/json")
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Batch processing ────────────────────────────────────────────────────────

_batch_sessions: dict = {}

def _batch_worker(token: str, pdf_paths: list, pdf_names: list, api_key: str,
                  output_dir: str = None, delete_inputs: bool = True):
    sess  = _batch_sessions[token]
    q     = sess["queue"]
    paths = sess["output_paths"]
    total = len(pdf_paths)
    pause_event: threading.Event = sess["pause_event"]   # set = running, clear = paused
    stop_event:  threading.Event = sess["stop_event"]    # set = stop requested

    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        q.put({"type": "batch_error", "message": str(e)})
        q.put(None); return

    with open(FIELD_INFO_JSON, encoding="utf-8") as f:
        field_info = json.load(f)

    ok = 0
    skipped = 0
    for i, (pdf_path, pdf_name) in enumerate(zip(pdf_paths, pdf_names)):
        # ── Check stop ──────────────────────────────────────────────────────────
        if stop_event.is_set():
            skipped += 1
            q.put({"type": "file_skipped", "index": i, "name": pdf_name})
            continue

        # ── Check pause (blocks until resumed or stopped) ────────────────────
        if not pause_event.is_set():
            q.put({"type": "batch_control", "state": "paused"})
            # Wait until pause_event is set again (resume) or stop arrives
            while not pause_event.wait(timeout=1):
                if stop_event.is_set():
                    break
            if stop_event.is_set():
                skipped += 1
                q.put({"type": "file_skipped", "index": i, "name": pdf_name})
                continue
            q.put({"type": "batch_control", "state": "running"})

        q.put({"type": "file_start", "index": i, "name": pdf_name, "total": total})
        had_error = False
        try:
            text = extract_text(pdf_path)
            if not text:
                raise ValueError("No se pudo extraer texto del PDF.")

            client = anthropic.Anthropic(api_key=api_key)
            msg = _claude_call_with_retry(
                lambda: client.messages.create(
                    model=_get_model(),
                    max_tokens=3000,
                    messages=[{"role": "user", "content": build_prompt(text)}],
                ),
                step_name=f"Lote [{pdf_name}]",
            )
            raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

            extracted = {}
            buf = raw
            while buf:
                start = buf.find("{")
                if start == -1: break
                buf = buf[start:]
                depth, in_str, esc, end = 0, False, False, -1
                for ci, ch in enumerate(buf):
                    if esc: esc = False; continue
                    if ch == "\\" and in_str: esc = True; continue
                    if ch == '"': in_str = not in_str; continue
                    if in_str: continue
                    if ch == "{": depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0: end = ci; break
                if end == -1: break
                candidate = buf[:end + 1]; buf = buf[end + 1:]
                try:
                    d = json.loads(candidate)
                    fid = str(d.get("field", "")).strip()
                    val = d.get("value")
                    conf = float(d.get("confidence", 0.9))
                    if fid and val is not None and str(val) not in ("", "null", "None"):
                        extracted[fid] = {"value": str(val), "confidence": conf}
                except (json.JSONDecodeError, ValueError):
                    pass

            if output_dir:
                stem = os.path.splitext(pdf_name)[0]
                out_path = os.path.join(output_dir, f"formulario_{stem}.pdf")
            else:
                out_path = os.path.join(tempfile.gettempdir(), f"foliar_batch_{token}_{i}.pdf")

            field_values = build_field_values(extracted, field_info)
            fill_form(field_values, out_path)
            paths[i] = out_path
            ok += 1
            q.put({"type": "file_done", "index": i, "name": pdf_name, "fields": len(extracted)})
        except Exception as e:
            had_error = True
            sess["error_indices"].append(i)   # guardar índice fallido para retry
            q.put({"type": "file_error", "index": i, "name": pdf_name, "message": str(e)})
        finally:
            # Solo borrar el archivo de entrada si tuvo éxito.
            # Si falló, lo mantenemos para poder reintentar.
            if delete_inputs and not had_error:
                try: os.unlink(pdf_path)
                except OSError: pass

    stopped_early = stop_event.is_set()
    q.put({"type": "batch_done", "total": total, "ok": ok,
           "skipped": skipped, "stopped": stopped_early})
    q.put(None)


@app.route("/api/batch/start", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
@require_role("Admin", "Editor")
def api_batch_start():
    files = request.files.getlist("pdfs")
    if not files:
        return jsonify({"error": "No se recibieron archivos"}), 400
    if len(files) > 50:
        return jsonify({"error": "Máximo 50 archivos por lote"}), 400

    pdf_paths, pdf_names = [], []
    for f in files:
        if not _is_valid_pdf(f):
            return jsonify({"error": f"Archivo inválido: {f.filename}"}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        f.save(tmp.name); tmp.close()
        pdf_paths.append(tmp.name)
        pdf_names.append(f.filename)

    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    token = str(uuid.uuid4())
    _batch_sessions[token] = {
        "queue":         queue.Queue(),
        "output_paths":  [None] * len(pdf_paths),
        "names":         pdf_names,
        "pdf_paths":     list(pdf_paths),    # guardados para retry
        "error_indices": [],                 # llenado por el worker en errores
        "user_id":       current_user.id,
        "pause_event":   threading.Event(),
        "stop_event":    threading.Event(),
    }
    _batch_sessions[token]["pause_event"].set()
    threading.Thread(
        target=_batch_worker,
        args=(token, pdf_paths, pdf_names, api_key),
        daemon=True,
    ).start()
    return jsonify({"token": token, "count": len(pdf_paths)})


@app.route("/api/batch/stream/<token>")
@login_required
def api_batch_stream(token):
    sess = _batch_sessions.get(token)
    if not sess:
        return jsonify({"error": "Sesión no encontrada"}), 404
    if sess.get("user_id") != current_user.id:
        return jsonify({"error": "No autorizado"}), 403

    def generate():
        q = sess["queue"]
        while True:
            try:
                msg = q.get(timeout=180)
                if msg is None: break
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") in ("batch_done", "batch_error"): break
            except queue.Empty:
                yield f"data: {json.dumps({'type':'keepalive'})}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/batch/download/<token>/<int:index>")
@login_required
def api_batch_download(token, index):
    sess = _batch_sessions.get(token)
    if not sess: return "Sesión no encontrada", 404
    if sess.get("user_id") != current_user.id: return "No autorizado", 403
    paths = sess.get("output_paths", [])
    if index >= len(paths) or not paths[index]: return "Archivo no listo", 404
    name = sess["names"][index]
    stem = os.path.splitext(name)[0]
    return send_file(paths[index], as_attachment=True,
                     download_name=f"formulario_{stem}.pdf", mimetype="application/pdf")


@app.route("/api/batch/download/<token>/zip")
@login_required
def api_batch_download_zip(token):
    sess = _batch_sessions.get(token)
    if not sess: return "Sesión no encontrada", 404
    if sess.get("user_id") != current_user.id: return "No autorizado", 403
    paths = sess.get("output_paths", [])
    names = sess.get("names", [])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, p in enumerate(paths):
            if p and os.path.exists(p):
                stem = os.path.splitext(names[i])[0] if i < len(names) else f"formulario_{i}"
                zf.write(p, f"formulario_{stem}.pdf")
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name="lote_formularios.zip",
                     mimetype="application/zip")


@app.route("/api/batch/pause/<token>", methods=["POST"])
@login_required
def api_batch_pause(token):
    sess = _batch_sessions.get(token)
    if not sess: return jsonify({"error": "Sesión no encontrada"}), 404
    if sess.get("user_id") != current_user.id: return jsonify({"error": "No autorizado"}), 403
    sess["pause_event"].clear()  # block worker before next file
    return jsonify({"ok": True, "state": "paused"})


@app.route("/api/batch/resume/<token>", methods=["POST"])
@login_required
def api_batch_resume(token):
    sess = _batch_sessions.get(token)
    if not sess: return jsonify({"error": "Sesión no encontrada"}), 404
    if sess.get("user_id") != current_user.id: return jsonify({"error": "No autorizado"}), 403
    sess["pause_event"].set()    # unblock worker
    return jsonify({"ok": True, "state": "running"})


@app.route("/api/batch/stop/<token>", methods=["POST"])
@login_required
def api_batch_stop(token):
    sess = _batch_sessions.get(token)
    if not sess: return jsonify({"error": "Sesión no encontrada"}), 404
    if sess.get("user_id") != current_user.id: return jsonify({"error": "No autorizado"}), 403
    sess["stop_event"].set()     # signal worker to skip remaining files
    sess["pause_event"].set()    # unblock if paused so it can see the stop signal
    return jsonify({"ok": True, "state": "stopped"})


@app.route("/api/batch/retry/<token>", methods=["POST"])
@login_required
def api_batch_retry(token):
    """Reintenta solo los archivos que fallaron en el lote original."""
    sess = _batch_sessions.get(token)
    if not sess: return jsonify({"error": "Sesión no encontrada"}), 404
    if sess.get("user_id") != current_user.id: return jsonify({"error": "No autorizado"}), 403

    error_indices = sess.get("error_indices", [])
    if not error_indices:
        return jsonify({"error": "No hay archivos fallidos para reintentar."}), 400

    all_paths  = sess.get("pdf_paths", [])
    all_names  = sess.get("names", [])
    output_dir = sess.get("output_dir")

    # Solo los que aún existen en disco
    valid = [
        (all_paths[i], all_names[i], i)
        for i in error_indices
        if i < len(all_paths) and os.path.exists(all_paths[i])
    ]
    if not valid:
        return jsonify({
            "error": "Los archivos originales ya no están disponibles. "
                     "Para modo carpeta reintentá normalmente; "
                     "para archivos subidos, subílos de nuevo."
        }), 400

    retry_paths  = [v[0] for v in valid]
    retry_names  = [v[1] for v in valid]
    orig_indices = [v[2] for v in valid]   # índices en el lote original

    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    new_token = str(uuid.uuid4())
    _batch_sessions[new_token] = {
        "queue":         queue.Queue(),
        "output_paths":  [None] * len(retry_paths),
        "names":         retry_names,
        "pdf_paths":     list(retry_paths),
        "error_indices": [],
        "user_id":       current_user.id,
        "output_dir":    output_dir,
        "pause_event":   threading.Event(),
        "stop_event":    threading.Event(),
    }
    _batch_sessions[new_token]["pause_event"].set()

    # Para modo subida: los archivos fallidos se conservaron → no borrar en retry tampoco
    delete = False  # nunca borrar en retry (folder mode siempre False; upload mode los guarda)

    threading.Thread(
        target=_batch_worker,
        args=(new_token, retry_paths, retry_names, api_key),
        kwargs={"output_dir": output_dir, "delete_inputs": delete},
        daemon=True,
    ).start()

    return jsonify({
        "ok":      True,
        "token":   new_token,
        "count":   len(retry_paths),
        "indices": orig_indices,   # mapeo new_index → orig_index para el frontend
    })


@app.route("/api/batch/start_folder", methods=["POST"])
@login_required
@require_role("Admin", "Editor")
def api_batch_start_folder():
    data = request.get_json() or {}
    input_folder  = data.get("input_folder",  "").strip()
    output_folder = data.get("output_folder", "").strip()

    if not input_folder:
        return jsonify({"error": "Especificá la carpeta de entrada."}), 400
    if not output_folder:
        return jsonify({"error": "Especificá la carpeta de salida."}), 400

    in_path = Path(input_folder)
    if not in_path.exists() or not in_path.is_dir():
        return jsonify({"error": f"La carpeta de entrada no existe: {input_folder}"}), 400

    pdfs = sorted(in_path.glob("*.pdf"))
    if not pdfs:
        return jsonify({"error": "No se encontraron archivos PDF en esa carpeta."}), 400
    if len(pdfs) > 50:
        return jsonify({"error": f"Hay {len(pdfs)} PDFs en la carpeta. El máximo es 50 por lote."}), 400

    out_path = Path(output_folder)
    try:
        out_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return jsonify({"error": f"No se pudo crear la carpeta de salida: {e}"}), 400

    try:
        api_key = _load_api_key()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    pdf_paths = [str(p) for p in pdfs]
    pdf_names = [p.name for p in pdfs]

    token = str(uuid.uuid4())
    _batch_sessions[token] = {
        "queue":         queue.Queue(),
        "output_paths":  [None] * len(pdfs),
        "names":         pdf_names,
        "pdf_paths":     list(pdf_paths),    # guardados para retry
        "error_indices": [],
        "user_id":       current_user.id,
        "output_dir":    str(out_path),
        "pause_event":   threading.Event(),
        "stop_event":    threading.Event(),
    }
    _batch_sessions[token]["pause_event"].set()
    threading.Thread(
        target=_batch_worker,
        args=(token, pdf_paths, pdf_names, api_key),
        kwargs={"output_dir": str(out_path), "delete_inputs": False},
        daemon=True,
    ).start()
    return jsonify({"token": token, "count": len(pdfs), "names": pdf_names})


@app.route("/api/desktop_path")
@login_required
def api_desktop_path():
    desktop = str(Path.home() / "Desktop")
    return jsonify({"desktop": desktop})


# ── Admin: configuración editable ────────────────────────────────────────────

@app.route("/api/admin/config", methods=["GET"])
@login_required
@require_role("Admin")
def api_admin_config_get():
    cfg = _load_config()
    key = cfg.get("anthropic_api_key", "")
    key_set     = bool(key and not key.startswith("sk-ant-PONE"))
    key_from_env = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    masked = (f"sk-ant-···{key[-6:]}" if key_set else "No configurada")
    return jsonify({
        "ok":             True,
        "api_key_masked": masked,
        "api_key_set":    key_set,
        "api_key_env":    key_from_env,   # True = viene de variable de entorno
        "model":          cfg.get("model", "claude-sonnet-4-6"),
        "model_env":      bool(os.environ.get("FOLIAR_MODEL", "").strip()),
        "estudio_nombre": cfg.get("estudio_nombre", "Estudio Arrechea"),
    })


@app.route("/api/admin/config", methods=["POST"])
@login_required
@require_role("Admin")
def api_admin_config_post():
    data = request.get_json() or {}
    result = _save_config(data)
    return jsonify(result)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        _ensure_user_columns()
    print("=" * 54)
    print("  Foliar — Agente de formularios")
    print("=" * 54)
    print("  Abrí tu navegador en:  http://localhost:5000")
    print("  Ctrl+C para detener")
    print("=" * 54)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
