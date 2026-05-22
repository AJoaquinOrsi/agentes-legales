from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from ..database import get_db
from ..models.models import User
from fastapi.security import OAuth2PasswordBearer as _OAuth2
from ..security import (
    create_access_token, verify_token, require_auth,
    hash_password, verify_password, validate_password_strength,
    check_login_rate_limit, record_failed_login, clear_failed_logins,
    revoke_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    display_name: str
    username: str


class UserInfo(BaseModel):
    id: str
    username: str
    display_name: str | None
    email: str | None


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("Contraseña insegura: " + ", ".join(errors))
        return v


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # Rate limit check (IP + per-username lockout)
    check_login_rate_limit(request, payload.username)

    user = db.query(User).filter(User.username == payload.username).first()

    # Constant-time comparison to prevent user enumeration timing attacks
    if not user:
        # Still call verify so timing is consistent
        verify_password("dummy", "$2b$12$dummy.hash.to.prevent.timing.attacks.padding")
        record_failed_login(payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    if not verify_password(payload.password, user.hashed_password):
        record_failed_login(payload.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado.",
        )

    clear_failed_logins(payload.username)
    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.username, "uid": user.id})
    return TokenResponse(
        access_token=token,
        display_name=user.display_name or user.username,
        username=user.username,
    )


@router.get("/me", response_model=UserInfo)
def me(db: Session = Depends(get_db), username: str = Depends(verify_token)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return UserInfo(id=user.id, username=user.username, display_name=user.display_name, email=user.email)


_bearer_scheme = _OAuth2(tokenUrl="/auth/login", auto_error=False)

@router.post("/logout")
def logout(token: str = Depends(_bearer_scheme)):
    """Invalida el token actual agregándolo al blacklist."""
    if token:
        revoke_token(token)
    return {"message": "Sesión cerrada."}


def require_admin(username: str = Depends(require_auth), db: Session = Depends(get_db)) -> str:
    """Solo el primer usuario registrado (administrador) puede realizar esta acción."""
    first_user = db.query(User).order_by(User.created_at).first()
    if not first_user or first_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el administrador puede realizar esta acción.",
        )
    return username


@router.post("/register", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    """Crear un nuevo usuario. Solo accesible por el administrador."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está en uso.",
        )
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado.",
        )
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        email=payload.email,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserInfo(id=user.id, username=user.username,
                    display_name=user.display_name, email=user.email)
