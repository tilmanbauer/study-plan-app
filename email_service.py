import logging
import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from sqlalchemy.orm import Session

from database import SessionLocal
from models import NotificationEvent, User

logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"


def _send_email(to: str, subject: str, body: str) -> None:
    if not SMTP_HOST or not SMTP_FROM:
        print("\n" + "=" * 60)
        print(f"EMAIL TO: {to}")
        print(f"SUBJECT: {subject}")
        print("-" * 60)
        print(body)
        print("=" * 60 + "\n")
        logger.info(f"Email logged for {to}: {subject}")
        return

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            if SMTP_TLS:
                server.starttls()
                server.ehlo()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise


def notify_student(student_email: str, plan_title: str, event_type: str,
                   comment: str = None) -> None:
    subjects = {
        "approved": "Your study plan has been approved",
        "rejected": "Your study plan has been rejected",
        "changes_requested": "Changes requested for your study plan",
    }
    subject = subjects.get(event_type, "Update on your study plan")

    status_text = event_type.replace("_", " ")
    body = (
        f"Your study plan '{plan_title}' has been {status_text}."
        if plan_title
        else f"Your study plan has been {status_text}."
    )

    if comment:
        body += f"\n\nComment from director:\n{comment}"

    _send_email(student_email, subject, body)


def queue_director_notification(
    event_type: str,
    plan_id: int,
    student_id: int,
    comment_text: str = None,
) -> None:
    db = SessionLocal()
    try:
        event = NotificationEvent(
            type=event_type,
            plan_id=plan_id,
            student_id=student_id,
            comment_text=comment_text,
            created_at=datetime.utcnow(),
            recipient_role="director",
        )
        db.add(event)
        db.commit()
    finally:
        db.close()


def _format_event_summary(db: Session, events: List[NotificationEvent]) -> str:
    submissions = [e for e in events if e.type == "plan_submitted"]
    comments = [e for e in events if e.type == "comment_added"]

    lines = []
    if submissions:
        lines.append(f"New submissions: {len(submissions)}")
        for e in submissions:
            student = db.query(User).filter(User.id == e.student_id).first()
            lines.append(
                f"  - Plan #{e.plan_id} by {student.name if student else 'Unknown'}"
            )

    if comments:
        lines.append(f"New comments: {len(comments)}")
        for e in comments:
            student = db.query(User).filter(User.id == e.student_id).first()
            lines.append(
                f"  - Plan #{e.plan_id} by {student.name if student else 'Unknown'}: {e.comment_text or ''}"
            )

    return "\n".join(lines) if lines else "No new activity."


def send_director_daily_summary() -> None:
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=1)
        events = (
            db.query(NotificationEvent)
            .filter(
                NotificationEvent.sent_at == None,
                NotificationEvent.created_at >= since,
            )
            .all()
        )

        if not events:
            print("No director notifications to send today.")
            return

        directors = db.query(User).filter(User.role == "director").all()
        if not directors:
            print("No directors found to send summary.")
            return

        summary = _format_event_summary(db, events)
        subject = "Daily summary: new study plan activity"

        for director in directors:
            body = f"Hello {director.name},\n\nHere is the daily summary of study plan activity:\n\n{summary}\n\nPlease log in to review."
            _send_email(director.email, subject, body)

        for event in events:
            event.sent_at = datetime.utcnow()
        db.commit()
        print(
            f"Sent daily summary to {len(directors)} director(s) for {len(events)} event(s)."
        )
    finally:
        db.close()
