from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[dict]
    messages_saved: int
