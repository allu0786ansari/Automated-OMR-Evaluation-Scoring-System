# backend/services/scoring_service.py
from typing import Dict, Optional
import pandas as pd
from pathlib import Path
from ..core.config import settings
from ..utils.logger import get_logger

logger = get_logger()


async def score_answers(exam_id: str, version: Optional[str], detected_answers: Dict[str, Optional[str]], settings_obj=settings) -> Dict:
    """
    Compare detected_answers (dict qnum->'A'/'B'/None) with answer key.
    Loads answer key from Excel at data/answer_keys/{exam_id}_keys.xlsx (sheet_name=version) by default.
    Returns dict: {"per_subject": {...}, "total": N}
    """

    # locate keys file
    keys_path_xlsx = Path(settings_obj.ANSWER_KEYS_DIR) / f"{exam_id}_keys.xlsx"
    if not keys_path_xlsx.exists():
        # fallback: maybe per-exam file named exam1.xlsx or single file with exam name
        raise FileNotFoundError(f"Answer key file not found at {keys_path_xlsx}. Please place Excel with sheets named A/B in answer_keys directory.")

    if not version:
        # default to sheet 'A' if not provided
        version = "A"

    try:
        df = pd.read_excel(keys_path_xlsx, sheet_name=version, engine="openpyxl")
    except Exception as e:
        logger.error(f"Failed reading answer key: {e}")
        raise

    # expected columns: Question, Answer
    if "Question" not in df.columns or "Answer" not in df.columns:
        # try first two columns fallback
        df = df.iloc[:, :2]
        df.columns = ["Question", "Answer"]

    # build key map
    key_map = {str(int(row["Question"])): str(row["Answer"]).strip() for _, row in df.iterrows()}

    # scoring: per-subject 20 questions each:
    # subject1: 1-20, subject2:21-40, subject3:41-60, subject4:61-80, subject5:81-100
    per_subject = {"subject1": 0, "subject2": 0, "subject3": 0, "subject4": 0, "subject5": 0}
    total = 0
    for qnum_str, detected in detected_answers.items():
        if qnum_str not in key_map:
            # ignore (template might have extra)
            continue
        correct = key_map[qnum_str]
        # compare
        if detected is not None and str(detected).strip().upper() == str(correct).strip().upper():
            # determine subject
            qnum = int(qnum_str)
            if 1 <= qnum <= 20:
                per_subject["subject1"] += 1
            elif 21 <= qnum <= 40:
                per_subject["subject2"] += 1
            elif 41 <= qnum <= 60:
                per_subject["subject3"] += 1
            elif 61 <= qnum <= 80:
                per_subject["subject4"] += 1
            elif 81 <= qnum <= 100:
                per_subject["subject5"] += 1
            total += 1

    # Optionally compute confidence as ratio of answered questions / 100
    answered = sum(1 for v in detected_answers.values() if v is not None)
    confidence = f"{answered}/100"

    return {"per_subject": per_subject, "total": total, "confidence": confidence}
