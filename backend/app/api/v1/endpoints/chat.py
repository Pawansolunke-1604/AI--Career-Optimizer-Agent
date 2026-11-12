from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest):
    return await chat(body.session_id, body.message)