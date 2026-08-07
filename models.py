from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Float,
    ForeignKey,
    DateTime,
    Text,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    personal_number = Column(String, unique=True, index=True, nullable=True)
    role = Column(String, default="student")
    hashed_password = Column(String, nullable=True)
    tuition_paying = Column(Boolean, default=False)
    registration_complete = Column(Boolean, default=False)

    plans = relationship("Plan", back_populates="student", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    admission_term = Column(String, nullable=True)
    status = Column(String, default="draft")
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("User", back_populates="plans")
    versions = relationship("PlanVersion", back_populates="plan", cascade="all, delete-orphan", order_by="desc(PlanVersion.version_number)")
    comments = relationship("Comment", back_populates="plan", cascade="all, delete-orphan", order_by="desc(Comment.created_at)")


class PlanVersion(Base):
    __tablename__ = "plan_versions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    previous_version_number = Column(Integer, nullable=True)
    diff_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("Plan", back_populates="versions")
    items = relationship("PlanItem", back_populates="version", cascade="all, delete-orphan")


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("plan_versions.id"), nullable=False)
    term = Column(String, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    custom_code = Column(String, nullable=True)
    custom_title = Column(String, nullable=True)
    credits = Column(Float, nullable=True)

    version = relationship("PlanVersion", back_populates="items")
    course = relationship("Course")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    university = Column(String, nullable=False)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    credits = Column(Float, nullable=False)
    term = Column(String, nullable=False)

    plan_items = relationship("PlanItem", back_populates="course")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("Plan", back_populates="comments")
    author = relationship("User", back_populates="comments")


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    recipient_role = Column(String, nullable=True)
