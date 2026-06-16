from typing import Optional

from pydantic import BaseModel

from app.models.diagnostic_report import DiagnosticReport


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    report: Optional[DiagnosticReport] = None
    report_markdown: Optional[str] = None
