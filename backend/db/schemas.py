# backend/db/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List


# User
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = "evaluator"


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str

    class Config:
        orm_mode = True


# Sheet upload response
class SheetCreateResp(BaseModel):
    sheet_id: str
    status: str


# Result
class ResultOut(BaseModel):
    sheet_id: str
    exam_id: str
    student_id: str
    version: Optional[str]
    answers: Dict[str, Optional[str]]
    per_subject: Dict[str, int]
    total: int
    flags: Optional[List[Dict[str, Any]]]

    class Config:
        orm_mode = True
