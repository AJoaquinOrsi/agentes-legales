"""
Router de WhatsApp — webhook para recibir mensajes y responder con MAESTRO.

Soporta dos proveedores (configurable con WHATSAPP_PROVIDER):
  - "twilio":  https://www.twilio.com/docs/whatsapp
  - "meta":    https://developers.facebook.com/docs/whatsapp/cloud-api

Flujo:
  1. WhatsApp provider recibe mensaje del usuario → llama POST /whatsapp/webhook
  2. Este router valida la firma, extrae el texto y el número de teléfono
  3. Llama a ClaudeService.chat() con el historial de conversación del número
  4. Envía la respuesta por la API del provider

Para conectar con Twilio:
  - Configurar la URL del webhook en Twilio Console:
    https://console.twilio.com → Messaging → Senders → WhatsApp sandbox
  - URL: https://tu-dominio.com/whatsapp/webhook

Para conectar con Meta Cloud API:
  - Configurar el webhook en Meta Developers → WhatsApp → Configuration
  - URL: https://tu-dominio.com/whatsapp/webhook
  - Verify Token: valor de META_WEBHOOK_VERIFY_TOKEN en .env
"""

import hmac
import hashlib
import logging
from collections import defaultdict
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..security import require_auth
from ..services.claude_service import ClaudeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

# Sesiones de conversación en memoria: {numero: [mensajes]}
# En producción reemplazar con Redis o tabla en BD
_sessions: dict[str, list[dict]] = defaultdict(list)
_MAX_SESSION_TURNS = 20


def _format_for_whatsapp(text: str) -> str:
    """Limpia markdown pesado para WhatsApp (soporta *bold* y _italic_ pero no ##)."""
    import re
    text = re.sub(r"^#{1,3}\s+", "*", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    text = text.strip()
    # WhatsApp tiene límite de ~4096 chars por mensaje
    if len(text) > 4000:
        text = text[:3950] + "\n…(respuesta truncada)"
    return text


# ── Twilio ────────────────────────────────────────────────────────────────────

def _validate_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """Valida la firma HMAC-SHA1 de Twilio."""
    if not settings.TWILIO_AUTH_TOKEN:
        logger.warning("Twilio webhook rechazado: TWILIO_AUTH_TOKEN no configurado")
        return False
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        return validator.validate(request_url, params, signature)
    except Exception:
        return False


async def _send_twilio(to: str, body: str) -> None:
    """Envía un mensaje WhatsApp vía Twilio."""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            data={"From": settings.TWILIO_WHATSAPP_FROM, "To": to, "Body": body},
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        )
        if not r.is_success:
            logger.error("Twilio send error %s: %s", r.status_code, r.text)


@router.post("/webhook")
async def twilio_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook para Twilio WhatsApp."""
    if settings.WHATSAPP_PROVIDER != "twilio":
        raise HTTPException(status_code=404)

    form = await request.form()
    params = dict(form)

    # Validar firma de Twilio
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    if not _validate_twilio_signature(url, params, signature):
        logger.warning("Twilio: firma inválida desde %s", request.client.host if request.client else "?")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Firma inválida")

    from_number = params.get("From", "")  # ej: "whatsapp:+5491123456789"
    body = params.get("Body", "").strip()

    if not from_number or not body:
        return {"status": "ignored"}

    logger.info("WhatsApp/Twilio ← %s: %s", from_number, body[:60])

    reply = await _process_message(from_number, body, db)
    await _send_twilio(from_number, reply)
    return {"status": "ok"}


# ── Meta Cloud API ────────────────────────────────────────────────────────────

def _validate_meta_signature(raw_body: bytes, signature: str) -> bool:
    """Valida la firma SHA256 de Meta."""
    if not settings.META_WHATSAPP_TOKEN:
        logger.warning("Meta webhook rechazado: META_WHATSAPP_TOKEN no configurado")
        return False
    app_secret = settings.META_WHATSAPP_TOKEN.encode()
    expected = "sha256=" + hmac.new(app_secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _send_meta(to: str, body: str) -> None:
    """Envía un mensaje WhatsApp vía Meta Cloud API."""
    url = f"https://graph.facebook.com/v20.0/{settings.META_WHATSAPP_PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.META_WHATSAPP_TOKEN}"},
        )
        if not r.is_success:
            logger.error("Meta send error %s: %s", r.status_code, r.text)


@router.get("/webhook")
async def meta_verify(request: Request):
    """Verificación del webhook de Meta (challenge)."""
    if settings.WHATSAPP_PROVIDER != "meta":
        raise HTTPException(status_code=404)
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == settings.META_WEBHOOK_VERIFY_TOKEN
    ):
        return int(params["hub.challenge"])
    raise HTTPException(status_code=403, detail="Token de verificación inválido")


@router.post("/webhook/meta")
async def meta_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook para Meta Cloud API."""
    if settings.WHATSAPP_PROVIDER != "meta":
        raise HTTPException(status_code=404)

    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not _validate_meta_signature(raw, sig):
        raise HTTPException(status_code=403, detail="Firma inválida")

    data = await request.json()
    try:
        entry = data["entry"][0]["changes"][0]["value"]
        msg = entry["messages"][0]
        from_number = msg["from"]
        body = msg.get("text", {}).get("body", "").strip()
    except (KeyError, IndexError):
        return {"status": "no_message"}

    if not body:
        return {"status": "ignored"}

    logger.info("WhatsApp/Meta ← %s: %s", from_number, body[:60])

    reply = await _process_message(from_number, body, db)
    await _send_meta(from_number, reply)
    return {"status": "ok"}


# ── Core: procesar mensaje con Claude ─────────────────────────────────────────

async def _process_message(phone: str, text: str, db: Session) -> str:
    """Llama al agente Claude con el historial de la sesión y devuelve la respuesta."""
    history = _sessions[phone]
    try:
        service = ClaudeService(db)
        result = await service.chat(text, history)

        # Actualizar sesión (limitar a MAX_SESSION_TURNS)
        new_history = result.get("conversation_history", [])
        _sessions[phone] = new_history[-(_MAX_SESSION_TURNS * 2):]

        reply = _format_for_whatsapp(result.get("respuesta", ""))
        return reply or "Lo siento, no pude procesar tu mensaje."

    except Exception as exc:
        logger.error("WhatsApp _process_message error: %s", exc)
        return "Hubo un error al procesar tu mensaje. Intentá de nuevo en unos minutos."


# ── Status endpoint ───────────────────────────────────────────────────────────

@router.get("/status", dependencies=[Depends(require_auth)])
def whatsapp_status():
    """Estado de la integración WhatsApp (requiere auth)."""
    return {
        "habilitado": settings.whatsapp_enabled,
    }
