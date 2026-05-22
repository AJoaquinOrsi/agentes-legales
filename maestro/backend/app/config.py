from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path absoluto al .env — independiente de dónde se inicie el servidor
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"
    DATABASE_URL: str = "sqlite:///./projects.db"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000"

    # Auth JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120
    ENVIRONMENT: str = "development"

    # Rate limiting
    CHAT_RATE_LIMIT_PER_MINUTE: int = 20
    CHAT_MAX_MESSAGE_LENGTH: int = 4000
    CHAT_MAX_HISTORY_TURNS: int = 20

    # ── Supabase (opcional — reemplaza DATABASE_URL con la URL de Supabase) ──
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Google (Drive + Calendar) ─────────────────────────────────────────────
    # OAuth 2.0 — cuenta personal (preferido sobre service account)
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_REFRESH_TOKEN: str = ""
    # Service account (fallback / bots sin interacción de usuario)
    GOOGLE_CREDENTIALS_PATH: str = "credenciales.json"
    # ID de la carpeta raíz de MAESTRO en Google Drive
    GOOGLE_DRIVE_ROOT_FOLDER_ID: str = ""
    # ID del calendario (usar "primary" para el principal)
    GOOGLE_CALENDAR_ID: str = "primary"

    # ── GitHub ────────────────────────────────────────────────────────────────
    # Personal Access Token (repo scope para repos privados; public_repo para públicos)
    GITHUB_TOKEN: str = ""

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    # Proveedor: "twilio" | "meta"
    WHATSAPP_PROVIDER: str = "twilio"
    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = ""   # ej: "whatsapp:+14155238886"
    # Meta Cloud API
    META_WHATSAPP_TOKEN: str = ""
    META_WHATSAPP_PHONE_ID: str = ""
    META_WEBHOOK_VERIFY_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # ignora vars de entorno del sistema que estén vacías
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def supabase_storage_enabled(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY and
                    "supabase.co" in self.SUPABASE_URL)

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_OAUTH_CLIENT_ID and self.GOOGLE_OAUTH_CLIENT_SECRET and self.GOOGLE_OAUTH_REFRESH_TOKEN)

    @property
    def google_enabled(self) -> bool:
        import os
        if self.google_oauth_enabled:
            return True
        return bool(self.GOOGLE_CREDENTIALS_PATH and os.path.exists(self.GOOGLE_CREDENTIALS_PATH))

    @property
    def github_enabled(self) -> bool:
        return bool(self.GITHUB_TOKEN)

    @property
    def whatsapp_enabled(self) -> bool:
        if self.WHATSAPP_PROVIDER == "twilio":
            return bool(self.TWILIO_ACCOUNT_SID and self.TWILIO_AUTH_TOKEN)
        return bool(self.META_WHATSAPP_TOKEN and self.META_WHATSAPP_PHONE_ID)


settings = Settings()
