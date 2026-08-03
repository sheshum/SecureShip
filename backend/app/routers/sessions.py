"""Session management endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_chat_session_repository
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import ChatSessionState, SessionItem, SessionUpdateRequest

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.patch("/{session_id}", response_model=SessionItem)
async def update_session(
    session_id: UUID,
    request: SessionUpdateRequest,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionItem:
    """Update session fields (e.g., set ended_at to close session).
    
    Args:
        session_id: ID of the session to update
        request: Fields to update
        session_repo: Session repository dependency
        
    Returns:
        Updated session item
        
    Raises:
        HTTPException: 404 if session not found, 400 if no fields to update
    """
    updates = request.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Convert ended_at string to datetime if present and set to now
    if "ended_at" in updates and updates["ended_at"] is not None:
        updates["ended_at"] = datetime.now(UTC)

    chat_session = session_repo.update_session(session_id, **updates)

    if chat_session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionItem(
        id=chat_session.id,
        state=ChatSessionState(chat_session.state),
        started_at=chat_session.started_at,
        ended_at=chat_session.ended_at,
    )
