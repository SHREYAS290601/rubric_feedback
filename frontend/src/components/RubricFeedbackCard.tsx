import { RubricFeedbackItem } from "../types";

interface RubricFeedbackCardProps {
  item: RubricFeedbackItem;
}

const statusLabels: Record<RubricFeedbackItem["status"], string> = {
  meets: "Meets",
  partially_meets: "Partially meets",
  needs_work: "Needs work",
  not_enough_evidence: "Not enough evidence"
};

function RubricFeedbackCard({ item }: RubricFeedbackCardProps) {
  const pointsPossible = typeof item.points_possible === "number" ? item.points_possible : null;
  const estimatedPoints = typeof item.estimated_points === "number" ? item.estimated_points : null;
  const hasScore = pointsPossible !== null && estimatedPoints !== null;
  const scorePercent = hasScore && pointsPossible
    ? Math.min(100, Math.max(0, (estimatedPoints / pointsPossible) * 100))
    : 0;

  return (
    <article className="rubric-card">
      <div className="card-topline">
        <h4>{item.criterion}</h4>
        <div className="card-pill-stack">
          <span className={`status-pill status-${item.status}`}>{statusLabels[item.status]}</span>
          {hasScore ? (
            <span className="score-pill">
              {formatPoints(estimatedPoints)} / {formatPoints(pointsPossible)} pts
            </span>
          ) : null}
        </div>
      </div>
      {hasScore ? (
        <div className="rubric-score" aria-label={`Formative coverage ${formatPoints(estimatedPoints)} out of ${formatPoints(pointsPossible)} points`}>
          <div className="score-meter">
            <span style={{ width: `${scorePercent}%` }} />
          </div>
          <small>{item.score_rationale ?? "Formative evidence coverage estimate, not a final grade."}</small>
        </div>
      ) : null}
      <div className="evidence-block">
        <span>Evidence</span>
        <p>{item.evidence_from_draft}</p>
      </div>
      <div className="suggestion-block">
        <span>Next revision</span>
        <p>{item.suggestion}</p>
      </div>
      <div className="suggestion-block">
        <span>Why it matters</span>
        <p>{item.why_it_matters}</p>
      </div>
    </article>
  );
}

function formatPoints(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export default RubricFeedbackCard;
