export type ReadinessLevel = "early" | "developing" | "strong";
export type FeedbackDepth = "quick" | "standard" | "deep";

export type CriterionStatus =
  | "meets"
  | "partially_meets"
  | "needs_work"
  | "not_enough_evidence";

export interface FeedbackRequest {
  assignment_title?: string;
  course_context?: string;
  learning_goal?: string;
  feedback_depth: FeedbackDepth;
  focus_areas: string[];
  draft_text: string;
  rubric_text: string;
}

export interface RubricFeedbackItem {
  criterion: string;
  status: CriterionStatus;
  evidence_from_draft: string;
  suggestion: string;
  why_it_matters: string;
  points_possible?: number | null;
  estimated_points?: number | null;
  score_rationale?: string | null;
}

export interface FeedbackMetric {
  label: string;
  value: string;
  detail: string;
}

export interface SectionFeedback {
  area: string;
  finding: string;
  why_it_matters: string;
  revision_move: string;
}

export interface InlineComment {
  target_text: string;
  comment: string;
  revision_prompt: string;
}

export interface RevisionPlanItem {
  priority: string;
  action: string;
  expected_impact: string;
  time_estimate: string;
}

export interface TopicCluster {
  label: string;
  draft_coverage: number;
  rubric_weight?: number | null;
  rubric_terms: string[];
  draft_terms: string[];
  missing_terms: string[];
  evidence_from_draft: string;
  interpretation: string;
  example_revision: string;
}

export interface TopicMap {
  method: string;
  summary: string;
  clusters: TopicCluster[];
}

export interface FeedbackResponse {
  session_id: string;
  overall_summary: string;
  readiness_level: ReadinessLevel;
  metrics: FeedbackMetric[];
  strengths: string[];
  top_priorities: string[];
  section_feedback: SectionFeedback[];
  rubric_feedback: RubricFeedbackItem[];
  inline_comments: InlineComment[];
  coaching_questions: string[];
  revision_plan: RevisionPlanItem[];
  topic_map?: TopicMap | null;
  revision_checklist: string[];
  disclaimer: string;
}
