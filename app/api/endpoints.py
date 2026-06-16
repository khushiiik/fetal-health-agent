import json
import re
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.adk.models import LlmRequest
from google.adk.runners import InMemoryRunner
from google.genai import types
from loguru import logger

from app.agents.orchestrator import orchestrator
from app.core.config import get_llm, settings
from app.models.chat import ChatRequest, ChatResponse
from app.models.diagnostic_report import DiagnosticReport
from app.services.report_formatter import report_to_markdown

router = APIRouter()

# Global runner instance to preserve session histories in memory
runner = InMemoryRunner(node=orchestrator)
runner.auto_create_session = True

# Global session storage for reports mapping session_id -> DiagnosticReport
session_reports: dict[str, DiagnosticReport] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Run a single turn of the multi-agent chat workflow or answer follow-ups from cache."""
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Check if a fetus ID (e.g. FET-1001) is requested in the message
        fetus_id_match = re.search(r"FET-\d+", request.message.upper())

        # Follow-up query: If no fetus ID is in the message and we already have a cached report
        if not fetus_id_match and session_id in session_reports:
            cached_report = session_reports[session_id]
            model = get_llm()

            # Construct a small context-based prompt for the LLM
            prompt = (
                f"You are a clinical assistant. Answer the user's question based on the following diagnostic report.\n"
                f"Report Summary: {cached_report.summary}\n"
                f"Overall Classification: {cached_report.analysis.overall_classification}\n"
                f"Vitals Breakdown:\n"
            )
            for row in cached_report.vitals_breakdown:
                prompt += f"- {row.vital_name}: {row.measured_value} {row.unit} (normal: {row.reference_min}-{row.reference_max}) -> {row.status}\n"
            if cached_report.notes:
                prompt += f"Notes: {cached_report.notes}\n"
            prompt += f"\nUser Question: {request.message}\nAnswer:"

            request_payload = LlmRequest(
                model=getattr(model, "model", settings.GEMINI_MODEL),
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)],
                    )
                ],
            )

            answer_text = ""
            async for chunk in model.generate_content_async(request_payload):
                if chunk.content and chunk.content.parts:
                    text_parts = [
                        part.text for part in chunk.content.parts if part.text
                    ]
                    if text_parts:
                        answer_text += "".join(text_parts)

            return ChatResponse(
                session_id=session_id,
                report=cached_report,
                report_markdown=answer_text.strip(),
            )

        # New query: Run the workflow runner
        new_message = types.Content(parts=[types.Part.from_text(text=request.message)])
        events = runner.run_async(
            user_id="default_user",
            session_id=session_id,
            new_message=new_message,
        )

        events_list = []
        async for event in events:
            events_list.append(event)
        report_markdown = ""
        diagnostic_report = None

        # Traverse events backwards to extract the final agent response and structured report
        for event in reversed(events_list):
            if not diagnostic_report:
                for resp in event.get_function_responses():
                    if (
                        resp.name == "format_report"
                        or resp.name == "run_fetal_analysis"
                    ):
                        raw_response = resp.response
                        try:
                            if isinstance(raw_response, dict):
                                if "report" in raw_response:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        raw_response["report"]
                                    )
                                    if (
                                        "report_markdown" in raw_response
                                        and not report_markdown
                                    ):
                                        report_markdown = raw_response[
                                            "report_markdown"
                                        ]
                                else:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        raw_response
                                    )
                            elif isinstance(raw_response, DiagnosticReport):
                                diagnostic_report = raw_response
                            elif isinstance(raw_response, str):
                                parsed = json.loads(raw_response)
                                if isinstance(parsed, dict) and "report" in parsed:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        parsed["report"]
                                    )
                                    if (
                                        "report_markdown" in parsed
                                        and not report_markdown
                                    ):
                                        report_markdown = parsed["report_markdown"]
                                else:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        parsed
                                    )
                        except Exception:
                            logger.exception(
                                "Failed to validate DiagnosticReport from tool response"
                            )

        # Fallback/safety: generate markdown if missing but report is present
        if diagnostic_report and not report_markdown:
            report_markdown = report_to_markdown(diagnostic_report)

        # If no report was generated (e.g. error messages), fetch final text response
        if not report_markdown:
            for event in reversed(events_list):
                if event.content and event.content.parts:
                    text_parts = [
                        part.text for part in event.content.parts if part.text
                    ]
                    if text_parts:
                        report_markdown = "".join(text_parts).strip()
                        break

        # Cache the report if successfully generated
        if diagnostic_report:
            session_reports[session_id] = diagnostic_report

        return ChatResponse(
            session_id=session_id,
            report=diagnostic_report,
            report_markdown=report_markdown,
        )
    except Exception as e:
        logger.exception("Error during chat workflow execution")
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_event(event: Any) -> Dict[str, Any]:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    elif hasattr(event, "__dict__"):
        data: Dict[str, Any] = {
            "author": getattr(event, "author", "unknown"),
            "timestamp": getattr(event, "timestamp", 0.0),
        }
        content = getattr(event, "content", None)
        if content:
            parts = getattr(content, "parts", [])
            data["content"] = {
                "parts": [{"text": getattr(p, "text", "")} for p in parts]
            }
        func_resps: List[Any] = getattr(event, "get_function_responses", lambda: [])()
        if func_resps:
            parts_list: List[Any] = data.setdefault("content", {}).setdefault(
                "parts", []
            )
            for resp in func_resps:
                parts_list.append(
                    {
                        "function_response": {
                            "name": getattr(resp, "name", ""),
                            "response": getattr(resp, "response", None),
                        }
                    }
                )
        return data
    return {"message": str(event)}


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streams multi-agent pipeline events as NDJSON to the client."""
    session_id = request.session_id or str(uuid.uuid4())
    fetus_id_match = re.search(r"FET-\d+", request.message.upper())

    async def event_generator():
        try:
            # 1. Follow-up Query: Serve from cached report
            if not fetus_id_match and session_id in session_reports:
                cached_report = session_reports[session_id]
                model = get_llm()
                prompt = (
                    f"You are a clinical assistant. Answer the user's question based on the following diagnostic report.\n"
                    f"Report Summary: {cached_report.summary}\n"
                    f"Overall Classification: {cached_report.analysis.overall_classification}\n"
                    f"Vitals Breakdown:\n"
                )
                for row in cached_report.vitals_breakdown:
                    prompt += f"- {row.vital_name}: {row.measured_value} {row.unit} (normal: {row.reference_min}-{row.reference_max}) -> {row.status}\n"
                if cached_report.notes:
                    prompt += f"Notes: {cached_report.notes}\n"
                prompt += f"\nUser Question: {request.message}\nAnswer:"

                request_payload = LlmRequest(
                    model=getattr(model, "model", settings.GEMINI_MODEL),
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=prompt)],
                        )
                    ],
                )

                answer_text = ""
                async for chunk in model.generate_content_async(request_payload):
                    if chunk.content and chunk.content.parts:
                        text_parts = [
                            part.text for part in chunk.content.parts if part.text
                        ]
                        if text_parts:
                            chunk_text = "".join(text_parts)
                            answer_text += chunk_text
                            yield json.dumps(
                                {
                                    "type": "follow_up_chunk",
                                    "session_id": session_id,
                                    "chunk": chunk_text,
                                }
                            ) + "\n"

                yield json.dumps(
                    {
                        "type": "follow_up_complete",
                        "session_id": session_id,
                        "report": cached_report.model_dump(mode="json"),
                        "answer": answer_text.strip(),
                    }
                ) + "\n"
                return

            # 2. New Analysis: Run sequentially START -> sql_agent -> research_agent
            new_message = types.Content(
                parts=[types.Part.from_text(text=request.message)]
            )
            events = runner.run_async(
                user_id="default_user",
                session_id=session_id,
                new_message=new_message,
            )

            diagnostic_report = None
            report_markdown = ""
            events_list = []
            async for event in events:
                events_list.append(event)
                yield json.dumps(
                    {
                        "type": "event",
                        "session_id": session_id,
                        "data": _serialize_event(event),
                    }
                ) + "\n"

            # 3. Post-execution extraction
            for event in reversed(events_list):
                if not diagnostic_report:
                    for resp in event.get_function_responses():
                        if (
                            resp.name == "format_report"
                            or resp.name == "run_fetal_analysis"
                        ):
                            raw_response = resp.response
                            try:
                                if isinstance(raw_response, dict):
                                    if "report" in raw_response:
                                        diagnostic_report = (
                                            DiagnosticReport.model_validate(
                                                raw_response["report"]
                                            )
                                        )
                                        if (
                                            "report_markdown" in raw_response
                                            and not report_markdown
                                        ):
                                            report_markdown = raw_response[
                                                "report_markdown"
                                            ]
                                    else:
                                        diagnostic_report = (
                                            DiagnosticReport.model_validate(
                                                raw_response
                                            )
                                        )
                                elif isinstance(raw_response, DiagnosticReport):
                                    diagnostic_report = raw_response
                                elif isinstance(raw_response, str):
                                    parsed = json.loads(raw_response)
                                    if isinstance(parsed, dict) and "report" in parsed:
                                        diagnostic_report = (
                                            DiagnosticReport.model_validate(
                                                parsed["report"]
                                            )
                                        )
                                        if (
                                            "report_markdown" in parsed
                                            and not report_markdown
                                        ):
                                            report_markdown = parsed["report_markdown"]
                                    else:
                                        diagnostic_report = (
                                            DiagnosticReport.model_validate(parsed)
                                        )
                            except Exception:
                                pass

            if diagnostic_report and not report_markdown:
                report_markdown = report_to_markdown(diagnostic_report)

            if not report_markdown:
                for event in reversed(events_list):
                    if event.content and event.content.parts:
                        text_parts = [
                            part.text for part in event.content.parts if part.text
                        ]
                        if text_parts:
                            report_markdown = "".join(text_parts).strip()
                            break

            if diagnostic_report:
                session_reports[session_id] = diagnostic_report

            yield json.dumps(
                {
                    "type": "complete",
                    "session_id": session_id,
                    "report": (
                        diagnostic_report.model_dump(mode="json")
                        if diagnostic_report
                        else None
                    ),
                    "report_markdown": report_markdown,
                }
            ) + "\n"

        except Exception as e:
            logger.exception("Error in chat_stream event generator")
            yield json.dumps({"type": "error", "error": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
