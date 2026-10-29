# AI Policy Assistant — RAG Upgrade

This release upgrades the existing `/api/v1/ai/ask` endpoint with **read-only, country-scoped, effective-date-filtered BM25 retrieval** over PostgreSQL leave and expense policy records, with source IDs and optional LLM generation. It does not create tables, change balances, or write to the database.

## Local setup (Windows CMD)

From `backend`:

```cmd
set "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/leave_expense_synthetic"
set "JWT_SECRET_KEY=your-existing-local-secret"
python -m uvicorn app.main:app --reload --port 8000
```

Log in through the frontend and open **AI Policy Assistant**. Example questions:
- What is my annual leave entitlement?
- Is a receipt required for travel expenses?
- What is the maximum consecutive sick leave?

Without an OpenAI API key the endpoint returns **retrieval-only** evidence and sources, not fabricated AI answers. For optional generated answers, set `OPENAI_API_KEY` in the backend environment before starting the server. The key must never be placed in the frontend or committed to Git.

## API

`POST /api/v1/ai/ask` with Bearer JWT and JSON `{ "question": "What is the annual leave entitlement?" }`. Returns `{ "answer": "...", "sources": [{"title": "...", "section": "Leave policy ..."}], "mode": "retrieval-only" | "llm-grounded" }`.

## Verification

```cmd
python -m pytest tests\test_ai_retrieval.py -q
```

Full pytest suite and database-backed integration tests should also be run in your local environment. This package was syntax-checked and retrieval-smoke-tested, but its full pytest suite could not be executed in the packaging environment because `pwdlib` is not installed there.

## Limitations

Retrieval is BM25-style lexical search (not embedding/vector similarity). Policy records are the knowledge base; PDF ingestion and vector embeddings can be added later. The LLM is instructed to cite source IDs, but answers must still be reviewed for accuracy; source IDs do not by themselves guarantee factual correctness. No policy decisions are delegated to the LLM.
