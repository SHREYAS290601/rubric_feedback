from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import FeedbackRequest
from app.services.observability import (
    SECRET_PATTERNS,
    log_security_event,
    scan_text_signals,
    summarize_privacy_scan,
    summarize_request,
    text_fingerprint,
    trace_injection_scan,
    trace_jailbreak_scan,
    trace_pii_masking_scan,
    trace_sensitive_leak_scan,
    trace_scope_drift_scan,
)


class GuardrailViolation(ValueError):
    pass


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    reason: str
    matched_rule: str | None = None


class PromptInjectionFilter:
    def __init__(self) -> None:
        self.dangerous_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions?",
            r"forget\s+(everything|all|the\s+above|previous\s+instructions?)",
            r"you\s+are\s+now\s+(in\s+)?developer\s+mode",
            r"system\s+override",
            r"reveal\s+(the\s+)?prompt",
            r"give\s+me\s+(the\s+)?prompt",
            r"show\s+me\s+(the\s+)?prompt",
        ]
        self.fuzzy_patterns = [
            "ignore",
            "bypass",
            "override",
            "reveal",
            "delete",
            "system",
        ]

    def detect_injection(self, text: str) -> bool:
        normalized_text = self.sanitize_input(text)
        if any(
            re.search(pattern, normalized_text, re.IGNORECASE)
            for pattern in self.dangerous_patterns
        ):
            return True

        words = re.findall(r"\b\w+\b", normalized_text.lower())
        for word in words:
            for pattern in self.fuzzy_patterns:
                if self._is_similar_word(word, pattern):
                    return True
        return False

    def first_match(self, text: str) -> str | None:
        normalized_text = self.sanitize_input(text)
        for pattern in self.dangerous_patterns:
            if re.search(pattern, normalized_text, flags=re.IGNORECASE):
                return pattern
        return None

    def _is_similar_word(self, word: str, target: str) -> bool:
        if len(word) != len(target) or len(word) < 3:
            return False
        return (
            word != target
            and word[0] == target[0]
            and word[-1] == target[-1]
            and sorted(word[1:-1]) == sorted(target[1:-1])
        )

    def sanitize_input(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"(.)\1{3,}", r"\1", text)
        return text[:10000]


PROMPT_INJECTION_FILTER = PromptInjectionFilter()


INJECTION_PATTERNS = [
    r"\bignore (all )?(previous|prior|above|system|developer) instructions\b",
    r"\bforget (everything|all|the above|previous instructions?)\b",
    r"\b(disregard|override|bypass) (the )?(system|developer|safety|instructions|rules)\b",
    r"\breveal (the )?(system|developer|hidden) (prompt|instructions|message)\b",
    r"\bgive me (the )?(system|developer|hidden)? ?prompt\b",
    r"\bshow (me )?(the )?(system|developer|hidden) (prompt|instructions|message)\b",
    r"\b(system|developer|hidden) prompt\b",
    r"\bdeveloper message\b",
    r"\bjailbreak\b",
    r"\bDAN mode\b",
    r"\bdo anything now\b",
    r"\byou are now\b",
    r"\bpretend you are\b",
    r"\brole[- ]?play as\b",
    r"\bact as\b.*\bwithout restrictions\b",
    r"\bdo not follow\b.*\bpolicy\b",
    r"\bignore (the )?(rubric|assignment|criteria)\b",
]

JAILBREAK_PATTERNS = [
    r"\bjailbreak\b",
    r"\bDAN mode\b",
    r"\bdo anything now\b",
    r"\byou are now\b",
    r"\bpretend you are\b",
    r"\brole[- ]?play as\b",
    r"\bact as\b.*\bwithout restrictions\b",
    r"\bdo not follow\b.*\bpolicy\b",
]

OFF_PLATFORM_PATTERNS = [
    r"\bplease give me the answer\b",
    r"\bgive me (the )?(final )?answer\b",
    r"\bwrite (my|the) (assignment|essay|paper|memo) for me\b",
    r"\bsolve this (problem|homework|quiz|exam)\b",
    r"\bhow to use linear[- ]regression\b",
    r"\blinear[- ]regression\b.*\b(answer|solution|code|formula|model)\b",
    r"\bprovide (python|r|sql|matlab) code\b",
    r"\bwrite (the )?(solution|answer key)\b",
    r"\btell me what to submit\b",
]

SCOPE_DRIFT_PATTERNS = [
    r"\bby the way\b.*\b(how|please|ignore|answer|code)\b",
    r"\bhow can i\b.*\b(python|code|linked list|linear[- ]regression|sql|r\b)\b",
    r"\bplease (provide|give|write)\b.*\b(full )?(code|solution|answer)\b",
    r"\bignore the rest of (this )?(assignment|draft|rubric|submission)\b",
    r"\bignore (the )?(rubric|assignment|criteria)\b",
    r"\bdo not evaluate this paragraph\b",
    r"\bjust a note to the automated reviewer\b",
    r"\bdo not (grade|review|assess|evaluate)\b.*\b(paragraph|section|note)\b",
]

