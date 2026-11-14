from fastapi import APIRouter
from ..services.ollama_service import get_ollama_status

router = APIRouter(prefix="/api/ollama", tags=["Ollama"])

@router.get("/status")
async def ollama_status():
    return await get_ollama_status()
