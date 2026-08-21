from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from app.database import get_db
from app.models import User
from app.schemas import ContactSyncRequest, UserResponse
from app.routers.auth import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/contacts", tags=["Contacts"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/verify-otp")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/sync", response_model=list[UserResponse])
def sync_contacts(
    request: ContactSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Registered users khuje ber kora, current user-ke exclude rekhe
    matched_users = db.query(User).filter(
        User.phone_number.in_(request.phone_numbers),
        User.id != current_user.id
    ).all()
    
    return matched_users