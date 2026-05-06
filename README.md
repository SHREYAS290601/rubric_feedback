# Rubric-Aware Writing Feedback MVP

Student-facing prototype for the Gies AI Solutions Developer take-home exercise.

The app implements Scenario C: students submit a written draft plus a rubric and receive formative feedback on structure, argumentation, and rubric alignment. Scenario D is represented as a future extension in the docs, not as core sprint scope.

## What Works

- React + TypeScript frontend
- FastAPI backend
- Optional Microsoft Entra sign-in with MSAL Browser
- Optional backend JWT validation for university Microsoft accounts
- JSON draft/rubric submission
- Draft and rubric document uploads
- `.txt`, `.md`, `.docx`, and text-based `.pdf` parsing
- Custom rubric criteria, weights, point bands, and performance levels used as feedback context
- Real OpenAI/Azure OpenAI provider path when configured
- Optional LangSmith traces for guardrails, AI calls, and result quality metrics
- Deterministic mock fallback when no API key is configured
- Prompt-injection, jailbreak, and off-platform-use guardrails before model calls
- Pydantic request and response schemas
- SQLite-backed sessions, events, and ratings for local prototype mode
- Student-facing feedback cards, priorities, checklist, and disclaimer

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## API

- `GET /api/health`
- `POST /api/feedback/generate`
- `POST /api/feedback/generate-file`
- `POST /api/feedback/rating`
- `POST /api/events`

## Prototype Notes

The current workflow is deterministic so the demo works without an API key. A production version can replace the internal workflow nodes with OpenAI or Azure OpenAI calls while preserving the same schemas:

1. Input validator
2. Rubric parser
3. Structure analyzer
4. Argumentation analyzer
5. Rubric alignment agent
6. Feedback synthesizer
7. Safety/quality checker
8. Pydantic output validation

The prototype avoids assigning grades and includes the required formative feedback disclaimer.

## Upload Support

Students can paste draft/rubric text or upload either document separately. Supported formats are:

- `.txt`
- `.md`
- `.docx`
- text-based `.pdf`

PDFs must contain selectable text. Scanned image-only PDFs should be OCR'd before upload. Rubric scoring language is parsed to understand criteria and expectations, but the app does not assign grades, points earned, or predicted scores.

## Microsoft Entra Sign-In

Local demo mode does not require sign-in. To require student authentication:

1. Register a Microsoft Entra single-page application for the frontend.
2. Register or expose an API scope for the backend, such as `api://YOUR_BACKEND_APP_ID/access_as_user`.
3. Set frontend env vars in `frontend/.env.local`:

```bash
VITE_MSAL_CLIENT_ID=YOUR_SPA_CLIENT_ID
VITE_MSAL_TENANT_ID=organizations
VITE_API_SCOPE=api://YOUR_BACKEND_APP_ID/access_as_user
```

4. Set backend env vars:

```bash
AUTH_REQUIRED=true
MS_TENANT_ID=organizations
MS_AUTH_AUDIENCE=api://YOUR_BACKEND_APP_ID
ALLOWED_EMAIL_DOMAINS=illinois.edu,uiuc.edu
```

For a real UIUC deployment, the app registration and allowed tenant/domain settings should be confirmed with campus IT.

## Real AI Provider

Without keys, the app uses deterministic local feedback. To call OpenAI:

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

If your local shell exposes the key as `CODEX_API_KEY`, the backend will use that as an alias for `OPENAI_API_KEY`:

```bash
AI_PROVIDER=openai
CODEX_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

For OpenAI-compatible providers such as OpenRouter, set a custom base URL and provider key:

```bash
AI_PROVIDER=openai
OPENAI_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=...
OPENAI_MODEL=openai/gpt-4.1-mini
```

For the UIUC DSRS LLM gateway, use the Messages-compatible endpoint. The backend detects this host and calls `/v1/messages` directly:

```bash
AI_PROVIDER=openai
OPENAI_BASE_URL=https://llm.dsrs.illinois.edu/v1
OPENAI_API_KEY=...
OPENAI_MODEL=openai/gpt-oss-120b
```

To call Azure OpenAI through the OpenAI-compatible v1 endpoint:

```bash
AI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=YOUR_DEPLOYMENT_NAME
```

The backend still runs input guardrails before model calls and validates model output against the feedback schema.

## AI Guardrails

The backend blocks submissions that appear to be:

- prompt-injection or jailbreak attempts,
- requests to reveal or override system instructions,
- requests to solve homework or provide subject-matter answers,
- requests for unrelated technical help such as linear-regression instructions or code,
- inputs that do not look like a writing draft plus rubric.

The LLM prompt also treats the draft and rubric as untrusted data and instructs the model to produce only formative writing feedback.

## Observability

The backend can emit LangSmith traces and structured local logs for the security-sensitive path:

- file input preparation,
- prompt-injection and jailbreak checks,
- off-platform request checks,
- provider selection and fallback,
- rubric/result metrics such as criterion count, scored items, revision steps, and topic clusters.

Set these in the backend process environment to enable LangSmith:

```bash
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=ai_sol_dev_review_drafts_proj
```

For student privacy, raw draft/rubric prompts are not sent to LangSmith by default. The default trace records counts and fingerprints. If a controlled evaluation run needs full prompt/response traces, explicitly add:

```bash
LANGSMITH_TRACE_RAW_PROMPTS=true
```

Do not enable raw prompt tracing for real student drafts unless students and the institution have approved that data flow.

To run the local security eval suite:

```bash
cd backend
AI_PROVIDER=mock python scripts/security_eval.py
```

The suite checks that a normal memo passes and that poisoned-doc, jailbreak/off-platform, and non-writing inputs are blocked.
