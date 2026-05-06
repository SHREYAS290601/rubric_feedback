from fastapi import APIRouter, Depends

from app.models import UsageEvent
from app.services.auth import AuthenticatedUser, require_user
from app.services.storage import save_event


router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("")
def record_event(event: UsageEvent, user: AuthenticatedUser = Depends(require_user)) -> dict[str, str]:
    event.properties["user_id"] = user.user_id
    event.properties["auth_mode"] = user.auth_mode
    save_event(event)
    return {"status": "saved"}
