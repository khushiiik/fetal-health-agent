from pydantic import BaseModel
from typing import Optional
from app.models.diagnostic_report import DiagnosticReport


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    report: Optional[DiagnosticReport] = None
