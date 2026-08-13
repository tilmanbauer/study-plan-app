from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import StudyPlan, StudyPlanVersion, StudyPlanItem, Comment, User
from schemas import (
    StudyPlanCreate,
    StudyPlanUpdate,
    StudyPlanOut,
    StudyPlanVersionWithDiff,
    CommentOut,
    CommentCreate,
    DecisionRequest,
)
from auth import get_current_user, require_role
from email_service import notify_student, queue_director_notification
import csv
import io

router = APIRouter(prefix="/plans", tags=["plans"])


def _course_key(item: StudyPlanItem) -> str:
    if item.course_id and item.course:
        return f"{item.course.code}: {item.course.title}"
    return f"{item.custom_code or '(custom)'}: {item.custom_title or ''}"


def _diff_versions(prev_items, curr_items) -> str:
    prev = {_course_key(i) for i in prev_items}
    curr = {_course_key(i) for i in curr_items}
    added = sorted(curr - prev)
    removed = sorted(prev - curr)
    parts = []
    if added:
        parts.append("Added: " + ", ".join(added))
    if removed:
        parts.append("Removed: " + ", ".join(removed))
    if not parts:
        return "No course changes."
    return "; ".join(parts)


def _get_plan_or_404(db: Session, plan_id: int) -> StudyPlan:
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _authorize_plan(plan: StudyPlan, current_user):
    if current_user.role == "student" and plan.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.get("", response_model=List[StudyPlanOut])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == "director":
        return db.query(StudyPlan).all()
    return db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).all()


@router.post("", response_model=StudyPlanOut)
def create_plan(
    plan: StudyPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("student")),
):
    existing = db.query(StudyPlan).filter(StudyPlan.student_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a study plan")

    db_plan = StudyPlan(
    student_id=current_user.id,
    title=plan.title,
    )

    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)

    version = StudyPlanVersion(plan_id=db_plan.id, version_number=1)
    db.add(version)
    db.commit()
    db.refresh(version)

    for item in plan.items:
        db.add(StudyPlanItem(
            version_id=version.id,
            term=item.term,
            course_id=item.course_id,
            custom_code=item.custom_code,
            custom_title=item.custom_title,
            credits=item.credits,
        ))

    db.commit()
    db.refresh(db_plan)
    return db_plan


@router.get("/{plan_id}", response_model=StudyPlanOut)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    _authorize_plan(plan, current_user)
    return plan


