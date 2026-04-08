from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/documents/{document_id}")
async def document_ws(websocket: WebSocket, document_id: int):
    key = f"document:{document_id}"
    await ws_manager.connect(key, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(key, websocket)
