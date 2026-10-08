from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    customer_id: str = "cus_1001"


class ToolCall(BaseModel):
    name: str
    args: dict
    result: dict


class Source(BaseModel):
    doc: str
    section: str
    score: float


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[ToolCall] = []
    sources: list[Source] = []
    escalated: bool = False
    awaiting_confirmation: bool = False
