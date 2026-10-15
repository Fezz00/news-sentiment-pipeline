# News Sentiment Pipeline

An end-to-end MLOps warm-up project: fetch live news via RSS, classify sentiment
with a pretrained Hugging Face model, store the results in Postgres, and serve
them through a FastAPI service — all runnable with one command.

## Architecture

```
RSS feeds --> ingestion worker --> Postgres <-- FastAPI --> clients
                (feedparser +        (articles       (/predict,
                 HF pipeline)         table)         /news/latest)
```

Three containers, three jobs. The API and the worker never call each other —
they communicate only through the database, so either can crash, restart, or be
rebuilt independently.

| Path | Role |
|---|---|
| `app/` | FastAPI service. Loads the sentiment model once and serves HTTP. |
| `ingestion/` | Worker loop: poll RSS feeds, score new articles, write to Postgres. |
| `scripts/rescore.py` | One-off maintenance: re-score every stored article with the currently configured model. |
| `tests/` | Pytest suite — runs without Docker, Postgres, or network access. |
| `docker-compose.yml` | Runs Postgres, the API, and the worker together. |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/predict` | `{"text": "..."}` → `{"label": "neutral", "score": 0.94}` |
| `GET` | `/news/latest?limit=20` | Most recent scored articles from the database |
| `GET` | `/health` | Liveness check |

Interactive API docs (Swagger UI) are served at `/docs`.

## Running locally

```bash
cd news-sentiment-pipeline
cp .env.example .env          # then edit POSTGRES_PASSWORD
docker compose up --build     # add -d to run in the background
```

The API is then on `http://localhost:8000`:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Stocks rally on strong earnings"}'

curl http://localhost:8000/news/latest
```

`/news/latest` is empty at first — the worker needs a minute to download the
model and complete its first RSS poll.

Common commands:

```bash
docker compose stop           # pause; `start` resumes with data intact
docker compose down           # stop and remove containers (volumes survive)
docker compose down -v        # also delete the database and model cache
docker compose logs -f api    # follow one service's logs
docker compose config         # validate the compose file and show resolved values
```

## Configuration

All configuration comes from environment variables, loaded from `.env` locally
and injected by Compose into the containers. See `.env.example` for the full
list.

| Variable | Default | Notes |
|---|---|---|
| `POSTGRES_PASSWORD` | — | **Required.** No default, so the app refuses to start without it. |
| `POSTGRES_USER` | `news` | |
| `POSTGRES_DB` | `news_sentiment` | |
| `POSTGRES_HOST` | `localhost` | Compose overrides this to `db` for the containers. |
| `POSTGRES_PORT` | `5432` | |
| `DATABASE_URL` | — | Optional override. If set, it wins over the variables above — which is what lets hosting platforms (Coolify, Heroku, Neon) inject a connection string directly. |
| `RSS_FEEDS` | BBC News | Comma-separated list of feed URLs. |
| `POLL_INTERVAL_SECONDS` | `300` | How often the worker polls. |
| `SENTIMENT_MODEL` | `cardiffnlp/twitter-roberta-base-sentiment-latest` | Any Hugging Face sentiment model. |

## The model

`cardiffnlp/twitter-roberta-base-sentiment-latest` — a **3-class** model
(`positive` / `neutral` / `negative`) trained on short social-media-style text.

The three-class part matters. An earlier version used
`distilbert-base-uncased-finetuned-sst-2-english`, which is **binary** —
trained on movie reviews with no neutral option. Given a factual headline it was
forced to pick a side, and did so confidently:

| Headline | Binary model | 3-class model |
|---|---|---|
| "What Is Umami?" | negative 1.00 | neutral 0.94 |
| "Police officer's funeral to take place after crash" | positive 1.00 | negative 0.75 |
| "Fetching AMD SEV Reports (With Zig)" | negative 1.00 | neutral 0.93 |

Swapping models is a one-line change in `.env`. Existing rows keep their old
labels, so run `scripts/rescore.py` afterwards to re-score history:

```bash
docker compose exec -T api python < scripts/rescore.py
```

## Running tests

Tests substitute an in-memory SQLite database for Postgres and a stub for the
sentiment model, so they need no Docker, no database, and no network:

```bash
cp .env.example .env          # required: POSTGRES_PASSWORD has no default
python -m venv .venv && source .venv/bin/activate
pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
pytest
```

## Design notes

- **Separate API and worker** so a failing RSS source degrades the data to
  *stale* rather than taking the API down.
- **Model loaded once** per process via `@lru_cache`, not per request. The
  Hugging Face cache is a shared Docker volume, so the API and worker download
  it once between them and keep it across container recreations.
- **Thin HTTP layer.** `app/main.py` holds almost no logic — validation lives in
  `app/schemas.py`, persistence in `app/db.py`, inference in `app/sentiment.py`.
  That separation is why the worker and the test suite can reuse everything
  except the HTTP layer.
- **Routes are sync, not `async def`.** Model inference is CPU-bound and
  blocking; FastAPI runs sync routes in a threadpool, so one slow prediction
  doesn't stall the event loop.
- **Secrets have no defaults.** Non-secret settings (host, port, database name)
  get convenient defaults; the password deliberately does not, so a
  misconfigured environment fails loudly at startup instead of falling back to a
  guessable value.
- **Duplicate protection in two layers** — an in-memory set catches repeats
  within one polling cycle (real feeds do repeat URLs), a database query catches
  repeats across cycles, and a `UNIQUE` constraint on `url` guarantees
  correctness if both are bypassed.

## Known limitations / next steps

- `/health` only proves the process is answering; it doesn't check the database.
  A readiness check would run `SELECT 1` and return 503 when Postgres is
  unreachable.
- No schema migrations. `Base.metadata.create_all()` creates missing tables but
  never alters existing ones, so changing a column needs Alembic.
- No `restart:` policy in Compose — if the worker process died, Docker would not
  revive it.
- The worker uses a plain `while True: ... sleep()` loop rather than a scheduler
  (APScheduler, Celery beat), so the interval drifts and there's no retry/backoff.
- `feedparser`'s `bozo` flag isn't checked, so a malformed or unreachable feed
  silently yields zero articles.
- Raw feed payloads are discarded after parsing. Since an RSS feed is a moving
  window, fields we didn't extract are unrecoverable — archiving the raw
  response would make results recomputable.
- Predictions run one at a time; Hugging Face pipelines support batching.
- No auth or rate limiting on `/predict`.
- No model/prediction versioning, so nothing records which model scored a row.
