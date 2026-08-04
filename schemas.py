from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    code: str
    title: str
    credits: float
    term: str
    university: str


class CourseOut(BaseModel):
    id: int
    code: str
    title: str
    credits: float
    term: str
    university: str

    class Config:
        from_attributes = True


class StudyPlanItemIn(BaseModel):
    term: str
    course_id: Optional[int] = None
    custom_code: Optional[str] = None
    custom_title: Optional[str] = None
    credits: Optional[float] = None


class StudyPlanItemOut(BaseModel):
    id: int
    term: str
    course_id: Optional[int]
    custom_code: Optional[str]
    custom_title: Optional[str]
    credits: Optional[float]
    course: Optional[CourseOut]

    class Config:
        from_attributes = True


class StudyPlanVersionOut(BaseModel):
    id: int
    version_number: int
    created_at: datetime
    items: List[StudyPlanItemOut]

    class Config:
        from_attributes = True


class StudyPlanVersionWithDiff(BaseModel):
    id: int
    version_number: int
    created_at: datetime
    items: List[StudyPlanItemOut]
    previous_version_number: Optional[int]
    diff_summary: Optional[str]

    class Config:
        from_attributes = True


class CommentOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author: UserOut

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    text: str


class StudyPlanCreate(BaseModel):
    title: Optional[str] = None
    admission_term: Optional[str] = None
    items: List[StudyPlanItemIn]


class StudyPlanUpdate(BaseModel):
    title: Optional[str] = None
    admission_term: Optional[str] = None
    items: List[StudyPlanItemIn]


class StudyPlanOut(BaseModel):
    id: int
    student_id: int
    title: Optional[str]
    admission_term: Optional[str]
    status: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    student: UserOut
    versions: List[StudyPlanVersionOut]
    comments: List[CommentOut]

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

    class Config:
        from_attributes = True


class DecisionRequest(BaseModel):
    decision: str
    comment: Optional[str] = None
