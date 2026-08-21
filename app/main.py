from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, contacts, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Real-Time Messaging Backend")

# Browser theke sob request allow korar jonno CORS add kora holo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(contacts.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"status": "Messaging API is running"}