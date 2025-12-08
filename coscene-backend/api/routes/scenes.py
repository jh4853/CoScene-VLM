"""
Scene editing API routes.
Integrates with LangGraph agent for scene modifications.
"""
import os
import shutil
import tempfile
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    SceneEditRequest,
    SceneEditResponse,
    SceneVersionResponse,
    RenderResponse
)
from services.database import get_db
from services import storage
from services.render_service import get_render_service
from agents.scene_editor import process_scene_edit

try:
    from usd2gltf import convert_usd_to_gltf
except ImportError:
    convert_usd_to_gltf = None

router = APIRouter()


@router.post("/{session_id}/edit", response_model=SceneEditResponse)
async def edit_scene(
    session_id: UUID,
    request: SceneEditRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a scene edit request using the LangGraph agent.

    Flow:
    1. Get current scene USD
    2. Run agent workflow (parse → generate → render)
    3. Save new scene version
    4. Save renders
    5. Save user and assistant messages
    6. Return response
    """
    # Verify session exists
    session = await storage.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Update session activity
    await storage.update_session_activity(db, session_id)

    # Get current scene
    latest_version = await storage.get_latest_scene_version(db, session_id)
    current_usd = latest_version.usd_content if latest_version else ""

    # Save user message
    user_message = await storage.create_message(
        db=db,
        session_id=session_id,
        role="user",
        content=request.prompt
    )
    await db.flush()

    # Process edit with agent
    try:
        agent_result = await process_scene_edit(
            session_id=str(session_id),
            user_prompt=request.prompt,
            current_usd=current_usd
        )

        if agent_result["status"] != "success":
            # Agent failed
            error_msg = agent_result.get("error_message", "Unknown error")

            # Save error message
            await storage.create_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=f"I encountered an error: {error_msg}"
            )
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scene editing failed: {error_msg}"
            )

        # Additional validation: check if USD was actually generated
        if not agent_result.get("generated_usd") or agent_result["generated_usd"].strip() == "":
            error_msg = agent_result.get(
                "error_message") or "Failed to generate USD scene (empty result)"

            # Save error message
            await storage.create_message(
                db=db,
                session_id=session_id,
                role="assistant",
                content=f"I encountered an error: {error_msg}"
            )
            await db.commit()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Scene editing failed: {error_msg}"
            )

        # Save new scene version
        new_version = await storage.create_scene_version(
            db=db,
            session_id=session_id,
            usd_content=agent_result["generated_usd"],
            parent_version_id=latest_version.id if latest_version else None,
            created_by_message_id=user_message.id
        )
        await db.flush()

        # Save renders from agent state
        render_ids = {}
        if agent_result["status"] == "success":
            try:
                # Read renders from agent state (already rendered by render_output_node)
                output_renders = agent_result.get("output_scene_renders", {})

                for camera_angle, image_bytes in output_renders.items():
                    # Get image dimensions (PNG header parsing)
                    width = int.from_bytes(image_bytes[16:20], 'big')
                    height = int.from_bytes(image_bytes[20:24], 'big')

                    render_obj = await storage.create_render(
                        db=db,
                        scene_version_id=new_version.id,
                        camera_angle=camera_angle,
                        quality="preview",
                        width=width,
                        height=height,
                        blob_data=image_bytes,
                        render_time_ms=-1,  # Not tracked in simplified state
                        expires_in_hours=24  # Preview renders expire
                    )
                    render_ids[camera_angle] = render_obj.id

            except Exception as e:
                # Failed to save renders but USD was generated
                print(f"Failed to save renders: {e}")

        # Save assistant message
        await storage.create_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=f"Scene updated successfully. Version {new_version.version_number} created."
        )

        await db.commit()

        return SceneEditResponse(
            session_id=session_id,
            version_number=new_version.version_number,
            renders=render_ids,
            message="Scene updated successfully",
            status="success",
            usd_content=agent_result["generated_usd"]
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/{session_id}/scene", response_class=Response)
async def get_current_scene(
    session_id: UUID,
    format: str = "usd",
    db: AsyncSession = Depends(get_db)
):
    """
    Download current scene USD.
    """
    session = await storage.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    latest_version = await storage.get_latest_scene_version(db, session_id)
    if not latest_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scene versions found"
        )

    if format == "usd":
        return Response(
            content=latest_version.usd_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename=scene_v{latest_version.version_number}.usda"
            }
        )
    elif format == "gltf":
        # Check if usd2gltf is available
        if convert_usd_to_gltf is None:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="GLTF conversion not available. Please install usd2gltf library."
            )

        # Convert USD to GLTF using temporary files
        temp_dir = None
        try:
            # Create temporary directory for conversion
            temp_dir = tempfile.mkdtemp()
            usd_file_path = os.path.join(temp_dir, "scene.usda")
            gltf_file_path = os.path.join(temp_dir, "scene.gltf")

            # Write USD content to temporary file
            with open(usd_file_path, 'w') as f:
                f.write(latest_version.usd_content)

            # Convert USD to GLTF
            convert_usd_to_gltf(usd_file_path, gltf_file_path)

            # Read GLTF content
            with open(gltf_file_path, 'r') as f:
                gltf_content = f.read()

            return Response(
                content=gltf_content,
                media_type="model/gltf+json",
                headers={
                    "Content-Disposition": f"attachment; filename=scene_v{latest_version.version_number}.gltf"
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"GLTF conversion failed: {str(e)}"
            )
        finally:
            # Clean up temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
    else:
        # JSON format
        return SceneVersionResponse.model_validate(latest_version)


@router.get("/renders/{render_id}", response_class=Response)
async def get_render(
    render_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get rendered image by ID.
    Returns PNG image data.
    """
    render = await storage.get_render(db, render_id)

    if not render:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Render not found"
        )

    return Response(
        content=render.blob_data,
        media_type="image/png",
        headers={
            "Content-Disposition": f"inline; filename=render_{render_id}.png"
        }
    )
