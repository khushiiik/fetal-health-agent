from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.models.diagnostic_report import DiagnosticReport
from app.agents.orchestrator import orchestrator
from google.adk.runners import InMemoryRunner
from google.genai import types
from loguru import logger
import uuid
import json
from app.services.report_formatter import report_to_markdown

router = APIRouter()

# Global runner instance to preserve session histories in memory
runner = InMemoryRunner(node=orchestrator)
runner.auto_create_session = True


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Run a single turn of the multi-agent chat workflow."""
    try:
        session_id = request.session_id or str(uuid.uuid4())
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
            if not report_markdown and event.content and event.content.parts:
                text_parts = [part.text for part in event.content.parts if part.text]
                if text_parts:
                    report_markdown = "".join(text_parts).strip()

            if not diagnostic_report:
                for resp in event.get_function_responses():
                    if resp.name == "format_report":
                        raw_response = resp.response
                        try:
                            if isinstance(raw_response, dict):
                                if "report" in raw_response:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        raw_response["report"]
                                    )
                                    if "report_markdown" in raw_response and not report_markdown:
                                        report_markdown = raw_response["report_markdown"]
                                else:
                                    diagnostic_report = DiagnosticReport.model_validate(
                                        raw_response
                                    )
                            elif isinstance(raw_response, DiagnosticReport):
                                diagnostic_report = raw_response
                            elif isinstance(raw_response, str):
                                parsed = json.loads(raw_response)
                                if isinstance(parsed, dict) and "report" in parsed:
                                    diagnostic_report = DiagnosticReport.model_validate(parsed["report"])
                                    if "report_markdown" in parsed and not report_markdown:
                                        report_markdown = parsed["report_markdown"]
                                else:
                                    diagnostic_report = DiagnosticReport.model_validate(parsed)
                        except Exception:
                            logger.exception(
                                "Failed to validate DiagnosticReport from tool response"
                            )

        # Fallback/safety: generate markdown if missing but report is present
        if diagnostic_report and not report_markdown:
            report_markdown = report_to_markdown(diagnostic_report)

        return ChatResponse(
            session_id=session_id,
            report=diagnostic_report,
            report_markdown=report_markdown,
        )
    except Exception as e:
        logger.exception("Error during chat workflow execution")
        raise HTTPException(status_code=500, detail=str(e))
