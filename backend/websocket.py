"""
WebSocket Manager — Real-time event broadcasting.
"""
import json
import asyncio
from fastapi import WebSocket
from typing import Set


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events to all clients."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    async def broadcast(self, event: str, data: dict):
        """Broadcast an event to all connected clients."""
        message = json.dumps({"event": event, "data": data}, default=str)
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    def broadcast_sync(self, event: str, data: dict):
        """Synchronous wrapper for broadcasting (for use from threads)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast(event, data), loop
                )
            else:
                loop.run_until_complete(self.broadcast(event, data))
        except RuntimeError:
            # No event loop available — skip broadcast
            pass


# Global singleton
ws_manager = WebSocketManager()
