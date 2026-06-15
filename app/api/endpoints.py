from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.models.diagnostic_report import DiagnosticReport
from app.agents.orchestrator import orchestrator
from google.adk.runners import InMemoryRunner
from google.genai import types
from loguru import logger
import uuid

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
        response_text = ""
        diagnostic_report = None

        # Traverse events backwards to extract the final agent response and structured report
        for event in reversed(events_list):
            if not response_text and event.content and event.content.parts:
                text_parts = [part.text for part in event.content.parts if part.text]
                if text_parts:
                    response_text = "".join(text_parts).strip()

            if not diagnostic_report:
                for resp in event.get_function_responses():
                    if resp.name == "format_report":
                        raw_response = resp.response
                        try:
                            if isinstance(raw_response, DiagnosticReport):
                                diagnostic_report = raw_response
                            elif isinstance(raw_response, dict):
                                diagnostic_report = DiagnosticReport.model_validate(
                                    raw_response
                                )
                            elif isinstance(raw_response, str):
                                diagnostic_report = (
                                    DiagnosticReport.model_validate_json(raw_response)
                                )
                        except Exception:
                            logger.exception(
                                "Failed to validate DiagnosticReport from tool response"
                            )

        return ChatResponse(
            session_id=session_id,
            response=response_text,
            report=diagnostic_report,
        )
    except Exception as e:
        logger.exception("Error during chat workflow execution")
        raise HTTPException(status_code=500, detail=str(e))
