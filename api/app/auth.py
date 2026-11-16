from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKSet

from .config import settings

bearer = HTTPBearer(auto_error=False)
_jwks: dict[str, Any] | None = None
_jwks_expires = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class User:
    id: str
    email: str


async def _get_jwks() -> dict[str, Any]:
    global _jwks, _jwks_expires
    now = datetime.now(timezone.utc)
    if _jwks is not None and now < _jwks_expires:
        return _jwks
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")
        response.raise_for_status()
        _jwks = response.json()
        _jwks_expires = now + timedelta(minutes=10)
        return _jwks


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if credentials is None or not settings.supabase_url or not settings.supabase_public_key:
        raise HTTPException(status_code=401, detail="Sign in to continue")
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        if algorithm in {"ES256", "RS256", "EdDSA"}:
            jwks = await _get_jwks()
            key_set = PyJWKSet.from_dict(jwks)
            key = next((item.key for item in key_set.keys if item.key_id == header.get("kid")), None)
            if key is None:
                raise jwt.InvalidTokenError("Signing key not found")
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                audience="authenticated",
                issuer=f"{settings.supabase_url}/auth/v1",
                options={"require": ["exp", "sub"]},
            )
            user_id = claims.get("sub")
            email = claims.get("email")
        elif algorithm == "HS256":
            # Supabase's legacy symmetric tokens must be checked by Auth, never decode-only.
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{settings.supabase_url}/auth/v1/user",
                    headers={"apikey": settings.supabase_public_key, "Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                profile = response.json()
            user_id, email = profile.get("id"), profile.get("email")
        else:
            raise jwt.InvalidTokenError("Unsupported signing algorithm")
        if not user_id or not email:
            raise jwt.InvalidTokenError("Token has no user identity")
        return User(id=str(user_id), email=str(email))
    except (jwt.PyJWTError, httpx.HTTPError, ValueError, StopIteration) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
