from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


DISCLAIMER = (
    "This tool provides formative feedback to help you revise. "
    "It does not assign a grade and does not replace instructor feedback."
)


class ReadinessLevel(str, Enum):
    early = "early"
    developing = "developing"
    strong = "strong"


class CriterionStatus(str, Enum):
    meets = "meets"
    partially_meets = "partially_meets"
    needs_work = "needs_work"
    not_enough_evidence = "not_enough_evidence"


class FeedbackDepth(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"


class FeedbackRequest(BaseModel):
    assignment_title: Optional[str] = Field(default=None, max_length=140)
    course_context: Optional[str] = Field(default=None, max_length=140)
    learning_goal: Optional[str] = Field(default=None, max_length=500)
    feedback_depth: FeedbackDepth = FeedbackDepth.standard
    focus_areas: list[str] = Field(default_factory=list, max_length=6)
    draft_text: str = Field(min_length=80, max_length=30000)
    rubric_text: str = Field(min_length=20, max_length=12000)


class RubricCriterion(BaseModel):
    name: str
    description: str
    weight: Optional[float] = None
    performance_levels: list[str] = Field(default_factory=list)


class RubricFeedbackItem(BaseModel):
    criterion: str
    status: CriterionStatus
    evidence_from_draft: str
    suggestion: str
    why_it_matters: str
    points_possible: Optional[float] = None
    estimated_points: Optional[float] = None
    score_rationale: Optional[str] = None


class FeedbackMetric(BaseModel):
    label: str
    value: str
    detail: str


class SectionFeedback(BaseModel):
    area: str
    finding: str
    why_it_matters: str
    revision_move: str


class RevisionPlanItem(BaseModel):
    priority: str
    action: str
    expected_impact: str
    time_estimate: str


class InlineComment(BaseModel):
    target_text: str
    comment: str
    revision_prompt: str


class TopicCluster(BaseModel):
    label: str
    draft_coverage: float = Field(ge=0, le=1)
    rubric_weight: Optional[float] = None
    rubric_terms: list[str] = Field(default_factory=list, max_length=8)
    draft_terms: list[str] = Field(default_factory=list, max_length=8)
    missing_terms: list[str] = Field(default_factory=list, max_length=8)
    evidence_from_draft: str
    interpretation: str
    example_revision: str


class TopicMap(BaseModel):
    method: str
    summary: str
    clusters: list[TopicCluster] = Field(default_factory=list, max_length=8)


class FeedbackResponse(BaseModel):
    session_id: UUID = Field(default_factory=uuid4)
    overall_summary: str
    readiness_level: ReadinessLevel
    metrics: list[FeedbackMetric] = Field(default_factory=list, max_length=6)
    strengths: list[str] = Field(min_length=1, max_length=5)
    top_priorities: list[str] = Field(min_length=1, max_length=5)
    section_feedback: list[SectionFeedback] = Field(default_factory=list, max_length=8)
    rubric_feedback: list[RubricFeedbackItem]
    inline_comments: list[InlineComment] = Field(default_factory=list, max_length=6)
    coaching_questions: list[str] = Field(default_factory=list, max_length=6)
    revision_plan: list[RevisionPlanItem] = Field(default_factory=list, max_length=6)
    topic_map: Optional[TopicMap] = None
    revision_checklist: list[str] = Field(min_length=1, max_length=8)
    disclaimer: str = DISCLAIMER


class UsageEvent(BaseModel):
    session_id: Optional[UUID] = None
    event_name: str = Field(min_length=2, max_length=80)
    properties: dict[str, Any] = Field(default_factory=dict)


class RatingRequest(BaseModel):
    session_id: UUID
    usefulness_rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=1000)


class StoredRating(RatingRequest):
    rating_id: UUID = Field(default_factory=uuid4)
