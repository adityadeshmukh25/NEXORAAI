
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


class CodeFix(Base):

    __tablename__ = "code_fixes"

    id = Column(Integer, primary_key=True, index=True)

    generation_id = Column(
        Integer,
        ForeignKey("code_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    debugging_session_id = Column(
        Integer,
        ForeignKey("debugging_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_path = Column(Text, nullable=False)

    original_code = Column(Text, nullable=False)

    corrected_code = Column(Text, nullable=False)

    status = Column(
        String(30),
        default="pending",
        nullable=False,
    )

    backup_path = Column(Text, nullable=True)

    rejection_reason = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    reviewed_at = Column(DateTime, nullable=True)

    applied_at = Column(DateTime, nullable=True)