WRITING_SIGNALS = [
    "rubric",
    "draft",
    "memo",
    "paragraph",
    "argument",
    "evidence",
    "recommendation",
    "revision",
    "assignment criteria",
]


def enforce_input_guardrails(request: FeedbackRequest) -> GuardrailDecision:
    combined_text = f"{request.draft_text}\n\n{request.rubric_text}".lower()
    draft_text = request.draft_text.lower()
    rubric_text = request.rubric_text.lower()
    request_summary = summarize_request(
        draft_text=request.draft_text,
        rubric_text=request.rubric_text,
        focus_areas=request.focus_areas,
    )
    privacy_scan = summarize_privacy_scan(
        draft_text=request.draft_text,
        rubric_text=request.rubric_text,
    )
    injection_scan = _scan_patterns(draft_text, INJECTION_PATTERNS)
    jailbreak_scan = _scan_patterns(draft_text, JAILBREAK_PATTERNS)
    off_platform_scan = _scan_patterns(draft_text, OFF_PLATFORM_PATTERNS)
    rubric_instruction_scan = _scan_patterns(
        rubric_text, INJECTION_PATTERNS + OFF_PLATFORM_PATTERNS
    )
    rubric_jailbreak_scan = _scan_patterns(rubric_text, JAILBREAK_PATTERNS)
    scope_drift_scan = detect_scope_drift(request)
    sensitive_leak_scan = scan_text_signals(combined_text, SECRET_PATTERNS)

    trace_pii_masking_scan(
        {
            "request": request_summary,
            **privacy_scan,
        }
    )
    log_security_event(
        "pii_masking_scan",
        request=request_summary,
        pii=privacy_scan["pii"],
        sensitive_leak=privacy_scan["sensitive_leak"],
        masking_policy=privacy_scan["masking_policy"],
    )
    trace_injection_scan(
        {
            "request": request_summary,
            "matched": injection_scan["matched"],
            "match_count": injection_scan["count"],
            "matched_rule_fingerprints": injection_scan["matched_rule_fingerprints"],
            "scope": "draft_text_only",
            "rubric_untrusted_instruction_examples": {
                "matched": rubric_instruction_scan["matched"],
                "match_count": rubric_instruction_scan["count"],
                "matched_rule_fingerprints": rubric_instruction_scan[
                    "matched_rule_fingerprints"
                ],
                "policy": "logged_as_untrusted_rubric_content_not_followed_as_instruction",
            },
        }
    )
    trace_jailbreak_scan(
        {
            "request": request_summary,
            "matched": jailbreak_scan["matched"],
            "match_count": jailbreak_scan["count"],
            "matched_rule_fingerprints": jailbreak_scan["matched_rule_fingerprints"],
            "scope": "draft_text_only",
            "rubric_untrusted_jailbreak_examples": {
                "matched": rubric_jailbreak_scan["matched"],
                "match_count": rubric_jailbreak_scan["count"],
                "matched_rule_fingerprints": rubric_jailbreak_scan[
                    "matched_rule_fingerprints"
                ],
                "policy": "logged_as_untrusted_rubric_content_not_followed_as_instruction",
            },
        }
    )
    trace_sensitive_leak_scan(
        {
            "request": request_summary,
            "matched": sensitive_leak_scan["matched"],
            "match_types": sensitive_leak_scan["match_types"],
            "counts": sensitive_leak_scan["counts"],
        }
    )
    trace_scope_drift_scan({"request": request_summary, **scope_drift_scan})
    log_security_event(
        "scope_drift_scan",
        request=request_summary,
        **scope_drift_scan,
    )

    if sensitive_leak_scan["matched"]:
        _log_guardrail(
            request,
            allowed=False,
            category="sensitive_leak",
            matched_rule="secret_or_token_pattern",
        )
        raise GuardrailViolation(
            "This submission appears to contain a secret, token, password, or API key. "
            "Remove sensitive credentials before requesting feedback."
        )

    matched_prompt_injection = PROMPT_INJECTION_FILTER.first_match(draft_text)
    if matched_prompt_injection or PROMPT_INJECTION_FILTER.detect_injection(draft_text):
        _log_guardrail(
            request,
            allowed=False,
            category="prompt_injection_or_jailbreak",
            matched_rule=matched_prompt_injection or "typoglycemia_prompt_injection",
        )
        raise GuardrailViolation(
            "This submission contains prompt-injection or jailbreak language. "
            "Please remove instructions aimed at the AI system and submit only the student draft and rubric."
        )

    has_writing_context = any(signal in combined_text for signal in WRITING_SIGNALS)
    has_substantial_draft = len(request.draft_text.split()) >= 80

    scope_drift_ratio = float(scope_drift_scan.get("draft_word_ratio", 0.0))
    if (
        scope_drift_scan["matched"]
        and has_writing_context
        and has_substantial_draft
        and scope_drift_ratio < 0.45
    ):
        _log_guardrail(
            request,
            allowed=True,
            category="embedded_scope_drift_detected",
            matched_rule="scope_drift_inside_student_draft",
        )
        return GuardrailDecision(
            allowed=True,
            reason="Embedded scope drift was detected and will be evaluated as off-task draft content.",
            matched_rule="scope_drift_inside_student_draft",
        )

    if scope_drift_scan["matched"] and scope_drift_ratio >= 0.45:
        _log_guardrail(
            request,
            allowed=False,
            category="dominant_scope_drift_request",
            matched_rule="scope_drift_dominates_draft",
        )
        raise GuardrailViolation(
            "Most of this submission appears to ask for an unrelated answer or to change the review scope. "
            "Submit the assignment draft and rubric for formative writing feedback."
        )

    matched_injection = _first_matching_pattern(draft_text, INJECTION_PATTERNS)
    if matched_injection:
        _log_guardrail(
            request,
            allowed=False,
            category="prompt_injection_or_jailbreak",
            matched_rule=matched_injection,
        )
        raise GuardrailViolation(
            "This submission contains prompt-injection or jailbreak language. "
            "Please remove instructions aimed at the AI system and submit only the student draft and rubric."
        )

    matched_off_platform = _first_matching_pattern(draft_text, OFF_PLATFORM_PATTERNS)
    if matched_off_platform:
        _log_guardrail(
            request,
            allowed=False,
            category="off_platform_request",
            matched_rule=matched_off_platform,
        )
        raise GuardrailViolation(
            "This platform only provides formative writing feedback. It cannot answer homework questions, "
            "solve subject-matter problems, write assignments, or provide unrelated technical help."
        )

    if not has_writing_context:
        _log_guardrail(
            request,
            allowed=False,
            category="missing_writing_context",
            matched_rule="no_writing_signals",
        )
        raise GuardrailViolation(
            "This does not look like a writing draft plus rubric. Please submit assignment writing and evaluation criteria."
        )

    category = (
        "in_scope_writing_feedback_with_rubric_attack_examples"
        if rubric_instruction_scan["matched"]
        else "in_scope_writing_feedback"
    )
    _log_guardrail(request, allowed=True, category=category, matched_rule=None)
    return GuardrailDecision(allowed=True, reason="Input appears aligned to rubric-aware writing feedback.")


