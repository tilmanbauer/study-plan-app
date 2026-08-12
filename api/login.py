import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserOut, TokenOut, UserProfileUpdate
from auth import (
    get_current_user,
    require_role,
    create_access_token,
    verify_password,
    get_password_hash,
)
from config import DIRECTOR_ACCOUNT_SECRET
from utils import validate_personal_number

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    personal_number: str
    admission_term: str


class DirectorCreateRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: str = "student"
    admission_term: str = ""
    director_secret: str


class ProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    personal_number: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class DirectorFlagsUpdate(BaseModel):
    tuition_paying: bool
    registration_complete: bool


def _password_strength(password: str) -> bool:
    if len(password) < 10:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    if not re.search(r"[^A-Za-z0-9]", password):
        return False
    return True


def _validate_role(role: str) -> None:
    if role not in ("student", "director"):
        raise HTTPException(status_code=400, detail="Role must be student or director")


@router.post("/login", response_model=TokenOut)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is closed")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/register", response_model=TokenOut)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if not _password_strength(req.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 10 characters and include uppercase, lowercase, digit, and special character"
        )

    if not validate_personal_number(req.personal_number):
        raise HTTPException(status_code=400, detail="Invalid personal number")

    user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        first_name=req.first_name,
        last_name=req.last_name,
        personal_number=req.personal_number,
        admission_term=req.admission_term,
        role="student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}


@router.post("/director/users", response_model=UserOut)
def director_create_user(
    req: DirectorCreateRequest,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    if not DIRECTOR_ACCOUNT_SECRET:
        raise HTTPException(status_code=403, detail="Director account creation is disabled")
    if req.director_secret != DIRECTOR_ACCOUNT_SECRET:
        raise HTTPException(status_code=403, detail="Invalid director secret")

    _validate_role(req.role)

    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if not _password_strength(req.password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 10 characters and include uppercase, lowercase, digit, and special character"
        )

    user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        first_name=req.first_name,
        last_name=req.last_name,
        role=req.role,
        admission_term=req.admission_term,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


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
    current_user.admission_term = update.admission_term
    db.commit()
    db.refresh(current_user)
    return current_user



@router.post("/me/password")
def change_password(
    req: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.hashed_password or not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if not _password_strength(req.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 10 characters and include uppercase, lowercase, digit, and special character"
        )

    current_user.hashed_password = get_password_hash(req.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
def close_account(
    user_id: int,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "director":
        raise HTTPException(status_code=400, detail="Cannot close director accounts")
    user.is_active = False
    db.commit()
    return {"ok": True}


@router.patch("/users/{user_id}/director-flags", response_model=UserOut)
def update_director_flags(
    user_id: int,
    update: DirectorFlagsUpdate,
    current_user: User = Depends(require_role("director")),
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
