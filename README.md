# P105

A claim-level article review app. It splits pasted text into claims, searches the web with Tavily, asks an OpenAI-compatible model to compare the search snippets with each claim, and shows the cited sources. It is a research aid, not an authoritative fake-news detector: sources can be wrong, duplicated, or incomplete.

## Configure providers

The app needs a Tavily API key for search and an OpenAI API key for source assessment. Copy `.env.example` to `.env` and fill in the keys. `OPENAI_BASE_URL` can point to an OpenAI-compatible API; `OPENAI_MODEL` selects its model. `TAVILY_TOPIC` accepts `general` or `news`.

If either provider is not configured, affected claims return `uncertain`. Do not commit `.env` or send API keys to the browser.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --env-file .env
```

Open <http://127.0.0.1:8000> for the interface, <http://127.0.0.1:8000/docs> for the API schema, and <http://127.0.0.1:8000/healthz> for the process health check.

## Verdict policy

- Each article is limited to the first 8 extracted claims to bound provider calls.
- Search snippets are treated as untrusted content and are sent to the configured model for claim-by-claim assessment.
- `supported` or `refuted` requires relevant assessments from at least 2 distinct source hosts. Conflicting support and contradiction yields `mixed`; insufficient evidence yields `uncertain`.
- The displayed confidence is model-estimated, not a calibrated probability. Distinct hostnames do not guarantee independent reporting; inspect the linked sources.
- Claim text is sent to Tavily and the configured model provider. Do not submit sensitive or private material unless your provider terms and privacy policy permit it.

## API

`POST /analyze`

```json
{"text": "Paste article text here."}
```

The response includes the overall verdict, per-claim rationale, confidence note, review signals, and source title, URL, excerpt, and publication date when available.

## Tests

```powershell
python -m pytest -q
```

Tests use mocked provider responses and do not need API keys or internet access.

## Docker deployment

Copy `.env.example` to `.env`, configure provider keys, then run:

```powershell
docker compose up --build
```

The container runs as a non-root user and exposes a health check. On a hosting platform, set the same environment variables using its secret manager and build from the `Dockerfile`. Before exposing this API publicly, put it behind authentication and rate limiting to prevent unauthorized provider usage; use HTTPS and configure a privacy notice for submitted text.
