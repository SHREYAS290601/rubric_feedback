# Appendix: AI-Use Documentation

## AI Tools Used

I used AI tools such as ChatGPT, Claude, and/or Codex to brainstorm, structure, and refine this sprint plan.

AI was used as a planning and writing assistant. I reviewed, edited, and finalized the submission to reflect my own technical judgment, scope decisions, and understanding of learner-centered design.

## How AI Contributed

AI helped with:

- comparing the four scenarios,
- selecting Scenario C as the strongest MVP,
- framing Scenario D as a future extension,
- brainstorming a realistic technical architecture,
- outlining an agentic AI workflow,
- creating a two-week sprint plan,
- identifying risks and mitigations,
- refining the final language for clarity.

AI did not make the final scope decision independently. I chose to keep Scenario C as the MVP because it offers a realistic two-week build while still showing technical depth through agentic AI, structured outputs, validation, and product analytics.

## Prompts Used

### Prompt 1

```text
I am completing a take-home exercise for an AI Solutions Developer role. The task is to choose one student-facing edtech scenario and scope a two-week build sprint. Help me compare the scenarios and choose the one with the strongest technical depth beyond a chatbot.
```

### Contribution

This helped compare the four scenarios and identify Scenario C as a strong option because it supports agentic AI, rubric analysis, structured feedback, learner experience, and measurable quality controls.

---

### Prompt 2

```text
For Scenario C, help me design a V1 scope for a rubric-aware writing feedback tool. Include what the tool does and what it does not do.
```

### Contribution

This helped shape the V1 and non-goals. I refined the scope to keep the tool formative rather than grading-focused.

---

### Prompt 3

```text
Suggest a technical stack for a student-facing AI feedback tool using agentic AI, structured outputs, and a custom software pipeline.
```

### Contribution

This helped brainstorm React, FastAPI, LangGraph, OpenAI/Azure OpenAI, Pydantic, PostgreSQL, and document parsing libraries.

---

### Prompt 4

```text
Break this project into a realistic two-week sprint plan with concrete tasks and a definition of done.
```

### Contribution

This helped convert the MVP idea into a day-by-day sprint plan.

---

### Prompt 5

```text
What is the biggest risk in building an AI writing feedback tool for students, and how should I explain mitigation?
```

### Contribution

This helped identify feedback quality and trustworthiness as the biggest risk. I expanded the mitigation plan around rubric grounding, evidence-based feedback, structured validation, and learner-centered design.

---

### Prompt 6

```text
Help me include Scenario D as a future extension without over-scoping the two-week MVP.
```

### Contribution

This helped frame draft progress tracking as a future extension rather than part of the initial V1.

---

### Prompt 7

```text
Create markdown files that Codex can use, such as architecture.md, specs.md, sprint_plan.md, data_model.md, and agent_workflow.md.
```

### Contribution

This helped turn the sprint plan into structured implementation and documentation files that could guide a coding assistant or developer.

## Final Review

I reviewed and edited the AI-assisted output to make sure it:

- selected one primary scenario,
- stayed realistic for a two-week sprint,
- went beyond a generic chatbot,
- included student-facing learner experience,
- documented technical depth,
- avoided over-scoping Scenario D,
- clearly stated limitations and risks.
