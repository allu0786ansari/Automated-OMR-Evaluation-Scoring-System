# backend/services/omr_service.py
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple, List

from core.config import settings
from utils.Image_utils import load_image, rectify_perspective, compute_fill_ratio, save_overlay_image, detect_version_from_header_image
from db import crud
from utils.logger import get_logger
from services.scoring_service import score_answers

logger = get_logger()


async def process_sheet(file_path: str, sheet_id: str, exam_id: str, version: Optional[str], student_id: str = None, settings_obj=settings):
    """
    Process saved image file:
      - Rectify perspective
      - Detect version from header if not provided
      - Load template JSON (required)
      - Evaluate bubbles -> answers dict
      - Score using scoring_service
      - Save overlay and processed images
      - Persist result via crud.create_result_record
    """
    template_path = Path(settings_obj.ANSWER_KEYS_DIR) / f"{exam_id}_template.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template file for exam '{exam_id}' not found at {template_path}.")

    # load template
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    canvas_size = tuple(template.get("canvas_size", (1240, 1754)))

    # load image
    img = load_image(file_path)
    warped = rectify_perspective(img, canvas_size)

    # if version not given, try OCR on header
    detected_version = version
    if not detected_version:
        try:
            v = detect_version_from_header_image(warped)
            if v:
                detected_version = v
                logger.info(f"Detected version '{detected_version}' from header OCR for sheet {sheet_id}")
            else:
                logger.info(f"No version detected by OCR for sheet {sheet_id}; defaulting to A")
                detected_version = "A"
        except Exception as e:
            logger.warning(f"Header OCR failed for sheet {sheet_id}: {e}")
            detected_version = "A"

    answers = {}
    flags: List[Dict] = []
    per_question_scores = {}

    for qmeta in template["questions"]:
        qid = str(qmeta["q"])
        opt_scores = {}
        for opt in qmeta["options"]:
            opt_id = opt["id"]
            x, y, w, h = opt["bbox"]
            ratio = compute_fill_ratio(warped, x, y, w, h)
            opt_scores[opt_id] = float(ratio)
        sorted_opts = sorted(opt_scores.items(), key=lambda kv: kv[1], reverse=True)
        best_opt, best_score = sorted_opts[0]
        second_score = sorted_opts[1][1] if len(sorted_opts) > 1 else 0.0

        if best_score < 0.12:
            answers[qid] = None
            flags.append({"q": int(qid), "reason": "no_mark", "score": best_score})
        elif best_score - second_score < 0.10:
            answers[qid] = best_opt
            flags.append({"q": int(qid), "reason": "ambiguous", "scores": [best_score, second_score]})
        else:
            answers[qid] = best_opt

        per_question_scores[qid] = opt_scores

    # Score using scoring_service (pass detected_version)
    scoring = await score_answers(exam_id=exam_id, version=detected_version, detected_answers=answers, settings_obj=settings_obj)

    per_subject = scoring["per_subject"]
    total = scoring["total"]
    confidence = scoring.get("confidence", "n/a")

    # save overlay image
    overlay_path = Path(settings_obj.OVERLAY_DIR) / f"{sheet_id}_overlay.jpg"
    save_overlay_image(warped, template, answers, str(overlay_path))

    warped_path = Path(settings_obj.PROCESSED_DIR) / f"{sheet_id}_warped.jpg"
    warped_path.parent.mkdir(parents=True, exist_ok=True)
    import cv2
    cv2.imwrite(str(warped_path), warped)

    # Persist in DB: update sheet paths, create result record with student_id
    from ..db.session import SessionLocal
    db = SessionLocal()
    try:
        await crud.update_sheet_paths(db, sheet_id, warped_path=str(warped_path), overlay_path=str(overlay_path))
        # create result record — pass provided student_id (if None, fallback to sheet record value)
        sheet_record = await crud.get_sheet_by_id(db, sheet_id)
        sid = student_id or (sheet_record.student_id if sheet_record else "")
        result = await crud.create_result_record(
            db=db,
            sheet_id=sheet_id,
            exam_id=exam_id,
            student_id=sid,
            version=detected_version,
            answers=answers,
            per_subject=per_subject,
            total=total,
            flags=flags,
            confidence=str(confidence)
        )
        await crud.update_sheet_status(db, sheet_id, "processed", processed_at=datetime.utcnow())
    finally:
        db.close()

    return {
        "sheet_id": sheet_id,
        "answers": answers,
        "per_subject": per_subject,
        "total": total,
        "flags": flags,
        "confidence": confidence,
        "overlay_path": str(overlay_path),
        "warped_path": str(warped_path),
        "version_used": detected_version,
    }
