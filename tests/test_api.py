import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app.db import Base, get_db
from app.models import Article

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


main_module.app.dependency_overrides[get_db] = override_get_db


class DummyAnalyzer:
    def predict(self, text):
        return "positive", 0.99


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(main_module, "engine", test_engine)
    monkeypatch.setattr(main_module, "get_analyzer", lambda: DummyAnalyzer())


@pytest.fixture
def client():
    with TestClient(main_module.app) as c:
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict(client):
    response = client.post("/predict", json={"text": "Great news today!"})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "positive"
    assert body["score"] == pytest.approx(0.99)


def test_latest_news_empty(client):
    response = client.get("/news/latest")
    assert response.status_code == 200
    assert response.json() == []


def test_latest_news_returns_articles(client):
    db = TestingSessionLocal()
    db.add(
        Article(
            title="Sample",
            content="Body",
            url="https://example.com/1",
            source="Example",
            sentiment_label="positive",
            sentiment_score=0.9,
        )
    )
    db.commit()
    db.close()

    response = client.get("/news/latest")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Sample"
