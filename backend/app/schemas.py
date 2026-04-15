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


class PasswordLoginRequest(BaseModel):
    username: str
    password: str


class VerifyLoginCodeResponse(BaseModel):
    email: str
    role: str
    verified: bool


class ConversationSummary(BaseModel):
    conversation_id: int
    title: str
    created_at: str
    updated_at: str


class ConversationMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    sources: list[dict]


class ConversationDetail(BaseModel):
    conversation_id: int
    title: str
    created_at: str
    updated_at: str
    messages: list[ConversationMessage]
