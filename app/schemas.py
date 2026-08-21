from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SendOTPRequest(BaseModel):
    phone_number: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    phone_number: str

class UserResponse(BaseModel):
    id: int
    phone_number: str
    display_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ContactSyncRequest(BaseModel):
    phone_numbers: list[str]