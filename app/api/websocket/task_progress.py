"""Task-level WebSocket event broadcasting for real-time progress."""
from fastapi import WebSocket
from app.lib.logger import get_logger

logger = get_logger(__name__)


class TaskWebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, ws: WebSocket):
        await ws.accept()
        if task_id not in self._connections:
            self._connections[task_id] = []
        self._connections[task_id].append(ws)
        logger.debug("WS connected: task=%s total=%d", task_id, len(self._connections[task_id]))

    def disconnect(self, task_id: str, ws: WebSocket):
        if task_id in self._connections:
            self._connections[task_id] = [c for c in self._connections[task_id] if c != ws]
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast(self, task_id: str, event: dict):
        for ws in self._connections.get(task_id, []):
            try:
                await ws.send_json(event)
            except Exception:
                pass

    async def broadcast_stage_change(self, task_id: str, stage: str, status: str, percent: int, summary: str = ""):
        await self.broadcast(task_id, {
            "type": "task_stage_change",
            "data": {"task_id": task_id, "stage": stage, "status": status, "percent": percent, "summary": summary},
        })

    async def broadcast_defect_found(self, task_id: str, defect_id: str, severity: str, title: str):
        await self.broadcast(task_id, {
            "type": "task_defect_found",
            "data": {"task_id": task_id, "defect_id": defect_id, "severity": severity, "title": title},
        })

    async def broadcast_completed(self, task_id: str, status: str, defect_count: int):
        await self.broadcast(task_id, {
            "type": "task_completed",
            "data": {"task_id": task_id, "status": status, "defect_count": defect_count},
        })

    async def broadcast_error(self, task_id: str, error: str):
        await self.broadcast(task_id, {
            "type": "task_error",
            "data": {"task_id": task_id, "error": error},
        })


task_ws_manager = TaskWebSocketManager()
