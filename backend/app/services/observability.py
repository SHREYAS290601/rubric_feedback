from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

R = TypeVar("R")

logger = logging.getLogger("rubric_feedback")


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def langsmith_tracing_enabled() -> bool:
    tracing_requested = _bool_env("LANGSMITH_TRACING") or _bool_env(
        "LANGCHAIN_TRACING_V2"
    )
    return tracing_requested and bool(os.getenv("LANGSMITH_API_KEY"))


def raw_prompt_tracing_enabled() -> bool:
    return _bool_env("LANGSMITH_TRACE_RAW_PROMPTS")


_langsmith_traceable: Any | None = None
_wrap_openai: Any | None = None
_langsmith_load_attempted = False


def _load_langsmith() -> tuple[Any | None, Any | None]:
    global _langsmith_load_attempted, _langsmith_traceable, _wrap_openai
    if _langsmith_load_attempted:
        return _langsmith_traceable, _wrap_openai
    _langsmith_load_attempted = True
    try:
        from langsmith import traceable as langsmith_traceable
        from langsmith.wrappers import wrap_openai
    except Exception:  # pragma: no cover - optional dependency in local demo mode
        logger.warning("langsmith_package_unavailable")
        return None, None
    _langsmith_traceable = langsmith_traceable
    _wrap_openai = wrap_openai
    return _langsmith_traceable, _wrap_openai


