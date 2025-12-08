"""
Database storage operations for sessions, messages, scenes, and renders.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
import hashlib

from sqlalchemy import select, delete, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import Session, Message, SceneVersion, Render


# ============ Session Operations ============

async def create_session(db: AsyncSession, user_id: UUID, metadata: dict = None) -> Session:
    """Create a new editing session."""
    session = Session(
        user_id=user_id,
        extra_metadata=metadata or {},
    )
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: UUID) -> Optional[Session]:
    """Get session by ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    return result.scalar_one_or_none()


async def update_session_activity(db: AsyncSession, session_id: UUID):
    """Update last_active_at timestamp."""
    await db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(last_active_at=datetime.now())
    )


async def update_session_status(db: AsyncSession, session_id: UUID, status: str):
    """Update session status."""
    await db.execute(
        update(Session)
        .where(Session.id == session_id)
        .values(status=status)
    )


# ============ Message Operations ============

async def create_message(
    db: AsyncSession,
    session_id: UUID,
    role: str,
    content: str,
    metadata: dict = None
) -> Message:
    """Create a new message in a session."""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        extra_metadata=metadata or {},
    )
    db.add(message)
    await db.flush()
    return message


async def get_session_messages(
    db: AsyncSession,
    session_id: UUID,
    limit: int = 100
) -> List[Message]:
    """Get messages for a session, ordered by timestamp."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp)
        .limit(limit)
    )
    return result.scalars().all()


# ============ Scene Version Operations ============

async def create_scene_version(
    db: AsyncSession,
    session_id: UUID,
    usd_content: str,
    parent_version_id: Optional[UUID] = None,
    created_by_message_id: Optional[UUID] = None
) -> SceneVersion:
    """Create a new scene version."""
    # Get next version number
    result = await db.execute(
        select(SceneVersion.version_number)
        .where(SceneVersion.session_id == session_id)
        .order_by(desc(SceneVersion.version_number))
        .limit(1)
    )
    last_version = result.scalar_one_or_none()
    version_number = (last_version + 1) if last_version is not None else 1

    # Calculate checksum
    checksum = hashlib.sha256(usd_content.encode()).hexdigest()

    scene_version = SceneVersion(
        session_id=session_id,
        version_number=version_number,
        parent_version_id=parent_version_id,
        usd_content=usd_content,
        created_by_message_id=created_by_message_id,
        checksum=checksum,
    )
    db.add(scene_version)
    await db.flush()
    return scene_version


async def get_scene_version(db: AsyncSession, version_id: UUID) -> Optional[SceneVersion]:
    """Get scene version by ID."""
    result = await db.execute(
        select(SceneVersion).where(SceneVersion.id == version_id)
    )
    return result.scalar_one_or_none()


async def get_latest_scene_version(
    db: AsyncSession,
    session_id: UUID
) -> Optional[SceneVersion]:
    """Get latest scene version for a session."""
    result = await db.execute(
        select(SceneVersion)
        .where(SceneVersion.session_id == session_id)
        .order_by(desc(SceneVersion.version_number))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_scene_version_by_number(
    db: AsyncSession,
    session_id: UUID,
    version_number: int
) -> Optional[SceneVersion]:
    """Get scene version by version number."""
    result = await db.execute(
        select(SceneVersion)
        .where(
            SceneVersion.session_id == session_id,
            SceneVersion.version_number == version_number
        )
    )
    return result.scalar_one_or_none()


async def list_scene_versions(
    db: AsyncSession,
    session_id: UUID,
    limit: int = 20
) -> List[SceneVersion]:
    """List scene versions for a session."""
    result = await db.execute(
        select(SceneVersion)
        .where(SceneVersion.session_id == session_id)
        .order_by(desc(SceneVersion.version_number))
        .limit(limit)
    )
    return result.scalars().all()


# ============ Render Operations ============

async def create_render(
    db: AsyncSession,
    scene_version_id: UUID,
    camera_angle: str,
    quality: str,
    width: int,
    height: int,
    blob_data: bytes,
    render_time_ms: Optional[int] = None,
    expires_in_hours: Optional[int] = None
) -> Render:
    """Create a new render."""
    expires_at = None
    if expires_in_hours:
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)

    render = Render(
        scene_version_id=scene_version_id,
        camera_angle=camera_angle,
        quality=quality,
        width=width,
        height=height,
        blob_data=blob_data,
        render_time_ms=render_time_ms,
        expires_at=expires_at,
    )
    db.add(render)
    await db.flush()
    return render


async def get_render(db: AsyncSession, render_id: UUID) -> Optional[Render]:
    """Get render by ID."""
    result = await db.execute(
        select(Render).where(Render.id == render_id)
    )
    return result.scalar_one_or_none()


async def get_render_by_scene_and_angle(
    db: AsyncSession,
    scene_version_id: UUID,
    camera_angle: str
) -> Optional[Render]:
    """Get render by scene version and camera angle."""
    result = await db.execute(
        select(Render)
        .where(
            Render.scene_version_id == scene_version_id,
            Render.camera_angle == camera_angle
        )
        .order_by(desc(Render.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def cleanup_expired_renders(db: AsyncSession) -> int:
    """Delete expired renders and return count deleted."""
    result = await db.execute(
        delete(Render)
        .where(
            Render.expires_at.is_not(None),
            Render.expires_at < datetime.now()
        )
    )
    return result.rowcount
