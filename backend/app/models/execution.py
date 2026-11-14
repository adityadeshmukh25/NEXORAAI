
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
)

from app.database import Base


class CodeExecution(Base):
    __tablename__ = "code_executions"

    id = Column(Integer, primary_key=True, index=True)

    generation_id = Column(
        Integer,
        ForeignKey("code_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    command = Column(Text, nullable=True)

    exit_code = Column(Integer, nullable=True)

    stdout = Column(Text, nullable=True)

    stderr = Column(Text, nullable=True)

    execution_time = Column(Float, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    started_at = Column(DateTime, nullable=True)

    finished_at = Column(DateTime, nullable=True)
