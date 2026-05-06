# Evaluation and Risks

## Definition of Done

V1 is ready to put in front of a real student when the following are true.

## Functional Readiness

- Student can submit a draft and rubric without developer help.
- Backend validates the input.
- Backend runs the AI workflow successfully.
- Frontend displays structured feedback.
- Feedback is mapped to rubric criteria.
- Revision priorities and checklist are visible.
- Student can submit a usefulness rating.

## AI Output Readiness

- AI output passes schema validation.
- Feedback does not assign a final grade.
- Feedback does not claim to replace instructor review.
- Feedback is grounded in draft/rubric content.
- Rubric feedback includes evidence or clearly says `not_enough_evidence`.
- Feedback is constructive and learner-centered.
- The tool handles validation/model failures gracefully.

## Testing Readiness

- At least 5–8 sample submissions have been tested.
- Each sample includes a draft and rubric.
- Outputs have been reviewed for:
  - specificity,
  - tone,
  - rubric alignment,
  - hallucinated criteria,
  - usefulness for revision.
- Common error states have been tested:
  - missing rubric,
  - empty draft,
  - unsupported file,
  - very short draft,
  - AI validation failure.

## Product Readiness

- Usage events are captured.
- Feedback generation latency is logged.
- Failure events are logged.
- Student usefulness rating is captured.
- Disclaimer is visible.

## Suggested Disclaimer

> This tool provides formative feedback to help you revise. It does not assign a grade and does not replace instructor feedback.

## Evaluation Metrics

## Product Metrics

- feedback generation completion rate,
- average latency,
- failure rate,
- student usefulness rating,
- number of repeated uses,
- drop-off before feedback generation.

## AI Quality Metrics

- output validation failure rate,
- retry rate,
- rubric criteria successfully parsed,
- number of `not_enough_evidence` items,
- manual quality review score,
- hallucinated rubric criteria count.

## Learner Experience Metrics

- student usefulness rating,
- clarity of feedback,
- perceived actionability,
- whether the student knows what to revise next.

## Biggest Risk

The biggest risk is **feedback quality and trustworthiness**.

It is easy to generate feedback that sounds polished. It is harder to ensure that the feedback is actually grounded in the student's draft and the instructor's rubric.

The timeline could blow up if feedback is:

- vague,
- generic,
- overly harsh,
- fabricated,
- misaligned with the rubric,
- not actionable,
- perceived as a grade.

## Why This Risk Matters

The product is student-facing. If a student receives inaccurate or confusing feedback, they may revise in the wrong direction or lose trust in the tool.

For an education context, trust matters more than impressive model output.

## Mitigation Plan

### 1. Require an Explicit Rubric

Do not let the model invent evaluation criteria. The rubric anchors the feedback.

### 2. Parse the Rubric First

Convert the rubric into structured criteria before evaluating the draft.

### 3. Require Evidence from the Draft

Each rubric-level comment should include evidence from the draft or mark `not_enough_evidence`.

### 4. Avoid Grades

The system should not output scores, letter grades, or grade-like claims.

### 5. Use Structured Output Validation

Pydantic validation ensures that the response is complete and usable by the UI.

### 6. Add Safety/Quality Check

Before display, check for grading language, fabricated criteria, harsh tone, and unsupported claims.

### 7. Test with Realistic Samples

Use sample assignments and rubrics to identify failure patterns before student pilot.

### 8. Collect Student Feedback

Ask students whether the feedback was useful, clear, and actionable.

## Secondary Risks

## Scope Creep

### Risk

Trying to build Scenario C and Scenario D fully together could make the two-week timeline unrealistic.

### Mitigation

Keep Scenario C as V1. Mention Scenario D only as a future extension.

## File Parsing Complexity

### Risk

PDF parsing and OCR can consume too much time.

### Mitigation

Support pasted text and `.docx` first. Add text-based PDF only if time allows. Avoid OCR in V1.

## Latency

### Risk

Multi-step AI workflow may be slow.

### Mitigation

Use concise prompts, structured outputs, and limit input size. Log latency. Optimize later if needed.

## Privacy

### Risk

Student drafts may contain sensitive personal content.

### Mitigation

Avoid storing full draft text by default. Store metadata and analytics separately. Define retention policy.

## Rubric Ambiguity

### Risk

Rubrics may be vague or incomplete.

### Mitigation

Ask for clearer rubric/assignment instructions when needed. Use `not_enough_evidence` rather than guessing.

## Hallucination

### Risk

The model may invent requirements or overstate issues.

### Mitigation

Ground feedback in draft and rubric. Include safety checker. Validate output.

## Success Statement

The MVP succeeds if a student can walk away with a clearer understanding of what to revise next.
