import { type CSSProperties, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDownload } from '@fortawesome/free-solid-svg-icons'
import { FeedbackResponse, TopicCluster } from "../types";
import RubricFeedbackCard from "./RubricFeedbackCard";

interface FeedbackResultsProps {
  feedback: FeedbackResponse;
}

type FeedbackSection = "overview" | "map" | "rubric" | "coach" | "plan";

const feedbackSections: Array<{
  key: FeedbackSection;
  label: string;
  description: string;
}> = [
  {
    key: "overview",
    label: "Overview",
    description: "Summary and priorities"
  },
  {
    key: "map",
    label: "Map",
    description: "Draft clusters vs rubric clusters"
  },
  {
    key: "rubric",
    label: "Rubric",
    description: "Criteria alignment"
  },
  {
    key: "coach",
    label: "Coach",
    description: "Draft notes"
  },
  {
    key: "plan",
    label: "Plan",
    description: "Revision steps"
  }
];

function FeedbackResults({ feedback }: FeedbackResultsProps) {
  const [activeTab, setActiveTab] = useState<FeedbackSection>("overview");
  const [checkedItems, setCheckedItems] = useState<string[]>([]);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const [exportState, setExportState] = useState<"idle" | "saved">("idle");
  const [selectedClusterLabel, setSelectedClusterLabel] = useState<string | null>(null);
  const activeSection =
    feedbackSections.find((section) => section.key === activeTab) ?? feedbackSections[0];

  function toggleChecklist(item: string) {
    setCheckedItems((current) =>
      current.includes(item) ? current.filter((entry) => entry !== item) : [...current, item]
    );
  }

  async function copyPlan() {
    const plan = feedback.revision_plan
      .map((item, index) => {
        const level = getPriorityLevel(item.priority);
        const heading = level ? item.action : item.priority;
        const action = level ? item.expected_impact : item.action;
        return [
          `Step ${index + 1} - ${getPriorityLabel(item.priority)}`,
          heading,
          action,
          `Time: ${item.time_estimate}`
        ].join("\n");
      })
      .join("\n\n");
    const copied = await writeClipboardText(plan);
    setCopyState(copied ? "copied" : "error");
    window.setTimeout(() => setCopyState("idle"), 1600);
  }

  function exportFeedback(format: "json" | "markdown") {
    const timestamp = new Date().toISOString();
    const baseName = `revision-feedback-${feedback.session_id.slice(0, 8)}`;
    if (format === "json") {
      downloadTextFile(
        `${baseName}.json`,
        JSON.stringify(
          {
            exported_at: timestamp,
            export_format: "rubric-feedback-response-v1",
            feedback
          },
          null,
          2
        ),
        "application/json"
      );
    } else {
      downloadTextFile(
        `${baseName}.md`,
        feedbackToMarkdown(feedback, timestamp),
        "text/markdown"
      );
    }
    setExportState("saved");
    window.setTimeout(() => setExportState("idle"), 1600);
  }

  function renderSection(section: FeedbackSection) {
    if (section === "overview") {
      return (
        <div className="tab-panel">
          <section className="summary-panel">
            <span>Overall summary</span>
            <p>{feedback.overall_summary}</p>
          </section>
          <div className="insight-grid">
            <section className="insight-panel">
              <h3>Strengths</h3>
              <ul>
                {feedback.strengths.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>

            <section className="insight-panel priority-panel">
              <h3>Top priorities</h3>
              <ol>
                {feedback.top_priorities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </section>
          </div>

          <section className="section-feedback-grid">
            {feedback.section_feedback.map((item) => (
              <article className="section-feedback-card" key={item.area}>
                <h3>{item.area}</h3>
                <p>{item.finding}</p>
                <dl>
                  <div>
                    <dt>Why it matters</dt>
                    <dd>{item.why_it_matters}</dd>
                  </div>
                  <div>
                    <dt>Revision move</dt>
                    <dd>{item.revision_move}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </section>
        </div>
      );
    }

    if (section === "rubric") {
      return (
        <div className="tab-panel rubric-section">
          <div className="section-title-row">
            <h3>Rubric alignment</h3>
          </div>
          <div className="rubric-grid">
            {feedback.rubric_feedback.map((item) => (
              <RubricFeedbackCard item={item} key={item.criterion} />
            ))}
          </div>
        </div>
      );
    }

    if (section === "map") {
      const clusters = feedback.topic_map?.clusters ?? [];
      const selectedCluster =
        clusters.find((cluster) => cluster.label === selectedClusterLabel) ?? clusters[0];

      return (
        <div className="tab-panel topic-map-panel">
          <div className="section-title-row">
            <div>
              <h3>Live cluster graph</h3>
              <p className="panel-intro">
                AI feedback anchors the rubric targets, and this map shows how the student draft clusters around them.
              </p>
            </div>
            <span className="method-pill">Cluster map</span>
          </div>
          {clusters.length && selectedCluster ? (
            <div className="cluster-workspace">
              <TopicClusterGraph
                clusters={clusters}
                selectedLabel={selectedCluster.label}
                onSelect={setSelectedClusterLabel}
              />
              <TopicClusterLens cluster={selectedCluster} />
            </div>
          ) : (
            <section className="empty-panel">
              <h3>Topic map unavailable</h3>
              <p>Generate feedback again to build the non-AI topic coverage graph.</p>
            </section>
          )}
        </div>
      );
    }

    if (section === "coach") {
      return (
        <div className="tab-panel coach-grid">
          <section className="inline-comment-panel">
            <h3>Inline draft notes</h3>
            {feedback.inline_comments.map((item) => (
              <article className="inline-comment" key={`${item.target_text}-${item.comment}`}>
                <blockquote>{item.target_text}</blockquote>
                <p>{item.comment}</p>
                <strong>{item.revision_prompt}</strong>
              </article>
            ))}
          </section>

          <section className="coaching-panel">
            <h3>Revision questions</h3>
            <ol>
              {feedback.coaching_questions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ol>
            <label>
              <span>Revision notes</span>
              <textarea
                value={revisionNotes}
                onChange={(event) => setRevisionNotes(event.target.value)}
                rows={6}
                placeholder="Capture what you want to change in the next draft."
              />
            </label>
          </section>
        </div>
      );
    }

    return (
      <div className="tab-panel">
        <div className="section-title-row">
          <div>
            <h3>Revision plan</h3>
            <p className="panel-intro">
              Ordered next steps for the next draft, not a grade.
            </p>
          </div>
          <button type="button" className="secondary-button" onClick={copyPlan}>
            {copyState === "copied" ? "Copied to clipboard" : copyState === "error" ? "Copy failed" : "Copy plan"}
          </button>
        </div>
        <div className="plan-grid">
          {feedback.revision_plan.map((item, index) => (
            <article className="plan-card" key={`${item.priority}-${item.action}`}>
              <div className="plan-card-topline">
                <span>Step {index + 1}</span>
                <span>{item.time_estimate}</span>
              </div>
              <span className={`priority-tag priority-${getPriorityLevel(item.priority) ?? "focus"}`}>
                {getPriorityLabel(item.priority)}
              </span>
              <h4>{getPriorityLevel(item.priority) ? item.action : item.priority}</h4>
              <p>{getPriorityLevel(item.priority) ? item.expected_impact : item.action}</p>
              {getPriorityLevel(item.priority) ? null : <small>{item.expected_impact}</small>}
            </article>
          ))}
        </div>
      </div>
    );
  }

  return (
    <section className="results-shell">
      <div className="results-header">
        <div>
          <p className="eyebrow">Formative feedback</p>
          <h2>Revision snapshot</h2>
        </div>
        <div className="results-actions">
          <span className={`readiness-badge readiness-${feedback.readiness_level}`}>
            {feedback.readiness_level}
          </span>
          <button type="button" className="secondary-button export-button" onClick={() => exportFeedback("json")}>
            <FontAwesomeIcon icon={faDownload} /> JSON
          </button>
          <button type="button" className="secondary-button export-button" onClick={() => exportFeedback("markdown")}>
            <FontAwesomeIcon icon={faDownload} /> Markdown
          </button>
          {exportState === "saved" ? <small aria-live="polite">Saved</small> : null}
        </div>
      </div>

      <div className="metrics-row">
        {feedback.metrics.map((metric) => (
          <article className="metric-tile" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{formatDisplayValue(metric.value)}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </div>

      <div className="feedback-layout">
        <div className="result-tabs" role="tablist" aria-label="Feedback sections">
          {feedbackSections.map((section) => (
            <button
              type="button"
              className={activeTab === section.key ? "tab-button active" : "tab-button"}
              key={section.key}
              onClick={() => setActiveTab(section.key)}
              role="tab"
              aria-selected={activeTab === section.key}
            >
              {section.label}
            </button>
          ))}
        </div>
        <p className="active-tab-description">
          <strong>{activeSection.label}:</strong> {activeSection.description}
        </p>
        <div className="feedback-content">{renderSection(activeTab)}</div>
      </div>

      <section className="checklist-panel">
        <div className="section-title-row">
          <h3>Revision checklist</h3>
          <span>{checkedItems.length}/{feedback.revision_checklist.length} complete</span>
        </div>
        <ul>
          {feedback.revision_checklist.map((item) => (
            <li key={item} className={checkedItems.includes(item) ? "checked" : ""}>
              <button type="button" onClick={() => toggleChecklist(item)} aria-label={`Toggle ${item}`}>
                {checkedItems.includes(item) ? "✓" : ""}
              </button>
              {item}
            </li>
          ))}
        </ul>
      </section>

      <p className="disclaimer">{feedback.disclaimer}</p>
    </section>
  );
}

function TopicClusterGraph({
  clusters,
  selectedLabel,
  onSelect
}: {
  clusters: TopicCluster[];
  selectedLabel: string;
  onSelect: (label: string) => void;
}) {
  const center = { x: 50, y: 50 };
  const maxWeight = Math.max(...clusters.map((cluster) => cluster.rubric_weight ?? 0), 1);
  const positioned = clusters.map((cluster, index) => {
    const point = clusterPoint(index, clusters.length);
    const linkStart = linkEndPoint(point, center, 7.8);
    const linkEnd = linkEndPoint(center, point, 10.4);
    const weightScale = cluster.rubric_weight ? cluster.rubric_weight / maxWeight : 0.55;
    return {
      cluster,
      point,
      linkStart,
      linkEnd,
      size: 86 + cluster.draft_coverage * 20 + weightScale * 6
    };
  });

  return (
    <section className="graph-panel" aria-label="Interactive topic cluster graph">
      <div className="graph-stage" role="img" aria-label="Student draft surrounded by rubric topic clusters">
        <div className="graph-grid" aria-hidden="true" />
        <svg className="graph-links" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {positioned.map(({ cluster, linkStart, linkEnd }) => (
            <line
              className={cluster.label === selectedLabel ? "selected" : ""}
              x1={linkStart.x}
              y1={linkStart.y}
              x2={linkEnd.x}
              y2={linkEnd.y}
              style={{ strokeWidth: 2 + cluster.draft_coverage * 2.8 }}
              key={`edge-${cluster.label}`}
            />
          ))}
        </svg>
        <div className="graph-core" style={{ left: `${center.x}%`, top: `${center.y}%` }}>
          <strong>Student draft</strong>
          <span>{clusters.length} rubric clusters</span>
        </div>
        {positioned.map(({ cluster, point, size }, index) => {
          const selected = cluster.label === selectedLabel;
          const percent = Math.round(cluster.draft_coverage * 100);
          const visibleTerms = [
            ...cluster.draft_terms.slice(0, 4).map((term) => ({ term, type: "draft" })),
            ...cluster.missing_terms.slice(0, 3).map((term) => ({ term, type: "missing" }))
          ];

          return (
            <button
              type="button"
              className={selected ? "cluster-orb selected" : "cluster-orb"}
              style={{
                left: `${point.x}%`,
                top: `${point.y}%`,
                width: `${size}px`,
                height: `${size}px`,
                background: `conic-gradient(var(--green) ${percent}%, #eef3f1 0)`,
                animationDelay: `${index * 110}ms`
              }}
              onClick={() => onSelect(cluster.label)}
              onMouseEnter={() => onSelect(cluster.label)}
              key={cluster.label}
            >
              <span className="cluster-orb-inner">
                <em>{percent}%</em>
                <strong>{cluster.label}</strong>
              </span>
              <span className="cluster-dot-ring" aria-hidden="true">
                {visibleTerms.map(({ term, type }, termIndex) => (
                  <i
                    className={`cluster-mini-node ${type}`}
                    title={term}
                    style={miniNodeStyle(termIndex, visibleTerms.length)}
                    key={`${cluster.label}-${type}-${term}`}
                  />
                ))}
              </span>
            </button>
          );
        })}
      </div>
      <div className="graph-legend" aria-hidden="true">
        <span><em className="legend-dot draft" /> present in draft</span>
        <span><em className="legend-dot missing" /> missing from draft</span>
        <span><em className="legend-line" /> stronger link = better coverage</span>
      </div>
    </section>
  );
}

function TopicClusterLens({ cluster }: { cluster: TopicCluster }) {
  const percent = Math.round(cluster.draft_coverage * 100);
  const gap = Math.max(0, 100 - percent);
  const visibleRubricTerms = cluster.rubric_terms.filter(Boolean).slice(0, 7);
  const visibleDraftTerms = cluster.draft_terms.filter(Boolean).slice(0, 7);
  const visibleMissingTerms = cluster.missing_terms.filter(Boolean).slice(0, 7);

  return (
    <article className="cluster-lens" aria-live="polite">
      <div className="lens-header">
        <div>
          <span>Visual drill-down</span>
          <h4>{cluster.label}</h4>
        </div>
        <strong>{percent}%</strong>
      </div>

      <div className="lens-visual">
        <div
          className="coverage-donut"
          style={{ background: `conic-gradient(var(--green) ${percent}%, #f4dfd2 0)` }}
          aria-label={`${percent}% covered and ${gap}% gap`}
        >
          <span>{percent}%</span>
          <em>covered</em>
        </div>
        <div className="coverage-breakdown">
          <span>Cluster match</span>
          <div className="coverage-stack" aria-hidden="true">
            <i className="matched" style={{ width: `${percent}%` }} />
            <i className="gap" style={{ width: `${gap}%` }} />
          </div>
          <div className="coverage-key">
            <small><em className="legend-dot draft" /> draft overlap</small>
            <small><em className="legend-dot missing" /> gap to rubric</small>
          </div>
        </div>
      </div>

      <div className="language-flow" aria-label="Rubric to draft gap flow">
        <div className="flow-column">
          <span>Rubric target</span>
          <div>
            {visibleRubricTerms.map((term) => (
              <em className="term-chip" key={`rubric-${term}`}>{term}</em>
            ))}
          </div>
        </div>
        <strong className="flow-arrow" aria-hidden="true">→</strong>
        <div className="flow-column matched">
          <span>Visible in draft</span>
          <div>
            {visibleDraftTerms.length ? (
              visibleDraftTerms.map((term) => (
                <em className="term-chip" key={`draft-${term}`}>{term}</em>
              ))
            ) : (
              <small>No strong overlap yet</small>
            )}
          </div>
        </div>
        <strong className="flow-arrow" aria-hidden="true">→</strong>
        <div className="flow-column gap">
          <span>Gap to close</span>
          <div>
            {visibleMissingTerms.length ? (
              visibleMissingTerms.map((term) => (
                <em className="term-chip missing" key={`missing-${term}`}>{term}</em>
              ))
            ) : (
              <small>No major missing language</small>
            )}
          </div>
        </div>
      </div>

      <div className="lens-move">
        <span>Next visual cue</span>
        <p>{cluster.example_revision.replace(/^Example move:\s*/i, "")}</p>
      </div>
    </article>
  );
}

function clusterPoint(index: number, total: number): { x: number; y: number } {
  if (total <= 1) return { x: 50, y: 18 };

  const centerX = 50;
  const centerY = total <= 3 ? 52 : 50;
  const radiusX = total <= 3 ? 24 : 26;
  const radiusY = total <= 3 ? 24 : 25;
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / total;

  return {
    x: centerX + Math.cos(angle) * radiusX,
    y: centerY + Math.sin(angle) * radiusY
  };
}

function linkEndPoint(
  start: { x: number; y: number },
  end: { x: number; y: number },
  inset: number
): { x: number; y: number } {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const length = Math.sqrt(dx * dx + dy * dy) || 1;

  return {
    x: end.x - (dx / length) * inset,
    y: end.y - (dy / length) * inset
  };
}

function miniNodeStyle(index: number, total: number): CSSProperties {
  const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(total, 1);
  return {
    left: `${50 + Math.cos(angle) * 48}%`,
    top: `${50 + Math.sin(angle) * 48}%`
  };
}

function TermGroup({
  label,
  terms,
  fallback,
  tone = "default"
}: {
  label: string;
  terms: string[];
  fallback?: string;
  tone?: "default" | "missing";
}) {
  const visibleTerms = terms.filter(Boolean).slice(0, 6);
  return (
    <div className="term-group">
      <span>{label}</span>
      <div>
        {visibleTerms.length ? (
          visibleTerms.map((term) => (
            <em className={tone === "missing" ? "term-chip missing" : "term-chip"} key={term}>
              {term}
            </em>
          ))
        ) : (
          <small>{fallback ?? "None detected"}</small>
        )}
      </div>
    </div>
  );
}

function getPriorityLevel(priority: string): "critical" | "high" | "medium" | "low" | null {
  const normalized = priority.toLowerCase();
  if (/\b(critical|urgent|immediate)\b/.test(normalized)) return "critical";
  if (/\bhigh\b/.test(normalized)) return "high";
  if (/\bmedium\b/.test(normalized)) return "medium";
  if (/\blow\b/.test(normalized)) return "low";
  return null;
}

function formatDisplayValue(value: string): string {
  return value.replace(/_/g, " ");
}

function getPriorityLabel(priority: string): string {
  const level = getPriorityLevel(priority);
  if (level === "critical") return "Immediate priority";
  if (level === "high") return "High impact";
  if (level === "medium") return "Medium impact";
  if (level === "low") return "Lower effort";
  return "Focus area";
}

async function writeClipboardText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the legacy copy path below.
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "true");
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textArea);
  return copied;
}

function downloadTextFile(fileName: string, text: string, mimeType: string) {
  const blob = new Blob([text], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function feedbackToMarkdown(feedback: FeedbackResponse, exportedAt: string): string {
  const lines = [
    "# Rubric-Aware Revision Feedback",
    "",
    `Exported: ${exportedAt}`,
    `Session: ${feedback.session_id}`,
    `Readiness: ${formatDisplayValue(feedback.readiness_level)}`,
    "",
    "## Overall Summary",
    "",
    feedback.overall_summary,
    "",
    "## Metrics",
    "",
    ...feedback.metrics.map((metric) => (
      `- **${metric.label}:** ${formatDisplayValue(metric.value)} — ${metric.detail}`
    )),
    "",
    "## Strengths",
    "",
    ...feedback.strengths.map((item) => `- ${item}`),
    "",
    "## Top Priorities",
    "",
    ...feedback.top_priorities.map((item, index) => `${index + 1}. ${item}`),
    "",
    "## Rubric Alignment",
    "",
    ...feedback.rubric_feedback.flatMap((item) => {
      const score =
        item.points_possible != null && item.estimated_points != null
          ? ` (${item.estimated_points}/${item.points_possible} formative estimate)`
          : "";
      return [
        `### ${item.criterion}`,
        "",
        `Status: ${formatDisplayValue(item.status)}${score}`,
        "",
        `Evidence: ${item.evidence_from_draft}`,
        "",
        `Next revision: ${item.suggestion}`,
        "",
        `Why it matters: ${item.why_it_matters}`,
        ""
      ];
    }),
    "## Section Feedback",
    "",
    ...feedback.section_feedback.flatMap((item) => [
      `### ${item.area}`,
      "",
      item.finding,
      "",
      `Why it matters: ${item.why_it_matters}`,
      "",
      `Revision move: ${item.revision_move}`,
      ""
    ]),
    "## Inline Comments",
    "",
    ...feedback.inline_comments.flatMap((item, index) => [
      `### Comment ${index + 1}`,
      "",
      `> ${item.target_text}`,
      "",
      item.comment,
      "",
      `Revision prompt: ${item.revision_prompt}`,
      ""
    ]),
    "## Coaching Questions",
    "",
    ...feedback.coaching_questions.map((question, index) => `${index + 1}. ${question}`),
    "",
    "## Revision Plan",
    "",
    ...feedback.revision_plan.flatMap((item, index) => [
      `### Step ${index + 1}: ${getPriorityLabel(item.priority)}`,
      "",
      `Priority: ${item.priority}`,
      "",
      `Action: ${item.action}`,
      "",
      `Expected impact: ${item.expected_impact}`,
      "",
      `Time estimate: ${item.time_estimate}`,
      ""
    ]),
    "## Topic Map",
    "",
    feedback.topic_map ? feedback.topic_map.summary : "No topic map available.",
    "",
    ...(feedback.topic_map?.clusters ?? []).flatMap((cluster) => [
      `### ${cluster.label}`,
      "",
      `Coverage: ${Math.round(cluster.draft_coverage * 100)}%`,
      "",
      `Rubric terms: ${cluster.rubric_terms.join(", ") || "None detected"}`,
      "",
      `Draft terms: ${cluster.draft_terms.join(", ") || "None detected"}`,
      "",
      `Missing terms: ${cluster.missing_terms.join(", ") || "None detected"}`,
      "",
      `Evidence: ${cluster.evidence_from_draft}`,
      "",
      `Interpretation: ${cluster.interpretation}`,
      "",
      `Example revision: ${cluster.example_revision}`,
      ""
    ]),
    "## Revision Checklist",
    "",
    ...feedback.revision_checklist.map((item) => `- [ ] ${item}`),
    "",
    "## Disclaimer",
    "",
    feedback.disclaimer,
    ""
  ];

  return lines.join("\n");
}

export default FeedbackResults;
