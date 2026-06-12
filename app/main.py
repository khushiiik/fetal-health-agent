from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai.errors import ClientError
from app.core.config import settings

app = FastAPI()

class GeminiRequest(BaseModel):
    text: str

@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "AI Fetal Health Assistant API is running"}

@app.post("/api/test-gemini")
def test_gemini(request: GeminiRequest):
    """Test endpoint to generate content using Gemini model."""
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=400, detail="GEMINI_API_KEY not configured")

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=request.text
        )
        return {"response": response.text}
    except ClientError as e:
        raise HTTPException(status_code=getattr(e, "code", 500), detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))