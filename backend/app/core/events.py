from app.core.websocket_manager import ws_manager


async def broadcast_document_status(document_id: int, payload: dict) -> None:
    key = f"document:{document_id}"
    await ws_manager.broadcast(key, payload)
