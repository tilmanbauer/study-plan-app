from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from database import Base, engine
from email_service import send_director_daily_summary
from api import plans, courses, login
from auth_oidc import router as oidc_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(login.router)
app.include_router(plans.router)
app.include_router(courses.router)
app.include_router(oidc_router)


@app.get("/")
def root():
    return FileResponse("static/index.html")


scheduler = BackgroundScheduler()
scheduler.add_job(send_director_daily_summary, "cron", hour=8, minute=0)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
