from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import Article
from app.schemas import ArticleOut, PredictRequest, PredictResponse
from app.sentiment import get_analyzer


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="News Sentiment API", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    label, score = get_analyzer().predict(payload.text)
    return PredictResponse(label=label, score=score)


@app.get("/news/latest", response_model=list[ArticleOut])
def latest_news(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(Article)
        .order_by(desc(Article.published_at))
        .limit(limit)
        .all()
    )
