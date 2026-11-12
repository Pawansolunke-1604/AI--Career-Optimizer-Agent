import logging

from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.career_agent import build_career_agent
from app.core.exceptions import LLMError, SessionNotFoundError
from app.schemas.chat import ChatResponse
from app.services.resume_service import render_markdown
from app.services.session_service import AnalysisSession, session_store

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Sorry, I could not come up with an answer. Could you rephrase your question?"


def summarize_turn(messages: list) -> tuple[str, list[str]]:
    """Return (final reply text, names of tools called during this turn)."""
    last_human = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    tools_used: list[str] = []
    for m in messages[last_human + 1:]:
        if isinstance(m, AIMessage):
               tools_used.extend(call["name"].replace(".", ":").split(":")[-1] for call in m.tool_calls)
            

    reply = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and not m.tool_calls and m.text.strip():
            reply = m.text.strip()
            break
    return reply or FALLBACK_REPLY, tools_used


def chat_with_session(session: AnalysisSession, message: str, model=None,
                      fallback_model=None) -> ChatResponse:
    session.user_messages.append(message)  # lets confirm_skill verify quotes against real user words
    agent = build_career_agent(session, model=model, fallback_model=fallback_model)
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config={"configurable": {"thread_id": session.session_id}, "recursion_limit": 12},
        )
    except Exception:
        logger.exception("Agent run failed")
        raise LLMError("The assistant is unavailable right now. Please try again.")
    reply, tools_used = summarize_turn(result["messages"])
    resume_markdown = None
    if "generate_optimized_resume" in tools_used and session.optimized_resume:
        resume_markdown = render_markdown(session.optimized_resume)
    return ChatResponse(session_id=session.session_id, reply=reply, tools_used=tools_used,
                        resume_markdown=resume_markdown)


async def chat(session_id: str, message: str) -> ChatResponse:
    session = session_store.get(session_id)
    if session is None:
        raise SessionNotFoundError("This analysis session has expired. Please analyze your resume again.")
    return await run_in_threadpool(chat_with_session, session, message)