from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import ChatRoomMessage
from app.routers import auth, contacts, chat

# Database tables auto create
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Real-Time Messaging Backend")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers Include
app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(chat.router)


@app.get("/")
def root():
    return {"status": "Messaging API is running"}


# Admin Endpoint: View All Room Messages
@app.get("/admin/all-data")
def get_all_data(db: Session = Depends(get_db)):
    messages = db.query(ChatRoomMessage).all()
    return {
        "total_messages": len(messages),
        "messages": [
            {
                "id": m.id,
                "room_code": m.room_code,
                "sender": m.sender,
                "content": m.content,
                "time": m.time,
                "created_at": str(m.created_at),
            }
            for m in messages
        ],
    }


# Room Delete Endpoint: Direct Browser বা Terminal theke delete kora
@app.get("/room/{room_code}/clear")
@app.delete("/room/{room_code}/clear")
def clear_room_messages(room_code: str, db: Session = Depends(get_db)):
    deleted_count = db.query(ChatRoomMessage).filter(ChatRoomMessage.room_code == str(room_code)).delete()
    db.commit()
    return {
        "status": "success",
        "room_code": room_code,
        "deleted_count": deleted_count,
        "message": f"Successfully deleted {deleted_count} messages"
    }
