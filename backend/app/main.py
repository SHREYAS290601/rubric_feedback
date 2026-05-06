from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import events, feedback
from app.services.observability import configure_logging
from app.services.storage import health_snapshot, init_db


configure_logging()

app = FastAPI(
    title="Rubric-Aware Writing Feedback MVP",
    description="Student-facing formative feedback tool for rubric-aligned writing revision.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(feedback.router)
app.include_router(events.router)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, object]:
    return health_snapshot()
