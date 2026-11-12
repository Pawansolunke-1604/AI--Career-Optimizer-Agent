import time

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

s = get_settings()
candidates = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]

for name in candidates:
    start = time.perf_counter()
    try:
        llm = ChatGoogleGenerativeAI(
            model=name, google_api_key=s.google_api_key, max_retries=0, timeout=30
        )
        llm.invoke("Say hi")
        print(f"OK    {name}  {time.perf_counter() - start:.1f}s")
    except Exception as e:
        print(f"FAIL  {name}  {str(e)[:100]}")