
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


if settings.database_url.startswith("sqlite:///"):
    db_path = settings.database_url.replace("sqlite:///", "", 1)

    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(settings.database_url)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models.project import Project
    from app.models.requirement_analysis import RequirementAnalysis
    from app.models.architecture_plan import ArchitecturePlan
    from app.models.code_generation import CodeGeneration
    from app.models.execution import CodeExecution
    from app.models.debugging import DebuggingSession
    from app.models.code_fix import CodeFix
    from app.models.repair_history import RepairHistory
    Base.metadata.create_all(bind=engine)
