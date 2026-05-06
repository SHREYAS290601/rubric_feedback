from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.agent_workflow import generate_feedback
from app.models import FeedbackDepth, FeedbackRequest, FeedbackResponse, RatingRequest, UsageEvent
from app.services.ai_provider import AIConfigurationError
from app.services.auth import AuthenticatedUser, require_user
from app.services.document_parser import extract_text
from app.services.guardrails import GuardrailViolation
from app.services.observability import log_security_event
from app.services.storage import get_session_exists, save_event, save_feedback, save_rating


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/generate", response_model=FeedbackResponse)
def create_feedback(request: FeedbackRequest, user: AuthenticatedUser = Depends(require_user)) -> FeedbackResponse:
    return _create_feedback_response(request, user)


def _create_feedback_response(request: FeedbackRequest, user: AuthenticatedUser) -> FeedbackResponse:
    save_event(
        UsageEvent(
            event_name="feedback_generation_started",
            properties={"user_id": user.user_id, "auth_mode": user.auth_mode},
        )
    )
    try:
        response = generate_feedback(request)
    except GuardrailViolation as exc:
        save_event(
            UsageEvent(
                event_name="feedback_guardrail_blocked",
                properties={"user_id": user.user_id, "reason": str(exc)},
            )
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AIConfigurationError as exc:
        save_event(UsageEvent(event_name="feedback_ai_configuration_missing", properties={"error": str(exc)}))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log_security_event(
            "feedback_generation_failed",
            error_type=exc.__class__.__name__,
            user_id=user.user_id,
            auth_mode=user.auth_mode,
        )
        save_event(UsageEvent(event_name="feedback_generation_failed", properties={"error": str(exc)}))
        raise HTTPException(status_code=500, detail="Could not generate reliable feedback.") from exc

    save_feedback(response)
    save_event(
        UsageEvent(
            session_id=response.session_id,
            event_name="feedback_generation_completed",
            properties={"readiness_level": response.readiness_level.value, "user_id": user.user_id},
        )
    )
    return response


@router.post("/generate-file", response_model=FeedbackResponse)
async def create_feedback_from_file(
    draft_text: Optional[str] = Form(default=None),
    rubric_text: Optional[str] = Form(default=None),
    assignment_title: Optional[str] = Form(default=None),
    course_context: Optional[str] = Form(default=None),
    learning_goal: Optional[str] = Form(default=None),
    feedback_depth: FeedbackDepth = Form(default=FeedbackDepth.standard),
    focus_areas: str = Form(default=""),
    draft_file: Optional[UploadFile] = File(default=None),
    rubric_file: Optional[UploadFile] = File(default=None),
    user: AuthenticatedUser = Depends(require_user),
) -> FeedbackResponse:
    final_draft_text = await _text_from_upload_or_form(
        upload=draft_file,
        fallback_text=draft_text,
        label="draft",
        minimum_length=80,
    )
    final_rubric_text = await _text_from_upload_or_form(
        upload=rubric_file,
        fallback_text=rubric_text,
        label="rubric",
        minimum_length=20,
    )

    request = FeedbackRequest(
        assignment_title=assignment_title,
        course_context=course_context,
        learning_goal=learning_goal,
        feedback_depth=feedback_depth,
        focus_areas=[area.strip() for area in focus_areas.split(",") if area.strip()],
        draft_text=final_draft_text,
        rubric_text=final_rubric_text,
    )
    log_security_event(
        "feedback_file_inputs_prepared",
        draft_file_name=draft_file.filename if draft_file else None,
        rubric_file_name=rubric_file.filename if rubric_file else None,
        draft_text_chars=len(final_draft_text),
        rubric_text_chars=len(final_rubric_text),
    )
    return _create_feedback_response(request, user)


async def _text_from_upload_or_form(
    *,
    upload: Optional[UploadFile],
    fallback_text: Optional[str],
    label: str,
    minimum_length: int,
) -> str:
    if upload and upload.filename:
        suffix = Path(upload.filename).suffix
        try:
            with NamedTemporaryFile(suffix=suffix, delete=True) as temp_file:
                temp_file.write(await upload.read())
                temp_file.flush()
                extracted_text = extract_text(Path(temp_file.name))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Could not read the {label} file: {exc}") from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not extract text from the {label} file.") from exc

        if len(extracted_text.strip()) < minimum_length:
            raise HTTPException(status_code=400, detail=f"The {label} file did not contain enough readable text.")
        return extracted_text

    if fallback_text and len(fallback_text.strip()) >= minimum_length:
        return fallback_text.strip()

    raise HTTPException(status_code=400, detail=f"Please provide a {label} as pasted text or an uploaded file.")


@router.post("/rating")
def rate_feedback(request: RatingRequest, user: AuthenticatedUser = Depends(require_user)) -> dict[str, str]:
    if not get_session_exists(request.session_id):
        raise HTTPException(status_code=404, detail="Feedback session was not found.")

    save_rating(request)
    save_event(
        UsageEvent(
            session_id=request.session_id,
            event_name="rating_submitted",
            properties={"usefulness_rating": request.usefulness_rating, "user_id": user.user_id},
        )
    )
    return {"status": "saved"}
