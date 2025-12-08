"""
Pydantic models for API requests and responses.
"""
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field


# ============ Session Models ============

class SessionCreate(BaseModel):
    """Request to create a new editing session."""
    user_id: UUID
    initial_scene: Optional[str] = Field(
        None, description="Optional initial USD scene content")
    extra_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SessionResponse(BaseModel):
    """Response containing session details."""
    id: UUID
    user_id: UUID
    status: Literal["active", "suspended", "completed"]
    started_at: datetime
    last_active_at: datetime
    extra_metadata: Dict[str, Any]

    class Config:
        from_attributes = True


# ============ Message Models ============

class MessageCreate(BaseModel):
    """Request to send a message in a session."""
    content: str = Field(..., min_length=1, max_length=5000)
    role: Literal["user", "assistant", "system"] = "user"


class MessageResponse(BaseModel):
    """Response containing message details."""
    id: UUID
    session_id: UUID
    role: str
    content: str
    timestamp: datetime
    extra_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ============ Scene Edit Models ============

class SceneEditRequest(BaseModel):
    """Request to edit a scene using natural language."""
    prompt: str = Field(..., min_length=1, max_length=1000,
                        description="Natural language edit instruction")
    session_id: UUID


class SceneEditResponse(BaseModel):
    """Response after processing a scene edit."""
    session_id: UUID
    version_number: int
    renders: Dict[str, UUID] = Field(
        description="Map of camera_angle -> render_id")
    message: str
    status: Literal["success", "partial_success", "failed"]
    usd_content: Optional[str] = None


# ============ Scene Version Models ============

class SceneVersionResponse(BaseModel):
    """Response containing scene version details."""
    id: UUID
    session_id: UUID
    version_number: int
    parent_version_id: Optional[UUID]
    usd_content: str
    created_at: datetime
    checksum: Optional[str]

    class Config:
        from_attributes = True


class SceneVersionListResponse(BaseModel):
    """Response containing list of scene versions."""
    versions: list[SceneVersionResponse]
    total: int


# ============ Render Models ============

class RenderRequest(BaseModel):
    """Request to render a scene."""
    scene_version_id: UUID
    camera_angle: str = "perspective"
    quality: Literal["preview", "verification", "final"] = "preview"


class RenderResponse(BaseModel):
    """Response containing render details (without blob data)."""
    id: UUID
    scene_version_id: UUID
    camera_angle: str
    quality: str
    width: int
    height: int
    render_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ WebSocket Models ============

class WSMessage(BaseModel):
    """WebSocket message structure."""
    type: Literal["edit_request", "status", "progress",
                  "usd_generated", "frames_rendered", "complete", "error"]
    data: Dict[str, Any] = Field(default_factory=dict)


class EditRequestWS(BaseModel):
    """WebSocket edit request payload."""
    type: Literal["edit_request"] = "edit_request"
    content: str


class StatusUpdateWS(BaseModel):
    """WebSocket status update payload."""
    type: Literal["status"] = "status"
    status: Literal["processing", "complete", "failed"]
    message: Optional[str] = None


class ProgressUpdateWS(BaseModel):
    """WebSocket progress update payload."""
    type: Literal["progress"] = "progress"
    step: str
    message: str


class USDGeneratedWS(BaseModel):
    """WebSocket USD generation complete payload."""
    type: Literal["usd_generated"] = "usd_generated"
    usd_patch: str


class FramesRenderedWS(BaseModel):
    """WebSocket frames rendered payload."""
    type: Literal["frames_rendered"] = "frames_rendered"
    frames: Dict[str, UUID]  # camera_angle -> render_id


class CompleteWS(BaseModel):
    """WebSocket edit complete payload."""
    type: Literal["complete"] = "complete"
    renders: Dict[str, UUID]
    message: str
    version_number: int


class ErrorWS(BaseModel):
    """WebSocket error payload."""
    type: Literal["error"] = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============ Health Check Models ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime
    checks: Dict[str, bool] = Field(default_factory=dict)


# ============ Agent State Models (for LangGraph) ============

class SceneEditState(BaseModel):
    """State passed through LangGraph nodes."""
    session_id: str
    user_prompt: str
    current_usd: str
    rendered_frames: list[UUID] = Field(default_factory=list)
    status: str = "pending"
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
