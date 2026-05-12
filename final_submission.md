# AI Solutions Developer Take-Home Exercise

## Scenario Chosen

I chose **Scenario C**: a tool that gives students instant, personalized feedback on written assignments before instructor review. I built it as a **Rubric-Aware Writing Feedback MVP** and left Scenario D, multi-draft progress tracking, as a future extension.

## 1. What I Built

V1 lets a student submit a draft and rubric, then receive structured formative feedback on structure, argumentation, evidence use, and rubric alignment.

The MVP includes:

- a React/TypeScript website with a landing page, submission workspace, loading state, feedback results, and rating flow;
- pasted draft/rubric input, with file-upload support represented in the workflow;
- a FastAPI backend with feedback, event, rating, and health endpoints;
- Pydantic schemas for requests and responses;
- an agentic workflow for validation, rubric parsing, draft analysis, rubric alignment, feedback synthesis, and safety checks;
- deterministic fallback feedback when no LLM provider is configured.

The feedback includes a summary, readiness level, strengths, top priorities, rubric feedback, inline comments, coaching questions, topic map, revision plan, checklist, and formative disclaimer.

V1 does **not** grade work, submit to an LMS, rewrite the assignment, detect plagiarism, support OCR/scanned PDFs, or implement full draft-to-draft tracking.

## 2. Stack and Why

**React + TypeScript:** I used this for a clear student workflow with reliable typed components for submission, feedback cards, revision planning, and ratings.

**Python + FastAPI:** I used FastAPI for typed API routes, validation, file-aware request handling, model-provider integration, and fallback feedback logic.

**Pydantic:** I used Pydantic to validate AI/fallback output before the frontend displays it.

**OpenAI/Azure OpenAI-ready workflow:** I designed the workflow for an LLM provider but kept deterministic local output so the prototype stays demoable without keys or credits.

**Prototype storage with PostgreSQL path:** The architecture supports sessions, usage events, ratings, latency, failure metadata, rubric criteria, feedback results, and future draft versioning.

## 3. Sprint Tasks

### Phase 1, Week 1: Full-Stack MVP Build

| Day | Focus | Work | Output |
|---|---|---|---|
| Day 1 | Scope | Define the student journey, V1 boundaries, API contract, response shape, and safety rules. | Locked product flow. |
| Day 2 | Scaffolding | Set up React/TypeScript UI, FastAPI app, health route, CORS, config, and base styling. | Running frontend and backend. |
| Day 3 | Submission | Build draft/rubric inputs, assignment fields, submit state, request schema, validation, and `/api/feedback/generate`. | Frontend submits to backend. |
| Day 4 | First feedback loop | Add loading/error states, deterministic feedback, and Pydantic response schema. | First end-to-end response. |
| Day 5 | Results | Build summary, strengths, priorities, rubric cards, checklist, and staged local workflow. | Structured feedback UI. |
| Day 6 | Signals | Add usefulness rating, `/api/events`, `/api/feedback/rating`, event storage, and basic logging. | Ratings and usage events. |
| Day 7 | Polish | Improve responsive UI, copy, empty states, disclaimer placement, guardrails, fallback errors, and file-aware handling. | Demoable MVP. |

### Phase 2, Week 2: Hardening and Pilot Readiness

| Day | Focus | Work | Output |
|---|---|---|---|
| Day 8 | Rubric quality | Improve rubric parsing, criteria extraction, vague-rubric handling, and validation. | Stronger rubric alignment. |
| Day 9 | Draft analysis | Strengthen structure, argumentation, evidence detection, and off-prompt handling. | More specific draft feedback. |
| Day 10 | Alignment | Refine statuses, require draft evidence, and add `not_enough_evidence`. | Less guessing, better grounding. |
| Day 11 | Safety | Tighten formative language, remove grade-like framing, validate output, and improve failures. | Safer student-facing output. |
| Day 12 | Testing | Review logs, latency, events, ratings, and realistic draft/rubric examples. | Known quality gaps. |
| Day 13 | UX | Fix confusing states, improve readability, adjust card hierarchy, and check mobile usability. | Cleaner pilot experience. |
| Day 14 | Handoff | Finalize documentation, limitations, demo script, Scenario D notes, and handoff materials. | Completed submission package. |

## 4. Definition of Done

