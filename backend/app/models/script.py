from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.video_project import current_utc_time

class Script(Base):
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    script_text = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    estimated_duration = Column(Integer, default=0)
    hook = Column(String, nullable=True)
    payoff = Column(String, nullable=True)
    status = Column(String, default="DRAFT")
    created_at = Column(DateTime(timezone=True), default=current_utc_time)

    project = relationship("VideoProject", back_populates="scripts")
