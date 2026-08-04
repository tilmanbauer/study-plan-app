import os
from sqlalchemy.orm import Session
from database import engine, Base
from models import User, Course
from auth import get_password_hash

DB_FILE = "study_plans.db"

if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = Session(bind=engine)

DEMO_USERS = [
    {"email": "student@university.edu", "name": "Student Demo", "password": "student", "role": "student"},
    {"email": "director@university.edu", "name": "Director Demo", "password": "director", "role": "director"},
]

DEMO_COURSES = [
    {"code": "DD2350", "title": "Algorithms, Data Structures and Complexity", "credits": 7.5, "term": "Fall 2026", "university": "KTH"},
    {"code": "SF1935", "title": "Probability Theory and Statistics", "credits": 7.5, "term": "Fall 2026", "university": "KTH"},
    {"code": "MM2001", "title": "Mechanics", "credits": 7.5, "term": "Spring 2027", "university": "SU"},
]


def seed_users(db: Session) -> None:
    for u in DEMO_USERS:
        db.add(User(
            email=u["email"],
            name=u["name"],
            hashed_password=get_password_hash(u["password"]),
            role=u["role"],
        ))


def seed_courses(db: Session) -> None:
    for c in DEMO_COURSES:
        if not db.query(Course).filter(
            Course.code == c["code"],
            Course.term == c["term"],
            Course.university == c["university"],
        ).first():
            db.add(Course(**c))


seed_users(db)
seed_courses(db)
db.commit()
db.close()
