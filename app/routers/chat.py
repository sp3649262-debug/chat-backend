import json
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChatRoomMessage

router = APIRouter()

# --- Database Saver ---
def save_message_to_db(room_code: str, sender: str, content: str, time_str: str = ""):
    try:
        db = SessionLocal()
        if not time_str:
            time_str = datetime.now().strftime("%I:%M %p")
        msg = ChatRoomMessage(
            room_code=str(room_code),
            sender=str(sender),
            content=str(content),
            time=time_str
        )
        db.add(msg)
        db.commit()
        db.close()
    except Exception as e:
        print(f"DB Save Error: {e}")

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.rooms:
            self.rooms[room_code] = []
        self.rooms[room_code].append(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.rooms and websocket in self.rooms[room_code]:
            self.rooms[room_code].remove(websocket)
            if not self.rooms[room_code]:
                del self.rooms[room_code]

    async def broadcast(self, room_code: str, message: str):
        if room_code in self.rooms:
            for connection in list(self.rooms[room_code]):
                try:
                    await connection.send_text(message)
                except Exception:
                    self.disconnect(room_code, connection)

manager = ConnectionManager()

async def handle_chat_session(websocket: WebSocket, room_code: str, default_user: str):
    await manager.connect(room_code, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            sender = default_user
            content = data
            msg_time = datetime.now().strftime("%I:%M %p")
            
            # Extract content if JSON
            try:
                payload = json.loads(data)
                if isinstance(payload, dict):
                    sender = payload.get("sender") or payload.get("user") or payload.get("name") or default_user
                    content = payload.get("content") or payload.get("message") or payload.get("text") or data
                    msg_time = payload.get("time") or msg_time
            except Exception:
                pass

            # 1. Broadcast immediately to all users in the room
            await manager.broadcast(room_code, data)

            # 2. Save in database
            save_message_to_db(room_code, sender, content, msg_time)

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(room_code, websocket)

# Support both URL structures (with or without username parameter)
@router.websocket("/ws/{room_code}")
async def ws_single(websocket: WebSocket, room_code: str):
    await handle_chat_session(websocket, room_code, "Anonymous")

@router.websocket("/ws/{room_code}/{user_name}")
async def ws_double(websocket: WebSocket, room_code: str, user_name: str):
    await handle_chat_session(websocket, room_code, user_name)
