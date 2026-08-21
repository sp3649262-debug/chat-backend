import json
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChatRoomMessage

router = APIRouter()

# --- Database Helper Functions ---

def save_message(room_code: str, sender: str, content: str, time: str = ""):
    """Room-er message database-e save kora"""
    db = SessionLocal()
    try:
        if not time:
            time = datetime.now().strftime("%I:%M %p")
        msg = ChatRoomMessage(
            room_code=room_code,
            sender=sender,
            content=content,
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
    """Purono chat history database theke fetch kora"""
    db = SessionLocal()
    try:
        messages = db.query(ChatRoomMessage).filter(ChatRoomMessage.room_code == room_code).all()
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


# --- WebSocket Room Connection Manager ---

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

    async def broadcast(self, room_code: str, message: str):
        if room_code in self.rooms:
            for connection in self.rooms[room_code]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"Error broadcasting message: {e}")


manager = RoomConnectionManager()


# --- WebSocket Endpoint ---

@router.websocket("/ws/{room_code}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_name: str):
    await manager.connect(room_code, websocket)

    try:
        while True:
            # 1. Frontend theke text/json data receive kora
            raw_text = await websocket.receive_text()

            sender_name = user_name
            msg_content = raw_text
            msg_time = datetime.now().strftime("%I:%M %p")

            # 2. JSON kina check kora
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    sender_name = parsed.get("sender", user_name)
                    msg_content = parsed.get("content", parsed.get("message", raw_text))
                    msg_time = parsed.get("time", msg_time)
            except Exception:
                pass

            # 3. Database-e save kora
            save_message(
                room_code=room_code,
                sender=sender_name,
                content=msg_content,
                time=msg_time
            )

            # 4. Frontend-e message broadcast kora
            await manager.broadcast(room_code, raw_text)

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