V1 is ready for a real student when:

- a student can submit a draft and rubric without developer help;
- the backend returns structured rubric-aligned feedback;
- the UI separates strengths, priorities, rubric feedback, and next steps;
- each rubric item cites draft evidence or uses `not_enough_evidence`;
- the system avoids grades and labels feedback as formative;
- schema validation runs before display;
- the app handles missing rubrics, short drafts, unsupported files, and provider failures;
- the system captures ratings and basic usage events;
- the UI works well enough for a small pilot.

## 5. System Protection

I protected the system at three levels.

**Product protection:** The tool gives formative guidance only. It does not grade, claim instructor authority, or replace instructor review.

**Data protection:** The architecture avoids storing full draft text unless required. It favors session IDs, metadata, ratings, and event logs over unnecessary student identifiers. A production version should add access controls, retention limits, and private draft storage.

**AI protection:** The workflow parses the rubric before evaluation, grounds feedback in the draft and rubric, uses `not_enough_evidence` instead of guessing, validates responses with Pydantic, and checks for harsh tone, fabricated criteria, and grade-like language.

## 6. Biggest Risk

The biggest risk is **feedback quality and trustworthiness**.

AI feedback can sound polished while still being vague, unsupported, or misaligned. That could damage trust and lead students to revise in the wrong direction. I reduced this risk with rubric grounding, draft evidence, staged analysis, schema validation, safety checks, and usefulness ratings. The MVP succeeds when a student leaves knowing what to revise next.

## Appendix: AI-Use Documentation

### AI Tools Used

I used ChatGPT/Codex to plan, build, and refine the MVP. AI supported product scoping, frontend implementation, backend architecture, workflow design, safety planning, and documentation. I reviewed and adapted the output to match my build decisions and the AI Solutions Developer exercise.

### Prompt 1: Website / Frontend Build

```text
Help me build the student-facing website for a rubric-aware writing feedback MVP. The product should let a student submit an assignment draft and rubric, then receive structured formative feedback. Design the frontend as a clean React + TypeScript interface with a strong landing section, draft and rubric input fields, assignment context fields, file upload support, loading states, feedback result cards, revision priorities, rubric-alignment feedback, coaching questions, a revision checklist, and a usefulness rating widget. The experience should feel clear, student-centered, and trustworthy, and it should explain that the feedback is formative and does not replace instructor review.
```

AI helped shape the landing page, submission workflow, feedback display, rubric cards, rating widget, loading state, and formative disclaimer.

### Prompt 2: Backend / API Build

```text
Help me build the backend for a rubric-aware writing feedback MVP using FastAPI and Pydantic. The backend should expose endpoints for health checks, feedback generation, file-based feedback generation, usage events, and usefulness ratings. It should validate draft and rubric inputs, support pasted text and file upload, parse documents where possible, run a feedback-generation workflow, return structured JSON to the frontend, and store basic events or ratings for product evaluation. Include guardrails for input length, unsupported files, formative-only feedback, authentication-aware access, error handling, and deterministic mock output when an LLM provider is not configured.
```

AI helped define the FastAPI routes, Pydantic schemas, validation, event logging, rating capture, document boundaries, and fallback behavior.

### Prompt 3: Agentic AI Architecture / Workflow

```text
Using the architecture and agent workflow documents, help me design the AI workflow for a rubric-aware writing feedback system that demonstrates technical depth beyond a single chatbot response. The workflow should process a student draft and rubric through separate stages: input validation, rubric parsing, draft structure analysis, argumentation analysis, rubric alignment, feedback synthesis, safety and quality checking, and final Pydantic output validation. The system should produce learner-centered formative feedback with evidence from the draft, readiness level, strengths, top priorities, rubric feedback, inline comments, coaching questions, topic mapping, and a revision checklist. It should avoid grades, avoid fabricating rubric criteria, mark uncertain items as not_enough_evidence, and treat AI feedback as guidance rather than instructor judgment.
```

AI helped define the staged workflow: structured state, rubric parsing, draft analysis, rubric alignment, safety checks, schema validation, fallback behavior, and observability.

### Final Human Review

I edited the AI-assisted work to reflect the actual MVP: a React frontend, FastAPI backend, structured AI workflow, validation, guardrails, ratings, and formative feedback positioning.