def traceable_stage(
    *args: Any, **kwargs: Any
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    if langsmith_tracing_enabled():
        langsmith_traceable, _ = _load_langsmith()
        if langsmith_traceable is not None:
            return langsmith_traceable(*args, **kwargs)

    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        return func

    return decorator


def maybe_wrap_openai_client(client: Any) -> Any:
    """Wrap OpenAI only when explicitly allowed to trace raw prompts."""

    if not langsmith_tracing_enabled():
        return client
    if not raw_prompt_tracing_enabled():
        logger.info(
            "langsmith_raw_prompt_trace_disabled "
            + json.dumps(
                {
                    "reason": "LANGSMITH_TRACE_RAW_PROMPTS is not true",
                    "privacy_default": "student_drafts_and_rubrics_are_not_sent_to_langsmith_as_raw_prompts",
                }
            )
        )
        return client
    _, wrap_openai = _load_langsmith()
    if wrap_openai is None:
        return client
    return wrap_openai(client)


def text_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def text_stats(text: str) -> dict[str, int | str]:
    words = [word for word in text.split() if word.strip()]
    return {
        "chars": len(text),
        "words": len(words),
        "fingerprint": text_fingerprint(text),
    }


def summarize_request(
    *, draft_text: str, rubric_text: str, focus_areas: list[str]
) -> dict[str, Any]:
    return {
        "draft": text_stats(draft_text),
        "rubric": text_stats(rubric_text),
        "focus_area_count": len(focus_areas),
    }


PII_PATTERNS: dict[str, str] = {
    "email": r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "phone": r"\b(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "uin": r"\b\d{9}\b",
    "netid_hint": r"\bnet\s?id\b|\b[A-Z]{2,6}\d{1,4}\b",
}

SECRET_PATTERNS: dict[str, str] = {
    "api_key": r"\b(?:sk|sk-or-v1|dsrs|lsv2)_[A-Za-z0-9_\-]{16,}\b|\b(?:sk-or-v1|dsrs)-[A-Za-z0-9_\-]{16,}\b",
    "bearer_token": r"\bBearer\s+[A-Za-z0-9._\-]{16,}\b",
    "password_assignment": r"\b(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*\S+",
}


def scan_text_signals(text: str, patterns: dict[str, str]) -> dict[str, Any]:
    matches: dict[str, int] = {}
    for label, pattern in patterns.items():
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            matches[label] = count
    return {
        "matched": bool(matches),
        "match_types": sorted(matches),
        "counts": matches,
    }


def summarize_privacy_scan(*, draft_text: str, rubric_text: str) -> dict[str, Any]:
    combined = f"{draft_text}\n\n{rubric_text}"
    pii = scan_text_signals(combined, PII_PATTERNS)
    secrets = scan_text_signals(combined, SECRET_PATTERNS)
    return {
        "pii": pii,
        "sensitive_leak": secrets,
        "masking_policy": "raw_text_never_logged; detected PII/secrets are reported by category and count only",
    }


def enum_payload(value: Enum | str | None, enum_name: str) -> dict[str, str | None]:
    if isinstance(value, Enum):
        return {"enum": enum_name, "value": str(value.value)}
    return {"enum": enum_name, "value": str(value) if value is not None else None}


def summarize_feedback_request_model(request: Any) -> dict[str, Any]:
    return {
        "model": "FeedbackRequest",
        "assignment_title_present": bool(getattr(request, "assignment_title", None)),
        "course_context_present": bool(getattr(request, "course_context", None)),
        "learning_goal_present": bool(getattr(request, "learning_goal", None)),
        "feedback_depth": enum_payload(
            getattr(request, "feedback_depth", None), "FeedbackDepth"
        ),
        "focus_area_count": len(getattr(request, "focus_areas", []) or []),
        "draft": text_stats(getattr(request, "draft_text", "") or ""),
        "rubric": text_stats(getattr(request, "rubric_text", "") or ""),
    }


def summarize_rubric_criteria_model(criteria: list[Any]) -> dict[str, Any]:
    return {
        "item_model": "RubricCriterion",
        "count": len(criteria),
        "weighted_count": sum(
            1
            for criterion in criteria
            if getattr(criterion, "weight", None) is not None
        ),
        "performance_level_count": sum(
            len(getattr(criterion, "performance_levels", []) or [])
            for criterion in criteria
        ),
        "criteria": [
            {
                "name_fingerprint": text_fingerprint(
                    getattr(criterion, "name", "") or ""
                ),
                "description": text_stats(getattr(criterion, "description", "") or ""),
                "has_weight": getattr(criterion, "weight", None) is not None,
                "performance_levels": len(
                    getattr(criterion, "performance_levels", []) or []
                ),
            }
            for criterion in criteria[:8]
        ],
    }


def summarize_feedback_response_model(
    response: Any, *, provider: str
) -> dict[str, Any]:
    rubric_items = getattr(response, "rubric_feedback", []) or []
    section_items = getattr(response, "section_feedback", []) or []
    inline_items = getattr(response, "inline_comments", []) or []
    revision_items = getattr(response, "revision_plan", []) or []
    metrics = getattr(response, "metrics", []) or []
    status_counts: dict[str, int] = {}
    for item in rubric_items:
        status = getattr(
            getattr(item, "status", None), "value", getattr(item, "status", "unknown")
        )
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    return {
        "model": "FeedbackResponse",
        "provider": provider,
        "session_id": str(getattr(response, "session_id", "")),
        "readiness_level": enum_payload(
            getattr(response, "readiness_level", None), "ReadinessLevel"
        ),
        "component_models": {
            "FeedbackMetric": len(metrics),
            "RubricFeedbackItem": len(rubric_items),
            "SectionFeedback": len(section_items),
            "InlineComment": len(inline_items),
            "RevisionPlanItem": len(revision_items),
        },
        "criterion_status": {"enum": "CriterionStatus", "counts": status_counts},
        "scored_rubric_items": sum(
            1
            for item in rubric_items
            if getattr(item, "estimated_points", None) is not None
            and getattr(item, "points_possible", None) is not None
        ),
        "strength_count": len(getattr(response, "strengths", []) or []),
        "priority_count": len(getattr(response, "top_priorities", []) or []),
        "checklist_count": len(getattr(response, "revision_checklist", []) or []),
        "topic_map_present": getattr(response, "topic_map", None) is not None,
    }


def summarize_topic_map_model(topic_map: Any | None) -> dict[str, Any]:
    if topic_map is None:
        return {"model": "TopicMap", "present": False, "TopicCluster": 0}
    clusters = getattr(topic_map, "clusters", []) or []
    return {
        "model": "TopicMap",
        "present": True,
        "method": getattr(topic_map, "method", ""),
        "summary": text_stats(getattr(topic_map, "summary", "") or ""),
        "TopicCluster": len(clusters),
        "clusters": [
            {
                "model": "TopicCluster",
                "label_fingerprint": text_fingerprint(
                    getattr(cluster, "label", "") or ""
                ),
                "draft_coverage": getattr(cluster, "draft_coverage", None),
                "rubric_weight": getattr(cluster, "rubric_weight", None),
                "rubric_terms_count": len(getattr(cluster, "rubric_terms", []) or []),
                "draft_terms_count": len(getattr(cluster, "draft_terms", []) or []),
                "missing_terms_count": len(getattr(cluster, "missing_terms", []) or []),
            }
            for cluster in clusters[:8]
        ],
    }


def model_inventory_payload() -> dict[str, Any]:
    return {
        "enums": ["CriterionStatus", "FeedbackDepth", "ReadinessLevel"],
        "pydantic_models": [
            "FeedbackMetric",
            "FeedbackRequest",
            "FeedbackResponse",
            "InlineComment",
            "RevisionPlanItem",
            "RubricCriterion",
            "RubricFeedbackItem",
            "SectionFeedback",
            "TopicCluster",
            "TopicMap",
        ],
    }


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(
                secret in lowered
                for secret in (
                    "api_key",
                    "token",
                    "secret",
                    "password",
                    "authorization",
                    "key",
                )
            ):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@traceable_stage(run_type="tool", name="Security Event")
def _trace_security_event(event_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"event": event_name, "payload": payload}


@traceable_stage(run_type="chain", name="Feedback Model Inventory")
def trace_feedback_model_inventory(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="chain", name="Feedback Request Model")
def trace_feedback_request_model(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="chain", name="Rubric Criteria Model")
def trace_rubric_criteria_model(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="chain", name="Feedback Response Model")
def trace_feedback_response_model(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="chain", name="Topic Map Model")
def trace_topic_map_model(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="tool", name="PII Masking Scan")
def trace_pii_masking_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="tool", name="Injection Scan")
def trace_injection_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="tool", name="Jailbreak Scan")
def trace_jailbreak_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="tool", name="Sensitive Leak Scan")
def trace_sensitive_leak_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@traceable_stage(run_type="tool", name="Scope Drift Scan")
def trace_scope_drift_scan(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


def log_security_event(event_name: str, **payload: Any) -> None:
    safe_payload = _redact(payload)
    logger.info(
        "%s %s", event_name, json.dumps(safe_payload, sort_keys=True, default=str)
    )
    if langsmith_tracing_enabled():
        _trace_security_event(event_name, safe_payload)
