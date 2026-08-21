import sqlite3
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List

router = APIRouter(prefix="/chat", tags=["Chat"])

# SQLite Database Initialization
DB_FILE = "chat_history.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT,
                sender TEXT,
                content TEXT,
                time TEXT
            )
        """)
        conn.commit()

init_db()

def save_message(room_code: str, sender: str, content: str, time: str):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO messages (room_code, sender, content, time) VALUES (?, ?, ?, ?)",
            (room_code, sender, content, time)
        )
        conn.commit()

def get_room_history(room_code: str) -> List[dict]:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sender, content, time FROM messages WHERE room_code = ? ORDER BY id ASC",
            (room_code,)
        )
        rows = cursor.fetchall()
        return [{"sender": r[0], "content": r[1], "time": r[2]} for r in rows]

class RoomConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.rooms:
            self.rooms[room_code] = []
        self.rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.rooms:
            self.rooms[room_code].remove(websocket)
            if not self.rooms[room_code]:
                del self.rooms[room_code]

    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.rooms:
            for connection in self.rooms[room_code]:
                await connection.send_json(message)

manager = RoomConnectionManager()

@router.websocket("/ws/{room_code}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_name: str):
    await manager.connect(room_code, websocket)
    
    # 1. Connect holei purono messages pathiye dao
    history = get_room_history(room_code)
    await websocket.send_json({"type": "history", "data": history})
    
    try:
        while True:
            data = await websocket.receive_json()
            # 2. Notun message database-e save koro
            save_message(
                room_code=room_code,
                sender=data.get('sender', user_name),
                content=data.get('content', ''),
                time=data.get('time', '')
            )
            # 3. Live broadcast koro
            await manager.broadcast(room_code, {"type": "message", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)