import json
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChatRoomMessage

# Prefix /chat ebong normal path duto-i support korbe
router = APIRouter()

# --- Database Helper Functions ---

def save_message(room_code: str, sender: str, content: str, time: str = ""):
    db = SessionLocal()
    try:
        if not time:
            time = datetime.now().strftime("%I:%M %p")
        msg = ChatRoomMessage(
            room_code=str(room_code),
            sender=str(sender),
            content=str(content),
            time=time
        )
        db.add(msg)
        db.commit()
    except Exception as e:
        print(f"Error saving message: {e}")
        db.rollback()
    finally:
        db.close()


def get_room_history(room_code: str):
    db = SessionLocal()
    try:
        messages = db.query(ChatRoomMessage).filter(ChatRoomMessage.room_code == str(room_code)).all()
        return [
            {
                "sender": m.sender,
                "content": m.content,
                "time": m.time
            }
            for m in messages
        ]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []
    finally:
        db.close()


# --- Room Manager ---

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
            if websocket in self.rooms[room_code]:
                self.rooms[room_code].remove(websocket)
            if len(self.rooms[room_code]) == 0:
                del self.rooms[room_code]

    async def broadcast(self, room_code: str, message: dict):
        if room_code in self.rooms:
            for connection in list(self.rooms[room_code]):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(room_code, connection)


manager = RoomConnectionManager()


# --- Main Chat Handler ---

async def handle_chat(websocket: WebSocket, room_code: str, user_name: str):
    await manager.connect(room_code, websocket)

    # 1. Join korar por purono history pathano (Flutter jeta wait korche)
    history = get_room_history(room_code)
    await websocket.send_json({"type": "history", "data": history})

    try:
        while True:
            # 2. Flutter theke message recieve
            data = await websocket.receive_json()

            sender = data.get("sender", user_name)
            content = data.get("content", data.get("message", ""))
            msg_time = data.get("time", datetime.now().strftime("%I:%M %p"))

            # 3. Database-e save
            save_message(room_code, sender, content, msg_time)

            # 4. Flutter expect korche erokom structured JSON broadcast
            broadcast_payload = {
                "type": "message",
                "data": {
                    "sender": sender,
                    "content": content,
                    "time": msg_time
                }
            }
            await manager.broadcast(room_code, broadcast_payload)

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
    except Exception as e:
        print(f"WS Exception: {e}")
        manager.disconnect(room_code, websocket)


# Flutter-e thaka URL /chat/ws/... support
@router.websocket("/chat/ws/{room_code}/{user_name}")
async def ws_with_chat_prefix(websocket: WebSocket, room_code: str, user_name: str):
    await handle_chat(websocket, room_code, user_name)

# Normal /ws/... support
@router.websocket("/ws/{room_code}/{user_name}")
async def ws_without_prefix(websocket: WebSocket, room_code: str, user_name: str):
    await handle_chat(websocket, room_code, user_name)
