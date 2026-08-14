"""Session management endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.dependencies import get_chat_session_repository, require_admin_auth
from app.repositories.chat_sessions import ChatSessionRepository
from app.schemas.sessions import ChatSessionState, SessionItem, SessionListResponse, SessionUpdateRequest

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse, dependencies=[Depends(require_admin_auth)])
async def list_sessions(
    limit: int = 100,
    offset: int = 0,
    state: Annotated[ChatSessionState | None, Query()] = None,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)] = None,
) -> SessionListResponse:
    """List all chat sessions with pagination.

    Args:
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip
        state: Optional filter by session state
        session_repo: Session repository dependency

    Returns:
        List of chat sessions
    """
    sessions_data = session_repo.list_sessions(limit=limit, offset=offset, state=state)
    total = session_repo.count_sessions(state=state)
    return SessionListResponse(
        sessions=[
            SessionItem(
                id=s.id,
                state=ChatSessionState(s.state),
                started_at=s.started_at,
                ended_at=s.ended_at,
                customer_id=s.customer_id,
                customer_name=(f"{s.customer.first_name} {s.customer.last_name}" if s.customer else None),
            )
            for s in sessions_data
        ],
        total=total,
    )


@router.patch("/{session_id}", response_model=SessionItem)
async def update_session(
    session_id: UUID,
    request: SessionUpdateRequest,
    response: Response,
    session_repo: Annotated[ChatSessionRepository, Depends(get_chat_session_repository)],
) -> SessionItem:
    """Update session fields (e.g., set ended_at to close session).

    Args:
        session_id: ID of the session to update
        request: Fields to update
        response: FastAPI response (used to delete session cookie on close)
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
    closing = "ended_at" in updates and updates["ended_at"] is not None
    if closing:
        updates["ended_at"] = datetime.now(UTC)

    chat_session = session_repo.update_session(session_id, **updates)

    if closing:
        response.delete_cookie("session_id", path="/", samesite="strict")
        response.delete_cookie("has_session", path="/", samesite="strict")

    if chat_session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return SessionItem(
        id=chat_session.id,
        state=ChatSessionState(chat_session.state),
        started_at=chat_session.started_at,
        ended_at=chat_session.ended_at,
    )
