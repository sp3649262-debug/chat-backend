from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User
from app.schemas import SendOTPRequest, VerifyOTPRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

SECRET_KEY = "SUPER_SECRET_CHAT_KEY_CHANGE_THIS"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

otp_store: dict[str, str] = {}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/send-otp")
def send_otp(request: SendOTPRequest):
    otp = "123456"
    otp_store[request.phone_number] = otp
    return {"message": "OTP sent successfully", "test_otp": otp}

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(request: VerifyOTPRequest, db: Session = Depends(get_db)):
    stored_otp = otp_store.get(request.phone_number)
    
    if not stored_otp or stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid or expired OTP"
        )

    user = db.query(User).filter(User.phone_number == request.phone_number).first()
    if not user:
        user = User(phone_number=request.phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)

    otp_store.pop(request.phone_number, None)

    token = create_access_token({"sub": str(user.id), "phone": user.phone_number})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "phone_number": user.phone_number
    }