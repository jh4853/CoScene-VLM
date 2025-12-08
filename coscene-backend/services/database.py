"""
SQLAlchemy ORM models and database session management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    LargeBinary,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from api.config import get_settings

settings = get_settings()

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for ORM models
Base = declarative_base()


# ============ ORM Models ============

class Session(Base):
    """User editing session."""
    __tablename__ = "sessions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    last_active_at = Column(DateTime, default=func.now(), nullable=False)
    status = Column(
        String(20),
        default="active",
        nullable=False,
        index=True,
    )
    extra_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    scene_versions = relationship("SceneVersion", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('active', 'suspended', 'completed')"),
    )


class Message(Base):
    """Conversation message."""
    __tablename__ = "messages"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session", "session_id", "timestamp"),
        CheckConstraint("role IN ('user', 'assistant', 'system')"),
    )


class SceneVersion(Base):
    """Scene version with USD content."""
    __tablename__ = "scene_versions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    parent_version_id = Column(PGUUID(as_uuid=True), ForeignKey("scene_versions.id", ondelete="SET NULL"))
    usd_content = Column(Text, nullable=False)
    created_by_message_id = Column(PGUUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"))
    checksum = Column(String(64))
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="scene_versions")
    renders = relationship("Render", back_populates="scene_version", cascade="all, delete-orphan")
    parent_version = relationship("SceneVersion", remote_side=[id])

    __table_args__ = (
        Index("idx_scene_versions_session", "session_id", "version_number"),
        Index("idx_scene_versions_checksum", "checksum"),
    )


class Render(Base):
    """Rendered image."""
    __tablename__ = "renders"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    scene_version_id = Column(PGUUID(as_uuid=True), ForeignKey("scene_versions.id", ondelete="CASCADE"), nullable=False)
    camera_angle = Column(String(50), nullable=False)
    quality = Column(String(20), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    blob_data = Column(LargeBinary, nullable=False)
    render_time_ms = Column(Integer)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime)

    # Relationships
    scene_version = relationship("SceneVersion", back_populates="renders")

    __table_args__ = (
        Index("idx_renders_scene", "scene_version_id", "camera_angle"),
        Index("idx_renders_expires", "expires_at"),
        CheckConstraint("quality IN ('preview', 'verification', 'final')"),
    )


# ============ Database Dependency ============

async def get_db() -> AsyncSession:
    """
    Dependency that provides an async database session.
    Use with FastAPI Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============ Database Initialization ============

async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """Drop all tables (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
