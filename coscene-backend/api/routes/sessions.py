"""
Session management API routes.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    SessionCreate,
    SessionResponse,
    MessageResponse,
    SceneVersionResponse,
    SceneVersionListResponse
)
from services.database import get_db
from services import storage
from services.usd_service import get_usd_service

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new editing session.

    If initial_scene is provided, creates first scene version.
    Otherwise, creates empty scene.
    """
    # Create session
    session = await storage.create_session(
        db=db,
        user_id=request.user_id,
        metadata=request.extra_metadata
    )

    # Create initial scene version if provided
    if request.initial_scene:
        usd_service = get_usd_service()
        is_valid, error = usd_service.validate_usd(request.initial_scene)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid USD content: {error}"
            )

        await storage.create_scene_version(
            db=db,
            session_id=session.id,
            usd_content=request.initial_scene
        )
    else:
        # Create empty scene
        usd_service = get_usd_service()
        empty_scene = usd_service.create_empty_scene()

        await storage.create_scene_version(
            db=db,
            session_id=session.id,
            usd_content=empty_scene
        )

    await db.commit()

    return SessionResponse.model_validate(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get session details."""
    session = await storage.get_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    End session and mark as completed.
    Does not actually delete from DB, just updates status.
    """
    session = await storage.get_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    await storage.update_session_status(db, session_id, "completed")
    await db.commit()


@router.get("/{session_id}/history", response_model=list[MessageResponse])
async def get_session_history(
    session_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get conversation history for a session."""
    session = await storage.get_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    messages = await storage.get_session_messages(db, session_id, limit=limit)

    return [MessageResponse.model_validate(msg) for msg in messages]


@router.get("/{session_id}/versions", response_model=SceneVersionListResponse)
async def list_scene_versions(
    session_id: UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List scene versions for a session."""
    session = await storage.get_session(db, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    versions = await storage.list_scene_versions(db, session_id, limit=limit)

    return SceneVersionListResponse(
        versions=[SceneVersionResponse.model_validate(v) for v in versions],
        total=len(versions)
    )
