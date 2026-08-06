from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from pydantic import BaseModel
from database import get_db
from models import User
from schemas import TokenOut, UserOut
from auth import authenticate_user, create_access_token, get_current_user
from config import ENABLE_TEST_LOGIN

router = APIRouter(prefix="/auth", tags=["auth"])

TEST_ACCOUNTS = {
    "student1@example.com": {"name": "Test Student 1", "role": "student"},
    "student2@example.com": {"name": "Test Student 2", "role": "student"},
    "student3@example.com": {"name": "Test Student 3", "role": "student"},
    "director@example.com": {"name": "Test Director", "role": "director"},
}

class TestLoginRequest(BaseModel):
    email: str

@router.get("/test-login-enabled")
def test_login_enabled():
    return {"enabled": ENABLE_TEST_LOGIN}

@router.post("/test-login")
def test_login(req: TestLoginRequest, db: Session = Depends(get_db)):
    if not ENABLE_TEST_LOGIN:
        raise HTTPException(status_code=403, detail="Test login disabled")

    info = TEST_ACCOUNTS.get(req.email)
    if not info:
        raise HTTPException(status_code=400, detail="Unknown test account")

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        user = User(email=req.email, name=info["name"], role=info["role"])
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
    
@router.post("/token", response_model=TokenOut)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
