# backend/api/results.py
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
import pandas as pd

from ..db.session import get_db
from ..db import crud  # implement functions like get_result_by_sheet, get_results_by_exam
from ..services.export_service import generate_results_csv  # implement later

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/sheet/{sheet_id}")
async def get_result_by_sheet(sheet_id: str, db: Session = Depends(get_db)):
    """
    Return result JSON for a processed sheet.
    """
    res = await crud.get_result_by_sheet(db, sheet_id)
    if not res:
        raise HTTPException(status_code=404, detail="Result not found")
    return JSONResponse(content=res)


@router.get("/exam/{exam_id}")
async def get_results_by_exam(exam_id: str, db: Session = Depends(get_db)):
    """
    Return list of results for an exam.
    """
    results = await crud.get_results_by_exam(db, exam_id)
    return JSONResponse(content={"exam_id": exam_id, "count": len(results), "results": results})


@router.get("/export/{exam_id}")
async def export_results(exam_id: str, format: str = "csv", db: Session = Depends(get_db)):
    """
    Export results for exam in CSV or Excel.
    """
    results = await crud.get_results_by_exam(db, exam_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results for this exam")

    # create DataFrame
    df = pd.DataFrame(results)

    if format.lower() == "csv":
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        headers = {
            'Content-Disposition': f'attachment; filename="results_{exam_id}.csv"'
        }
        return StreamingResponse(iter([stream.getvalue()]),
                                 media_type="text/csv",
                                 headers=headers)
    elif format.lower() in ("xls", "xlsx", "excel"):
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="results")
        stream.seek(0)
        headers = {
            'Content-Disposition': f'attachment; filename="results_{exam_id}.xlsx"'
        }
        return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers=headers)
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use csv or xlsx.")
