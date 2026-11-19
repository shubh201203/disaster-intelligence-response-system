import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import WebSocket
from app.core.logger import logger

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        payload_str = json.dumps(message)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.error(f"Error sending websocket message: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_event(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any]
    ):
        event_payload = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entity_type": entity_type,
            "entity_id": entity_id,
            "data": data
        }
        await self.broadcast(event_payload)

ws_manager = WebSocketManager()
