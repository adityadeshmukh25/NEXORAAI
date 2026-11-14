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
from sqlalchemy.orm import relationship

from app.database import Base


class CodeGeneration(Base):
    __tablename__ = "code_generations"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    architecture_plan_id = Column(
        Integer,
        ForeignKey("architecture_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status = Column(
        String(50),
        default="pending",
        nullable=False
    )

    summary = Column(Text, nullable=True)

    generated_files = Column(
        JSON,
        default=list,
        nullable=False
    )

    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    project = relationship("Project")

    architecture_plan = relationship("ArchitecturePlan")