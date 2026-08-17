
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Nyimpen semua koneksi WebSocket yang lagi aktif, buat broadcast bareng."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        # kirim ke semua client, kalau ada yang udah putus diem-diem
        # (browser ditutup dll) langsung dibuang dari list
        dead_connections = []
        payload = json.dumps(message, default=str)  # default=str buat handle datetime/enum

        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


manager = ConnectionManager()


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # ga expect client kirim apa-apa, cuma jaga koneksi tetep kebuka
            # sambil nunggu ada broadcast dari simulation.py
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)