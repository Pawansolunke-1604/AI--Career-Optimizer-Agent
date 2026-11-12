# TODO: api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import health
from app.api.v1.endpoints import analysis
from app.api.v1.endpoints import chat
from app.api.v1.endpoints import resumes


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(resumes.router, tags=["resumes"])
