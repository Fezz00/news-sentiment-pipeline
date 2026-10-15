"""Re-score every stored article using the currently configured model."""

from app.db import SessionLocal
from app.models import Article
from app.sentiment import get_analyzer


def main() -> None:
    analyzer = get_analyzer()
    db = SessionLocal()
    try:
        articles = db.query(Article).all()
        print(f"re-scoring {len(articles)} articles...")

        changed = 0
        for article in articles:
            text = f"{article.title}. {article.content or ''}".strip()
            label, score = analyzer.predict(text)

            if article.sentiment_label != label:
                changed += 1
                print(f"  {article.sentiment_label:8} -> {label:8}  {article.title[:55]}")

            article.sentiment_label = label
            article.sentiment_score = score

        db.commit()
        print(f"done: {changed} of {len(articles)} labels changed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
