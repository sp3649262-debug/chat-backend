from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import User, Message
from app.routers import auth, contacts, chat

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

# Admin endpoint to view all database records
@app.get("/admin/all-data")
def get_all_data(db: Session = Depends(get_db)):
    users = db.query(User).all()
    messages = db.query(Message).all()
    return {
        "total_users": len(users),
        "users": [
            {
                "id": u.id,
                "phone_number": u.phone_number,
                "display_name": u.display_name,
                "created_at": str(u.created_at)
            }
            for u in users
        ],
        "total_messages": len(messages),
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "content": m.content,
                "status": m.status,
                "timestamp": str(m.timestamp)
            }
            for m in messages
        ]
    }