@router.get("/{plan_id}/versions/{version_number}", response_model=StudyPlanVersionWithDiff)
def get_version(
    plan_id: int,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    _authorize_plan(plan, current_user)

    version = (
        db.query(StudyPlanVersion)
        .filter(
            StudyPlanVersion.plan_id == plan_id,
            StudyPlanVersion.version_number == version_number,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    prev_version = (
        db.query(StudyPlanVersion)
        .filter(
            StudyPlanVersion.plan_id == plan_id,
            StudyPlanVersion.version_number < version_number,
        )
        .order_by(StudyPlanVersion.version_number.desc())
        .first()
    )

    previous_version_number = prev_version.version_number if prev_version else None
    diff_summary = (
        _diff_versions(prev_version.items, version.items)
        if previous_version
        else None
    )

    return StudyPlanVersionWithDiff(
        id=version.id,
        version_number=version.version_number,
        created_at=version.created_at,
        items=version.items,
        previous_version_number=previous_version_number,
        diff_summary=diff_summary,
    )


@router.post("/{plan_id}/update", response_model=StudyPlanOut)
def update_plan(
    plan_id: int,
    plan_update: StudyPlanUpdate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    if plan.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plan not found")

    new_version_number = plan.current_version + 1
    version = StudyPlanVersion(plan_id=plan.id, version_number=new_version_number)
    db.add(version)
    db.commit()
    db.refresh(version)

    for item in plan_update.items:
        db.add(StudyPlanItem(
            version_id=version.id,
            term=item.term,
            course_id=item.course_id,
            custom_code=item.custom_code,
            custom_title=item.custom_title,
            credits=item.credits,
        ))

    plan.current_version = new_version_number
    plan.title = plan_update.title
    plan.status = "draft"
    plan.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{plan_id}/submit")
def submit_plan(
    plan_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    if plan.student_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plan not found")
    plan.status = "pending"
    plan.updated_at = datetime.utcnow()
    db.commit()
    queue_director_notification("plan_submitted", plan_id, current_user.id)
    return {"ok": True}


@router.post("/{plan_id}/comments", response_model=CommentOut)
def add_comment(
    plan_id: int,
    comment: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    db_comment = Comment(
        plan_id=plan_id, author_id=current_user.id, text=comment.text
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    if current_user.role == "student":
        queue_director_notification(
            "comment_added", plan_id, current_user.id, comment.text
        )

    return db_comment


@router.post("/{plan_id}/decide")
def decide(
    plan_id: int,
    request: DecisionRequest,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)
    if request.decision not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400, detail="Decision must be approved or rejected"
        )

    plan.status = request.decision
    plan.updated_at = datetime.utcnow()
    db.commit()

    notify_student(plan.student.email, plan.title, request.decision, request.comment)

    if request.comment:
        db.add(Comment(
            plan_id=plan_id, author_id=current_user.id, text=request.comment
        ))
        db.commit()

    return {"ok": True}


@router.post("/{plan_id}/request-changes")
def request_changes(
    plan_id: int,
    request: DecisionRequest,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    plan = _get_plan_or_404(db, plan_id)

    plan.status = "changes_requested"
    plan.updated_at = datetime.utcnow()
    db.commit()

    notify_student(
        plan.student.email, plan.title, "changes_requested", request.comment
    )

    if request.comment:
        db.add(Comment(
            plan_id=plan_id, author_id=current_user.id, text=request.comment
        ))
        db.commit()

    return {"ok": True}

@router.get("/export/{term}")
def export_term_csv(
    term: str,
    current_user: User = Depends(require_role("director")),
    db: Session = Depends(get_db),
):
    plans = db.query(StudyPlan).all()

    course_codes = set()
    student_rows = []

    for plan in plans:
        latest = (
            db.query(StudyPlanVersion)
            .filter(StudyPlanVersion.plan_id == plan.id)
            .order_by(StudyPlanVersion.version_number.desc())
            .first()
        )
        if not latest:
            continue

        term_items = [
            i for i in latest.items
            if i.term == term and (i.course_id or i.custom_code)
        ]
        if not term_items:
            continue

        student = plan.student
        student_course_codes = set()

        for item in term_items:
            if item.course_id and item.course:
                student_course_codes.add(item.course.code)
            elif item.custom_code:
                student_course_codes.add(item.custom_code)

        course_codes.update(student_course_codes)

        admission_year = ""
        if plan.student.admission_term:
            parts = plan.student.admission_term.split()
            if parts:
                admission_year = parts[-1]

        student_rows.append({
            "personal_number": student.personal_number or "",
            "last_name": student.last_name or "",
            "first_name": student.first_name or "",
            "admission_year": admission_year,
            "tuition_paying": "yes" if student.tuition_paying else "no",
            "registration_complete": "yes" if student.registration_complete else "no",
            "courses": student_course_codes,
        })

    sorted_codes = sorted(course_codes)

    output = io.StringIO()
    writer = csv.writer(output)

    header = [
        "Personal number",
        "Last name",
        "First name",
        "Admission year",
        "Tuition paying",
        "Admission complete",
    ] + sorted_codes
    writer.writerow(header)

    for row in student_rows:
        csv_row = [
            row["personal_number"],
            row["last_name"],
            row["first_name"],
            row["admission_year"],
            row["tuition_paying"],
            row["registration_complete"],
        ] + ["X" if code in row["courses"] else "" for code in sorted_codes]
        writer.writerow(csv_row)

    filename = f"registrations_{term.replace(' ', '_')}.csv"

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
