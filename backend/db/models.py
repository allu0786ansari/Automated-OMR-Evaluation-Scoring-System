# backend/db/models.py
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from .session import Base
import datetime


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name = Column(String(256), nullable=True)
    role = Column(String(64), default="evaluator")  # evaluator/admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"
    exam_id = Column(String(128), primary_key=True, index=True)
    name = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Optional: metadata JSON for exam specifics
    metadata = Column(JSON, nullable=True)


class AnswerKey(Base):
    """
    Stores normalized answer keys per exam and version.
    Optionally you may keep the original Excel file in data/answer_keys/.
    """
    __tablename__ = "answer_keys"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(String(128), ForeignKey("exams.exam_id"), nullable=False)
    version = Column(String(8), nullable=False)  # 'A', 'B', ...
    question_number = Column(Integer, nullable=False)
    correct_answer = Column(String(8), nullable=False)


class Sheet(Base):
    __tablename__ = "sheets"
    sheet_id = Column(String(64), primary_key=True, index=True)
    exam_id = Column(String(128), ForeignKey("exams.exam_id"), nullable=False)
    student_id = Column(String(128), index=True, nullable=False)
    version = Column(String(8), nullable=True)
    original_path = Column(String(1024), nullable=True)
    warped_path = Column(String(1024), nullable=True)
    overlay_path = Column(String(1024), nullable=True)
    status = Column(String(32), default="pending")  # pending/processing/processed/flagged/error
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    result_id = Column(Integer, ForeignKey("results.id"), nullable=True)


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String(64), ForeignKey("sheets.sheet_id"), nullable=False, unique=True)
    exam_id = Column(String(128), ForeignKey("exams.exam_id"), nullable=False)
    student_id = Column(String(128), nullable=False)
    version = Column(String(8), nullable=True)
    # answers stored as {"1":"A", "2":"C", ...}
    answers = Column(JSON, nullable=False)
    # flags list: e.g. [{"q":3,"reason":"no_mark"}, ...]
    flags = Column(JSON, nullable=True)
    # per subject scores
    per_subject = Column(JSON, nullable=False)  # {"subject1":18,...}
    total = Column(Integer, nullable=False)
    confidence = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String(64), ForeignKey("sheets.sheet_id"), nullable=True)
    user = Column(String(128), nullable=True)
    action = Column(String(256), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
