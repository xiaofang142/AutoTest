from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.lib.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
active_connections: dict[str, list[WebSocket]] = {}


@router.websocket("/ws/runs/{run_id}")
async def run_progress_ws(websocket: WebSocket, run_id: str):
    await websocket.accept()
    if run_id not in active_connections:
        active_connections[run_id] = []
    active_connections[run_id].append(websocket)
    logger.info(f"WebSocket connected: run_id={run_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections[run_id].remove(websocket)
        if not active_connections[run_id]:
            del active_connections[run_id]


async def push_run_progress(run_id: str, data: dict):
    if run_id not in active_connections:
        return
    dead = []
    for ws in active_connections[run_id]:
        try:
            await ws.send_json({"type": "run_progress", "data": data})
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections[run_id].remove(ws)


async def push_defect_found(run_id: str, defect: dict):
    if run_id not in active_connections:
        return
    for ws in active_connections[run_id]:
        try:
            await ws.send_json({"type": "defect_found", "data": defect})
        except Exception:
            pass


async def push_run_completed(run_id: str, summary: dict):
    if run_id not in active_connections:
        return
    for ws in active_connections[run_id]:
        try:
            await ws.send_json({"type": "run_completed", "data": summary})
        except Exception:
            pass
