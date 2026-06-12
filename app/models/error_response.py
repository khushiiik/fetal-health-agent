from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str
    message: str

class NotFound(BaseModel):
    fetus_id: str
    message: str = "No record found for the given fetus ID"