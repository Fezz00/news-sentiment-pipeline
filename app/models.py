from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String, unique=True, nullable=False, index=True)
    source = Column(String, nullable=True)
    category = Column(String, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    sentiment_label = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
