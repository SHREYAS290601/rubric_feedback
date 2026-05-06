from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.config import AuthSettings, get_auth_settings


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    name: str
    email: str
    net_id: str
    tenant_id: str
    auth_mode: str


@lru_cache(maxsize=8)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys")


def require_user(authorization: Optional[str] = Header(default=None)) -> AuthenticatedUser:
    settings = get_auth_settings()
    if not settings.required:
        return AuthenticatedUser(
            user_id="demo-user",
            name="Demo Student",
            email="demo@illinois.edu",
            net_id="demo",
            tenant_id="demo",
            auth_mode="demo",
        )

    if not settings.audience:
        raise HTTPException(status_code=500, detail="Authentication is enabled but MS_AUTH_AUDIENCE is not configured.")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Microsoft sign-in is required.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        token_tenant_id = unverified.get("tid")
        if not token_tenant_id:
            raise ValueError("Token is missing tenant id.")

        configured_tenant = settings.tenant_id
        if configured_tenant not in {"common", "organizations"} and token_tenant_id != configured_tenant:
            raise ValueError("Token tenant is not allowed.")

        signing_key = _jwks_client(configured_tenant).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.audience,
            issuer=f"https://login.microsoftonline.com/{token_tenant_id}/v2.0",
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired Microsoft access token.") from exc

    email = _claim_email(claims)
    if settings.allowed_email_domains and not _email_domain_allowed(email, settings):
        raise HTTPException(status_code=403, detail="This prototype is restricted to allowed university email domains.")

    return AuthenticatedUser(
        user_id=str(claims.get("oid") or claims.get("sub")),
        name=str(claims.get("name") or email),
        email=email,
        net_id=email.split("@", 1)[0],
        tenant_id=str(claims.get("tid")),
        auth_mode="microsoft_entra",
    )


def _claim_email(claims: dict[str, object]) -> str:
    for key in ("preferred_username", "email", "upn", "unique_name"):
        value = claims.get(key)
        if isinstance(value, str) and "@" in value:
            return value.lower()
    raise ValueError("Token does not contain a usable email claim.")


def _email_domain_allowed(email: str, settings: AuthSettings) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in settings.allowed_email_domains
