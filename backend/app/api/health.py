
from fastapi import APIRouter

from app.config import settings
from app.services.ollama_service import ollama_service

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version
    }


@router.get("/ollama/status")
async def ollama_status():
    return await ollama_service.check_connection()
