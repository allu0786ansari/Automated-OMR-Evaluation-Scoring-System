# backend/api/omr.py
import io
import uuid
import shutil
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.session import get_db
from ..db import crud  # implement later: create_sheet_record, update_sheet_status, get_sheet_by_id
from ..services import omr_service  # implement later: process_sheet(file_path, sheet_id, exam_id, version)
from ..db.models import Sheet  # model placeholder

router = APIRouter(prefix="/omr", tags=["omr"])


@router.post("/upload", status_code=201)
async def upload_omr_sheet(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_id: str = Form(...),
    student_id: str = Form(...),
    version: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user=Depends(lambda: None),  # placeholder for auth dependency; replace with get_current_active_user
):
    """
    Upload an OMR sheet image. Returns a sheet_id. Processing is done in background.
    Required form fields: exam_id, student_id. Optional: version (A/B).
    """
    # Basic validation
    if file.content_type.split("/")[0] != "image":
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # create a unique sheet id
    sheet_id = str(uuid.uuid4())

    # save file to disk
    upload_path = settings.UPLOAD_DIR / f"{sheet_id}_{file.filename}"
    with upload_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # create DB record (status = pending)
    # Implement crud.create_sheet_record(db, sheet_id, exam_id, student_id, version, original_path)
    await crud.create_sheet_record(
        db=db,
        sheet_id=sheet_id,
        exam_id=exam_id,
        student_id=student_id,
        version=version,
        original_path=str(upload_path),
    )

    # enqueue background task to process the sheet
    background_tasks.add_task(
        _process_sheet_background, str(upload_path), sheet_id, exam_id, version
    )

    return {"sheet_id": sheet_id, "status": "queued"}


async def _process_sheet_background(file_path: str, sheet_id: str, exam_id: str, version: Optional[str]):
    """
    wrapper for calling the service to process the sheet.
    Uses the omr_service to process and will update DB via crud functions.
    """
    try:
        # process_sheet should save processed images and results to DB via crud
        result = await omr_service.process_sheet(file_path, sheet_id, exam_id, version, settings)
        # result expected: dict with answers, per_subject scores, total, flags, paths, confidence
        # update DB record to processed
        # await crud.update_sheet_result(db, sheet_id, result)
        # We do not have db here; omr_service should persist results itself or crud functions should be imported
    except Exception as e:
        # Ideally update DB with error state
        try:
            # await crud.update_sheet_status_error(db, sheet_id, str(e))
            pass
        finally:
            # Logging omitted here, but should log
            print(f"Error processing sheet {sheet_id}: {e}")


@router.get("/status/{sheet_id}")
async def get_sheet_status(sheet_id: str, db: Session = Depends(get_db)):
    """
    Get processing status of a sheet.
    """
    sheet = await crud.get_sheet_by_id(db, sheet_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")
    return {"sheet_id": sheet_id, "status": sheet.status, "processed_at": sheet.processed_at}


@router.get("/overlay/{sheet_id}")
async def get_overlay_image(sheet_id: str, db: Session = Depends(get_db)):
    """
    Return overlay image (if available) for human review.
    """
    sheet = await crud.get_sheet_by_id(db, sheet_id)
    if not sheet:
        raise HTTPException(status_code=404, detail="Sheet not found")
    overlay_path = sheet.overlay_path if hasattr(sheet, "overlay_path") else None
    if not overlay_path:
        raise HTTPException(status_code=404, detail="Overlay not available")
    return FileResponse(overlay_path, media_type="image/jpeg", filename=f"{sheet_id}_overlay.jpg")
