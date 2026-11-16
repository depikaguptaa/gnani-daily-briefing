from html import escape
from urllib.parse import quote

import httpx

from .config import settings


class ProviderError(RuntimeError):
    pass


async def synthesize(script: str) -> bytes:
    if not settings.gnani_api_key:
        raise ProviderError("Gnani TTS is not configured")
    request = {
        "text": script,
        "model": settings.gnani_model,
        "voice": settings.gnani_voice,
        "language": settings.gnani_language,
        "audio_config": {"container": "mp3", "sample_rate": 48000, "bitrate": "128k"},
    }
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            "https://api.vachana.ai/api/v1/tts/inference",
            headers={"X-API-Key-ID": settings.gnani_api_key, "Content-Type": "application/json"},
            json=request,
        )
        if response.is_error:
            detail = response.text[:300]
            raise ProviderError(f"Gnani TTS returned HTTP {response.status_code}: {detail}")
        if not response.content:
            raise ProviderError("Gnani TTS returned an empty audio file")
        return response.content


def _storage_headers() -> dict[str, str]:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ProviderError("Private episode storage is not configured")
    return {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
    }


async def store_audio(object_key: str, audio: bytes) -> None:
    path = quote(f"{settings.audio_bucket}/{object_key}", safe="/")
    headers = {**_storage_headers(), "Content-Type": "audio/mpeg", "x-upsert": "true"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{settings.supabase_url}/storage/v1/object/{path}", headers=headers, content=audio)
        response.raise_for_status()


async def load_audio(object_key: str) -> bytes:
    path = quote(f"{settings.audio_bucket}/{object_key}", safe="/")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(f"{settings.supabase_url}/storage/v1/object/{path}", headers=_storage_headers())
        response.raise_for_status()
        return response.content


async def delete_audio(object_key: str) -> None:
    bucket = quote(settings.audio_bucket, safe="")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(
            f"{settings.supabase_url}/storage/v1/object/{bucket}",
            headers=_storage_headers(),
            json={"prefixes": [object_key]},
        )
        response.raise_for_status()


async def send_episode_email(to_email: str, title: str, topic: str, episode_id: str) -> None:
    if not settings.resend_api_key:
        raise ProviderError("Resend email is not configured")
    url = f"{settings.app_url}/dashboard?episode={quote(episode_id)}"
    safe_title, safe_topic, safe_url = escape(title), escape(topic), escape(url, quote=True)
    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": f"Your daily briefing is ready: {title}",
        "html": (
            f"<div style='font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#192329'>"
            f"<p style='color:#718078;text-transform:uppercase;letter-spacing:.12em;font-size:12px'>Daily Context</p>"
            f"<h1 style='font-size:28px'>{safe_title}</h1><p>Your briefing on <b>{safe_topic}</b> is ready to listen.</p>"
            f"<p><a href='{safe_url}' style='display:inline-block;padding:14px 20px;background:#204a3e;color:white;text-decoration:none;border-radius:8px'>Listen to episode</a></p>"
            "<p style='color:#718078;font-size:13px'>Sign in with the email address that receives this message to open your private episode.</p></div>"
        ),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}", "Idempotency-Key": f"episode-ready-{episode_id}"},
            json=payload,
        )
        response.raise_for_status()
