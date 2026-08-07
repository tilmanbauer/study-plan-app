from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth

from database import get_db
from models import User
from auth import create_access_token
from config import (
    OIDC_CLIENT_ID,
    OIDC_CLIENT_SECRET,
    OIDC_DISCOVERY_URL,
    OIDC_REDIRECT_URI,
    DIRECTOR_EMAILS,
)

router = APIRouter(prefix="/auth/oidc", tags=["auth"])

oauth = OAuth()

if OIDC_DISCOVERY_URL and OIDC_CLIENT_ID and OIDC_CLIENT_SECRET:
    oauth.register(
        name="university",
        client_id=OIDC_CLIENT_ID,
        client_secret=OIDC_CLIENT_SECRET,
        server_metadata_url=OIDC_DISCOVERY_URL,
        client_kwargs={"scope": "openid email profile"},
    )


def _ensure_oidc_configured() -> None:
    if "university" not in oauth._clients:
        raise HTTPException(status_code=501, detail="OIDC not configured")


@router.get("/login")
async def oidc_login(request: Request):
    _ensure_oidc_configured()
    redirect_uri = OIDC_REDIRECT_URI or str(request.url_for("oidc_callback"))
    return await oauth.university.authorize_redirect(request, redirect_uri)


@router.get("/callback", name="oidc_callback")
async def oidc_callback(request: Request, db: Session = Depends(get_db)):
    _ensure_oidc_configured()

    token = await oauth.university.authorize_access_token(request)
    userinfo = token.get("userinfo")

    if not userinfo:
        raise HTTPException(status_code=400, detail="OIDC userinfo missing")

    email = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="OIDC email missing")

    role = "director" if email in DIRECTOR_EMAILS else "student"

    full_name = userinfo.get("name", email)
    parts = full_name.split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        db.add(user)
    else:
        if not user.first_name:
            user.first_name = first_name
        if not user.last_name:
            user.last_name = last_name
        user.role = role
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "user": user}
