# Data Model

## Database Choice

Use PostgreSQL for V1 because it is reliable, familiar, and strong for structured application data.

The MVP does not require a vector database because the core task analyzes one submitted draft and one rubric at a time. If future versions add retrieval from course materials or prior drafts, PostgreSQL with `pgvector` or a dedicated vector database could be considered.

## Design Goals

The schema should support:

- feedback sessions,
- rubric criteria,
- structured feedback output,
- usage analytics,
- student usefulness ratings,
- future draft versioning for Scenario D.

## Privacy Principle

Avoid storing full student drafts unless required. For a pilot, prefer storing metadata, generated feedback, and anonymized usage events.

If full drafts are stored, add retention limits and access controls.

## Tables

## 1. feedback_sessions

Tracks each feedback generation attempt.

```sql
CREATE TABLE feedback_sessions (
    session_id UUID PRIMARY KEY,
    user_id TEXT NULL,
    assignment_title TEXT NULL,
    course_context TEXT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    total_latency_ms INTEGER NULL,
    model_provider TEXT NULL,
    model_name TEXT NULL
);
```

### Notes

`user_id` can be nullable or anonymized for early pilot use.

`status` examples:

- `started`
- `completed`
- `failed`
- `validation_failed`

## 2. rubrics

Stores rubric metadata.

```sql
CREATE TABLE rubrics (
    rubric_id UUID PRIMARY KEY,
    session_id UUID REFERENCES feedback_sessions(session_id),
    rubric_text_hash TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Notes

Store a hash instead of raw rubric text if privacy or data retention is a concern.

## 3. rubric_criteria

Stores parsed rubric criteria.

```sql
CREATE TABLE rubric_criteria (
    criterion_id UUID PRIMARY KEY,
    rubric_id UUID REFERENCES rubrics(rubric_id),
    name TEXT NOT NULL,
    description TEXT NULL,
    weight NUMERIC NULL,
    display_order INTEGER NOT NULL
);
```

## 4. feedback_results

Stores final structured feedback.

```sql
CREATE TABLE feedback_results (
    feedback_id UUID PRIMARY KEY,
    session_id UUID REFERENCES feedback_sessions(session_id),
    overall_summary TEXT NOT NULL,
    readiness_level TEXT NOT NULL,
    strengths JSONB NOT NULL,
    top_priorities JSONB NOT NULL,
    revision_checklist JSONB NOT NULL,
    disclaimer TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 5. rubric_feedback_items

Stores criterion-level feedback.

```sql
CREATE TABLE rubric_feedback_items (
    item_id UUID PRIMARY KEY,
    feedback_id UUID REFERENCES feedback_results(feedback_id),
    criterion_name TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_from_draft TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    display_order INTEGER NOT NULL
);
```

### Allowed Status Values

- `meets`
- `partially_meets`
- `needs_work`
- `not_enough_evidence`

## 6. usage_events

Captures product and AI workflow events.

```sql
CREATE TABLE usage_events (
    event_id UUID PRIMARY KEY,
    session_id UUID NULL REFERENCES feedback_sessions(session_id),
    user_id TEXT NULL,
    event_name TEXT NOT NULL,
    properties JSONB NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Example Event Names

- `session_started`
- `draft_submitted`
- `rubric_submitted`
- `feedback_generation_started`
- `feedback_generation_completed`
- `feedback_generation_failed`
- `output_validation_failed`
- `feedback_viewed`
- `rating_submitted`

### Example Properties

```json
{
  "latency_ms": 32450,
  "model": "gpt-4.1",
  "draft_length_chars": 8500,
  "rubric_criteria_count": 5,
  "retry_count": 1
}
```

## 7. feedback_ratings

Stores student usefulness ratings.

```sql
CREATE TABLE feedback_ratings (
    rating_id UUID PRIMARY KEY,
    session_id UUID REFERENCES feedback_sessions(session_id),
    usefulness_rating INTEGER CHECK (usefulness_rating BETWEEN 1 AND 5),
    comment TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## Future Scenario D Tables

These are not required for V1 but show extensibility.

## 8. assignment_drafts

Stores draft versions if multi-draft tracking is added.

```sql
CREATE TABLE assignment_drafts (
    draft_id UUID PRIMARY KEY,
    user_id TEXT NULL,
    assignment_title TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    draft_text_hash TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 9. draft_comparisons

Stores comparison output between draft versions.

```sql
CREATE TABLE draft_comparisons (
    comparison_id UUID PRIMARY KEY,
    previous_draft_id UUID REFERENCES assignment_drafts(draft_id),
    current_draft_id UUID REFERENCES assignment_drafts(draft_id),
    improvements JSONB NOT NULL,
    remaining_gaps JSONB NOT NULL,
    thinking_evolution_summary TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## Data Retention Recommendation

For a student-facing pilot:

- store session metadata and analytics,
- avoid storing raw drafts by default,
- if storing drafts, define a retention period,
- separate personally identifiable data from feedback metadata,
- provide clear notice to users.

## Metrics Enabled by This Model

Product metrics:

- number of feedback sessions,
- completion rate,
- average latency,
- usefulness rating,
- failure rate,
- repeated use.

AI quality metrics:

- validation failure rate,
- retry rate,
- criteria with frequent `not_enough_evidence`,
- average number of revision priorities,
- model latency.

Learning metrics:

- whether students find feedback useful,
- which rubric criteria are most often weak,
- whether future drafts improve after feedback.
