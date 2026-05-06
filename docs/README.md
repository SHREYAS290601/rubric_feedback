# Gies AI Solutions Developer Take-Home Package

## Project

**Rubric-Aware Writing Feedback MVP with Draft Progress Extension**

## Primary Scenario

**Scenario C:** A feedback tool that analyzes a submitted written assignment and returns instant, personalized feedback on structure, argumentation, and rubric alignment so learners can improve before instructor review.

## Future Extension

**Scenario D:** A writing companion that tracks progress across multiple drafts, surfacing what improved, what still needs work, and how the student’s thinking evolved.

Scenario D is intentionally framed as a future extension, not part of the core two-week MVP.

## Purpose of These Markdown Files

These files are designed to help Codex or another coding assistant understand the intended product, architecture, sprint scope, data model, agent workflow, and final submission requirements.

## Files

| File | Purpose |
|---|---|
| `specs.md` | Product requirements, V1 scope, non-goals, user stories, acceptance criteria |
| `architecture.md` | System architecture, stack decisions, services, APIs, data flow |
| `agent_workflow.md` | Agentic AI pipeline, LangGraph-style nodes, schemas, prompts, fallback logic |
| `data_model.md` | PostgreSQL tables, event tracking, privacy notes |
| `sprint_plan.md` | Two-week sprint plan, priorities, daily tasks, deliverables |
| `evaluation_and_risks.md` | Definition of done, evaluation metrics, risks, mitigations |
| `ai_use_appendix.md` | AI-use documentation required by the take-home exercise |
| `final_submission_draft.md` | Polished two-page-style submission draft |
| `codex_build_prompt.md` | A single prompt Codex can use to build or scaffold the MVP |

## MVP Philosophy

The MVP should be technically credible but realistically scoped for two weeks. The goal is not to build a full LMS-integrated grading system. The goal is to build a focused formative feedback tool that is student-centered, rubric-aware, and powered by a multi-step agentic workflow rather than a single generic chatbot.

## Key Principle

> The core success measure is not whether the AI sounds intelligent. It is whether the student can revise more effectively after using it.
