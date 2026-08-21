import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.database import Base

class ChatRoomMessage(Base):
    __tablename__ = "room_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_code = Column(String, index=True, nullable=False)
    sender = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    time = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
