from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AuthSettings:
    required: bool
    tenant_id: str
    audience: str | None
    allowed_email_domains: tuple[str, ...]


@dataclass(frozen=True)
class AISettings:
    provider: str
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str
    azure_openai_api_key: str | None
    azure_openai_endpoint: str | None
    azure_openai_deployment: str | None


def get_auth_settings() -> AuthSettings:
    domains = tuple(
        domain.strip().lower()
        for domain in os.getenv("ALLOWED_EMAIL_DOMAINS", "illinois.edu,uiuc.edu").split(",")
        if domain.strip()
    )
    return AuthSettings(
        required=_bool_env("AUTH_REQUIRED", False),
        tenant_id=os.getenv("MS_TENANT_ID", "organizations"),
        audience=os.getenv("MS_AUTH_AUDIENCE") or None,
        allowed_email_domains=domains,
    )


def get_ai_settings() -> AISettings:
    openai_base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_URL") or None
    default_openai_model = "openai/gpt-4.1-mini" if openai_base_url and "openrouter.ai" in openai_base_url else "gpt-4.1-mini"
    openai_api_key = _openai_api_key_for_base_url(openai_base_url)
    return AISettings(
        provider=os.getenv("AI_PROVIDER", "auto").strip().lower(),
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model=os.getenv("OPENAI_MODEL") or os.getenv("OPENROUTER_MODEL") or default_openai_model,
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or None,
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT") or None,
    )


def _openai_api_key_for_base_url(base_url: str | None) -> str | None:
    candidates = [
        os.getenv("OPENAI_API_KEY"),
        os.getenv("OPENROUTER_API_KEY"),
        os.getenv("CODEX_API_KEY"),
        os.getenv("KEY"),
    ]
    if base_url and "llm.dsrs.illinois.edu" in base_url:
        dsrs_key = next((key for key in candidates if key and key.startswith("dsrs-")), None)
        if dsrs_key:
            return dsrs_key
    return next((key for key in candidates if key), None)
