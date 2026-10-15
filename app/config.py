from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_user: str = "news"
    postgres_password: str
    postgres_db: str = "news_sentiment"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")

    rss_feeds_raw: str = Field(
        default="http://feeds.bbci.co.uk/news/rss.xml", alias="RSS_FEEDS"
    )
    poll_interval_seconds: int = Field(default=300, alias="POLL_INTERVAL_SECONDS")
    sentiment_model: str = Field(
        default="cardiffnlp/twitter-roberta-base-sentiment-latest",
        alias="SENTIMENT_MODEL",
    )

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rss_feeds(self) -> list[str]:
        return [f.strip() for f in self.rss_feeds_raw.split(",") if f.strip()]


settings = Settings()
