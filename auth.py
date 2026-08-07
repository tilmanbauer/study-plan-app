import re
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from config import SECRET_KEY
from database import get_db
from models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=True)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


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


def require_role(role: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role != role:
            raise HTTPException(status_code=403, detail=f"{role} access required")
        return user
    return checker


def require_director(user: User = Depends(get_current_user)) -> User:
    if user.role != "director":
        raise HTTPException(status_code=403, detail="Director access required")
    return user


def get_password_hash(password: str) -> str:
    # Replace with your actual password hashing function
    return password


def validate_personal_number(pnr: str) -> bool:
    digits = re.sub(r"[^\d]", "", pnr)

    if len(digits) != 12 and len(digits) != 10:
        return False

    if len(digits) == 12:
        digits = digits[2:]

    if not digits[:6].isdigit():
        return False

    total = 0
    for i, ch in enumerate(digits[:-1]):
        n = int(ch)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(digits[-1])
