from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import String, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()
class School(Base):
    __tablename__ = 'schools'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str | None] = mapped_column(ForeignKey('schools.id'), index=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[str]
    class_name: Mapped[str | None]
    active: Mapped[bool] = mapped_column(default=True)
class Teaching(Base):
    __tablename__ = 'teacher_assignments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    teacher_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'))
    class_name: Mapped[str]
    subject: Mapped[str]
    __table_args__ = (UniqueConstraint('teacher_id', 'class_name', 'subject'),)
class Lesson(Base):
    __tablename__ = 'lessons'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    class_name: Mapped[str]
    subject: Mapped[str]
    title: Mapped[str]
    topic: Mapped[str]
    objectives: Mapped[str]
    content: Mapped[str]
    status: Mapped[str] = mapped_column(default='draft')
class Assessment(Base):
    __tablename__ = 'assessments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_id: Mapped[str] = mapped_column(ForeignKey('schools.id'), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    class_name: Mapped[str]
    subject: Mapped[str]
    title: Mapped[str]
    kind: Mapped[str]
    instructions: Mapped[str]
    questions: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(default='draft')
    due_at: Mapped[str | None]
    max_score: Mapped[int] = mapped_column(default=100)
    attempts_allowed: Mapped[int] = mapped_column(default=1)
class Submission(Base):
    __tablename__ = 'submissions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(unique=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey('assessments.id'), index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[float | None]
    feedback: Mapped[str] = mapped_column(default='')
    released: Mapped[bool] = mapped_column(default=False)
    submitted_at: Mapped[str] = mapped_column(default=now)
class Progress(Base):
    __tablename__ = 'lesson_progress'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    student_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    lesson_id: Mapped[str] = mapped_column(ForeignKey('lessons.id'))
    __table_args__ = (UniqueConstraint('student_id', 'lesson_id'),)
class Refresh(Base):
    __tablename__ = 'refresh_tokens'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    expires: Mapped[int]
class DemoRequest(Base):
    __tablename__ = 'demo_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    school_name: Mapped[str]
    contact: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str]
    location: Mapped[str]
    students: Mapped[int]
    preferred_date: Mapped[str]
    message: Mapped[str]
class Audit(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str]
    created_at: Mapped[str] = mapped_column(default=now)
