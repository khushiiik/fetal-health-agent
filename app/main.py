from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.genai import types
from app.core.config import settings, get_llm
from app.api.endpoints import router as api_router

app = FastAPI()

app.include_router(api_router, prefix="/api")


class GeminiRequest(BaseModel):
    text: str


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "AI Fetal Health Assistant API is running"}


@app.post("/api/test-gemini")
async def test_gemini(request: GeminiRequest):
    """Test endpoint to generate content using the configured model."""
    try:
        from google.adk.models import LlmRequest
        model = get_llm()
        request_payload = LlmRequest(
            model=settings.GEMINI_MODEL,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=request.text)])]
        )
        
        response_text = ""
        async for chunk in model.generate_content_async(request_payload):
            if chunk.content and chunk.content.parts:
                text_parts = [part.text for part in chunk.content.parts if part.text]
                if text_parts:
                    response_text += "".join(text_parts)
                    
        return {"response": response_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
