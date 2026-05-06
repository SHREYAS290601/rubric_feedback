from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import uuid4

from app.models import (
    DISCLAIMER,
    CriterionStatus,
    FeedbackDepth,
    FeedbackMetric,
    FeedbackRequest,
    FeedbackResponse,
    InlineComment,
    ReadinessLevel,
    RevisionPlanItem,
    RubricCriterion,
    RubricFeedbackItem,
    SectionFeedback,
    TopicCluster,
    TopicMap,
)
from app.services.ai_provider import (
    generate_llm_feedback,
    llm_configuration_error,
    llm_is_configured,
)
from app.services.guardrails import detect_scope_drift, enforce_input_guardrails
from app.services.observability import (
    log_security_event,
    model_inventory_payload,
    summarize_feedback_request_model,
    summarize_feedback_response_model,
    summarize_rubric_criteria_model,
    summarize_topic_map_model,
    summarize_request,
    traceable_stage,
    trace_feedback_model_inventory,
    trace_feedback_request_model,
    trace_feedback_response_model,
    trace_rubric_criteria_model,
    trace_topic_map_model,
)


@dataclass
class FeedbackState:
    request: FeedbackRequest
    criteria: list[RubricCriterion] = field(default_factory=list)
    structure_findings: dict[str, list[str] | str] = field(default_factory=dict)
    argument_findings: dict[str, list[str] | str] = field(default_factory=dict)
    rubric_feedback: list[RubricFeedbackItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    scope_drift: dict[str, object] = field(default_factory=dict)


def generate_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Run guarded feedback generation.

    If an OpenAI/Azure OpenAI provider is configured, use it with strict
    structured output. Otherwise run the deterministic local workflow so the
    prototype remains demoable without keys.
    """

    log_security_event(
        "feedback_pipeline_started",
        request=summarize_request(
            draft_text=request.draft_text,
            rubric_text=request.rubric_text,
            focus_areas=request.focus_areas,
        ),
    )
    trace_feedback_model_inventory(model_inventory_payload())
    trace_feedback_request_model(summarize_feedback_request_model(request))
    enforce_input_guardrails(request)
    scope_drift = detect_scope_drift(request)
    if llm_is_configured():
        try:
            response = _apply_scope_drift_feedback(
                _response_with_topic_map(generate_llm_feedback(request), request),
                request,
                scope_drift,
            )
            _trace_response_models(response, provider="llm")
            _trace_feedback_result(_feedback_trace_summary(response, provider="llm"))
            log_security_event(
                "feedback_pipeline_completed",
                provider="llm",
                result=_feedback_trace_summary(response, provider="llm"),
            )
            return response
        except Exception as exc:
            # Keep the student flow alive if an external provider returns invalid
            # schema output, runs out of credits, or has a transient outage.
            log_security_event(
                "llm_feedback_fallback_to_local",
                error_type=exc.__class__.__name__,
                provider="llm",
            )
            pass
    configuration_error = llm_configuration_error()
    if configuration_error:
        raise configuration_error

    state = FeedbackState(request=request, scope_drift=scope_drift)
    _validate_inputs(state)
    _parse_rubric(state)
    trace_rubric_criteria_model(summarize_rubric_criteria_model(state.criteria))
    _analyze_structure(state)
    _analyze_argumentation(state)
    _align_to_rubric(state)
    response = _apply_scope_drift_feedback(
        _synthesize_feedback(state), request, scope_drift
    )
    checked_response = _quality_check(response)
    _trace_response_models(checked_response, provider="local")
    _trace_feedback_result(_feedback_trace_summary(checked_response, provider="local"))
    log_security_event(
        "feedback_pipeline_completed",
        provider="local",
        result=_feedback_trace_summary(checked_response, provider="local"),
    )
    return checked_response


@traceable_stage(run_type="chain", name="Feedback Result Summary")
def _trace_feedback_result(payload: dict[str, object]) -> dict[str, object]:
    return payload


def _feedback_trace_summary(
    response: FeedbackResponse, *, provider: str
) -> dict[str, object]:
    scored_items = [
        item
        for item in response.rubric_feedback
        if item.estimated_points is not None and item.points_possible is not None
    ]
    return {
        "provider": provider,
        "session_id": str(response.session_id),
        "readiness_level": response.readiness_level.value,
        "rubric_feedback_items": len(response.rubric_feedback),
        "scored_rubric_items": len(scored_items),
        "inline_comments": len(response.inline_comments),
        "revision_plan_steps": len(response.revision_plan),
        "topic_clusters": len(response.topic_map.clusters) if response.topic_map else 0,
    }


def _trace_response_models(response: FeedbackResponse, *, provider: str) -> None:
    trace_feedback_response_model(summarize_feedback_response_model(response, provider=provider))
    trace_topic_map_model(summarize_topic_map_model(response.topic_map))


def _validate_inputs(state: FeedbackState) -> None:
    draft_words = _words(state.request.draft_text)
    rubric_words = _words(state.request.rubric_text)

    if len(draft_words) < 80:
        state.warnings.append("Draft is short, so feedback may be limited.")
    if len(rubric_words) < 20:
        state.warnings.append("Rubric is brief, so alignment may be less specific.")


def _parse_rubric(state: FeedbackState) -> None:
    rubric_text = state.request.rubric_text
    lines = _rubric_lines(rubric_text)
    criteria = _parse_points_rubric(lines)
    if criteria:
        state.criteria = criteria
        return

    candidate_lines = [
        line
        for line in lines
        if (
            len(line.split()) >= 2
            and not _looks_like_rubric_header(line)
            and not _looks_like_noncriterion_line(line)
            and _looks_like_rubric_candidate(line)
        )
    ]
    criteria = []

    for index, line in enumerate(candidate_lines[:8], start=1):
        name, description = _split_criterion(line, index)
        criteria.append(
            RubricCriterion(
                name=name,
                description=description,
                weight=_extract_weight(line),
                performance_levels=_extract_performance_levels(line),
            )
        )

    if not criteria:
        criteria = [
            RubricCriterion(
                name="Rubric Alignment",
                description="Addresses the assignment criteria provided by the instructor.",
            )
        ]

    state.criteria = criteria


def _analyze_structure(state: FeedbackState) -> None:
    draft = state.request.draft_text
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", draft) if p.strip()]
    first_paragraph = paragraphs[0] if paragraphs else draft[:500]
    off_prompt = _is_off_prompt_memo_submission(state)

    thesis_markers = ("argue", "recommend", "should", "because", "therefore")
    has_claim = any(marker in first_paragraph.lower() for marker in thesis_markers)
    has_transitions = any(
        marker in draft.lower()
        for marker in (
            "however",
            "therefore",
            "first",
            "second",
            "finally",
            "in contrast",
        )
    )

    strengths: list[str] = []
    issues: list[str] = []

    if off_prompt:
        issues.append(
            "The submission reads like a reflection essay rather than the requested executive consulting memo."
        )

    if len(paragraphs) >= 3:
        strengths.append("The draft is separated into multiple sections or paragraphs.")
    else:
        issues.append(
            "The organization may be hard to follow because the draft has few paragraph breaks."
        )

    if has_claim:
        strengths.append(
            "The opening appears to include a central claim or recommendation."
        )
    else:
        issues.append(
            "The central claim or recommendation could be stated more directly near the beginning."
        )

    if has_transitions:
        strengths.append("The draft uses some transition language to guide the reader.")
    else:
        issues.append("Transitions between ideas could be clearer.")

    state.structure_findings = {
        "summary": "Structure review completed for organization, claim clarity, and flow.",
        "strengths": strengths,
        "issues": issues,
        "evidence": [_sample_sentence(draft)],
    }


def _analyze_argumentation(state: FeedbackState) -> None:
    draft = state.request.draft_text
    off_prompt = _is_off_prompt_memo_submission(state)
    evidence_markers = (
        "data",
        "case",
        "research",
        "example",
        "because",
        "evidence",
        "%",
        "$",
    )
    has_evidence = any(marker in draft.lower() for marker in evidence_markers)
    has_counterpoint = any(
        marker in draft.lower()
        for marker in ("although", "however", "risk", "tradeoff")
    )

    strong_claims = []
    unsupported_claims = []
    reasoning_gaps = []

    if off_prompt:
        unsupported_claims.append(
            "The draft does not yet make a prioritized recommendation for NovaMart executives."
        )
        reasoning_gaps.append(
            "The analysis needs to use the disruption details as business evidence, not only as reflection."
        )

    if has_evidence:
        strong_claims.append("The draft includes some evidence or explanatory support.")
    else:
        unsupported_claims.append(
            "Several claims may need more concrete evidence from the case, prompt, or course materials."
        )

    if has_counterpoint:
        strong_claims.append("The draft acknowledges some complexity or tradeoffs.")
    else:
        reasoning_gaps.append(
            "Consider addressing tradeoffs, risks, or counterarguments to strengthen the reasoning."
        )

    state.argument_findings = {
        "summary": "Argument review completed for claim support, reasoning, and evidence use.",
        "strong_claims": strong_claims,
        "unsupported_claims": unsupported_claims,
        "reasoning_gaps": reasoning_gaps,
    }


def _align_to_rubric(state: FeedbackState) -> None:
    items: list[RubricFeedbackItem] = []

    for criterion in state.criteria:
        items.append(
            _with_formative_score(
                _rubric_feedback_for_criterion(state, criterion), criterion
            )
        )

    state.rubric_feedback = items


def _synthesize_feedback(state: FeedbackState) -> FeedbackResponse:
    structure_strengths = list(state.structure_findings.get("strengths", []))
    argument_strengths = list(state.argument_findings.get("strong_claims", []))
    structure_issues = list(state.structure_findings.get("issues", []))
    unsupported_claims = list(state.argument_findings.get("unsupported_claims", []))
    reasoning_gaps = list(state.argument_findings.get("reasoning_gaps", []))

    max_items = 5 if state.request.feedback_depth == FeedbackDepth.deep else 3
    off_prompt = _is_off_prompt_memo_submission(state)
    if off_prompt:
        strengths = [
            "The draft is readable and identifies technology dependence as a relevant theme.",
            "It recognizes customer trust and employee training as concerns worth developing.",
        ][:max_items]
        priorities = [
            "Reframe the reflection as an executive consulting memo with a clear recommendation.",
            "Use specific NovaMart disruption evidence such as delayed deliveries, support tickets, partner risk, and routing failure.",
            "Add immediate, near-term, and prevention actions instead of broad values statements.",
        ][:max_items]
    else:
        strengths = (structure_strengths + argument_strengths)[:max_items] or [
            "The draft gives you a starting point for revision."
        ]
        priorities = (structure_issues + unsupported_claims + reasoning_gaps)[
            :max_items
        ] or ["Make the strongest rubric connections more explicit."]

    needs_work_count = sum(
        item.status in {CriterionStatus.needs_work, CriterionStatus.not_enough_evidence}
        for item in state.rubric_feedback
    )
    readiness = (
        ReadinessLevel.early
        if off_prompt or needs_work_count >= max(2, len(state.rubric_feedback) // 2)
        else ReadinessLevel.developing
    )

    checklist = [
        "State the main claim or recommendation clearly near the beginning.",
        "Add specific evidence for the most important claims.",
        "Connect each major section back to the rubric language.",
        "Revise transitions so the reader can follow the argument.",
        "Check whether any rubric criterion still lacks enough evidence.",
    ]
    if state.request.learning_goal:
        checklist.insert(
            0,
            f"Check whether the revision supports your goal: {state.request.learning_goal}",
        )

    return FeedbackResponse(
        session_id=uuid4(),
        overall_summary=_overall_summary(state, off_prompt),
        readiness_level=readiness,
        metrics=_build_metrics(state, readiness),
        strengths=strengths,
        top_priorities=priorities,
        section_feedback=_build_section_feedback(state),
        rubric_feedback=state.rubric_feedback,
        inline_comments=_build_inline_comments(state),
        coaching_questions=_build_coaching_questions(state),
        revision_plan=_build_revision_plan(state, priorities),
        topic_map=_build_topic_map(state),
        revision_checklist=checklist,
        disclaimer=DISCLAIMER,
    )


def _quality_check(response: FeedbackResponse) -> FeedbackResponse:
    banned_grade_terms = ("grade", "A+", "A-", "B+", "B-", "score")
    if any(
        term.lower() in response.overall_summary.lower() for term in banned_grade_terms
    ):
        response.overall_summary = response.overall_summary.replace("grade", "feedback")
    return response


def _response_with_topic_map(
    response: FeedbackResponse, request: FeedbackRequest
) -> FeedbackResponse:
    state = FeedbackState(request=request)
    _parse_rubric(state)
    if (
        len(state.criteria) == 1
        and state.criteria[0].name == "Rubric Alignment"
        and response.rubric_feedback
    ):
        state.criteria = [
            RubricCriterion(
                name=item.criterion,
                description=item.suggestion,
                weight=item.points_possible,
            )
            for item in response.rubric_feedback[:8]
        ]
    state.rubric_feedback = response.rubric_feedback
    return response.model_copy(update={"topic_map": _build_topic_map(state)})


def _apply_scope_drift_feedback(
    response: FeedbackResponse,
    request: FeedbackRequest,
    scope_drift: dict[str, object],
) -> FeedbackResponse:
    if not scope_drift.get("matched"):
        return response

    target_text = _scope_drift_target_text(request, scope_drift)
    priority = (
        "Remove the off-topic paragraph that asks for an unrelated answer or tries to "
        "change how the reviewer evaluates the assignment."
    )
    section = SectionFeedback(
        area="Assignment focus and scope control",
        finding=(
            "One section of the draft shifts away from the assignment and asks an unrelated "
            "question instead of continuing the business analysis."
        ),
        why_it_matters=(
            "The rubric evaluates the submitted business analysis. Embedded instructions to "
            "answer another task are scope drift and should be treated as draft content to remove."
        ),
        revision_move=(
            "Delete the off-topic paragraph and replace it only if the assignment needs more "
            "analysis of the fine-tuning versus RAG decision."
        ),
    )
    inline = InlineComment(
        target_text=target_text,
        comment=(
            "This paragraph is off-task and prompt-injection-like. The tool should not answer it; "
            "the revision should remove it."
        ),
        revision_prompt=(
            "What business-analysis point should be here instead, or should this paragraph be deleted?"
        ),
    )
    plan_item = RevisionPlanItem(
        priority="Remove scope drift",
        action="Delete the unrelated request and any instruction telling the reviewer to ignore the rubric or assignment.",
        expected_impact="The draft stays aligned to the assignment and avoids confusing the feedback workflow.",
        time_estimate="5 minutes",
    )

    metrics = [
        FeedbackMetric(
            label="Scope control",
            value="Needs refocus",
            detail="An off-topic or injection-like paragraph was detected and ignored as an instruction.",
        )
    ] + [
        metric for metric in response.metrics if metric.label.lower() != "feedback depth"
    ]
    rubric_feedback = _mark_scope_rubric_item(response.rubric_feedback)

    return response.model_copy(
        update={
            "overall_summary": (
                "One paragraph breaks assignment focus by asking for unrelated help; remove it. "
                + response.overall_summary
            ),
            "readiness_level": ReadinessLevel.early,
            "metrics": metrics[:6],
            "top_priorities": _prepend_unique(priority, response.top_priorities, limit=5),
            "section_feedback": [section]
            + [
                item
                for item in response.section_feedback
                if item.area.lower() != section.area.lower()
            ][:7],
            "rubric_feedback": rubric_feedback,
            "inline_comments": [inline] + response.inline_comments[:5],
            "revision_plan": [plan_item] + response.revision_plan[:5],
            "revision_checklist": _prepend_unique(
                "Remove unrelated requests, code questions, or instructions that try to change the assignment scope.",
                response.revision_checklist,
                limit=8,
            ),
        }
    )


def _scope_drift_target_text(
    request: FeedbackRequest, scope_drift: dict[str, object]
) -> str:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n+", request.draft_text)
        if paragraph.strip()
    ]
    matches = scope_drift.get("matches")
    if isinstance(matches, list) and matches:
        first_match = matches[0]
        if isinstance(first_match, dict):
            paragraph_index = first_match.get("paragraph_index")
            if isinstance(paragraph_index, int) and 1 <= paragraph_index <= len(paragraphs):
                return paragraphs[paragraph_index - 1][:220]
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        if any(
            marker in lowered
            for marker in (
                "ignore the rest",
                "do not evaluate",
                "linked list",
                "python",
                "please provide the full code",
            )
        ):
            return paragraph[:220]
    return _sample_sentence(request.draft_text)[:220]


def _mark_scope_rubric_item(
    items: list[RubricFeedbackItem],
) -> list[RubricFeedbackItem]:
    updated: list[RubricFeedbackItem] = []
    changed = False
    for item in items:
        lowered = item.criterion.lower()
        if any(term in lowered for term in ("focus", "scope", "assignment")):
            updated.append(
                item.model_copy(
                    update={
                        "status": CriterionStatus.needs_work,
                        "evidence_from_draft": (
                            "A paragraph asks for an unrelated answer and tells the reviewer "
                            "not to evaluate that paragraph."
                        ),
                        "suggestion": (
                            "Remove the unrelated request so the submission stays focused on the assignment."
                        ),
                        "why_it_matters": (
                            "Scope control is part of academic writing and also prevents prompt-injection-like text from steering feedback."
                        ),
                    }
                )
            )
            changed = True
        else:
            updated.append(item)
    if changed:
        return updated
    return [
        RubricFeedbackItem(
            criterion="Assignment focus and scope control",
            status=CriterionStatus.needs_work,
            evidence_from_draft=(
                "A paragraph asks for unrelated help and tries to change the review scope."
            ),
            suggestion="Remove the off-topic paragraph and keep the analysis focused on the rubric.",
            why_it_matters=(
                "The tool evaluates the submitted writing; it should never answer unrelated embedded requests."
            ),
        )
    ] + items


def _prepend_unique(item: str, values: list[str], *, limit: int) -> list[str]:
    normalized_item = item.lower()
    result = [item]
    for value in values:
        if value.lower() != normalized_item:
            result.append(value)
        if len(result) >= limit:
            break
    return result[:limit]


def _overall_summary(state: FeedbackState, off_prompt: bool) -> str:
    if off_prompt:
        return (
            "The draft is readable, but it does not yet match the assignment: it reads as a reflection "
            "instead of an executive consulting memo. The next revision should convert the ideas into a "
            "problem diagnosis, evidence-based recommendation, stakeholder trade-off analysis, and action plan."
        )
    return (
        "This draft has a workable foundation, but the next revision should focus "
        "on clearer rubric alignment, stronger evidence, and more explicit reasoning."
    )


def _parse_points_rubric(lines: list[str]) -> list[RubricCriterion]:
    start_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "assessment rubric" in line.lower()
            or line.lower() in {"rubric", "grading rubric"}
        ),
        -1,
    )
    if start_index < 0:
        return []

    header_end = next(
        (
            index
            for index, line in enumerate(lines[start_index:], start=start_index)
            if line.lower() in {"pts", "points", "score"}
        ),
        -1,
    )
    if header_end < 0:
        return []

    criteria: list[RubricCriterion] = []
    row_lines: list[str] = []
    for line in lines[header_end + 1 :]:
        if _is_rubric_stop_line(line):
            break
        if re.fullmatch(r"\d+(?:\.\d+)?", line):
            criterion = _criterion_from_points_row(
                row_lines, float(line), len(criteria) + 1
            )
            if criterion:
                criteria.append(criterion)
            row_lines = []
            continue
        if line and not _looks_like_rubric_header(line):
            row_lines.append(line)

    return criteria[:8]


def _criterion_from_points_row(
    row_lines: list[str], points: float, index: int
) -> RubricCriterion | None:
    cleaned = [
        line
        for line in row_lines
        if line
        and not _looks_like_noncriterion_line(line)
        and not re.fullmatch(r"page\s+\d+", line, re.IGNORECASE)
    ]
    if not cleaned:
        return None

    description_start = len(cleaned)
    for position, line in enumerate(cleaned):
        if position > 0 and _looks_like_descriptor_start(line):
            description_start = position
            break
        if position >= 3 and not line.endswith(","):
            description_start = position + 1
            break

    name_parts = cleaned[:description_start]
    description_parts = cleaned[description_start:]
    name = _clean_criterion_name(_clean_inline_text(" ".join(name_parts)))[:80]
    description = _clean_inline_text(" ".join(description_parts)) or _clean_inline_text(
        " ".join(cleaned)
    )
    if not name:
        name = f"Criterion {index}"

    return RubricCriterion(
        name=name,
        description=description,
        weight=points,
        performance_levels=["Excellent", "Proficient", "Developing", "Needs Revision"],
    )


def _looks_like_descriptor_start(line: str) -> bool:
    lowered = line.lower().strip()
    descriptor_starts = (
        "defines",
        "uses",
        "provides",
        "gives",
        "thoughtfully",
        "addresses",
        "mentions",
        "unclear",
        "little",
        "no clear",
        "ignores",
        "executive-ready",
        "generally",
        "some structure",
        "disorganized",
        "clear,",
        "mostly clear",
        "understandable",
        "difficult",
    )
    return lowered.startswith(descriptor_starts)


def _rubric_feedback_for_criterion(
    state: FeedbackState, criterion: RubricCriterion
) -> RubricFeedbackItem:
    draft = state.request.draft_text
    draft_lower = draft.lower()
    name_lower = criterion.name.lower()
    off_prompt = _is_off_prompt_memo_submission(state)

    if "problem" in name_lower or "framing" in name_lower:
        evidence = _best_sentence(
            draft,
            (
                "cyber incident",
                "technology can fail",
                "late deliveries",
                "routing",
                "disruption",
            ),
        )
        status = (
            CriterionStatus.needs_work
            if off_prompt
            else CriterionStatus.partially_meets
        )
        suggestion = "Open with a precise diagnosis of the fulfillment disruption, its root causes, and why it matters to NovaMart executives."
        why = "The assignment asks for crisis framing, not a broad reflection on technology."
    elif "evidence" in name_lower or "analysis" in name_lower:
        evidence = _best_sentence(
            draft, ("late", "customers", "technology", "case", "support", "partners")
        )
        has_specific_data = any(
            marker in draft_lower
            for marker in ("72-hour", "31%", "support tickets", "enterprise partners")
        )
        status = (
            CriterionStatus.partially_meets
            if has_specific_data
            else CriterionStatus.needs_work
        )
        suggestion = "Bring in concrete scenario details and explain their operational, customer, financial, and trust implications."
        why = "Evidence-based analysis is what turns the memo from opinion into a business recommendation."
    elif "recommendation" in name_lower:
        evidence = _best_sentence(
            draft, ("should", "training", "transparent", "prepared", "recommendation")
        )
        has_prioritized_actions = any(
            marker in draft_lower
            for marker in (
                "immediate",
                "near-term",
                "prevent",
                "prioritize",
                "stabilize",
            )
        )
        status = (
            CriterionStatus.partially_meets
            if has_prioritized_actions
            else CriterionStatus.needs_work
        )
        suggestion = "Replace broad advice with prioritized immediate, recovery, and prevention actions."
        why = "Executives need a sequence of feasible actions, not only values or general observations."
    elif "stakeholder" in name_lower or "trade" in name_lower:
        evidence = _best_sentence(
            draft,
            ("customers", "workers", "employees", "partners", "technology", "security"),
        )
        stakeholder_hits = sum(
            1
            for marker in (
                "customers",
                "workers",
                "employees",
                "partners",
                "technology",
                "security",
            )
            if marker in draft_lower
        )
        status = (
            CriterionStatus.partially_meets
            if stakeholder_hits >= 2
            else CriterionStatus.needs_work
        )
        suggestion = "Name the trade-offs for customers, employees, enterprise partners, and technology or security teams."
        why = "Stakeholder trade-offs show that the recommendation is feasible under real constraints."
    elif "organization" in name_lower or "memo" in name_lower or "style" in name_lower:
        evidence = _best_sentence(
            draft,
            ("reflection essay", "technology and society", "my thoughts", "conclusion"),
        )
        status = (
            CriterionStatus.needs_work
            if off_prompt
            else CriterionStatus.partially_meets
        )
        suggestion = "Restructure the piece with memo headings such as executive summary, diagnosis, analysis, recommendation, risks, and metrics."
        why = "The expected deliverable is an executive-ready memo, so structure is part of the task."
    elif (
        "clarity" in name_lower
        or "professional" in name_lower
        or "revision" in name_lower
    ):
        evidence = _best_sentence(
            draft, ("in my opinion", "personally", "overall", "should")
        )
        status = CriterionStatus.partially_meets
        suggestion = "Keep the readable tone, but make the language more specific, concise, and action-oriented."
        why = "Clear professional prose helps the reader see exactly what decision the memo recommends."
    else:
        return _generic_rubric_feedback(state, criterion)

    return RubricFeedbackItem(
        criterion=criterion.name,
        status=status,
        evidence_from_draft=evidence,
        suggestion=suggestion,
        why_it_matters=why,
    )


def _with_formative_score(
    item: RubricFeedbackItem, criterion: RubricCriterion
) -> RubricFeedbackItem:
    if criterion.weight is None:
        return item

    ratios = {
        CriterionStatus.meets: 0.9,
        CriterionStatus.partially_meets: 0.62,
        CriterionStatus.needs_work: 0.32,
        CriterionStatus.not_enough_evidence: 0.0,
    }
    estimated = round(criterion.weight * ratios[item.status], 1)
    if estimated.is_integer():
        estimated = int(estimated)

    return item.model_copy(
        update={
            "points_possible": criterion.weight,
            "estimated_points": estimated,
            "score_rationale": (
                "Formative evidence coverage estimate from the submitted draft and rubric; "
                "not a final grade."
            ),
        }
    )


def _generic_rubric_feedback(
    state: FeedbackState, criterion: RubricCriterion
) -> RubricFeedbackItem:
    draft_lower = state.request.draft_text.lower()
    criterion_terms = [
        word.lower()
        for word in re.findall(
            r"[A-Za-z]{5,}", f"{criterion.name} {criterion.description}"
        )
    ][:8]
    overlap = sum(1 for term in criterion_terms if term in draft_lower)

    if overlap >= 2:
        status = CriterionStatus.partially_meets
        evidence = _best_sentence(state.request.draft_text, tuple(criterion_terms))
        suggestion = f"Make the connection to '{criterion.name}' more explicit with specific draft evidence."
        why_it_matters = (
            "The reader should not have to infer how the draft satisfies the rubric."
        )
    elif overlap == 1:
        status = CriterionStatus.needs_work
        evidence = "The draft touches this area, but the connection is not yet developed enough."
        suggestion = f"Add a focused sentence or paragraph that directly addresses '{criterion.name}'."
        why_it_matters = "A visible rubric connection makes revision more actionable."
    else:
        status = CriterionStatus.not_enough_evidence
        evidence = "Not enough evidence was found in the draft to evaluate this criterion confidently."
        suggestion = f"Review the rubric language for '{criterion.name}' and add content that clearly responds to it."
        why_it_matters = "Marking uncertainty is safer than guessing and helps the learner decide what content to add."

    return RubricFeedbackItem(
        criterion=criterion.name,
        status=status,
        evidence_from_draft=evidence,
        suggestion=suggestion,
        why_it_matters=why_it_matters,
    )


def _split_criterion(line: str, index: int) -> tuple[str, str]:
    if "|" in line:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        if len(cells) >= 2:
            return (
                _clean_criterion_name(cells[0])[:80] or f"Criterion {index}",
                " | ".join(cells[1:]) or line,
            )

    separators = [":", "-", "–", "—"]
    for separator in separators:
        if separator in line:
            name, description = line.split(separator, 1)
            return (
                _clean_criterion_name(name.strip())[:80] or f"Criterion {index}",
                description.strip() or line,
            )
    words = line.split()
    name = " ".join(words[: min(4, len(words))])
    return _clean_criterion_name(name) or f"Criterion {index}", line


def _rubric_lines(rubric_text: str) -> list[str]:
    raw_lines = [line.strip() for line in rubric_text.splitlines() if line.strip()]
    if len(raw_lines) <= 1:
        raw_lines = re.split(
            r"(?<=[.!?])\s+(?=[A-Z][A-Za-z0-9 ,&/\-()]{2,60}:)", rubric_text
        )

    lines = []
    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if not stripped or re.fullmatch(r"[\|\-\:\s]+", stripped):
            continue
        line = re.sub(r"^#+\s*", "", stripped).strip()
        if not re.fullmatch(r"\d+(?:\.\d+)?", line):
            line = re.sub(r"^(?:[\-\*]|\d+[\.\)])\s+", "", line).strip()
        lines.append(line.strip("|").strip())
    return lines


def _is_off_prompt_memo_submission(state: FeedbackState) -> bool:
    rubric_lower = state.request.rubric_text.lower()
    draft_lower = state.request.draft_text.lower()
    expects_memo = any(
        marker in rubric_lower
        for marker in (
            "consulting memo",
            "executive summary",
            "memo structure",
            "student role",
            "recommendation",
        )
    )
    reflection_style = any(
        marker in draft_lower
        for marker in (
            "reflection essay",
            "my thoughts",
            "in my opinion",
            "i personally",
            "technology and society",
        )
    )
    lacks_memo_sections = not any(
        marker in draft_lower
        for marker in (
            "executive summary",
            "problem diagnosis",
            "recommendation",
            "risks and metrics",
            "action plan",
        )
    )
    return expects_memo and reflection_style and lacks_memo_sections


def _is_rubric_stop_line(line: str) -> bool:
    lowered = line.lower()
    return lowered.startswith(
        (
            "instructor notes",
            "sample student",
            "student submission",
            "assignment context",
            "suggested memo structure",
        )
    )


def _looks_like_noncriterion_line(line: str) -> bool:
    lowered = line.lower().strip()
    if re.fullmatch(r"page\s+\d+", lowered):
        return True
    blocked_starts = (
        "assignment title",
        "assignment context",
        "assignment rubric",
        "student role",
        "student deliverable",
        "scenario",
        "fictional course",
        "suggested memo",
        "instructor notes",
        "intended quality",
        "estimated rubric band",
        "use case",
        "should detect",
        "page ",
    )
    return lowered.startswith(blocked_starts)


def _looks_like_rubric_candidate(line: str) -> bool:
    lowered = line.lower()
    if any(separator in line for separator in ("|", ":", " - ", " – ", " — ")):
        return True
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:%|pts?|points?)\b", line, re.IGNORECASE):
        return True
    criterion_terms = (
        "argument",
        "evidence",
        "organization",
        "clarity",
        "analysis",
        "reasoning",
        "rubric",
        "criteria",
        "actionability",
        "grammar",
        "structure",
        "support",
        "claim",
    )
    return any(term in lowered for term in criterion_terms)


def _looks_like_rubric_header(line: str) -> bool:
    lowered = line.lower()
    if "|" in line:
        cells = [cell.strip().lower() for cell in line.split("|") if cell.strip()]
        header_terms = {
            "criterion",
            "criteria",
            "points",
            "score",
            "excellent",
            "good",
            "fair",
            "poor",
        }
        if cells and cells[0] in {"criterion", "criteria", "category"}:
            return True
        return len(cells) >= 3 and sum(cell in header_terms for cell in cells) >= 2
    return lowered in {
        "criteria",
        "criterion",
        "rubric",
        "scoring",
        "score",
    } or lowered.startswith("criterion ")


def _clean_inline_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = cleaned.replace(" ,", ",").replace(" - ", "-")
    return cleaned.strip(" :|")


def _clean_criterion_name(name: str) -> str:
    cleaned = re.sub(
        r"\s*\(\s*\d+(?:\.\d+)?\s*(?:pts?|points?)\s*\)", "", name, flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"\s+\d+(?:\.\d+)?\s*(?:pts?|points?)\b", "", cleaned, flags=re.IGNORECASE
    )
    return _clean_inline_text(cleaned)


def _extract_performance_levels(line: str) -> list[str]:
    levels: list[str] = []
    if "|" in line:
        cells = [cell.strip() for cell in line.split("|") if cell.strip()]
        levels.extend(cell for cell in cells[1:] if len(cell.split()) >= 1)

    known_level_pattern = re.compile(
        r"\b(excellent|exceeds expectations|meets expectations|proficient|developing|"
        r"needs improvement|needs work|partial|poor|novice|advanced|acceptable)\b",
        re.IGNORECASE,
    )
    levels.extend(match.group(0) for match in known_level_pattern.finditer(line))

    point_bands = re.findall(
        r"\b\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?\s*(?:pts?|points?)\b",
        line,
        re.IGNORECASE,
    )
    levels.extend(point_bands)

    unique_levels: list[str] = []
    for level in levels:
        normalized = re.sub(r"\s+", " ", level).strip()
        if normalized and normalized.lower() not in {
            item.lower() for item in unique_levels
        }:
            unique_levels.append(normalized[:120])
    return unique_levels[:6]


def _build_metrics(
    state: FeedbackState, readiness: ReadinessLevel
) -> list[FeedbackMetric]:
    draft_words = len(_words(state.request.draft_text))
    criteria_count = len(state.criteria)
    evidence_count = sum(
        1
        for item in state.rubric_feedback
        if item.status != CriterionStatus.not_enough_evidence
    )
    depth_label = state.request.feedback_depth.value.capitalize()
    possible_points = sum(criterion.weight or 0 for criterion in state.criteria)
    estimated_points = sum(item.estimated_points or 0 for item in state.rubric_feedback)

    metrics = [
        FeedbackMetric(
            label="Readiness",
            value=readiness.value.capitalize(),
            detail="Formative estimate based on rubric coverage and revision needs.",
        ),
        FeedbackMetric(
            label="Draft length",
            value=f"{draft_words} words",
            detail="Used to calibrate how much evidence the workflow can inspect.",
        ),
        FeedbackMetric(
            label="Rubric criteria",
            value=str(criteria_count),
            detail="Parsed criteria used as anchors for feedback.",
        ),
    ]

    if possible_points:
        metrics.append(
            FeedbackMetric(
                label="Rubric coverage",
                value=f"{_format_points(estimated_points)}/{_format_points(possible_points)} pts",
                detail="Formative evidence estimate from rubric weights, not a grade.",
            )
        )

    metrics.extend(
        [
            FeedbackMetric(
                label="Grounded comments",
                value=f"{evidence_count}/{criteria_count}",
                detail="Rubric items with enough draft evidence to discuss confidently.",
            ),
            FeedbackMetric(
                label="Feedback depth",
                value=depth_label,
                detail="Controls how many revision moves and coaching prompts are returned.",
            ),
        ]
    )
    return metrics


def _format_points(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _build_section_feedback(state: FeedbackState) -> list[SectionFeedback]:
    focus_areas = {area.lower() for area in state.request.focus_areas}
    structure_issues = list(state.structure_findings.get("issues", []))
    reasoning_gaps = list(state.argument_findings.get("reasoning_gaps", []))
    unsupported_claims = list(state.argument_findings.get("unsupported_claims", []))

    sections = [
        SectionFeedback(
            area="Opening and purpose",
            finding=(
                structure_issues[0]
                if structure_issues
                else "The draft gives the reader an identifiable starting point."
            ),
            why_it_matters="A clear opening helps the learner control the reader's expectations before evidence appears.",
            revision_move="Rewrite the first 2-3 sentences so they name the recommendation, audience, and decision context.",
        ),
        SectionFeedback(
            area="Evidence and support",
            finding=(
                unsupported_claims[0]
                if unsupported_claims
                else "The draft includes some support for the recommendation."
            ),
            why_it_matters="Specific evidence is what turns a reasonable opinion into an argument a reviewer can assess.",
            revision_move="Add one concrete case fact, data point, or course concept after each major claim.",
        ),
        SectionFeedback(
            area="Reasoning and tradeoffs",
            finding=(
                reasoning_gaps[0]
                if reasoning_gaps
                else "The draft acknowledges complexity or risk."
            ),
            why_it_matters="Business writing is stronger when it shows why the recommendation still holds under constraints.",
            revision_move="Add a short tradeoff sentence that explains what could go wrong and how the plan manages it.",
        ),
    ]

    if "rubric alignment" in focus_areas or "rubric" in focus_areas:
        sections.insert(
            1,
            SectionFeedback(
                area="Rubric alignment",
                finding="Some rubric criteria are easier to see than others.",
                why_it_matters="Students revise better when criteria are visible in the draft, not only implied.",
                revision_move="Add a margin note or topic sentence that echoes the rubric language for each major section.",
            ),
        )

    return sections[:5]


def _build_inline_comments(state: FeedbackState) -> list[InlineComment]:
    draft = state.request.draft_text
    first = _sample_sentence(draft)
    sentences = [
        sentence
        for sentence in re.split(r"(?<=[.!?])\s+", draft.strip())
        if sentence.strip()
    ]
    last = sentences[-1] if sentences else first

    comments = [
        InlineComment(
            target_text=first,
            comment="This is a good place to sharpen the central claim.",
            revision_prompt="Can the reader identify the recommendation and the reason for it in one pass?",
        ),
        InlineComment(
            target_text=last[:220],
            comment="The ending can do more synthesis work.",
            revision_prompt="What should the reader believe or do differently after reading this draft?",
        ),
    ]

    if state.request.feedback_depth == FeedbackDepth.deep and len(sentences) > 2:
        middle = sentences[len(sentences) // 2]
        comments.insert(
            1,
            InlineComment(
                target_text=middle[:220],
                comment="This section may need a clearer evidence-to-claim bridge.",
                revision_prompt="What evidence supports this point, and how does it connect to the rubric?",
            ),
        )

    return comments


def _build_coaching_questions(state: FeedbackState) -> list[str]:
    questions = [
        "What is the single most important decision or recommendation the reader should remember?",
        "Which claim would a skeptical instructor ask you to support with stronger evidence?",
        "Where does the draft directly use the rubric language, and where is the connection only implied?",
        "What tradeoff or risk would make your recommendation more credible if acknowledged?",
    ]

    if state.request.learning_goal:
        questions.insert(
            0,
            f"How does this draft show progress toward your stated goal: {state.request.learning_goal}?",
        )

    if state.request.feedback_depth == FeedbackDepth.quick:
        return questions[:3]
    return questions[:5]


def _build_revision_plan(
    state: FeedbackState, priorities: list[str]
) -> list[RevisionPlanItem]:
    plan = [
        RevisionPlanItem(
            priority="Clarify the main claim",
            action="Revise the opening so the recommendation and decision context are explicit.",
            expected_impact="Readers understand the purpose before evaluating details.",
            time_estimate="10 minutes",
        ),
        RevisionPlanItem(
            priority="Add evidence",
            action="Attach one case fact, course concept, or data point to each major claim.",
            expected_impact="Feedback becomes more grounded and rubric alignment improves.",
            time_estimate="20 minutes",
        ),
        RevisionPlanItem(
            priority="Map to rubric",
            action="Compare each paragraph against the rubric and add missing criteria coverage.",
            expected_impact="The draft is easier for a student and instructor to evaluate.",
            time_estimate="15 minutes",
        ),
    ]

    if priorities:
        plan[0].priority = priorities[0]

    if state.request.feedback_depth == FeedbackDepth.deep:
        plan.append(
            RevisionPlanItem(
                priority="Strengthen reasoning",
                action="Add one sentence explaining why the evidence supports the recommendation.",
                expected_impact="The draft moves from listing facts to making an argument.",
                time_estimate="15 minutes",
            )
        )

    return plan


_STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "assignment",
    "because",
    "before",
    "being",
    "between",
    "business",
    "could",
    "criteria",
    "criterion",
    "draft",
    "essay",
    "feedback",
    "from",
    "have",
    "into",
    "more",
    "must",
    "only",
    "other",
    "paper",
    "prompt",
    "provide",
    "provides",
    "rubric",
    "should",
    "student",
    "submission",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "used",
    "uses",
    "using",
    "when",
    "where",
    "which",
    "with",
    "within",
    "work",
    "writing",
}


def _build_topic_map(state: FeedbackState) -> TopicMap:
    """Create an explainable, non-AI topic allocation view.

    Each rubric criterion becomes an ideal topic cluster. The draft is mapped
    into those clusters by normalized keyword overlap plus the formative rubric
    status, so the visual remains stable even when the LLM path is enabled.
    """

    feedback_by_criterion = {
        item.criterion.lower(): item for item in state.rubric_feedback
    }
    draft_tokens = set(_topic_terms(state.request.draft_text, limit=120))
    clusters: list[TopicCluster] = []

    for criterion in state.criteria[:8]:
        rubric_terms = _topic_terms(
            f"{criterion.name} {criterion.description}", limit=8
        )
        if not rubric_terms:
            rubric_terms = _topic_terms(criterion.name, limit=4) or [
                criterion.name.lower()
            ]

        feedback_item = feedback_by_criterion.get(criterion.name.lower())
        if not feedback_item:
            feedback_item = _closest_feedback_item(
                criterion.name, state.rubric_feedback
            )

        matched_terms = [
            term
            for term in rubric_terms
            if _topic_term_present(term, draft_tokens, state.request.draft_text)
        ]
        missing_terms = [term for term in rubric_terms if term not in matched_terms]
        lexical_coverage = len(matched_terms) / max(1, len(rubric_terms))
        status_coverage = _coverage_from_status(
            feedback_item.status if feedback_item else None
        )
        coverage = round(
            min(1.0, max(0.0, (lexical_coverage * 0.6) + (status_coverage * 0.4))), 2
        )

        evidence_keywords = tuple(matched_terms or rubric_terms)
        evidence = (
            feedback_item.evidence_from_draft
            if feedback_item and feedback_item.evidence_from_draft
            else _best_sentence(state.request.draft_text, evidence_keywords)
        )
        clusters.append(
            TopicCluster(
                label=criterion.name,
                draft_coverage=coverage,
                rubric_weight=criterion.weight,
                rubric_terms=rubric_terms,
                draft_terms=(matched_terms or _topic_terms(evidence, limit=5))[:8],
                missing_terms=missing_terms[:8],
                evidence_from_draft=evidence,
                interpretation=_topic_interpretation(coverage),
                example_revision=_topic_example_revision(criterion.name, missing_terms),
            )
        )

    return TopicMap(
        method="Rubric cluster model",
        summary=(
            "Rubric criteria are projected as target clusters, then the draft is mapped against those "
            "clusters so students can see coverage gaps quickly."
        ),
        clusters=clusters,
    )


def _closest_feedback_item(
    criterion_name: str, items: list[RubricFeedbackItem]
) -> RubricFeedbackItem | None:
    criterion_terms = set(_topic_terms(criterion_name, limit=8))
    best_item: RubricFeedbackItem | None = None
    best_overlap = 0
    for item in items:
        overlap = len(
            criterion_terms.intersection(_topic_terms(item.criterion, limit=8))
        )
        if overlap > best_overlap:
            best_item = item
            best_overlap = overlap
    return best_item


def _coverage_from_status(status: CriterionStatus | None) -> float:
    ratios = {
        CriterionStatus.meets: 0.92,
        CriterionStatus.partially_meets: 0.64,
        CriterionStatus.needs_work: 0.3,
        CriterionStatus.not_enough_evidence: 0.05,
    }
    return ratios.get(status, 0.35)


def _topic_terms(text: str, limit: int = 8) -> list[str]:
    counts: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text.lower()):
        normalized = _normalize_topic_token(token)
        if len(normalized) < 4 or normalized in _STOPWORDS:
            continue
        counts[normalized] = counts.get(normalized, 0) + 1
    return [
        term
        for term, _count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )[:limit]
    ]


def _normalize_topic_token(token: str) -> str:
    token = token.strip("-").replace("-", " ")
    token = re.sub(r"[^a-z ]", "", token)
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif (
        token.endswith("s")
        and len(token) > 5
        and not token.endswith(("ss", "sis", "us"))
    ):
        token = token[:-1]
    return token.strip()


def _topic_term_present(term: str, draft_tokens: set[str], draft_text: str) -> bool:
    if term in draft_tokens:
        return True
    term_parts = [part for part in term.split() if part]
    if len(term_parts) > 1 and all(part in draft_tokens for part in term_parts):
        return True
    return term in draft_text.lower()


def _topic_interpretation(coverage: float) -> str:
    if coverage >= 0.72:
        return "Strong overlap with the rubric cluster."
    if coverage >= 0.42:
        return "Partial overlap; the topic is visible but needs clearer evidence."
    return "Visible gap; this rubric topic is not yet supported enough in the draft."


def _topic_example_revision(criterion_name: str, missing_terms: list[str]) -> str:
    if missing_terms:
        terms = ", ".join(missing_terms[:2])
        return (
            f"Example move: add one sentence that names {terms} and connects it to a concrete detail "
            f"for {criterion_name}."
        )
    return (
        f"Example move: keep {criterion_name} visible by naming the criterion in a topic sentence "
        "and pairing it with a concrete draft detail."
    )


def _extract_weight(line: str) -> float | None:
    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
    if percent_match:
        return float(percent_match.group(1))

    points_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:pts?|points?)\b", line, re.IGNORECASE
    )
    if points_match:
        return float(points_match.group(1))

    return None


def _sample_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        if 40 <= len(sentence) <= 240:
            return sentence
    return text.strip()[:220]


def _best_sentence(text: str, keywords: tuple[str, ...]) -> str:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text.strip())
        if sentence.strip()
    ]
    if not sentences:
        return text.strip()[:220]

    best = max(
        sentences,
        key=lambda sentence: (
            sum(
                1
                for keyword in keywords
                if keyword and keyword.lower() in sentence.lower()
            ),
            40 <= len(sentence) <= 260,
            -abs(len(sentence) - 140),
        ),
    )
    return best[:260]


def _words(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text)
