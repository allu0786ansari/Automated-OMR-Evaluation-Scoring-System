# backend/services/export_service.py
from typing import List, Dict
import pandas as pd
import io
from pathlib import Path
from ..core.config import settings
from ..utils.logger import get_logger

logger = get_logger()


def generate_results_dataframe(results: List[Dict]) -> pd.DataFrame:
    """
    Normalize results list (from CRUD) into a flat DataFrame for export.
    """
    rows = []
    for r in results:
        row = {
            "sheet_id": r.get("sheet_id"),
            "exam_id": r.get("exam_id"),
            "student_id": r.get("student_id"),
            "version": r.get("version"),
            "total": r.get("total"),
            "confidence": r.get("confidence"),
            "created_at": r.get("created_at"),
        }
        per_subject = r.get("per_subject", {})
        for i in range(1, 6):
            row[f"subject{i}"] = per_subject.get(f"subject{i}", None)
        # flatten answers if needed as JSON string
        row["answers_json"] = str(r.get("answers", {}))
        rows.append(row)
    df = pd.DataFrame(rows)
    return df


def export_results_to_csv(results: List[Dict], exam_id: str) -> str:
    df = generate_results_dataframe(results)
    out_dir = Path(settings.RESULTS_EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"results_{exam_id}.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)


def export_results_to_excel_bytes(results: List[Dict]) -> bytes:
    df = generate_results_dataframe(results)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="results")
    stream.seek(0)
    return stream.read()
