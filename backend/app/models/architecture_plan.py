from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ArchitecturePlan(Base):
    __tablename__ = "architecture_plans"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    requirement_analysis_id = Column(
        Integer,
        ForeignKey("requirement_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    architecture_result = Column(
        JSON,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    project = relationship("Project")

    requirement_analysis = relationship(
        "RequirementAnalysis"
    )