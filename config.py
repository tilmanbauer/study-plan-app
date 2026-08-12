import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/studyplan.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL")
OIDC_REDIRECT_URI = os.getenv(
    "OIDC_REDIRECT_URI",
    "https://study-planner-math.app.cloud.cbh.kth.se/auth/oidc/callback",
)

DIRECTOR_EMAILS = [
    email.strip()
    for email in os.getenv("DIRECTOR_EMAILS", "").split(",")
    if email.strip()
]

ENABLE_TEST_LOGIN = os.getenv("ENABLE_TEST_LOGIN", "false").lower() == "true"
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() in ("true", "1", "yes")

# Director secret for creating accounts without personal number validation
DIRECTOR_ACCOUNT_SECRET = os.getenv("DIRECTOR_ACCOUNT_SECRET", "")