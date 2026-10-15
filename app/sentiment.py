from functools import lru_cache

from transformers import pipeline

from app.config import settings


class SentimentAnalyzer:
    def __init__(self, model_name: str):
        self._pipeline = pipeline("sentiment-analysis", model=model_name)

    def predict(self, text: str) -> tuple[str, float]:
        result = self._pipeline(text[:512])[0]
        return result["label"].lower(), float(result["score"])


@lru_cache
def get_analyzer() -> SentimentAnalyzer:
    return SentimentAnalyzer(settings.sentiment_model)
