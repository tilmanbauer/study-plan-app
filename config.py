import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./studyplan.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET")
OIDC_DISCOVERY_URL = os.getenv("OIDC_DISCOVERY_URL")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI")
