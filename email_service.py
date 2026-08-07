import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.orm import Session
from database import SessionLocal
from models import NotificationEvent, User
from config import EMAIL_ENABLED

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@kth.se")


def _send_email(to: str, subject: str, body: str) -> None:
    if not EMAIL_ENABLED:
        print(f"[EMAIL] To: {to}\nSubject: {subject}\n{body}\n")
        return

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
        print(f"Email sent to {to}: {subject}")
    except Exception as e:
        print(f"Failed to send email to {to}: {e}")



def notify_student(student_email: str, plan_id: int, message: str) -> None:
    subject = f"Update on your study plan #{plan_id}"
    body = f"Hello,\n\n{message}\n\nLog in to review your plan."
    _send_email(student_email, subject, body)


def notify_directors(director_emails: List[str], plan_id: int, student_name: str, message: str) -> None:
    subject = f"Study plan #{plan_id} update"
    body = f"Hello,\n\n{student_name} has updated study plan #{plan_id}.\n\n{message}\n\nLog in to review."
    for email in director_emails:
        _send_email(email, subject, body)


def _format_event_summary(db: Session, events: List[NotificationEvent]) -> str:
    submissions = [e for e in events if e.type == "plan_submitted"]
    comments = [e for e in events if e.type == "comment_added"]

    def _user_name(user):
        if not user:
            return "Unknown"
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        if user.first_name:
            return user.first_name
        return user.email

    lines = []
    if submissions:
        lines.append(f"New submissions: {len(submissions)}")
        for e in submissions:
            student = db.query(User).filter(User.id == e.student_id).first()
            lines.append(f"  - Plan #{e.plan_id} by {_user_name(student)}")

    if comments:
        lines.append(f"New comments: {len(comments)}")
        for e in comments:
            student = db.query(User).filter(User.id == e.student_id).first()
            lines.append(f"  - Plan #{e.plan_id} by {_user_name(student)}: {e.comment_text or ''}")

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
            name = director.first_name or director.email
            body = f"Hello {name},\n\nHere is the daily summary of study plan activity:\n\n{summary}\n\nPlease log in to review."
            _send_email(director.email, subject, body)

        for event in events:
            event.sent_at = datetime.utcnow()
        db.commit()
        print(f"Sent daily summary to {len(directors)} director(s) for {len(events)} event(s).")
    finally:
        db.close()
