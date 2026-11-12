from fastapi import FastAPI
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppError

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
app.include_router(api_router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message})