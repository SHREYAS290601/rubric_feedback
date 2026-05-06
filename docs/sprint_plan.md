# Two-Week Sprint Plan

## Sprint Goal

Build a working MVP of a rubric-aware writing feedback tool that can be put in front of a small number of real students for formative feedback.

## Sprint Constraints

- Timebox: two weeks.
- Focus: Scenario C as the core MVP.
- Scenario D is only a future extension.
- No final grading.
- No full LMS integration.
- No scanned PDF/OCR support.
- Prioritize working end-to-end flow over feature breadth.

## Week 1: Foundation and Core AI Workflow

| Day | Focus | Tasks | Output |
|---|---|---|---|
| Day 1 | Discovery and scope lock | Confirm student persona, assignment type, sample rubric, privacy constraints, and success metrics. Decide supported file types. | Final V1 scope and success criteria |
| Day 2 | Architecture and schemas | Design system architecture, API contract, feedback schema, database tables, and UI wireframe. | Architecture notes, Pydantic schemas, UI sketch |
| Day 3 | App skeleton | Build React submission interface and FastAPI backend skeleton. Add health check and feedback endpoint placeholder. | Running frontend/backend scaffold |
| Day 4 | Input handling | Implement text input and `.docx` parsing. Validate draft length, rubric presence, and unsupported file types. | Input validation and parsing working |
| Day 5 | Rubric parser | Build Rubric Parser Agent. Convert rubric text into structured criteria. Add validation and fallback for vague rubrics. | Parsed rubric JSON |
| Day 6 | Draft analyzers | Build Structure Analyzer and Argumentation Analyzer nodes. Return structured analysis objects. | Structure and argumentation outputs |
| Day 7 | Rubric alignment | Build Rubric Alignment Agent and first version of Feedback Synthesizer. | End-to-end AI workflow prototype |

## Week 2: Reliability, UX, Testing, and Handoff

| Day | Focus | Tasks | Output |
|---|---|---|---|
| Day 8 | Validation and fallback | Add Pydantic output validation, retry handling, and safe fallback messages for model or schema failure. | Reliable validated feedback response |
| Day 9 | Feedback UI | Build feedback results UI with rubric-level cards, strengths, priorities, and revision checklist. | Student-facing feedback page |
| Day 10 | Analytics | Add usage event capture: session started, draft submitted, feedback generated, user rating, latency, failure events. | Basic product analytics |
| Day 11 | Sample testing | Test with 5–8 sample assignments and rubrics. Identify vague, harsh, or hallucinated feedback. | Test notes and prompt issues |
| Day 12 | Quality improvements | Improve prompts, tighten tone, reduce generic feedback, add “not enough evidence” behavior. | Better feedback quality |
| Day 13 | Pilot dry run | Conduct small internal test with one or two students/staff if available. Fix UX and reliability issues. | Pilot-ready fixes |
| Day 14 | Polish and handoff | Final polish, documentation, demo script, known limitations, and next-sprint recommendations. | MVP demo and handoff notes |

## Priority Order

### Must-Have

- Draft and rubric input.
- Rubric parser.
- Structure analysis.
- Argumentation analysis.
- Rubric alignment feedback.
- Structured output validation.
- Student-facing feedback UI.
- Basic error handling.
- Formative disclaimer.

### Should-Have

- `.docx` parsing.
- Usage event capture.
- Student usefulness rating.
- Basic latency logging.
- Feedback quality test set.

### Could-Have

- Text-based PDF parsing.
- Export feedback as PDF.
- Draft history stub for future Scenario D.
- Admin view for aggregate usage metrics.

### Not in Scope

- Full LMS integration.
- Plagiarism detection.
- Official grading.
- OCR.
- Multi-draft comparison.
- Instructor dashboard.
- Full authentication system.

## Sprint Demo Script

A simple final demo should show:

1. Student opens tool.
2. Student pastes assignment draft.
3. Student pastes rubric.
4. Student clicks generate feedback.
5. System shows loading/progress state.
6. Feedback appears in structured sections:
   - summary,
   - strengths,
   - priorities,
   - rubric feedback,
   - checklist.
7. Student rates usefulness.
8. Backend logs event and rating.

## Stretch Goal

If all must-have items are completed early, add a small future-facing draft version field or database stub to show how Scenario D could be supported later.

Do not build full draft comparison in this sprint.
