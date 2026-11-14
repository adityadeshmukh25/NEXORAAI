
from contextlib import asynccontextmanager
from app.api import architecture
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import health, projects, requirements
from app.api import code_generation
from app.api.code_fixes import router as code_fixes_router
from app.api.debugging import router as debugging_router
from app.api.execution import router as execution_router
from app.api.repair import router as repair_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous AI Software Engineer API",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(requirements.router, prefix="/api")
app.include_router(architecture.router, prefix="/api")
app.include_router(execution_router)
app.include_router(debugging_router)
app.include_router(code_fixes_router)
app.include_router(repair_router, prefix="/api")
app.include_router(
    code_generation.router,
    prefix="/api"
)

@app.get("/")
async def root():
    return {
        "message": "Autonomous AI Software Engineer API is running",
        "version": settings.app_version
    }
