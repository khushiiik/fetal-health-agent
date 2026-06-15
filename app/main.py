import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai.errors import ClientError
from app.core.config import settings
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
def test_gemini(request: GeminiRequest):
    """Test endpoint to generate content using Gemini model."""
    try:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            project_id = settings.GOOGLE_CLOUD_PROJECT or "fetal-health-agent"
            model_name = f"projects/{project_id}/locations/us-central1/publishers/google/models/{settings.GEMINI_MODEL}"
            client = genai.Client(vertexai=True)
        else:
            model_name = settings.GEMINI_MODEL
            client = genai.Client()
        response = client.models.generate_content(
            model=model_name, contents=request.text
        )
        return {"response": response.text}
    except ClientError as e:
        raise HTTPException(status_code=getattr(e, "code", 500), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
