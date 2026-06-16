from fastapi import FastAPI
from app.api.endpoints import router as api_router

app = FastAPI()

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"message": "AI Fetal Health Assistant API is running"}
