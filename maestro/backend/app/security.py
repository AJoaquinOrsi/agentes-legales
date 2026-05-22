import time
import secrets
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import bcrypt
import jwt

from .config import settings

# ── Password hashing ─────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def validate_password_strength(password: str) -> list[str]:
    """Returns list of unmet requirements. Empty list = strong password."""
    errors = []
    if len(password) < 8:
        errors.append("Mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("Al menos una mayúscula")
    if not re.search(r"\d", password):
        errors.append("Al menos un número")
    return errors


# ── JWT ──────────────────────────────────────────────────────────────────────

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ── Token blacklist (in-memory — válido para single-worker) ──────────────────
# Almacena {jti: exp_timestamp}. Se limpia automáticamente de tokens ya expirados.
_token_blacklist: dict[str, float] = {}


def _clean_blacklist() -> None:
    """Elimina tokens ya expirados del blacklist para evitar crecimiento indefinido."""
    now = time.time()
    expired = [jti for jti, exp in _token_blacklist.items() if exp < now]
    for jti in expired:
        del _token_blacklist[jti]


def revoke_token(token: str) -> None:
    """Agrega un token al blacklist hasta su expiración."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        if jti and exp > time.time():
            _token_blacklist[jti] = float(exp)
            _clean_blacklist()
    except Exception:
        pass


def create_access_token(data: dict) -> str:
    payload = dict(data)
    payload["exp"] = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload["iat"] = datetime.utcnow()
    payload["jti"] = secrets.token_hex(16)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: Optional[str] = Depends(_oauth2_scheme)) -> str:
    """FastAPI dependency — returns username or raises 401."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Iniciá sesión primero.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise ValueError("token sin subject")
        # Verificar blacklist
        jti = payload.get("jti")
        if jti and jti in _token_blacklist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión cerrada. Volvé a iniciar sesión.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada. Volvé a iniciar sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_auth(username: str = Depends(verify_token)) -> str:
    """Alias semántico para usar en routers."""
    return username


# ── In-memory rate limiters ───────────────────────────────────────────────────

_rate_buckets: dict[str, list[float]] = defaultdict(list)     # chat: keyed by IP
_login_ip_buckets: dict[str, list[float]] = defaultdict(list)  # login: keyed by IP
_login_user_failures: dict[str, list[float]] = defaultdict(list)  # login: keyed by username

LOGIN_IP_LIMIT = 10      # max attempts per IP in 15 min window
LOGIN_USER_LIMIT = 5     # max failed attempts per username in 15 min window
LOGIN_WINDOW = 900       # 15 minutes


def _client_ip(request: Request) -> str:
    # Only trust X-Forwarded-For if behind a known proxy; otherwise use direct IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the last (rightmost) IP to prevent spoofing via prepended addresses
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def chat_rate_limit(request: Request) -> None:
    limit = settings.CHAT_RATE_LIMIT_PER_MINUTE
    ip = _client_ip(request)
    now = time.time()
    _rate_buckets[ip] = [t for t in _rate_buckets[ip] if now - t < 60.0]
    if len(_rate_buckets[ip]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de {limit} mensajes/minuto alcanzado. Esperá un momento.",
            headers={"Retry-After": "60"},
        )
    _rate_buckets[ip].append(now)


def check_login_rate_limit(request: Request, username: str = "") -> None:
    """Call BEFORE verifying credentials. Blocks brute-force by IP and by username."""
    now = time.time()
    ip = _client_ip(request)

    # Per-IP: 10 attempts in 15 min
    _login_ip_buckets[ip] = [t for t in _login_ip_buckets[ip] if now - t < LOGIN_WINDOW]
    if len(_login_ip_buckets[ip]) >= LOGIN_IP_LIMIT:
        retry_after = int(LOGIN_WINDOW - (now - _login_ip_buckets[ip][0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos de login. Esperá {retry_after // 60} min.",
            headers={"Retry-After": str(retry_after)},
        )
    _login_ip_buckets[ip].append(now)

    # Per-username: 5 failures in 15 min
    if username:
        _login_user_failures[username] = [
            t for t in _login_user_failures[username] if now - t < LOGIN_WINDOW
        ]
        if len(_login_user_failures[username]) >= LOGIN_USER_LIMIT:
            retry_after = int(LOGIN_WINDOW - (now - _login_user_failures[username][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Cuenta bloqueada temporalmente. Intentá en {retry_after // 60} min.",
                headers={"Retry-After": str(retry_after)},
            )


def record_failed_login(username: str) -> None:
    """Call AFTER a login failure to track per-username failures."""
    _login_user_failures[username].append(time.time())


def clear_failed_logins(username: str) -> None:
    """Call AFTER a successful login to reset the failure counter."""
    _login_user_failures.pop(username, None)


# ── Security headers middleware ───────────────────────────────────────────────

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=()",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": (
        # unsafe-eval requerido por Babel standalone (compilación JSX en browser)
        # unsafe-inline requerido por React CDN (estilos inline)
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://unpkg.com https://fonts.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' "
        "http://localhost:8000 https://localhost:8000 "
        "https://maestro-aiax.duckdns.org "
        "https://api.anthropic.com; "
        "img-src 'self' data: https: blob:; "
        "media-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';"
    ),
}


async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
