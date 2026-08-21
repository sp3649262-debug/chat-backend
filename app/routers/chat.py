from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChatRoomMessage

router = APIRouter()

# --- Database Helper Functions ---

def save_message(room_code: str, sender: str, content: str, time: str = ""):
    """Room er protiti message database-e save kora"""
    db = SessionLocal()
    try:
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
    """Purono chat history fetch kora"""
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
        # Room code onujayi active websocket connection list
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
            for connection in self.rooms[room_code]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting message: {e}")


manager = RoomConnectionManager()


# --- WebSocket Endpoint ---

@router.websocket("/ws/{room_code}/{user_name}")
async def websocket_endpoint(websocket: WebSocket, room_code: str, user_name: str):
    await manager.connect(room_code, websocket)

    # 1. User join korar shathe shathe purono chat history pathano
    history = get_room_history(room_code)
    await websocket.send_json({"type": "history", "data": history})

    try:
        while True:
            # 2. Frontend theke notun message receive kora
            data = await websocket.receive_json()

            # 3. Notun message database-e save kora
            save_message(
                room_code=room_code,
                sender=data.get("sender", user_name),
                content=data.get("content", ""),
                time=data.get("time", "")
            )

            # 4. Room-er shob connected users-er kache broadcast kora
            await manager.broadcast(room_code, {"type": "message", "data": data})

    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
