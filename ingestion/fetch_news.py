import logging
import time
from datetime import datetime, timezone

import feedparser

from app.config import settings
from app.db import Base, SessionLocal, engine
from app.models import Article
from app.sentiment import get_analyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingestion")


def clean_text(raw: str) -> str:
    return " ".join(raw.split())


def fetch_once() -> None:
    analyzer = get_analyzer()
    db = SessionLocal()
    seen_urls = set()
    try:
        for feed_url in settings.rss_feeds:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                url = entry.get("link")
                if not url or url in seen_urls:
                    continue
                if db.query(Article).filter_by(url=url).first():
                    continue
                seen_urls.add(url)

                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", ""))
                text_for_model = f"{title}. {summary}".strip()
                label, score = analyzer.predict(text_for_model or title)

                published_struct = entry.get("published_parsed")
                published_at = (
                    datetime(*published_struct[:6], tzinfo=timezone.utc)
                    if published_struct
                    else None
                )

                tags = entry.get("tags")
                category = tags[0].get("term") if tags else None

                db.add(
                    Article(
                        title=title,
                        content=summary,
                        url=url,
                        source=feed.feed.get("title", feed_url),
                        category=category,
                        published_at=published_at,
                        sentiment_label=label,
                        sentiment_score=score,
                    )
                )
                logger.info("Stored: %s [%s %.2f]", title, label, score)
        db.commit()
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    while True:
        try:
            fetch_once()
        except Exception:
            logger.exception("Ingestion cycle failed")
        time.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    main()
