import { FormEvent, useState } from "react";
import { FeedbackDepth } from "../types";

interface DraftFormProps {
  isLoading: boolean;
  onSubmit: (payload: {
    assignment_title?: string;
    course_context?: string;
    learning_goal?: string;
    feedback_depth: FeedbackDepth;
    focus_areas: string[];
    draft_text: string;
    rubric_text: string;
    draftFile?: File | null;
    rubricFile?: File | null;
  }) => void;
}

const sampleDraft = `This memo recommends that Apex Foods prioritize a regional pilot before expanding the new subscription service nationally. The company has strong brand recognition, but the case suggests that operational capacity and customer retention are still uncertain.

The main benefit of a regional pilot is that it lets Apex test demand while limiting the cost of fulfillment issues. If the pilot tracks churn, average order value, and delivery delays, leaders can decide whether the model is ready to scale.

However, the recommendation also carries risk. A small pilot may not capture national demand, and competitors could move faster. Apex should define success metrics before launch and decide what evidence would trigger expansion, revision, or cancellation.`;

const sampleRubric = `Argument Quality: Presents a clear recommendation and supports it with reasoning.
Evidence Use: Uses case facts, data, or course concepts to justify the recommendation.
Organization: Uses a logical structure with clear transitions between ideas.
Risk Analysis: Identifies tradeoffs, risks, or alternative interpretations.
Actionability: Provides specific next steps that a business leader could use.`;

const acceptedFileTypes = ".txt,.md,.docx,.pdf";
const acceptedFileLabel = ".txt, .md, .docx, or text-based .pdf";

function DraftForm({ isLoading, onSubmit }: DraftFormProps) {
  const assignmentTitle = "Business Case Memo";
  const courseContext = "Strategy module";
  const learningGoal = "Make the recommendation clearer and better supported.";
  const feedbackDepth: FeedbackDepth = "deep";
  const focusAreas = ["Rubric alignment", "Evidence", "Argumentation"];
  const [draftText, setDraftText] = useState(sampleDraft);
  const [rubricText, setRubricText] = useState(sampleRubric);
  const [draftFile, setDraftFile] = useState<File | null>(null);
  const [rubricFile, setRubricFile] = useState<File | null>(null);
  const [securityError, setSecurityError] = useState<string | null>(null);

  const draftWordCount = draftText.trim() ? draftText.trim().split(/\s+/).length : 0;
  const rubricCriteriaCount = rubricText.split(/\n/).filter((line) => line.trim()).length;
  const visibleSecurityFindings = scanVisibleInput(draftFile ? "" : draftText, rubricFile ? "" : rubricText);
  const hasUploadedFiles = Boolean(draftFile || rubricFile);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSecurityError(null);
    if (visibleSecurityFindings.length > 0) {
      setSecurityError(
        "Remove prompt-injection, jailbreak, or off-platform answer requests before generating feedback."
      );
      return;
    }
    onSubmit({
      assignment_title: assignmentTitle || undefined,
      course_context: courseContext || undefined,
      learning_goal: learningGoal || undefined,
      feedback_depth: feedbackDepth,
      focus_areas: focusAreas,
      draft_text: draftText,
      rubric_text: rubricText,
      draftFile,
      rubricFile
    });
  }

  return (
    <form className="submission-panel" onSubmit={handleSubmit}>
      <div className="editor-grid">
        <section className="editor-panel">
          <div className="editor-heading">
            <label htmlFor="draft-text">Draft text</label>
            <span>{draftFile ? "file attached" : `${draftWordCount} words`}</span>
          </div>
          <textarea
            id="draft-text"
            value={draftFile ? "" : draftText}
            onChange={(event) => {
              setDraftText(event.target.value);
              setSecurityError(null);
            }}
            rows={13}
            disabled={Boolean(draftFile)}
            placeholder={draftFile ? `Using uploaded file: ${draftFile.name}` : undefined}
          />
          <label className="file-drop">
            <input
              type="file"
              accept={acceptedFileTypes}
              onChange={(event) => {
                setDraftFile(event.target.files?.[0] ?? null);
                setSecurityError(null);
              }}
            />
            <span className="upload-button">Upload draft</span>
            <strong>{draftFile ? draftFile.name : acceptedFileLabel}</strong>
          </label>
        </section>

        <section className="editor-panel">
          <div className="editor-heading">
            <label htmlFor="rubric-text">Rubric or assignment criteria</label>
            <span>{rubricFile ? "file attached" : `${rubricCriteriaCount} criteria`}</span>
          </div>
          <textarea
            id="rubric-text"
            value={rubricFile ? "" : rubricText}
            onChange={(event) => {
              setRubricText(event.target.value);
              setSecurityError(null);
            }}
            rows={13}
            disabled={Boolean(rubricFile)}
            placeholder={rubricFile ? `Using uploaded file: ${rubricFile.name}` : undefined}
          />
          <label className="file-drop">
            <input
              type="file"
              accept={acceptedFileTypes}
              onChange={(event) => {
                setRubricFile(event.target.files?.[0] ?? null);
                setSecurityError(null);
              }}
            />
            <span className="upload-button">Upload rubric</span>
            <strong>{rubricFile ? rubricFile.name : acceptedFileLabel}</strong>
          </label>
        </section>
      </div>

      <div className="action-row">
        <div className="action-copy">
          <strong>Feedback pass</strong>
          <span>
            Draft and rubric are scanned for prompt injection, jailbreak attempts, off-platform answer requests,
            and rubric scoring before feedback runs.
          </span>
          <div className="security-strip" aria-live="polite">
            <SecurityCheck label="Injection scan" state={securityState(isLoading, visibleSecurityFindings.length > 0, hasUploadedFiles)} />
            <SecurityCheck label="Jailbreak check" state={securityState(isLoading, visibleSecurityFindings.length > 0, hasUploadedFiles)} />
            <SecurityCheck label="Scope check" state={isLoading ? "running" : "ready"} />
            <SecurityCheck label="Rubric scoring parse" state={isLoading ? "running" : "ready"} />
          </div>
          {securityError ? <span className="security-error">{securityError}</span> : null}
        </div>
        <div className="action-buttons">
          {draftFile || rubricFile ? (
            <button
              type="button"
              className="secondary-button"
              onClick={() => {
                setDraftFile(null);
                setRubricFile(null);
                setSecurityError(null);
              }}
              disabled={isLoading}
            >
              Remove files
            </button>
          ) : null}
          <button
            type="submit"
            className="primary-button"
            disabled={
              isLoading ||
              (!draftFile && draftText.trim().length < 80) ||
              (!rubricFile && rubricText.trim().length < 20)
            }
          >
            {isLoading ? "Generating..." : "Generate feedback"}
          </button>
        </div>
      </div>
    </form>
  );
}

