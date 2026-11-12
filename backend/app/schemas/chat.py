from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tools_used: list[str] = Field(default_factory=list)  # which tools the agent called this turn
    resume_markdown: str | None = None  # set when the agent generated a resume this turn