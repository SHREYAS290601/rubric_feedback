import { AccountInfo } from "@azure/msal-browser";
import { useEffect, useRef, useState } from "react";
import { authConfig, getAccessToken, initializeAuth, signIn, signOut } from "./auth";
import AuthPanel from "./components/AuthPanel";
import DraftForm from "./components/DraftForm";
import FeedbackResults from "./components/FeedbackResults";
import LandingHero from "./components/LandingHero";
import RatingWidget from "./components/RatingWidget";
import { FeedbackRequest, FeedbackResponse } from "./types";

const API_BASE = "";

function App() {
  const [feedback, setFeedback] = useState<FeedbackResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [authReady, setAuthReady] = useState(!authConfig.enabled);
  const [account, setAccount] = useState<AccountInfo | null>(null);
  const workspaceRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    let mounted = true;
    initializeAuth()
      .then((activeAccount) => {
        if (!mounted) return;
        setAccount(activeAccount);
        setAuthReady(true);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : "Could not initialize Microsoft sign-in.");
        setAuthReady(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  function scrollToWorkspace() {
    workspaceRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <main className="app-shell">
      <LandingHero onStart={scrollToWorkspace} />

      <section className="workspace-section" id="workspace-anchor" ref={workspaceRef}>
        <div className="section-heading">
          <p className="eyebrow">Revision workspace</p>
          <h2>Submit a draft and rubric</h2>
          <p>
            Keep the input simple. The tool will return rubric alignment, coaching questions, and a revision plan.
          </p>
        </div>
        <AuthPanel
          account={account}
          isReady={authReady}
          onSignIn={async () => {
            setError(null);
            try {
              setAccount(await signIn());
            } catch (err) {
              setError(err instanceof Error ? err.message : "Microsoft sign-in failed.");
            }
          }}
          onSignOut={async () => {
            await signOut();
            setAccount(null);
          }}
        />
        <DraftForm
          isLoading={isLoading}
          onSubmit={async ({ draftFile, rubricFile, ...payload }) => {
            setError(null);
            setIsLoading(true);
            setFeedback(null);

            try {
              const token = await getAccessToken(account);
              const response = draftFile || rubricFile
                ? await submitFileFeedback({ draftFile, rubricFile, payload, accessToken: token })
                : await submitJsonFeedback(payload, token);
              setFeedback(response);
              window.setTimeout(() => {
                document.getElementById("results-anchor")?.scrollIntoView({ behavior: "smooth", block: "start" });
              }, 100);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Something went wrong.");
            } finally {
              setIsLoading(false);
            }
          }}
        />
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      {isLoading ? (
        <section className="loading-panel" aria-live="polite">
          <div className="spinner" />
          <div>
            <h2>Generating feedback</h2>
            <p>Parsing the rubric, reviewing the draft, and checking the response for formative tone.</p>
          </div>
        </section>
      ) : null}

      <div id="results-anchor" />
      {feedback ? (
        <>
          <FeedbackResults feedback={feedback} />
          <RatingWidget sessionId={feedback.session_id} getToken={() => getAccessToken(account)} />
        </>
      ) : null}
    </main>
  );
}

async function submitJsonFeedback(payload: {
  assignment_title?: string;
  course_context?: string;
  learning_goal?: string;
  feedback_depth: FeedbackRequest["feedback_depth"];
  focus_areas: string[];
  draft_text: string;
  rubric_text: string;
}, accessToken?: string): Promise<FeedbackResponse> {
  const response = await fetch(`${API_BASE}/api/feedback/generate`, {
    method: "POST",
    headers: authHeaders(accessToken, { "Content-Type": "application/json" }),
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Could not generate feedback.");
  }

  return response.json();
}

async function submitFileFeedback(
  {
    draftFile,
    rubricFile,
    payload,
    accessToken
  }: {
    draftFile?: File | null;
    rubricFile?: File | null;
    payload: FeedbackRequest;
    accessToken?: string;
  }
): Promise<FeedbackResponse> {
  const form = new FormData();
  if (draftFile) {
    form.append("draft_file", draftFile);
  } else {
    form.append("draft_text", payload.draft_text);
  }
  if (rubricFile) {
    form.append("rubric_file", rubricFile);
  } else {
    form.append("rubric_text", payload.rubric_text);
  }
  form.append("feedback_depth", payload.feedback_depth);
  form.append("focus_areas", payload.focus_areas.join(","));
  if (payload.assignment_title) form.append("assignment_title", payload.assignment_title);
  if (payload.course_context) form.append("course_context", payload.course_context);
  if (payload.learning_goal) form.append("learning_goal", payload.learning_goal);

  const response = await fetch(`${API_BASE}/api/feedback/generate-file`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: form
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? "Could not generate feedback from that file.");
  }

  return response.json();
}

function authHeaders(accessToken?: string, base: Record<string, string> = {}): Record<string, string> {
  if (!accessToken) return base;
  return { ...base, Authorization: `Bearer ${accessToken}` };
}

export default App;