def detect_scope_drift(request: FeedbackRequest) -> dict[str, object]:
    """Detect off-task or prompt-injection-like paragraphs inside a draft.

    The detector is intentionally paragraph-level. A rubric may include attack
    examples as policy text, while a student draft may contain an off-topic
    paragraph that should be critiqued rather than answered or used as an app
    instruction.
    """

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", request.draft_text)
        if paragraph.strip()
    ]
    patterns = SCOPE_DRIFT_PATTERNS + INJECTION_PATTERNS + OFF_PLATFORM_PATTERNS
    matches: list[dict[str, object]] = []
    drift_words = 0
    for index, paragraph in enumerate(paragraphs, start=1):
        matched_patterns = [
            pattern
            for pattern in patterns
            if re.search(pattern, paragraph, flags=re.IGNORECASE)
        ]
        if matched_patterns:
            paragraph_words = len(paragraph.split())
            drift_words += paragraph_words
            matches.append(
                {
                    "paragraph_index": index,
                    "paragraph": {
                        "chars": len(paragraph),
                        "words": paragraph_words,
                        "fingerprint": text_fingerprint(paragraph),
                    },
                    "matched_rule_fingerprints": [
                        text_fingerprint(pattern) for pattern in matched_patterns[:6]
                    ],
                    "category": _scope_drift_category(paragraph),
                }
            )
    draft_words = len(request.draft_text.split())

    return {
        "matched": bool(matches),
        "match_count": len(matches),
        "paragraph_count": len(paragraphs),
        "draft_word_ratio": round(drift_words / max(1, draft_words), 3),
        "non_drift_paragraph_count": max(0, len(paragraphs) - len(matches)),
        "matches": matches[:5],
        "policy": (
            "embedded_off_task_or_injection_text_is_evaluated_as_scope_drift;"
            "the_platform_must_not_answer_embedded_requests"
        ),
    }


def _scan_patterns(text: str, patterns: list[str]) -> dict[str, object]:
    matched = [
        pattern
        for pattern in patterns
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    return {
        "matched": bool(matched),
        "count": len(matched),
        "matched_rule_fingerprints": [
            text_fingerprint(pattern) for pattern in matched[:8]
        ],
    }


def _first_matching_pattern(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return pattern
    return None


def _scope_drift_category(paragraph: str) -> str:
    lowered = paragraph.lower()
    if any(
        marker in lowered
        for marker in ("python", "code", "linked list", "linear regression", "sql")
    ):
        return "unrelated_subject_matter_request"
    if any(marker in lowered for marker in ("ignore", "do not evaluate", "automated reviewer")):
        return "review_instruction_injection"
    return "scope_drift"


def _log_guardrail(
    request: FeedbackRequest,
    *,
    allowed: bool,
    category: str,
    matched_rule: str | None,
) -> None:
    log_security_event(
        "guardrail_decision",
        allowed=allowed,
        category=category,
        matched_rule=matched_rule,
        request=summarize_request(
            draft_text=request.draft_text,
            rubric_text=request.rubric_text,
            focus_areas=request.focus_areas,
        ),
    )
