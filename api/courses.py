from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import csv
import io

from database import get_db
from models import Course, User
from schemas import CourseCreate, CourseOut
from auth import require_role

router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=List[CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).all()


@router.post("/admin/courses", response_model=CourseOut)
def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("director")),
):
    existing = db.query(Course).filter(
        Course.code == course.code,
        Course.term == course.term,
        Course.university == course.university,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Course already exists for this term and university"
        )

    db_course = Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.delete("/admin/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("director")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    db.delete(course)
    db.commit()
    return {"ok": True}


@router.post("/admin/courses/import", response_model=List[CourseOut])
def import_courses_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("director")),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    content = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    required = {"code", "title", "credits", "term", "university"}
    if not required.issubset(reader.fieldnames or []):
        raise HTTPException(
            status_code=400, detail=f"CSV must contain columns: {required}"
        )

    imported = []
    for row in reader:
        code = row["code"].strip()
        title = row["title"].strip()
        try:
            credits = float(row["credits"])
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid credits for {code}")
        term = row["term"].strip()
        university = row["university"].strip()

        existing = db.query(Course).filter(
            Course.code == code,
            Course.term == term,
            Course.university == university,
        ).first()
        if existing:
            existing.title = title
            existing.credits = credits
            imported.append(existing)
        else:
            course = Course(
                code=code, title=title, credits=credits, term=term, university=university
            )
            db.add(course)
            db.flush()
            imported.append(course)

    db.commit()
    return imported
