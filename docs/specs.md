# Product Specification

## Product Name

**Rubric-Aware Writing Feedback MVP**

## Selected Scenario

Primary scenario: **Scenario C**

> A feedback tool that analyzes a submitted written assignment and returns instant, personalized feedback on structure, argumentation, and rubric alignment — giving learners the chance to improve before instructor review.

## Product Summary

Build a student-facing formative feedback tool where a learner can submit a written assignment draft and an instructor-provided rubric, then receive structured feedback on organization, argumentation, evidence use, and rubric alignment.

The tool should not grade the student. It should help the learner revise before instructor review.

## Target User

### Primary User

A student working on a written assignment such as:

- business case analysis,
- consulting memo,
- reflection paper,
- research response,
- strategy recommendation,
- course module writing assignment.

### Secondary User

A course team, instructor, TA, or instructional designer who wants students to receive earlier formative guidance before final submission.

## Problem

Students often submit writing assignments without knowing whether their draft aligns with the rubric. Instructors and TAs cannot always provide early draft feedback to every student. A rubric-aware AI feedback tool can help students identify improvement areas before final review.

## V1 Goal

Create a two-week MVP that:

1. accepts a student draft,
2. accepts a rubric,
3. analyzes the draft through a structured AI workflow,
4. returns rubric-aligned formative feedback,
5. provides revision priorities and a checklist,
6. captures basic usage and quality signals.

## V1 Scope

### V1 Does

- Allow a student to paste text or upload a `.docx` file.
- Allow a student or instructor to paste a rubric.
- Parse the rubric into structured criteria.
- Analyze the draft for:
  - structure,
  - thesis/central claim,
  - paragraph flow,
  - argumentation,
  - evidence use,
  - logical gaps,
  - rubric alignment.
- Return feedback organized into:
  - overall summary,
  - readiness level,
  - strengths,
  - top revision priorities,
  - rubric-level feedback,
  - revision checklist.
- Require the AI to reference evidence from the draft when giving rubric feedback.
- Avoid assigning grades.
- Show a disclaimer that feedback is formative.
- Store basic usage events and feedback ratings.
- Validate AI output before displaying it.

### V1 Does Not Do

- Does not assign a final grade.
- Does not replace instructor or TA judgment.
- Does not submit work to the LMS.
- Does not rewrite the full assignment automatically.
- Does not perform plagiarism detection.
- Does not support scanned PDFs or OCR.
- Does not support multimodal submissions.
- Does not guarantee perfect correctness.
- Does not fully implement multi-draft tracking.
- Does not attempt deep LMS integration in the first sprint.

## Future Extension: Scenario D

The architecture should allow a future Scenario D extension.

Future draft-progress features may include:

- store multiple draft versions,
- compare draft 1 and draft 2,
- show what improved,
- identify remaining gaps,
- detect whether prior feedback was addressed,
- visualize rubric alignment over time,
- summarize how the student’s thinking evolved.

This is outside V1 unless all core MVP tasks are completed early.

## User Stories

### Student Submission

As a student, I want to submit my draft and rubric so that I can receive feedback before final submission.

### Rubric Feedback

As a student, I want feedback mapped to rubric criteria so that I know which requirements I am meeting and which need work.

### Revision Priorities

As a student, I want the system to identify my top revision priorities so that I do not feel overwhelmed.

### Evidence-Based Feedback

As a student, I want the tool to explain why it gave feedback so that I can trust and act on the suggestions.

### Instructor Safety

As an instructor, I want the system to avoid assigning grades so that students do not mistake AI feedback for official evaluation.

### Product Improvement

As a product team member, I want basic usage events and student ratings so that we can understand whether the tool is useful.

## Functional Requirements

### Input

- Text draft input.
- Optional `.docx` upload.
- Rubric text input.
- Assignment title field.
- Optional course/module name.

### Processing

- Validate that draft and rubric are not empty.
- Validate draft length.
- Parse rubric into criteria.
- Analyze draft structure.
- Analyze argumentation.
- Compare draft against rubric criteria.
- Generate structured feedback.
- Validate generated feedback against schema.

### Output

The system should display:

- overall summary,
- readiness level,
- 2–3 strengths,
- 3 top revision priorities,
- rubric feedback cards,
- revision checklist,
- formative disclaimer.

### Analytics

Track:

- session started,
- draft submitted,
- feedback generated,
- feedback generation failed,
- latency,
- user usefulness rating,
- user optional comment.

## Non-Functional Requirements

### Usability

- A student should be able to use the tool without training.
- Feedback should be concise but specific.
- The UI should avoid overwhelming the learner.

### Reliability

- AI output must be validated before display.
- Failures should result in a clear fallback message.
- Unsupported files should be rejected politely.

### Privacy

- Avoid storing full draft text unless necessary.
- If draft text is stored, use retention limits and access controls.
- Store analytics separately from full draft content where possible.

### Performance

- V1 should aim to return feedback within a reasonable pilot threshold.
- For a first pilot, a target of under 60 seconds is acceptable.
- Long-term target should be lower through caching, chunking, and model routing.

### Safety

- Do not assign grades.
- Do not claim instructor authority.
- Do not fabricate rubric requirements.
- Do not provide punitive or discouraging feedback.
- Make clear that the tool provides formative guidance.

## Acceptance Criteria

V1 is acceptable when:

- A student can submit a draft and rubric.
- The backend returns structured feedback.
- The feedback maps to rubric criteria.
- The output includes revision priorities and checklist.
- The UI renders feedback clearly.
- Schema validation prevents malformed AI outputs.
- At least 5–8 sample submissions are tested.
- Basic usage analytics are captured.
- The system includes a formative feedback disclaimer.
