# backend/db/crud.py
import asyncio
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from . import models
from .session import get_db
from sqlalchemy import select, insert
from ..utils.logger import get_logger

logger = get_logger()

# NOTE: All functions are async but internally run sync DB calls in threadpool using asyncio.to_thread
# This keeps the FastAPI route code using await intact.


async def create_user(db: Session, username: str, hashed_password: str, full_name: str = None, role: str = "evaluator"):
    def _create():
        user = models.User(username=username, hashed_password=hashed_password, full_name=full_name, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return await asyncio.to_thread(_create)


async def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    def _get():
        return db.query(models.User).filter(models.User.username == username).first()
    return await asyncio.to_thread(_get)


async def create_exam(db: Session, exam_id: str, name: str = None, metadata: dict = None):
    def _create():
        exam = models.Exam(exam_id=exam_id, name=name, exam_metadata=metadata)
        db.add(exam)
        db.commit()
        db.refresh(exam)
        return exam
    return await asyncio.to_thread(_create)


async def get_exam(db: Session, exam_id: str) -> Optional[models.Exam]:
    def _get():
        return db.query(models.Exam).filter(models.Exam.exam_id == exam_id).first()
    return await asyncio.to_thread(_get)


async def create_sheet_record(db: Session, sheet_id: str, exam_id: str, student_id: str, version: Optional[str], original_path: str):
    def _create():
        sheet = models.Sheet(
            sheet_id=sheet_id,
            exam_id=exam_id,
            student_id=student_id,
            version=version,
            original_path=original_path,
            status="pending"
        )
        db.add(sheet)
        db.commit()
        db.refresh(sheet)
        return sheet
    return await asyncio.to_thread(_create)


async def update_sheet_status(db: Session, sheet_id: str, status: str, processed_at=None):
    def _update():
        sheet = db.query(models.Sheet).filter(models.Sheet.sheet_id == sheet_id).first()
        if not sheet:
            return None
        sheet.status = status
        if processed_at:
            sheet.processed_at = processed_at
        db.add(sheet)
        db.commit()
        db.refresh(sheet)
        return sheet
    return await asyncio.to_thread(_update)


async def update_sheet_paths(db: Session, sheet_id: str, warped_path: str = None, overlay_path: str = None):
    def _update():
        sheet = db.query(models.Sheet).filter(models.Sheet.sheet_id == sheet_id).first()
        if not sheet:
            return None
        if warped_path:
            sheet.warped_path = warped_path
        if overlay_path:
            sheet.overlay_path = overlay_path
        db.add(sheet)
        db.commit()
        db.refresh(sheet)
        return sheet
    return await asyncio.to_thread(_update)


async def create_result_record(db: Session, sheet_id: str, exam_id: str, student_id: str, version: Optional[str],
                               answers: Dict[str, Optional[str]], per_subject: Dict[str, int], total: int, flags: List[Dict] = None, confidence: str = None):
    def _create():
        result = models.Result(
            sheet_id=sheet_id,
            exam_id=exam_id,
            student_id=student_id,
            version=version,
            answers=answers,
            per_subject=per_subject,
            total=total,
            flags=flags or [],
            confidence=confidence
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        # update sheet.result_id and status
        sheet = db.query(models.Sheet).filter(models.Sheet.sheet_id == sheet_id).first()
        if sheet:
            sheet.result_id = result.id
            sheet.status = "processed"
            db.add(sheet)
        db.commit()
        return result
    return await asyncio.to_thread(_create)


async def get_sheet_by_id(db: Session, sheet_id: str) -> Optional[models.Sheet]:
    def _get():
        return db.query(models.Sheet).filter(models.Sheet.sheet_id == sheet_id).first()
    return await asyncio.to_thread(_get)


async def get_result_by_sheet(db: Session, sheet_id: str) -> Optional[dict]:
    def _get():
        res = db.query(models.Result).filter(models.Result.sheet_id == sheet_id).first()
        if not res:
            return None
        return {
            "sheet_id": res.sheet_id,
            "exam_id": res.exam_id,
            "student_id": res.student_id,
            "version": res.version,
            "answers": res.answers,
            "per_subject": res.per_subject,
            "total": res.total,
            "flags": res.flags,
            "confidence": res.confidence,
            "created_at": res.created_at.isoformat()
        }
    return await asyncio.to_thread(_get)


async def get_results_by_exam(db: Session, exam_id: str) -> List[dict]:
    def _get():
        rows = db.query(models.Result).filter(models.Result.exam_id == exam_id).all()
        outputs = []
        for r in rows:
            outputs.append({
                "sheet_id": r.sheet_id,
                "exam_id": r.exam_id,
                "student_id": r.student_id,
                "version": r.version,
                "answers": r.answers,
                "per_subject": r.per_subject,
                "total": r.total,
                "flags": r.flags,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat()
            })
        return outputs
    return await asyncio.to_thread(_get)


# AnswerKey helpers - used if you persist keys to DB (optional)
async def bulk_upsert_answer_keys_from_list(db: Session, exam_id: str, version: str, kv_list: List[dict]):
    """
    kv_list: [{"question_number":1,"correct_answer":"A"}, ...]
    """
    def _op():
        # delete existing for exam+version then insert
        db.query(models.AnswerKey).filter(models.AnswerKey.exam_id == exam_id, models.AnswerKey.version == version).delete()
        for kv in kv_list:
            ak = models.AnswerKey(exam_id=exam_id, version=version, question_number=kv["question_number"], correct_answer=kv["correct_answer"])
            db.add(ak)
        db.commit()
        return True
    return await asyncio.to_thread(_op)


async def get_answer_key_from_db(db: Session, exam_id: str, version: str) -> Optional[dict]:
    def _get():
        rows = db.query(models.AnswerKey).filter(models.AnswerKey.exam_id == exam_id, models.AnswerKey.version == version).order_by(models.AnswerKey.question_number.asc()).all()
        if not rows:
            return None
        return {str(r.question_number): r.correct_answer for r in rows}
    return await asyncio.to_thread(_get)


async def log_audit(db: Session, sheet_id: str, user: str, action: str, comment: str = None):
    def _log():
        entry = models.AuditLog(sheet_id=sheet_id, user=user, action=action, comment=comment)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    return await asyncio.to_thread(_log)
