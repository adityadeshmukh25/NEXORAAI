from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.database import Base


class DebuggingSession(Base):
    __tablename__ = "debugging_sessions"

    id = Column(Integer, primary_key=True, index=True)

    generation_id = Column(
        Integer,
        ForeignKey("code_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    execution_id = Column(
        Integer,
        ForeignKey("code_executions.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    error_summary = Column(Text, nullable=True)

    root_cause = Column(Text, nullable=True)

    suggested_fix = Column(Text, nullable=True)

    corrected_code = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    completed_at = Column(DateTime, nullable=True)