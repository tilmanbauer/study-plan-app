from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserOut
from auth import get_current_user, create_access_token, require_director, require_role, validate_personal_number
from config import ENABLE_TEST_LOGIN

router = APIRouter(prefix="/auth", tags=["auth"])

TEST_ACCOUNTS = {
    "student1@example.com": {"first_name": "Test", "last_name": "Student 1", "role": "student"},
    "student2@example.com": {"first_name": "Test", "last_name": "Student 2", "role": "student"},
    "student3@example.com": {"first_name": "Test", "last_name": "Student 3", "role": "student"},
    "director@example.com": {"first_name": "Test", "last_name": "Director", "role": "director"},
}


class TestLoginRequest(BaseModel):
    email: str


class UserProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    personal_number: str


class DirectorFlagsUpdate(BaseModel):
    tuition_paying: bool
    registration_complete: bool


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
        user = User(
            email=req.email,
            first_name=info["first_name"],
            last_name=info["last_name"],
            role=info["role"],
        )
        db.add(user)
    else:
        user.first_name = info["first_name"]
        user.last_name = info["last_name"]
        user.role = info["role"]
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/complete")
def profile_complete(current_user: User = Depends(get_current_user)):
    missing = []
    if not current_user.first_name:
        missing.append("first_name")
    if not current_user.last_name:
        missing.append("last_name")
    if not current_user.personal_number:
        missing.append("personal_number")
    return {"complete": len(missing) == 0, "missing": missing}


@router.patch("/me", response_model=UserOut)
def update_profile(
    update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update this profile")

    if not validate_personal_number(update.personal_number):
        raise HTTPException(status_code=400, detail="Invalid personal number")

    current_user.first_name = update.first_name
    current_user.last_name = update.last_name
    current_user.personal_number = update.personal_number
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/users/{user_id}/director-flags", response_model=UserOut)
def get_director_flags(
    user_id: int,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/users/{user_id}/director-flags", response_model=UserOut)
def update_director_flags(
    user_id: int,
    update: DirectorFlagsUpdate,
    current_user: User = Depends(require_director),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.tuition_paying = update.tuition_paying
    user.registration_complete = update.registration_complete
    db.commit()
    db.refresh(user)
    return user
