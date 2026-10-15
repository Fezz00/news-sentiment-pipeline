from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    label: str
    score: float


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    source: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None
    sentiment_label: Optional[str] = None
    sentiment_score: Optional[float] = None
