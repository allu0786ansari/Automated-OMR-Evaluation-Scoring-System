# backend/db/models.py
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, ForeignKey
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

    # Relationship
    audit_logs = relationship("AuditLog", back_populates="user_ref")


class Exam(Base):
    __tablename__ = "exams"
    exam_id = Column(String(128), primary_key=True, index=True)
    name = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata = Column(JSON, nullable=True)  # optional JSON metadata

    # Relationships
    answer_keys = relationship("AnswerKey", back_populates="exam")
    sheets = relationship("Sheet", back_populates="exam")
    results = relationship("Result", back_populates="exam")


class AnswerKey(Base):
    __tablename__ = "answer_keys"
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(String(128), ForeignKey("exams.exam_id"), nullable=False)
    version = Column(String(8), nullable=False)  # 'A', 'B', ...
    question_number = Column(Integer, nullable=False)
    correct_answer = Column(String(8), nullable=False)

    # Relationship
    exam = relationship("Exam", back_populates="answer_keys")


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

    # Relationships
    exam = relationship("Exam", back_populates="sheets")
    result = relationship("Result", back_populates="sheet", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="sheet")


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String(64), ForeignKey("sheets.sheet_id"), nullable=False, unique=True)
    exam_id = Column(String(128), ForeignKey("exams.exam_id"), nullable=False)
    student_id = Column(String(128), nullable=False)
    version = Column(String(8), nullable=True)
    answers = Column(JSON, nullable=False)   # {"1": "A", "2": "C", ...}
    flags = Column(JSON, nullable=True)      # [{"q":3,"reason":"no_mark"}, ...]
    per_subject = Column(JSON, nullable=False)  # {"subject1":18, ...}
    total = Column(Integer, nullable=False)
    confidence = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    sheet = relationship("Sheet", back_populates="result")
    exam = relationship("Exam", back_populates="results")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    sheet_id = Column(String(64), ForeignKey("sheets.sheet_id"), nullable=True)
    user = Column(String(128), ForeignKey("users.username"), nullable=True)
    action = Column(String(256), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    sheet = relationship("Sheet", back_populates="audit_logs")
    user_ref = relationship("User", back_populates="audit_logs")
