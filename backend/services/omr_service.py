# backend/services/omr_service.py
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple, List

from ..core.config import settings
from ..utils.image_utils import load_image, rectify_perspective, compute_fill_ratio, save_overlay_image
from ..db import crud
from ..db.session import get_db
from ..utils.logger import get_logger
from ..services.scoring_service import score_answers

logger = get_logger()


async def process_sheet(file_path: str, sheet_id: str, exam_id: str, version: Optional[str], settings_obj=settings):
    """
    Main entry to process a saved image file:
      - Rectify perspective
      - Load template JSON (required)
      - Evaluate bubbles -> answers dict
      - Score using scoring_service
      - Save overlay and processed images
      - Persist result via crud.create_result_record
    """
    # Ensure template exists for the exam (template JSON expected at data/answer_keys/{exam_id}_template.json)
    template_path = Path(settings_obj.ANSWER_KEYS_DIR) / f"{exam_id}_template.json"
    if not template_path.exists():
        raise FileNotFoundError(f"Template file for exam '{exam_id}' not found at {template_path}. Please provide a template JSON mapping question -> bboxes.")

    # load template
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    # template expected structure:
    # {"questions": [{"q":1, "options":[{"id":"A","bbox":[x,y,w,h]}, ...]}, ...], "canvas_size":[W,H]}

    # load image
    img = load_image(file_path)
    # rectify/perspective warp to canonical canvas defined by template (optional)
    canvas_size = tuple(template.get("canvas_size", (1240, 1754)))
    warped = rectify_perspective(img, canvas_size)

    answers = {}
    flags: List[Dict] = []
    per_question_scores = {}  # store fill ratio per opt for transparency

    # Evaluate each question
    for qmeta in template["questions"]:
        qid = str(qmeta["q"])
        opt_scores = {}
        for opt in qmeta["options"]:
            opt_id = opt["id"]
            x, y, w, h = opt["bbox"]
            # crop ROI from warped image (grayscale inside)
            ratio = compute_fill_ratio(warped, x, y, w, h)
            opt_scores[opt_id] = float(ratio)
        # decide best option
        sorted_opts = sorted(opt_scores.items(), key=lambda kv: kv[1], reverse=True)
        best_opt, best_score = sorted_opts[0]
        second_score = sorted_opts[1][1] if len(sorted_opts) > 1 else 0.0

        # heuristics
        if best_score < 0.12:
            answers[qid] = None
            flags.append({"q": int(qid), "reason": "no_mark", "score": best_score})
        elif best_score - second_score < 0.10:
            # ambiguous but pick best_opt - also flag
            answers[qid] = best_opt
            flags.append({"q": int(qid), "reason": "ambiguous", "scores": [best_score, second_score]})
        else:
            answers[qid] = best_opt

        per_question_scores[qid] = opt_scores

    # score answers
    scoring = await score_answers(exam_id=exam_id, version=version, detected_answers=answers, settings_obj=settings_obj)

    per_subject = scoring["per_subject"]
    total = scoring["total"]
    confidence = scoring.get("confidence", "n/a")

    # save overlay image
    overlay_path = Path(settings_obj.OVERLAY_DIR) / f"{sheet_id}_overlay.jpg"
    save_overlay_image(warped, template, answers, str(overlay_path))

    # save warped path
    warped_path = Path(settings_obj.PROCESSED_DIR) / f"{sheet_id}_warped.jpg"
    warped_path.parent.mkdir(parents=True, exist_ok=True)
    # write warped as jpg
    import cv2
    cv2.imwrite(str(warped_path), warped)

    # persist results using DB
    # need DB session: use dependency context manager get_db()
    from ..db.session import SessionLocal
    db = SessionLocal()
    try:
        # update sheet paths & status
        await crud.update_sheet_paths(db, sheet_id, warped_path=str(warped_path), overlay_path=str(overlay_path))
        result = await crud.create_result_record(
            db=db,
            sheet_id=sheet_id,
            exam_id=exam_id,
            student_id=scoring.get("student_id", ""),  # scoring_service may not know student id; API had it earlier
            version=version,
            answers=answers,
            per_subject=per_subject,
            total=total,
            flags=flags,
            confidence=str(confidence)
        )
        # update processed timestamp
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
    }
