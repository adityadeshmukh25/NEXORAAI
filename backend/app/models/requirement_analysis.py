
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class RequirementAnalysis(Base):
    __tablename__ = "requirement_analyses"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    original_requirements = Column(Text, nullable=False)

    analysis_result = Column(JSON, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    project = relationship(
        "Project",
        back_populates="requirement_analyses"
    )
