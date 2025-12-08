"""
WebSocket endpoint for real-time scene editing updates.
"""
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates.

    Message format:
    Client -> Server:
        {"type": "edit_request", "content": "user prompt"}

    Server -> Client:
        {"type": "status", "status": "processing", "message": "..."}
        {"type": "progress", "step": "generating", "message": "..."}
        {"type": "complete", "renders": {...}, "message": "..."}
        {"type": "error", "error_code": "...", "message": "..."}
    """
    await manager.connect(session_id, websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                if message.get("type") == "edit_request":
                    # Send acknowledgment
                    await manager.send_message(session_id, {
                        "type": "status",
                        "status": "processing",
                        "message": "Processing your request..."
                    })

                    # To integrate with agent streaming...
                    # For now, send simple response
                    await manager.send_message(session_id, {
                        "type": "status",
                        "status": "complete",
                        "message": "Edit processing started. Check REST API for results."
                    })

                elif message.get("type") == "ping":
                    # Heartbeat
                    await manager.send_message(session_id, {
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    })

                else:
                    # Unknown message type
                    await manager.send_message(session_id, {
                        "type": "error",
                        "error_code": "UNKNOWN_MESSAGE_TYPE",
                        "message": f"Unknown message type: {message.get('type')}"
                    })

            except json.JSONDecodeError:
                await manager.send_message(session_id, {
                    "type": "error",
                    "error_code": "INVALID_JSON",
                    "message": "Invalid JSON format"
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}")
        manager.disconnect(session_id)
