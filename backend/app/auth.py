from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    token: str


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def decode_token(token: str, settings: Settings) -> dict:
    """Prüft ein Supabase-Access-Token und gibt die Claims zurück."""
    options = {"require": ["sub", "exp"]}
    header = jwt.get_unverified_header(token)

    if header.get("alg") == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256-Token, aber kein SUPABASE_JWT_SECRET gesetzt")
        key = settings.supabase_jwt_secret
        algorithms = ["HS256"]
    else:
        key = _jwks_client(settings.jwks_url).get_signing_key_from_jwt(token).key
        algorithms = ["ES256", "RS256"]

    return jwt.decode(
        token,
        key,
        algorithms=algorithms,
        audience="authenticated",
        issuer=settings.issuer,
        options=options,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Nicht angemeldet")
    try:
        claims = decode_token(credentials.credentials, settings)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Ungültiges Token: {e}") from e
    return CurrentUser(id=claims["sub"], email=claims.get("email"), token=credentials.credentials)


UserDep = Annotated[CurrentUser, Depends(get_current_user)]
