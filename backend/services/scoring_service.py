# backend/services/scoring_service.py
from typing import Dict, Optional
import pandas as pd
from pathlib import Path
from core.config import settings
from utils.logger import get_logger

logger = get_logger()


def _normalize_sheet_name(version: str) -> str:
    """
    Accept different version name inputs and map to sheet name in Excel.
    E.g., "A", "SET-A", "SET A" -> "A"
    """
    if not version:
        return "A"
    v = str(version).upper().strip()
    v = v.replace("SET", "").replace("-", "").replace(" ", "")
    # if after removals it's empty, fallback to A
    return v if v else "A"


async def score_answers(exam_id: str, version: Optional[str], detected_answers: Dict[str, Optional[str]], settings_obj=settings) -> Dict:
    """
    Compare detected_answers (dict qnum->'A'/'B'/None) with answer key.
    Loads answer key from Excel at data/answer_keys/{exam_id}_keys.xlsx (sheet_name=version) by default.
    Returns dict: {"per_subject": {...}, "total": N}
    """
    keys_path_xlsx = Path(settings_obj.ANSWER_KEYS_DIR) / f"{exam_id}_keys.xlsx"
    if not keys_path_xlsx.exists():
        # try alternative filename without suffix
        alt = Path(settings_obj.ANSWER_KEYS_DIR) / f"{exam_id}.xlsx"
        if alt.exists():
            keys_path_xlsx = alt
        else:
            raise FileNotFoundError(f"Answer key file not found at {keys_path_xlsx}. Please place Excel with sheets named A/B in answer_keys directory.")

    # decide sheet name
    sheet_name = _normalize_sheet_name(version) if version else "A"

    # read list of sheet names to handle lowercase or variants
    try:
        xls = pd.ExcelFile(keys_path_xlsx, engine="openpyxl")
        available_sheets = [s.upper().replace(" ", "").replace("-", "") for s in xls.sheet_names]
        normalized_available = {s.upper().replace(" ", "").replace("-", ""): orig for orig, s in zip(xls.sheet_names, xls.sheet_names)}
        # find best match
        norm_requested = sheet_name.upper().replace(" ", "").replace("-", "")
        if norm_requested in normalized_available:
            actual_sheet_name = normalized_available[norm_requested]
        else:
            # fallback to first sheet
            actual_sheet_name = xls.sheet_names[0]
            logger.info(f"Requested sheet {sheet_name} not found; falling back to first sheet {actual_sheet_name}")
        df = pd.read_excel(keys_path_xlsx, sheet_name=actual_sheet_name, engine="openpyxl")
    except Exception as e:
        logger.error(f"Failed reading answer key Excel: {e}")
        raise

    # standardize columns
    if "Question" not in df.columns or "Answer" not in df.columns:
        df = df.iloc[:, :2]
        df.columns = ["Question", "Answer"]

    key_map = {str(int(row["Question"])): str(row["Answer"]).strip().upper() for _, row in df.iterrows()}

    # scoring logic: 1-20 => subject1, 21-40 => subject2, ...
    per_subject = {"subject1": 0, "subject2": 0, "subject3": 0, "subject4": 0, "subject5": 0}
    total = 0
    for qnum_str, detected in detected_answers.items():
        if qnum_str not in key_map:
            continue
        correct = key_map[qnum_str]
        if detected is not None and str(detected).strip().upper() == correct:
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

    answered = sum(1 for v in detected_answers.values() if v is not None)
    confidence = f"{answered}/100"
    return {"per_subject": per_subject, "total": total, "confidence": confidence}
