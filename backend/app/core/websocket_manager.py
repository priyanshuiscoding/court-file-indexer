from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, key: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[key].append(websocket)

    def disconnect(self, key: str, websocket: WebSocket) -> None:
        if key in self.connections and websocket in self.connections[key]:
            self.connections[key].remove(websocket)

    async def broadcast(self, key: str, message: dict) -> None:
        for ws in list(self.connections.get(key, [])):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(key, ws)


ws_manager = ConnectionManager()
