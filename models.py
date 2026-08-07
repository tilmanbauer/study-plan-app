from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


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


    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False)
    title = Column(String, nullable=False)
    credits = Column(Float, nullable=False)
    term = Column(String, nullable=False)
    university = Column(String, nullable=False, default="KTH")

    def __repr__(self) -> str:
        return f"<Course id={self.id} code={self.code} term={self.term}>"


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    admission_term = Column(String, nullable=True)
    status = Column(String, default="draft")
    current_version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("User", back_populates="plans")
    versions = relationship(
        "StudyPlanVersion",
        back_populates="plan",
        order_by="desc(StudyPlanVersion.version_number)",
    )
    comments = relationship(
        "Comment", back_populates="plan", order_by="desc(Comment.created_at)"
    )

    def __repr__(self) -> str:
        return f"<StudyPlan id={self.id} status={self.status}>"


class StudyPlanVersion(Base):
    __tablename__ = "study_plan_versions"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("StudyPlan", back_populates="versions")
    items = relationship("StudyPlanItem", back_populates="version")

    def __repr__(self) -> str:
        return f"<StudyPlanVersion plan_id={self.plan_id} v={self.version_number}>"


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("study_plan_versions.id"), nullable=False)
    term = Column(String, nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    custom_code = Column(String, nullable=True)
    custom_title = Column(String, nullable=True)
    credits = Column(Float, nullable=True)

    version = relationship("StudyPlanVersion", back_populates="items")
    course = relationship("Course")

    def __repr__(self) -> str:
        return f"<StudyPlanItem id={self.id} term={self.term}>"


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("StudyPlan", back_populates="comments")
    author = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment id={self.id} plan_id={self.plan_id}>"


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # plan_submitted, comment_added
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    recipient_role = Column(String, nullable=False, default="director")

    def __repr__(self) -> str:
        return f"<NotificationEvent id={self.id} type={self.type}>"
