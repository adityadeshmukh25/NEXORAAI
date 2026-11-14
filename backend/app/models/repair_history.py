from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from app.database import Base


class RepairHistory(Base):
    __tablename__ = "repair_histories"

    id = Column(Integer, primary_key=True, index=True)

    generation_id = Column(
        Integer,
        ForeignKey("code_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(String(50), default="pending", nullable=False)

    attempts = Column(Integer, default=0, nullable=False)

    initial_errors = Column(JSON, default=list, nullable=False)

    attempt_details = Column(JSON, default=list, nullable=False)

    summary = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    completed_at = Column(DateTime, nullable=True)