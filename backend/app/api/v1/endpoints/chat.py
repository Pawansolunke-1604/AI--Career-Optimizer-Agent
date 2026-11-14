from fastapi import APIRouter, Depends

from app.core.rate_limit import rate_limit
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat

router = APIRouter(prefix="/chat")


@router.post("", response_model=ChatResponse,
             dependencies=[Depends(rate_limit("chat", per_ip=20, window_s=600, global_limit=15))])
async def chat_endpoint(body: ChatRequest):
    return await chat(body.session_id, body.message)