import { useState } from "react";

interface RatingWidgetProps {
  sessionId: string;
  getToken?: () => Promise<string | undefined>;
}

function RatingWidget({ sessionId, getToken }: RatingWidgetProps) {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  async function submitRating() {
    if (!rating) return;
    setStatus("saving");
    const token = getToken ? await getToken() : undefined;
    const response = await fetch("/api/feedback/rating", {
      method: "POST",
      headers: token
        ? { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
        : { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        usefulness_rating: rating,
        comment: comment || undefined
      })
    });

    setStatus(response.ok ? "saved" : "error");
  }

  return (
    <section className="rating-panel">
      <div>
        <h2>Was this useful?</h2>
        <p>Capture a quick learner signal for the pilot.</p>
      </div>
      <div className="rating-controls">
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            type="button"
            className={rating === value ? "rating-button selected" : "rating-button"}
            key={value}
            onClick={() => setRating(value)}
            aria-label={`${value} out of 5`}
          >
            {value}
          </button>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(event) => setComment(event.target.value)}
        placeholder="Optional comment"
        rows={3}
      />
      <button type="button" onClick={submitRating} disabled={!rating || status === "saving"}>
        {status === "saving" ? "Saving..." : "Submit rating"}
      </button>
      {status === "saved" ? <p className="success-copy">Rating saved.</p> : null}
      {status === "error" ? <p className="error-copy">Rating could not be saved.</p> : null}
    </section>
  );
}

export default RatingWidget;