function SecurityCheck({
  label,
  state
}: {
  label: string;
  state: "ready" | "running" | "server" | "blocked";
}) {
  const stateLabels = {
    ready: "Ready",
    running: "Running",
    server: "Server scan",
    blocked: "Needs review"
  };

  return (
    <span className={`security-chip security-${state}`}>
      <strong>{label}</strong>
      <em>{stateLabels[state]}</em>
    </span>
  );
}

function securityState(
  isLoading: boolean,
  hasVisibleFinding: boolean,
  hasUploadedFiles: boolean
): "ready" | "running" | "server" | "blocked" {
  if (hasVisibleFinding) return "blocked";
  if (isLoading) return "running";
  if (hasUploadedFiles) return "server";
  return "ready";
}

function scanVisibleInput(draft: string, rubric: string): string[] {
  const text = `${draft}\n${rubric}`.toLowerCase();
  const patterns = [
    /ignore (all )?(previous|prior|above|system|developer) instructions/,
    /(disregard|override|bypass) (the )?(system|developer|safety|instructions|rules)/,
    /(system|developer|hidden) prompt/,
    /jailbreak/,
    /do anything now/,
    /you are now/,
    /pretend you are/,
    /role[- ]?play as/,
    /give me (the )?(final )?answer/,
    /write (my|the) (assignment|essay|paper|memo) for me/,
    /solve this (problem|homework|quiz|exam)/,
    /linear[- ]regression.*(answer|solution|code|formula|model)/
  ];
  return patterns.filter((pattern) => pattern.test(text)).map((pattern) => pattern.source);
}

export default DraftForm;
